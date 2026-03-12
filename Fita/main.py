from fastapi import FastAPI
from routes import fire, fita, loc, time, yolo

app = FastAPI()
app.include_router(fire.router)
app.include_router(fita.router)
app.include_router(loc.router)
app.include_router(time.router)
app.include_router(yolo.router)