from fastapi import APIRouter, Form, Depends, status
from db.database import direct_get_conn, context_get_conn
from fastapi.responses import JSONResponse
from schemas import fita_schemas
from fastapi.exceptions import HTTPException
from sqlalchemy import text, Connection
from sqlalchemy.exc import SQLAlchemyError
from services import fita_svc

# about User - 로그인
router = APIRouter(prefix="/fita", tags=["fita"])

@router.post("/")
def user_login(userID: str = Form(...),
               loc: str = Form(...),
               conn: Connection = Depends(context_get_conn)):
    user_info = fita_svc.get_user_info(conn=conn, userID=userID)
    if not user_info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"해당 id {userID}는(은) 존재하지 않습니다.")
    fita_svc.update_user(conn=conn, userID=userID, loc=loc)
    return JSONResponse(content={}, status_code=status.HTTP_200_OK)
