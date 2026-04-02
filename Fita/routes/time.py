from fastapi import APIRouter, Form, Depends, status, Request
from db.database import direct_get_conn, context_get_conn
from fastapi.responses import JSONResponse
from schemas import fita_schemas
from fastapi.exceptions import HTTPException
from sqlalchemy import text, Connection
from sqlalchemy.exc import SQLAlchemyError
from services import fita_svc
import random, math
from datetime import datetime
from services import fita_svc

# about Time - 골든타임 계산
router = APIRouter(prefix="/time", tags=["time"])

# ----- 초기 골든타임 계산 -----

@router.get("/init/{user_id}")
async def calculate_time(request: Request, userID: int, conn: Connection = Depends(context_get_conn)):
    # 유저 정보 가져오기 (나이, 위치)
    user = fita_svc.get_user_info(conn=conn, userID=userID)
    user_loc = fita_svc.get_user_loc(conn=conn, userID=userID)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"해당 id {userID}는(은) 존재하지 않습니다.")
    ignition = fita_svc.get_fire_start(conn)
    
    # 골든타임 계산
    base_time = 480  # 기본 골든타임(초)
    floor_diff = abs(user_loc.floor - ignition.floor)
    fire_risk = (9 - floor_diff) * 20  # 층수 차이에 따른 위험도 감소, 최대 180초 감소

    # 평균 이동속도
    if user.age < 12:
        speed = 0.8
    elif user.age < 60:
        speed = 1.2
    else:
        speed = 0.6

    horizontal_distance = 0
    vertical_distance = floor_diff * 3  # 층당 3m 가정
    distance = math.sqrt(horizontal_distance**2 + vertical_distance**2)
    distance_factor = distance / speed
    age_factor = user.age * 0.5

    golden_time = base_time - fire_risk - distance_factor - age_factor
    golden_time = max(golden_time, 0)

    return JSONResponse(content={round(golden_time)}, status_code=status.HTTP_200_OK)