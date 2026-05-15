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
import io, os, base64, math
from routes import fire
from random import sample, choice


# about Time - 골든타임 계산
# about Object Detecting - 사물 감지, 미사용 아이템 안내, 아이템 사용 시 골든타임 추가
router = APIRouter(prefix="/time", tags=["time"])

# ----- 초기 골든타임 계산 -----

@router.get("/init/{userID}")
async def calculate_time(userID: str, request: Request, conn: Connection = Depends(context_get_conn)):
    # 유저 정보 가져오기 (나이, 위치)
    user = fita_svc.get_user_info(conn=conn, userID=userID)
    user_loc = fita_svc.get_user_loc(conn=conn, userID=userID)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"User {userID} does not exist.")
    ignition = fire_func.get_anchor(conn=conn, uuid = fire.ignition_point)
    print(ignition)
    
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

    return JSONResponse(content={"golden time" : round(golden_time)}, status_code=status.HTTP_200_OK)


# ----- 엔딩분기 -----

@router.get("/end/{userID}")
async def ending(userID: str, time: int,
                 request: Request, conn: Connection = Depends(context_get_conn)):
    user_loc = fita_svc.get_user_loc(conn=conn, userID=userID)
    obj = fita_svc.get_user_obj(conn=conn, userID=userID)
    user_obj = [k for k, v in {'faucet': obj.faucet, 'hydrant': obj.hydrant, 'extinguisher': obj.extinguisher}.items() if v is True]
    if user_loc.anchorTYPE == "exit" and time > 0 :
        return JSONResponse(content={"status": "success", "obj":user_obj, "message": f" You completed escape by floor {user_loc.floor}!"},
                            status_code=status.HTTP_200_OK)
    elif time == 0 :
        if user_loc.fireDT :
            return JSONResponse(content={"status": "fail", "obj":user_obj, "message": "Inability and death due to systemic burns, evacuation failure."},
                                status_code=status.HTTP_200_OK)
        else:
            message = choice(["Death from loss of consciousness, evacuation failure.", "Death from respiratory arrest, evacuation failure."])
            return JSONResponse(content={"status": "fail", "obj":user_obj, "message": message},
                                status_code=status.HTTP_200_OK)
        
    else:
        return JSONResponse(content={"status": "error", "message":"The evacuation is not over"},
                            status_code=status.HTTP_404_NOT_FOUND)


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
    preOBJ = [0, 0, 0]
    db_gen = context_get_conn()
    conn = next(db_gen)
    active_connections[userID] = websocket
    await websocket.accept()
    try:
        user_info = fita_svc.get_user_info(conn=conn, userID=userID)
        print(user_info)
    except HTTPException:
        await websocket.send_json({"status": "error", "message": "User {userID} is an unauthorized user."})
        active_connections.pop(userID, None)
        await websocket.close()
        return
    try:
        pre_file = await websocket.receive_json()
        pre_uOBJ = pre_file["obj"]
        while True:
            file = await websocket.receive_json()
            uOBJ = file["obj"] # 유저가 사용했다고 전송한 사물 리스트
            if uOBJ != pre_uOBJ : # 사용횟수가 추가 됐을 때만 DB와 비교해 업데이트
                db = fita_svc.get_user_obj(conn=conn, userID=userID)
                dbOBJ = [db.faucet, db.hydrant, db.extinguisher] # DB에 저장된 유저가 이미 사용한 사물 리스트
                useOBJ = [0 if (uOBJ[i]<pre_uOBJ[i] and dbOBJ[i]==False) else 1 for i in range(3)]
                if useOBJ != dbOBJ:
                    fita_svc.update_obj(conn=conn, userID=userID, faucet=useOBJ[0], hydrant=useOBJ[1], extinguisher=useOBJ[2])
                if uOBJ[1]>pre_uOBJ[1]:
                    candAnchor = fire_func.get_fire_expand(conn=conn, uuid=file["uuid"])
                    if len(candAnchor) > 2:
                        candAnchor = sample(candAnchor, 2)
                    for i in candAnchor:
                        fire_func.delete_fireDT(conn=conn, uuid=i)
                if uOBJ[2]>pre_uOBJ[2]:
                    candAnchor = fire_func.get_fire_expand(conn=conn, uuid=file["uuid"])
                    if len(candAnchor) > 3:
                        candAnchor = sample(candAnchor, 3)
                    for i in candAnchor:
                        fire_func.delete_fireDT(conn=conn, uuid=i)
                pre_uOBJ = uOBJ #pre_uOBJ 갱신
                # if addOBJ == [1, 1, 1]:
                    # await websocket.send_json({"status": "success", "message": "You have already used all the objects."})
                    # continue # 모든 사물 사용 시 안내

            image_bytes = base64.b64decode(file["img"])
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            input_data = preprocess_image(image)

            input_name = session.get_inputs()[0].name
            output_name = session.get_outputs()[0].name
            outputs = session.run([output_name], {input_name: input_data})

            predictions = outputs[0][0].transpose(1, 0) # 전치
            dOBJ = [0, 0, 0] # img를 통한 yolo 감지 사물 리스트
            
            for pred in predictions:
                class_scores = pred[4:]
                confidence = np.max(class_scores)
                class_id = np.argmax(class_scores)
                if confidence >= 0.8:
                    if class_id < len(dOBJ):
                        dOBJ[class_id] = 1
            await websocket.send_json({"status": "alert", "obj": dOBJ, "time": 0, "message": "Detected objects list."})
        

            # 감지 사물은 모두 반환, 물수건 +20/hydrant는 유저 주변 앵커 3개 fireDT 초기화, extitnguisher는 유저 주변 앵커 2개 fireDT 초기화
            # 사용시간 기본 고려
            print("time.py: ", userID, "obj", dOBJ)
        
            
    except WebSocketDisconnect:
        print(f"User {userID} is disconnected.")
        active_connections.pop(userID, None)

    except WebSocketException as e:
        print(f"system error: {e}")
        await websocket.send_json({"status": "error", "message": str(e)})


