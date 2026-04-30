from fastapi import APIRouter, Request, Depends, status, WebSocket, WebSocketDisconnect, WebSocketException
from fastapi.responses import JSONResponse
from db.database import direct_get_conn, context_get_conn
from typing import Dict
from schemas import fita_schemas
from fastapi.exceptions import HTTPException
from sqlalchemy import text, Connection
from sqlalchemy.exc import SQLAlchemyError
from services import fita_svc, fire_func
import asyncio

# about Location/Anchors - 실시간 위치 업데이트, 최단 경로 계산,
# 경로 이탈 판단, 대피 완료 판단, 엘리베이터 경고, 사용자 위치별 GUID 반환
router = APIRouter(prefix="/loc", tags=["loc"])
active_connections: Dict[str, WebSocket] = {}

# ----- 실시간 위치 업데이트, 엘리베이터 경고, 대피 완료 판단, 유저 패닉 감지 -----


guid = ["0",
        "f17a0001-0000-0000-0000-000000000001",
        "f17a0002-0000-0000-0000-000000000002",
        "f17a0003-0000-0000-0000-000000000003",
        "f17a0004-0000-0000-0000-000000000004",
        "f17a0005-0000-0000-0000-000000000005",
        "f17a0005-0000-0000-0000-000000000006",
        "f17a0005-0000-0000-0000-000000000007",
        "f17a0005-0000-0000-0000-000000000008",
        "f17a0005-0000-0000-0000-000000000009",
        "f17a0005-0000-0000-0000-000000000010"]

@router.websocket("/{userID}")
async def current_loc(websocket: WebSocket, userID: str):
    global guid

    db_gen = context_get_conn()
    conn = next(db_gen)
    active_connections[userID] = websocket
    await websocket.accept()
    try:
        user_info = fita_svc.get_user_info(conn=conn, userID=userID)
        print(user_info)
    except HTTPException:
        await websocket.send_json({"status": "error", "message": "Unauthorized User"})
        active_connections.pop(userID, None)
        await websocket.close()
        return
    
    trial = 0

    try:
        pre_loc = await websocket.receive_json() # 처음 위치 초기화
        pre_uuid = pre_loc.get("uuid")
        fita_svc.update_user(conn, userID, pre_uuid)
        pre_anchor = fita_svc.get_loc(conn, pre_uuid)
        while True:
        # 유저 패닉 감지 (12초 기준)
            try:
                loc = await asyncio.wait_for(websocket.receive_json(), timeout=15.0)
                if "uuid" not in loc:
                        await websocket.send_json({"status": "error", "message": "no data"})
                        continue
                uuid = loc.get("uuid")
                fita_svc.update_user(conn, userID, uuid)
                anchor = fita_svc.get_loc(conn, uuid)

                # 화재로 인해 통행 불가
                if anchor.fireDT == True:
                    await websocket.send_json({"status": "warning", "fire datetime": anchor.fireDT, "message": "fire occured"})
                # 엘리베이터 경고
                if anchor.anchorTYPE == "elevator":
                    await websocket.send_json({"status":"warning", "anchortype": "elevator", "message": "elevator warning"})

                # 대피 완료 판단
                if anchor.anchorTYPE == "exit":
                    await websocket.send_json({"status":200, "anchortype": "exit", "message": "excape success"})
                    userOBJ = fita_svc.get_user_obj(conn=conn, userID=userID)
                    await websocket.send_json({"unused items": userOBJ})
                    await websocket.close()
                    break
                
                # 층별 guid 로드 (올라갈 때는 pre_anchor.floor와 anchor.floor가 같음)
                if anchor.anchorNUM == 68 or anchor.anchorNUM == 79:
                    if pre_anchor.floor != anchor.floor: # 위층에서 아래층으로 내려올 때
                        fire_uuid_list = fire_func.get_fire_where(conn, anchor.floor)
                        await websocket.send_json({"status":200, "next guid":guid[anchor.floor], "fire state":fire_uuid_list, "message":"going downstair"})
                    else: # 위층으로
                        fire_uuid_list = fire_func.get_fire_where(conn, anchor.floor+1)
                        await websocket.send_json({"status":200, "next guid":guid[anchor.floor + 1], "fire state":fire_uuid_list, "message":"going upstair"})
            except asyncio.TimeoutError:
                # 유저 패닉 감지 시
                # await websocket.send_json({"status": "error", "message": "user panic", "time": -10})
                trial += 1
                if trial < 3:
                    continue
                else:
                    await websocket.send_json({"status": "warning", "message": "user panic three times"})
                    # active_connections.pop(userID, None)
                    # await websocket.close()
                    # break
                    continue

    except WebSocketDisconnect:
        # 웹소켓 close
        print(f"User {userID} is disconnected.")
        active_connections.pop(userID, None)

    except WebSocketException as e:
        # 일반 에러
        print(f"system error: {e}")
        await websocket.send_json({"status": "error", "message": str(e)})
        active_connections.pop(userID, None)