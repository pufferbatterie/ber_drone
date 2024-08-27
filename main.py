import asyncio
import datetime
import uvicorn
from fastapi.responses import FileResponse
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket, WebSocketDisconnect
from mathematik import generate_route

ANIMATION_SECS = 15
ANIMATION_STEPS = 100
COORDINATE_SUN21 = (48.36866181183537, 16.504183702854686)
COORDINATE_BILLA = (48.37583025859448, 16.50760671963752)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


def my_log(msg: str):
    """ use module logging !!"""
    print(f'{datetime.datetime.now()} # {msg}')


@app.get("/")
async def get():
    return FileResponse('index.html')


@app.websocket("/ws")
async def ws_con_handler(websocket: WebSocket):
    """ using fastapis websocket implementation... (other than https://pypi.org/project/websockets/)"""
    client_absender = f'{websocket.client.host}:{websocket.client.port}'
    try:
        await websocket.accept()
        my_log(f"New connection from {client_absender}")
        t_sleep = ANIMATION_SECS / ANIMATION_STEPS
        for coordinate in generate_route(COORDINATE_SUN21, COORDINATE_BILLA, ANIMATION_STEPS):
            await websocket.send_json(coordinate)
            await asyncio.sleep(t_sleep)
        my_log(f'{client_absender} done :)')
    except WebSocketDisconnect:
        my_log(f'{client_absender} left :(')


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000, )
