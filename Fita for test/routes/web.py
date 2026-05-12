from fastapi import APIRouter, WebSocket, WebSocketDisconnect, WebSocketException
from db.database import direct_get_conn, context_get_conn
from schemas import fita_schemas
from fastapi.exceptions import HTTPException
from sqlalchemy import text, Connection
from sqlalchemy.exc import SQLAlchemyError
from services import fire_func

# Web view - 화재 발생 지점 및 사용자 위치 파악
router = APIRouter(prefix="/web", tags=["web"])


