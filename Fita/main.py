from fastapi import FastAPI
from routes import fire, loc, time, web

app = FastAPI()
app.include_router(fire.router)
app.include_router(loc.router)
app.include_router(time.router)
app.include_router(web.router)