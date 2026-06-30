-- Bootstrap the Postgres instance on first container start.
--
-- The main `seedbank` DB is created automatically from POSTGRES_DB; we only
-- need to enable the extensions the application relies on.

-- Required extensions on the application DB.
\c seedbank
CREATE EXTENSION IF NOT EXISTS "citext";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
