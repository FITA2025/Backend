from fastapi import APIRouter, Request, Depends, status, Form
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException
from fastapi.templating import Jinja2Templates
from db.database import direct_get_conn, context_get_conn
from sqlalchemy import text, Connection
from schemas.fita_schema import Room, User, Anchor, AnchorWithRoom, UserWithAnchorSchema, RelationSchema, RelationWithAnchorsSchema
from sqlalchemy.exc import SQLAlchemyError

# router 생성
router = APIRouter(prefix="/fita", tags=["fita"])
# jinja2 Template 엔진 생성
templates = Jinja2Templates(directory="templates")

# 모든 유저 보기
@router.get("/")
async def get_all_users(request: Request):
    conn = None
    try:
        conn = direct_get_conn()
        query = """
                SELECT id, age, detect_obj, room_loc, anchor_loc FROM user
                """
        result = conn.execute(text(query))
        all_users = [User(user_id = row.id,
                     age = row.age,
                     detect_obj = row.detect_obj,
                     room_loc = row.room_loc, # None
                     anchor_loc = row.anchor_loc)
                 for row in result]
        result.close()
        return templates.TemplateResponse(
            request = request,
            name = "index.html",
            context = {"all_users": all_users}
        )
    except SQLAlchemyError as e:
        print(e)
        raise e
    finally:
        if conn:
            conn.close()

# 새 유저 생성
@router.get("/new")
def create_user_ui(request: Request):
    return templates.TemplateResponse(
        request = request,
        name = "new_user.html",
        context = {}
    )

@router.post("/new")
def create_user(
request: Request,
    id: int = Form(...),
    age: int = Form(...),
    detect_obj: str | None = Form(None, max_length=30),
    room_loc: str = Form(..., min_length=4, max_length=6),
    anchor_loc: int = Form(...),
    conn: Connection = Depends(context_get_conn)):
    
    try:
        
        query = text("""
            INSERT INTO user(id, age, detect_obj, room_loc, anchor_loc)
            VALUES (:id, :age, :detect_obj, :room_loc, :anchor_loc)
        """)

        conn.execute(query, {
            "id": id,
            "age": age,
            "detect_obj": detect_obj,
            "room_loc": room_loc,
            "anchor_loc": anchor_loc
        })

        conn.commit()
        return RedirectResponse("/fita", status_code=status.HTTP_302_FOUND)
    
    except SQLAlchemyError as e:
        print(e)
        conn.rollback()
