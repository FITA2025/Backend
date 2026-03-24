from fastapi import APIRouter, File, UploadFile, Request, Depends, status
from fastapi.responses import JSONResponse
from db.database import direct_get_conn, context_get_conn
from schemas import fita_schemas
from fastapi.exceptions import HTTPException
from sqlalchemy import text, Connection
from sqlalchemy.exc import SQLAlchemyError
from services import fita_svc

# about Location/Anchors - 실시간 위치 업데이트, 최단 경로 계산,
# 경로 이탈 판단, 대피 완료 판단, 엘리베이터 경고, 사용자 위치별 GUID 반환
router = APIRouter(prefix="/loc", tags=["loc"])

# ----- 실시간 위치 업데이트 -----

@router.post("/nowloc/{userID}")
def updpate_user_loc(request: Request, userID: str, uuid: str, conn: Connection = Depends(context_get_conn)):
    fita_svc.update_user(conn, userID, uuid)
    return JSONResponse(content={}, status_code=status.HTTP_200_OK)