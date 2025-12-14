
from fastapi import FastAPI, APIRouter, Request, Depends
from pydantic import BaseModel, Field
from typing import Optional
import math
from schemas.fita_schema import Room, User, Anchor, AnchorWithRoom, UserWithAnchorSchema, RelationSchema, RelationWithAnchorsSchema
from db.database import direct_get_conn, context_get_conn
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import random
from datetime import datetime
from fastapi.exceptions import HTTPException


router = APIRouter(prefix="/golden_time", tags=["golden_time"])


@router.post("/fire_start")
def fire_start(request: Request, conn = Depends(context_get_conn)):
    # 전체 앵커 조회
    query = "SELECT anchor_id, room_id, fireDT FROM anchor"
    result = conn.execute(text(query))
    anchors = result.fetchall()  # 리스트로 변환

    if not anchors:
        raise HTTPException(status_code=404, detail="No anchors found in DB")

    # 랜덤 선택
    selected_anchor = random.choice(anchors)
    print(selected_anchor)
    fire_dt = datetime.now()

    # fireDT 업데이트
    conn.execute(
        text("UPDATE anchor SET fireDT = :fire_dt WHERE anchor_id = :anchor_id"),
        {"fire_dt": fire_dt, "anchor_id": selected_anchor.anchor_id}
    )

    conn.commit()
    # 업데이트된 Anchor 다시 조회
    updated_result = conn.execute(
        text("SELECT anchor_id, room_id, fireDT FROM anchor WHERE anchor_id = :anchor_id"),
        {"anchor_id": selected_anchor.anchor_id}
    )
    updated_anchor = updated_result.fetchone()

    return dict(updated_anchor._mapping)  # SQLAlchemy Row → dict 변환



@router.get("/calculate/{user_id}")
async def calculate_golden_time(request: Request, user_id: int, conn = Depends(context_get_conn)):
    try:
        # 사용자 정보 조회
        user_query = """
            SELECT id, age, detect_obj, room_loc, anchor_loc FROM user WHERE id = :id
        """
        user_stmt = text(user_query).bindparams(id=user_id)
        user_result = conn.execute(user_stmt)
        row = user_result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        user_data = {
            "user_id": row[0],
            "age": row[1],
            "detect_obj": row[2],
            "room_loc": row[3],
            "anchor_loc": row[4]
        }

        # 발화 중인 Anchor 중 가장 빠른 fireDT 가져오기
        fire_query = """
            SELECT anchor_id, room_id, fireDT FROM anchor
            WHERE fireDT IS NOT NULL
            ORDER BY fireDT ASC
            LIMIT 1
        """
        fire_result = conn.execute(text(fire_query))
        fire_anchor = fire_result.fetchone()
        if not fire_anchor:
            raise HTTPException(status_code=404, detail="No active fire found")

        fire_room_id = fire_anchor[1]  # room_id
        fire_floor = int(fire_room_id[2])  # 예: T502 → '5'

        # 골든타임 계산
        base_time = 480  # 기본 골든타임(초)
        current_floor = int(user_data["room_loc"][2])
        floor_diff = abs(current_floor - fire_floor)
        fire_risk = floor_diff * 30  # 층수 차이에 따른 위험도

        # 평균 이동속도
        age = user_data["age"]
        if age < 12:
            speed = 0.8
        elif age < 60:
            speed = 1.2
        else:
            speed = 0.6

        horizontal_distance = user_data["anchor_loc"]
        vertical_distance = floor_diff * 3  # 층당 3m 가정
        distance = math.sqrt(horizontal_distance**2 + vertical_distance**2)
        distance_factor = distance / speed
        age_factor = age * 0.5

        golden_time = base_time - fire_risk - distance_factor - age_factor
        golden_time = max(golden_time, 0)

        return int(round(golden_time))

    except SQLAlchemyError as e:
        print(e)
        raise HTTPException(status_code=500, detail="Database error")
    finally:
        if conn:
            conn.close()
