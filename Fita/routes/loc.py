from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

# about Location/Anchors - 실시간 위치 업데이트, 최단 경로 계산,
# 경로 이탈 판단, 대피 완료 판단, 엘리베이터 경고, 사용자 위치별 GUID 반환
router = APIRouter(prefix="/loc", tags=["loc"])
