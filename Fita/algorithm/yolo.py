from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse
import onnxruntime as ort
import numpy as np
from PIL import Image
import io
import os

router = APIRouter(prefix="/yolo", tags=["yolo"])

# 모델 경로 설정
model_path = os.path.join(os.path.dirname(__file__), "yolo_bath.onnx")

# ONNX 모델 로드
session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])

# faucet 클래스만 사용
CLASS_NAMES = ["faucet"]


def preprocess_image(image: Image.Image, input_shape=(640, 640)):
    image = image.resize(input_shape)
    img_array = np.array(image).astype(np.float32)
    img_array = img_array / 255.0
    img_array = np.transpose(img_array, (2, 0, 1))  # CHW
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

@router.post("/predict")
async def predict(file: UploadFile = File(...)):
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")
    input_data = preprocess_image(image)

    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name

    outputs = session.run([output_name], {input_name: input_data})

    predictions = outputs[0][0]  # Remove batch dimension
    is_faucet = False

    for pred in predictions:
        confidence = float(pred[4])  # 원시 confidence 값 사용
        if confidence >= 75:  # 75 이상이면 faucet 감지
            is_faucet = True
            break

    return JSONResponse({"is_faucet": is_faucet})
