import asyncio
import datetime
from contextlib import asynccontextmanager
from typing import Any
import sqlalchemy
import uvicorn
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocket, WebSocketDisconnect
from sqlalchemy import create_engine, select, Select, func
from sqlmodel import SQLModel, Session

from WSConnectionmanager import ConnectionManager
from drone_position import DronePosition
from mathematik import generate_route

ANIMATION_SECS = 15
ANIMATION_STEPS = 100
COORDINATE_SUN21 = (48.36866181183537, 16.504183702854686)
COORDINATE_BILLA = (48.37583025859448, 16.50760671963752)


def my_log(msg: str):
    """ use module logging !!"""
    print(f'{datetime.datetime.now()} # {msg}')


def get_session():
    """
    docker exec -it mte-mysql-container mysql -pdb -udb
    docker rm -f mte-mysql-container
    # using an mysql server >8.4 on 172.30.103.253:3307
    docker run -d --name mte-mysql-container \
        -e MYSQL_USER=db \
        -e MYSQL_PASSWORD=db \
        -e MYSQL_ALLOW_EMPTY_PASSWORD=bitte \
        -e MYSQL_DATABASE=mte \
        -p 3307:3306 mysql:8.4 --mysql-native-password
    """
    engine = create_engine("mysql+pymysql://db:db@172.30.103.253:3307/mte")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


async def serial_loop():
    global data_queue  # dont use globals!
    i = 1
    my_log(f"Simulation loop {i} start")
    while True:
        try:

            t_sleep = ANIMATION_SECS / ANIMATION_STEPS
            for coordinate in generate_route(COORDINATE_SUN21, COORDINATE_BILLA, ANIMATION_STEPS):
                await asyncio.sleep(t_sleep)
                # await data_queue.put(coordinate)  # from serial port
                await manager.broadcast_json(coordinate)

            my_log(f"Simulation loop {i} done")
        except Exception as e:
            print(f'TODO: specific ex: {e}')
        finally:
            await asyncio.sleep(1)  # guard
        i += 1


@asynccontextmanager
async def lifespan(app: FastAPI):
    my_log("app startup")
    asyncio.create_task(serial_loop())
    yield  # app running
    my_log("app shutdoen")


data_queue = asyncio.Queue()
manager = ConnectionManager()
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
    print(f'exited {client_absender}')


@app.get("/droneposition")
def create_hero(*, session: Session = Depends(get_session)):
    """
    [["2024-01-01T00:05:00","a",1.3,2.4,1],["2024-01-01T01:00:00","b",5.6,1.2,1]]
    """
    rs = session.exec(get_statement_last())
    data = [r._data for r in rs]  # hack1 to json
    return JSONResponse(content=jsonable_encoder(data))  # hack2 to json


def get_statement_last() -> Select[Any]:
    """
    https://stackoverflow.com/questions/1313120/retrieving-the-last-record-in-each-group-mysql/1313293#1313293
    WITH ranked_messages AS (
      SELECT m.*, ROW_NUMBER() OVER (PARTITION BY name ORDER BY id DESC) AS rn
      FROM messages AS m
    )
    SELECT * FROM ranked_messages WHERE rn = 1;
    """
    subq = (
        select(DronePosition, func.row_number().over(
            partition_by=DronePosition.drone_id,
            order_by=DronePosition.t.desc()).label('rn'))
        .cte(name='ordered_per_drone')
    )
    stmt = select(subq).where(subq.c.rn == 1)
    return stmt


def insert_testdata():
    a1 = DronePosition(drone_id="a", t=datetime.datetime(year=2024, month=1, day=1, hour=0, minute=0, second=0),
                       latitude=1.2, lonitude=2.3)
    a2 = DronePosition(drone_id="a", t=datetime.datetime(year=2024, month=1, day=1, hour=0, minute=5, second=0),
                       latitude=1.3, lonitude=2.4)

    b1 = DronePosition(drone_id="b", t=datetime.datetime(year=2024, month=1, day=1, hour=0, minute=0, second=0),
                       latitude=3.1, lonitude=6.4)
    b2 = DronePosition(drone_id="b", t=datetime.datetime(year=2024, month=1, day=1, hour=1, minute=0, second=0),
                       latitude=5.6, lonitude=1.2)

    for s in get_session():
        try:
            s.add(a1)
            s.add(a2)
            s.add(b1)
            s.add(b2)
            s.commit()
        except sqlalchemy.exc.IntegrityError as e:
            print('Data already present')


if __name__ == '__main__':
    insert_testdata()
    uvicorn.run(app, host="0.0.0.0", port=8000, )
