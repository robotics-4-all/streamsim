FROM python:3.10

WORKDIR /streamsim

RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg \
        libsm6 \
        libxext6 \
        libgl1 \
        libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# The mqtt and redis transports are commlib optional extras but are imported at
# module level by stream_simulator/connectivity/commlib_factory.py.
RUN pip install --no-cache-dir -U \
        "commlib-py[mqtt,redis] @ https://github.com/robotics-4-all/commlib-py/archive/devel.zip"

COPY ./ /streamsim

# Editable install so configurations/*.yaml and resources/ resolve from the
# source tree instead of a package copy without package_data.
RUN pip install --no-cache-dir --no-deps -e .

WORKDIR /

COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    STREAMSIM_UID=streamsim

EXPOSE 1883 8883

ENTRYPOINT ["/entrypoint.sh"]
