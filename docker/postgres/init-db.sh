#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE grandflow_users;
    CREATE DATABASE grandflow_budget;
    CREATE DATABASE grandflow_ai;
EOSQL
