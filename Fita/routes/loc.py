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
from random import choice

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

async def fire_update(floor: list, websocket: WebSocket, conn: Connection):
    try:
        while True:
            await asyncio.sleep(20)
            floor[1] = fire_func.get_fire_uuid(conn, floor[0]) # floor 포인터 처리
            await websocket.send_json({"status": "fire update", "fire state":floor[1], "message":"current fire is now updated."})
    except WebSocketException as e:
        # 일반 에러
        print(f"system error: {e}")
        await websocket.send_json({"status": "error", "message": str(e)})

def user_goal(floor: int, anchorNUM: int, conn:Connection):
    try:
        fire_num5 = fire_func.get_fire_num(conn, floor=5) # 5층 불
        fire_num3 = fire_func.get_fire_num(conn, floor=3) # 3층 불
        if floor > 5: # 6층 이상은 계단 안내
            fire_num = fire_func.get_fire_num(conn, floor)
            if anchorNUM > 44 and anchorNUM != 54:
                for i in (anchorNUM, 54):
                    if i in fire_num:
                        return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=68, floor=floor-1)
                return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=79, floor=floor-1)
            elif anchorNUM < 45 or anchorNUM ==54:
                for i in (34, anchorNUM):
                    if i in fire_num:
                        return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=79, floor=floor-1)
                return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=68, floor=floor-1)
        elif floor == 5: # 5층
            for i in (35, anchorNUM): # 사용자보다 출구에 가까운 앵커에서 불이 났을 경우 반대편 계단으로 -> 1층
                if i in fire_num:
                    return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=79, floor=5)
            return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=99, floor=5)
        elif floor == 4 or floor == 3:
            if anchorNUM == 67 or anchorNUM == 79: # 좌측 계단 이용 시 5층 -> 1층 안내
                for i in (34, 53):
                    if i in fire_num5: # 5층 불 O
                        return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=79, floor=floor-1)
                return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=79, floor=floor) # 5층 먼저
            else: # 그 외의 경우
                for i in [18, 19, 20, 21, 35, 36, 37, 38, 39, 40]:
                    if i in fire_num3: # 3층 불 O
                        return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=79, floor=floor) # 5층으로 안내
                if floor==3: # 3층 안내
                    return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=99, floor=3)
                return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=68, floor=3) #4층 -> 3층 
        elif floor ==2:
            fire_num = fire_func.get_fire_num(conn, floor)
            if anchorNUM > 44 and anchorNUM != 54:
                for i in (anchorNUM, 54):
                    if i in fire_num:
                        return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=68, floor=floor-1)
                return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=79, floor=floor-1)
            elif anchorNUM < 45 or anchorNUM ==54:
                for i in (34, anchorNUM):
                    if i in fire_num:
                        return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=79, floor=floor-1)
                return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=68, floor=floor-1)
        elif floor == 1:
            if anchorNUM in [51, 52, 53, 67, 79]:
                return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=99, floor=1)
            else:
                return fita_svc.get_uuid_byNUM(conn=conn, anchorNUM=98, floor=1)
            

    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Internal Server Error was occured.")

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
        await websocket.send_json({"status": "error", "message": "User {userID} is an unauthorized user."})
        active_connections.pop(userID, None)
        await websocket.close()
        return
    
    trial = 0

    try:
        loc = await websocket.receive_json() # 처음 위치 초기화
        goalDist = loc.get("goalDist")
        uuid = loc.get("uuid")
        fita_svc.update_user(conn, userID, uuid)
        anchor = fita_svc.get_loc(conn, uuid)
        floor_ptr = [0, []]
        floor_ptr[0] = anchor.floor
        goal = ""
        if anchor.anchorTYPE == "way":
            goal = user_goal(conn=conn, floor=floor_ptr[0], anchorNUM=anchor.anchorNUM)
        asyncio.create_task(fire_update(floor_ptr, websocket, conn))

        while True:
        # 유저 패닉 감지 (15초 기준)
            try:
                new_loc = await asyncio.wait_for(websocket.receive_json(), timeout=15.0)
                if "uuid" not in new_loc:
                        await websocket.send_json({"status": "error", "message": "You need to send your current location."})
                        continue
                new_uuid = new_loc.get("uuid")
                new_goalDist = new_loc.get("goalDist")
                if uuid != new_uuid:
                    uuid = new_uuid
                    fita_svc.update_user(conn, userID, uuid)
                    anchor = fita_svc.get_loc(conn, uuid) # 사용자 위치 갱신

                # 조건 ---
                # 화재로 인해 통행 불가
                if anchor.fireDT == True:
                    await websocket.send_json({"status": "alert", "time": choice([-10, -20]),"goal":goal, "message": "Fire is now occured."})
                # 엘리베이터 경고
                if anchor.anchorTYPE == "elevator":
                    await websocket.send_json({"status":"alert", "time":0, "goal" : goal, "message": "elevator warning"})
                
                if anchor.anchorTYPE == "way":
                    new_goal = user_goal(conn=conn, floor=anchor.floor, anchorNUM=anchor.anchorNUM)
                    
                    if anchor.floor > 6 and anchor.floor > floor_ptr[0]:
                        await websocket.send_json({"status":"alert", "time":0, "goal": goal, "message": f"You are out of the path: go downstairs."})
                    if goal != new_goal:
                        goal = new_goal
                        await websocket.send_json({"status":"alert", "time":0, "goal": goal, "message": f"Goal anchor is changed {goal} to {new_goal}."})
                    elif goalDist < new_goalDist :
                        await websocket.send_json({"status":"alert", "time":0, "goal": goal, "message": f"You are out of the path: distance has increased."})
                    
                    gaolDist = new_goalDist # goalDist 갱신

                # 대피 완료 판단
                if anchor.anchorTYPE == "exit":
                    await websocket.send_json({"status":"success", "message": "You completed escape!"})
                    await websocket.close()
                    break
                
                # 층별 guid 로드 (올라갈 때는 pre_anchor.floor와 anchor.floor가 같음)
                if anchor.anchorNUM == 68 or anchor.anchorNUM == 79:
                    if anchor.floor != floor_ptr[0]: # 위층에서 아래층으로 내려올 때
                        floor_ptr[0] = anchor.floor
                        fire_uuid_list = fire_func.get_fire_uuid(conn, anchor.floor)
                        await websocket.send_json({"status":"guid update", "next guid":guid[anchor.floor], "goal": goal,
                                                   "fire state":fire_uuid_list, "message":"You are going downstair."})
                    else: # 위층으로
                        fire_uuid_list = fire_func.get_fire_uuid(conn, anchor.floor+1)
                        await websocket.send_json({"status":"guid update", "next guid":guid[anchor.floor + 1], "goal": goal,
                                                   "fire state":fire_uuid_list, "message":"You are going upstair."})
            
            except asyncio.TimeoutError:
                # 유저 패닉 감지 시
                # await websocket.send_json({"status": "error", "message": "user panic", "time": -10})
                trial += 1
                if trial < 3:
                    continue
                else:
                    await websocket.send_json({"status": "alert", "time": -10, "goal":goal, "message": "You are panic three times."})
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