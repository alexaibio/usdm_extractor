FROM python:3.11-slim

WORKDIR /home

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p ./data/output
RUN mkdir -p ./data/input

COPY ./app ./app
COPY ./.env ./.env
COPY ./requirements.txt ./
COPY ./docker-entrypoint.sh ./

RUN chmod +x ./docker-entrypoint.sh

RUN pip install --no-cache-dir --upgrade pip &&\
    pip install -r requirements.txt &&\
    rm -rf /root/.cache/pip &&\
    rm requirements.txt

ENTRYPOINT ["./docker-entrypoint.sh"]