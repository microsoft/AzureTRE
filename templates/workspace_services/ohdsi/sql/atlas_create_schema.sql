CREATE SCHEMA IF NOT EXISTS :"schema_name"
AUTHORIZATION :"admin_role";

COMMENT ON SCHEMA :"schema_name" IS 'Schema containing tables to support WebAPI functionality';

GRANT USAGE ON SCHEMA :"schema_name" TO PUBLIC;

GRANT ALL ON SCHEMA :"schema_name" TO GROUP :"admin_role";

GRANT USAGE ON SCHEMA :"schema_name" TO GROUP :"app_role";

ALTER DEFAULT PRIVILEGES IN SCHEMA :"schema_name" GRANT
INSERT,
SELECT,
UPDATE,
DELETE, REFERENCES,
        TRIGGER ON TABLES TO :"app_role";

ALTER DEFAULT PRIVILEGES IN SCHEMA :"schema_name" GRANT
SELECT, USAGE ON SEQUENCES TO :"app_role";

ALTER DEFAULT PRIVILEGES IN SCHEMA :"schema_name" GRANT EXECUTE ON FUNCTIONS TO :"app_role";

ALTER DEFAULT PRIVILEGES IN SCHEMA :"schema_name" GRANT USAGE ON TYPES TO :"app_role";
