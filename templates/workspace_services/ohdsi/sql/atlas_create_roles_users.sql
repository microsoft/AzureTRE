-- Quote identifiers and values with psql. A retry can reuse roles already created.
SELECT format('CREATE ROLE %I CREATEDB REPLICATION', :'admin_role')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'admin_role') \gexec
COMMENT ON ROLE :"admin_role" IS 'Administration group for OHDSI applications';

SELECT format('CREATE ROLE %I', :'app_role')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'app_role') \gexec
COMMENT ON ROLE :"app_role" IS 'Application group for OHDSI applications';

SELECT format('CREATE ROLE %I LOGIN', :'admin_username')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'admin_username') \gexec
ALTER ROLE :"admin_username" PASSWORD :'admin_password' VALID UNTIL 'infinity';
GRANT :"admin_role" TO :"admin_username";
COMMENT ON ROLE :"admin_username" IS 'Admin user account for OHDSI applications';

SELECT format('CREATE ROLE %I LOGIN', :'app_username')
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'app_username') \gexec
ALTER ROLE :"app_username" PASSWORD :'app_password' VALID UNTIL 'infinity';
GRANT :"app_role" TO :"app_username";
COMMENT ON ROLE :"app_username" IS 'Application user account for OHDSI applications';

GRANT ALL ON DATABASE :"database_name" TO GROUP :"admin_role";
GRANT CONNECT, TEMPORARY ON DATABASE :"database_name" TO GROUP :"app_role";
