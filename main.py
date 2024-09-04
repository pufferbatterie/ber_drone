import asyncio
import datetime
import decimal
import json
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

from drone_position import DronePosition
from mathematik import generate_route

ANIMATION_SECS = 15
ANIMATION_STEPS = 100
COORDINATE_SUN21 = (48.36866181183537, 16.504183702854686)
COORDINATE_BILLA = (48.37583025859448, 16.50760671963752)


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


@app.get("/droneposition")
def create_hero(*, session: Session = Depends(get_session)):
    """
    [["2024-01-01T00:05:00","a",1.3,2.4,1],["2024-01-01T01:00:00","b",5.6,1.2,1]]
    """
    rs = session.exec(get_statement_last())
    data = [r._data for r in rs]    # hack1 to json
    return JSONResponse(content=jsonable_encoder(data)) # hack2 to json


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
