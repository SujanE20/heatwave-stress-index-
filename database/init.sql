-- HEATSHIELD INDIA - PostgreSQL/PostGIS initialization
-- Runs automatically on first start of the `db` container.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;

COMMENT ON EXTENSION postgis IS
  'PostGIS is provisioned for spatial operations. Ward geometries are stored as GeoJSON (JSONB)
   by the application and rendered by Leaflet; a migration to native geometry columns is
   documented in docs/architecture.md.';

-- Optional: database-level role grant for the app user (created by POSTGRES_USER env).
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = current_user) THEN
    EXECUTE format('GRANT ALL ON SCHEMA public TO %I', current_user);
  END IF;
END $$;