from fastapi import APIRouter, Request, Depends, status, WebSocket, WebSocketDisconnect, WebSocketException
from fastapi.responses import JSONResponse
from db.database import direct_get_conn, context_get_conn
from typing import Dict
from schemas import fita_schemas
from fastapi.exceptions import HTTPException
from sqlalchemy import text, Connection
from sqlalchemy.exc import SQLAlchemyError
from services import fita_svc
import asyncio

# about Location/Anchors - 실시간 위치 업데이트, 최단 경로 계산,
# 경로 이탈 판단, 대피 완료 판단, 엘리베이터 경고, 사용자 위치별 GUID 반환
router = APIRouter(prefix="/loc", tags=["loc"])
active_connections: Dict[str, WebSocket] = {}

# ----- 실시간 위치 업데이트, 엘리베이터 경고, 대피 완료 판단, 유저 패닉 감지 -----

@router.websocket("/{userID}")
async def current_loc(websocket: WebSocket, userID: str):
    await websocket.accept()
    active_connections[userID] = websocket
    db_gen = context_get_conn()
    conn = next(db_gen)
    try:
        trial = 0
        while True:
            try:
            # 유저 패닉 감지 (15초 기준)
                loc = await asyncio.wait_for(websocket.receive_json(), timeout=15.0)
            
            except asyncio.TimeoutError:
                # 유저 패닉 감지 시
                await websocket.send_json({"status": "error", "message": "user panic", "time": -10})
                trial += 1
                if trial < 3:
                    continue
                else:
                    await websocket.sned_json({"status": "error", "message": "user panic three times"})
                    await websocket.close()
                    break
            except WebSocketDisconnect:
                print(f"User {userID} is disconnected.")
                active_connections.pop(userID, None)

            if "uuid" not in loc:
                await websocket.send_json({"status": "error", "message": "no data"})
                continue
            uuid = loc.get("uuid")
            fita_svc.update_user(conn, userID, uuid)
            anchor = fita_svc.get_loc(conn, uuid)

            # 엘리베이터 경고
            if anchor.anchorTYPE == "elevator":
                await websocket.send_json({"status":200, "anchortype": "elevator", "message": "elevator warning"})

            # 대피 완료 판단
            if anchor.anchorTYPE == "exit":
                await websocket.send_json({"status":200, "anchortype": "exit", "message": "excape success"})

            # 층별 guid 로드 (shared anchor 이후 추가 구현)
            if anchor.anchorNUM == 68 or anchor.anchorNUM == 79:
                await websocket.send_json({"status": 200, "guid": "", "message": "next floor"})

    except WebSocketDisconnect:
        print(f"User {userID} is disconnected.")
        active_connections.pop(userID, None)

    except WebSocketException as e:
        print(f"system error: {e}")
        await websocket.send_json({"status": "error", "message": str(e)})