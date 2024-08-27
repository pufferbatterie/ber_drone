#!/usr/bin/env bash

docker build . -t drone_logger
docker run --rm --name ber_drone -it -p8000:8000 drone_logger