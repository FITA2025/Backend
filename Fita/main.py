from fastapi import FastAPI
from routes import fita
from algorithm import yolo, golden_time

app = FastAPI()
app.include_router(fita.router)
app.include_router(yolo.router)
app.include_router(golden_time.router)