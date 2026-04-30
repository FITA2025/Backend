from fastapi import APIRouter, Form, Depends, status
from db.database import direct_get_conn, context_get_conn
from fastapi.responses import JSONResponse
from schemas import fita_schemas
from fastapi.exceptions import HTTPException
from sqlalchemy import text, Connection
from sqlalchemy.exc import SQLAlchemyError
import random, math, asyncio
from services import fire_func
import traceback

# about Fire - 발화 지점 랜덤 지정, 화재 경로 지정
router = APIRouter(prefix="/fire", tags=["fire"])

# 전역변수
ignition_point = ""

# ----- 발화 지점 랜덤 지정 -----

@router.post("/start")
async def fire_start(conn: Connection = Depends(context_get_conn)):
    query = "SELECT uuid FROM anchor"
    result = conn.execute(text(query))
    anchors = result.fetchall() # list
    if not anchors:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="해당 위치는(은) 존재하지 않습니다.")
    
    sel_anchor = random.choice(anchors)
    uuid = sel_anchor[0]
    print(uuid)
    global ignition_point
    ignition_point = uuid
    print(ignition_point)
    await fire_wrapper(ignition_point)
    return JSONResponse(content={"message" : "fire start now"}, status_code=status.HTTP_200_OK)

global fire_list
fire_list = []

async def fire_wrapper(uuid: str):
    asyncio.create_task(fire(uuid, 0))
    print(len(asyncio.all_tasks()))
    return JSONResponse(content ={"status": "success"}, status_code=status.HTTP_200_OK)

async def fire(uuid: str, depth: int):
    if depth > 12:
        return
    conn = direct_get_conn()
    try:
        fire_func.update_fireDT(conn, uuid)
        if uuid not in fire_list:
            fire_list.append(uuid)
            print(1)
        
        await asyncio.sleep(24) # 24초마다 사방으로 불 확산
        print("**:", fire_list)
        for B_anchor in list(fire_list):
            candidates = fire_func.get_fire_expand(conn, B_anchor)
            print("c*:", candidates)
            v_candidates = [c for c in candidates if c not in fire_list]
            print(v_candidates)
            if not v_candidates:
                print(4)
                if B_anchor in fire_list:
                    fire_list.remove(B_anchor)
                continue
            sel_anchor = random.choice(v_candidates)
            fire_list.append(sel_anchor)
            print(sel_anchor, depth+1)

            asyncio.create_task(fire(sel_anchor, depth+1))
        return
    
    except Exception as e:
        print(f"Fire expansion error : {e}")
        traceback.print_exc()
    finally:
        print("end")
        conn.close()
