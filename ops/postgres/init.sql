-- Bootstrap auxiliary databases that share the Postgres instance with the
-- main `seedbank` DB. Runs once on first container start.
--
-- The main `seedbank` DB is created automatically from POSTGRES_DB; we just
-- add `mlflow` here so the MLflow tracking server has its own backing store.

SELECT 'CREATE DATABASE mlflow'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'mlflow')\gexec

-- Required extensions on the application DB.
\c seedbank
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
