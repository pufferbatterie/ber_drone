import datetime
import sqlalchemy
from sqlalchemy import create_engine, select, func
from sqlmodel import SQLModel, Session

from drone_position import DronePosition


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


def get_statement_last() -> sqlalchemy.select:
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
