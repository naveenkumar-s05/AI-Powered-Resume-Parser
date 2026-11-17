-- Bootstrap a local PostgreSQL role + database for the resume parser.
-- Run as the postgres superuser:
--   psql -U postgres -f scripts/init_postgres.sql
-- Safe to re-run.
--
-- NOTE: the role password below is 'resume'. It must match the password in
-- your DATABASE_URL. If you prefer another password, either change it below
-- or run:  ALTER ROLE resume WITH PASSWORD '<your-password>';

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'resume') THEN
    CREATE ROLE resume WITH LOGIN PASSWORD 'resume';
  END IF;
END
$$;

SELECT 'CREATE DATABASE resume_db OWNER resume'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'resume_db')\gexec

\connect resume_db
GRANT ALL ON SCHEMA public TO resume;
