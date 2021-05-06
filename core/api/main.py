from fastapi import FastAPI
from .routers import ping


app = FastAPI()
app.include_router(ping.router)


@app.get('/')
async def home():
    return "Welcome to the TRE API"
