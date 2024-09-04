import datetime
import sqlalchemy
from sqlalchemy import create_engine, select, func
from sqlmodel import SQLModel, Session

from drone_position import DronePosition

engine = create_engine(
    "mysql+pymysql://db:db@172.30.103.253:3307/mte",
    # echo=True
)
print('creating tablers...')
SQLModel.metadata.create_all(engine)


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

    with Session(engine) as s:
        yield s


def insert_testdata():
    a1 = DronePosition(drone_id="a", t=datetime.datetime(year=2024, month=1, day=1, hour=0, minute=0, second=0),
                       latitude=1.2, longitude=2.3)
    a2 = DronePosition(drone_id="a", t=datetime.datetime(year=2024, month=1, day=1, hour=0, minute=5, second=0),
                       latitude=1.3, longitude=2.4)
    b1 = DronePosition(drone_id="b", t=datetime.datetime(year=2024, month=1, day=1, hour=0, minute=0, second=0),
                       latitude=3.1, longitude=6.4)
    b2 = DronePosition(drone_id="b", t=datetime.datetime(year=2024, month=1, day=1, hour=1, minute=0, second=0),
                       latitude=5.6, longitude=1.2)

    for s in get_session():
        try:
            s.add(a1)
            s.add(a2)
            s.add(b1)
            s.add(b2)
            s.commit()
        except sqlalchemy.exc.IntegrityError as e:
            print(f'Data already present e={e}')


def get_statement_last() -> sqlalchemy.select:
    """
    https://stackoverflow.com/questions/1313120/retrieving-the-last-record-in-each-group-mysql/1313293#1313293
    WITH ranked_messages AS (
      SELECT m.*, ROW_NUMBER() OVER (PARTITION BY name ORDER BY id DESC) AS rn
      FROM messages AS m
    )
    SELECT * FROM ranked_messages WHERE rn = 1;
    """

    hot_data_dt = datetime.datetime.now() - datetime.timedelta(minutes=10)

    subq = (select(DronePosition, func.row_number().over(
        partition_by=DronePosition.drone_id,
        order_by=DronePosition.t.desc()
    ).label('rn'))
            .where(DronePosition.t >= hot_data_dt)  # TODO: try perf
            .cte(name='ordered_per_drone'))

    stmt = select(subq).where(subq.c.rn == 1)

    # print(stmt.compile(compile_kwargs={"literal_binds": True}))
    #
    # WITH ordered_per_drone AS ( SELECT
    #   droneposition.t AS t,
    #   droneposition.drone_id AS drone_id,
    #   droneposition.latitude AS latitude,
    #   droneposition.longitude AS longitude,
    #   row_number() OVER (PARTITION BY droneposition.drone_id ORDER BY droneposition.t DESC) AS rn
    # FROM droneposition
    # WHERE droneposition.t >= '2024-09-04 23:25:47.090874'
    # )
    # SELECT    ordered_per_drone.t,
    #           ordered_per_drone.drone_id,
    #           ordered_per_drone.latitude,
    #           ordered_per_drone.longitude,
    #           ordered_per_drone.rn
    # FROM ordered_per_drone
    # WHERE ordered_per_drone.rn = 1

    """
    +----+-------------+---------------+------------+-------+---------------+-------------+---------+-------+------+----------+-----------------------------+
    | id | select_type | table         | partitions | type  | possible_keys | key         | key_len | ref   | rows | filtered | Extra                       |
    +----+-------------+---------------+------------+-------+---------------+-------------+---------+-------+------+----------+-----------------------------+
    |  1 | PRIMARY     | <derived2>    | NULL       | ref   | <auto_key0>   | <auto_key0> | 8       | const |    1 |   100.00 | NULL                        |
    |  2 | DERIVED     | droneposition | NULL       | range | PRIMARY       | PRIMARY     | 5       | NULL  |    4 |   100.00 | Using where; Using filesort |
    +----+-------------+---------------+------------+-------+---------------+-------------+---------+-------+------+----------+-----------------------------+
    
    +----+-------------+---------------+------------+------+---------------+-------------+---------+-------+------+----------+----------------+
    | id | select_type | table         | partitions | type | possible_keys | key         | key_len | ref   | rows | filtered | Extra          |
    +----+-------------+---------------+------------+------+---------------+-------------+---------+-------+------+----------+----------------+
    |  1 | PRIMARY     | <derived2>    | NULL       | ref  | <auto_key0>   | <auto_key0> | 8       | const |    1 |   100.00 | NULL           |
    |  2 | DERIVED     | droneposition | NULL       | ALL  | NULL          | NULL        | NULL    | NULL  |    4 |   100.00 | Using filesort |
    +----+-------------+---------------+------------+------+---------------+-------------+---------+-------+------+----------+----------------+
    """

    return stmt
