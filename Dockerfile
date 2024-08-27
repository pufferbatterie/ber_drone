FROM python:3.11-alpine

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . .

CMD python main.py

# docker build . -t drone_logger
# docker run --rm --device=/dev/ttyUSB0 drone_logger
# docker run --rm --name ber_drone -e -it -p8000:8000 drone_logger
