FROM python:3.13

WORKDIR /app

COPY services/worker/requirements.txt .
RUN --mount=type=cache,target=/root/.cache pip install -r requirements.txt

COPY shared ./shared
COPY services/worker/ .

ENV PYTHONPATH=/app
