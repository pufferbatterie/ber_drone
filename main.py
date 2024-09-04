import asyncio, datetime, uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket
from sqlmodel import Session
from WSConnectionmanager import ConnectionManager
from database import get_session, insert_testdata, get_statement_last
from drone_position import DronePosition
from mathematik import generate_route

ANIMATION_SECS = 15
ANIMATION_STEPS = 100
COORDINATE_SUN21 = (48.36866181183537, 16.504183702854686)
COORDINATE_BILLA = (48.37583025859448, 16.50760671963752)

manager = ConnectionManager()


def my_log(msg: str):
    """ use module logging !!"""
    print(f'{datetime.datetime.now()} # {msg}')


async def serial_loop():
    i = 1
    my_log(f"Simulation loop {i} start")
    while True:
        try:

            t_sleep = ANIMATION_SECS / ANIMATION_STEPS
            for coordinate in generate_route(COORDINATE_SUN21, COORDINATE_BILLA, ANIMATION_STEPS):
                await asyncio.sleep(t_sleep)
                await manager.broadcast_json(coordinate)
                for s in get_session():
                    s.add(DronePosition(t=datetime.datetime.now(), longitude=coordinate[0], latitude=coordinate[1], drone_id='c'))
                    s.commit()

            my_log(f"Simulation loop {i} done")
        except Exception as e:
            print(f'TODO: specific ex: {e}')
        finally:
            await asyncio.sleep(1)  # guard
        i += 1


@asynccontextmanager
async def lifespan(appl: FastAPI):
    my_log("app startup")
    asyncio.create_task(serial_loop())  # do not await!
    yield  # app running
    my_log("app shutdoen")


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def get():
    return FileResponse('index.html')


@app.websocket("/ws")
async def ws_con_handler(websocket: WebSocket):
    """ using fastapis websocket implementation... (other than https://pypi.org/project/websockets/)"""
    client_absender = f'{websocket.client.host}:{websocket.client.port}'
    await manager.connect(websocket)
    while websocket in manager.active_connections:
        await asyncio.sleep(1)
    my_log(f'exited {client_absender}')


@app.get("/droneposition")
def create_hero(*, session: Session = Depends(get_session)):
    """
    [["2024-01-01T00:05:00","a",1.3,2.4,1],["2024-01-01T01:00:00","b",5.6,1.2,1]]
    """
    rs = session.exec(get_statement_last())
    data = [r._data for r in rs]  # hack1 to json
    return JSONResponse(content=jsonable_encoder(data))  # hack2 to json


if __name__ == '__main__':
    insert_testdata()
    uvicorn.run(app, host="0.0.0.0", port=8000, )
