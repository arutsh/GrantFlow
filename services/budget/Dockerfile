FROM python:3.13

WORKDIR /app

# Install PostgreSQL client
RUN apt-get update && apt-get install -y postgresql-client && rm -rf /var/lib/apt/lists/*

COPY services/budget/requirements.txt .
RUN --mount=type=cache,target=/root/.cache pip install -r requirements.txt

COPY shared ./shared
COPY services/budget/. .
RUN chmod +x entrypoint.sh
RUN chmod +x shared/healthcheck.sh

CMD ["./entrypoint.sh"]

