from fastapi import APIRouter, Form, Depends, status
from db.database import direct_get_conn, context_get_conn
from fastapi.responses import JSONResponse
from schemas import fita_schemas
from fastapi.exceptions import HTTPException
from sqlalchemy import text, Connection
from sqlalchemy.exc import SQLAlchemyError
from services import fita_svc
import random, math
from datetime import datetime

# about Fire - 발화 지점 랜덤 지정, 화재 경로 지정, 이동 불가 구간 지정
router = APIRouter(prefix="/fire", tags=["fire"])

@router.post("/start")
def fire_start(conn = Depends(context_get_conn)):
    query = "SELECT uuid FROM anchor"
    result = conn.execute(text(query))
    anchors = result.fetchall() # list

    if not anchors:
        raise HTTPException(status_code=404, detail="해당 위치는(은) 존재하지 않습니다.")
    
    sel_anchor = random.choice(anchors)
    uuid = sel_anchor[0]
    fireDT=datetime.now()

    try:
        query = f"UPDATE anchor SET fireDT =:fireDT WHERE uuid =:uuid"
        bind_stmt = text(query).bindparams(uuid = uuid, fireDT = fireDT)
        result = conn.execute(bind_stmt)
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"해당 위치는(은) 존재하지 않습니다.")
        conn.commit()
            
    except SQLAlchemyError as e:
        print(e)
        conn.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="요청데이터가 제대로 전달되지 않았습니다.")

    return JSONResponse(content={}, status_code=status.HTTP_200_OK)