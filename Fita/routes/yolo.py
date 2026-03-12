from fastapi import APIRouter, File, UploadFile, Form, Depends, status, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from schemas import fita_schemas
from db.database import direct_get_conn, context_get_conn
from sqlalchemy import Connection
from services import fita_svc
import onnxruntime as ort
import numpy as np
from PIL import Image
import io
import os


# about Object Detecting - 사물 감지, 미사용 아이템 안내
router = APIRouter(prefix="/yolo", tags=["yolo"])

# ----- 사물 감지 및 DB 업데이트 -----

# 모델 경로 설정
model_path = os.path.join(os.path.dirname(__file__), "../algorithm/yolo.onnx")

# ONNX 모델 로드
session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

# 멀티클래스 yolo
CLASS_NAMES = ["faucet", "hydrant", "extinguisher"]


def preprocess_image(image: Image.Image, input_shape=(640, 640)):
    image = image.resize(input_shape)
    img_array = np.array(image).astype(np.float32)
    img_array = img_array / 255.0
    img_array = np.transpose(img_array, (2, 0, 1))  # CHW
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

@router.post("/")
async def predict(
    userID: str = Form(...),
    file: UploadFile = File(...),
    conn: Connection = Depends(context_get_conn)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    input_data = preprocess_image(image)

    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    outputs = session.run([output_name], {input_name: input_data})

    predictions = outputs[0][0].transpose(1, 0)     # 전치
    
    dOBJ = [0, 0, 0]
    userOBJ = fita_svc.get_user_obj(conn=conn, userID=userID)
    
    for pred in predictions:
        class_scores = pred[4:] 
        confidence = np.max(class_scores)
        class_id = np.argmax(class_scores)
        if confidence >= 0.75:
            if class_id < len(dOBJ):
                dOBJ[class_id] = 1

    if dOBJ[0]==0 and userOBJ.faucet==1: dOBJ[0]=1,
    if dOBJ[1]==0 and userOBJ.hydrant==1: dOBJ[1]=1,
    if dOBJ[2]==0 and userOBJ.extinguisher==1: dOBJ[3]=1

    fita_svc.update_obj(conn=conn, userID=userID,
                        faucet=dOBJ[0], hydrant=dOBJ[1], extinguisher=dOBJ[2])
        
                
    return JSONResponse(dOBJ)

# ----- 미사용 아이템 안내 -----
@router.get("/items")
def not_used_items(userID: str,
                   conn: Connection = Depends(context_get_conn)):
    userOBJ = fita_svc.get_user_obj(conn=conn, userID=userID)
    
    return JSONResponse(content = [userOBJ.faucet,
                                   userOBJ.hydrant, userOBJ.extinguisher])
