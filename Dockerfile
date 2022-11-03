FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8

COPY requirements.txt /
RUN pip3 install --no-cache-dir -r /requirements.txt

ENV MAX_WORKERS=4
COPY ./grontopi /app

