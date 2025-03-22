FROM python:3.10

WORKDIR /streamsim

RUN apt update && apt upgrade -y && apt install ffmpeg libsm6 libxext6  -y

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

RUN pip install https://github.com/robotics-4-all/commlib-py/archive/devel.zip -U

COPY ./ /streamsim

RUN pip install .

WORKDIR /

COPY ./entrypoint.sh /entrypoint.sh

ENV BROKER_HOST=0.0.0.0
ENV BROKER_PORT=1883
ENV BROKER_SSL=False
ENV BROKER_USERNAME=
ENV BROKER_PASSWORD=
ENV USE_REDIS=True

CMD ["python", "/streamsim/stream_simulator/bin/main.py", "test"]
