from fastapi import APIRouter, Depends, status, WebSocket, WebSocketDisconnect, WebSocketException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from schemas import fita_schemas
from typing import Dict
from db.database import direct_get_conn, context_get_conn
from sqlalchemy import Connection
from services import fita_svc, fire_func
import onnxruntime as ort
import numpy as np
from PIL import Image
import io
import os
import base64
import math


# about Time - 골든타임 계산
# about Object Detecting - 사물 감지, 미사용 아이템 안내, 아이템 사용 시 골든타임 추가
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
    ignition = fire_func.get_anchor(conn, )
    
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




active_connections: Dict[str, WebSocket] = {}

# ----- 사물 감지 및 DB 업데이트, 아이템 사용 골든타임 추가 -----

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

@router.websocket("/{userID}")
async def predict(websocket: WebSocket, userID: str):
    db_gen = context_get_conn()
    conn = next(db_gen)
    active_connections[userID] = websocket
    await websocket.accept()
    try:
        user_info = fita_svc.get_user_info(conn=conn, userID=userID)
        print(user_info)
    except HTTPException:
        await websocket.send_json({"status": "error", "message": "Unauthorized User"})
        active_connections.pop(userID, None)
        await websocket.close()
        return
    try:
        while True:
            file = await websocket.receive_json()
            image_bytes = base64.b64decode(file["image"])
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
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

            if dOBJ[0]==0 and userOBJ.faucet==1:
                dOBJ[0]=1
                await websocket.send_json({"status": 200, "object": "faucet", "time": 30})
            if dOBJ[1]==0 and userOBJ.hydrant==1:
                dOBJ[1]=1
                await websocket.send_json({"status": 200, "object": "hydrant", "time": 10})
            if dOBJ[2]==0 and userOBJ.extinguisher==1:
                dOBJ[3]=1
                await websocket.send_json({"status": 200, "object": "extinguisher", "time": 10})

            fita_svc.update_obj(conn=conn, userID=userID,
                                faucet=dOBJ[0], hydrant=dOBJ[1], extinguisher=dOBJ[2])
            
            if userOBJ.faucet==1 and userOBJ.hydrant==1 and userOBJ.extinguisher==1:
                await websocket.send_json({"status": 200, "message": "all objects were detected"})
                return 0 # 모든 사물 감지 시 웹소켓 연결 종료
            
    except WebSocketDisconnect:
        print(f"User {userID} is disconnected.")
        active_connections.pop(userID, None)

    except WebSocketException as e:
        print(f"system error: {e}")
        await websocket.send_json({"status": "error", "messeage": str(e)})


