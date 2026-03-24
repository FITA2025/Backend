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

# about Time - 골든타임 계산, 아이템 사용 골든타임 추가, 유저 패닉 감지
router = APIRouter(prefix="/time", tags=["time"])


