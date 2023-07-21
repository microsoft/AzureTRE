create schema IF NOT EXISTS webapi_security;

DROP TABLE IF EXISTS webapi_security.security;

CREATE TABLE webapi_security.security
(
    email character varying(255),
    password character varying(255)
);

GRANT USAGE ON SCHEMA webapi_security TO PUBLIC;
GRANT ALL ON SCHEMA webapi_security TO GROUP ohdsi_admin;


do $$

	declare tables_count integer := 0;
	declare roles_count integer := 0;

begin
	
	while tables_count <> 3 loop
		raise notice 'Waiting for application security tables to become ready...';
	 	PERFORM pg_sleep(10);
	  	tables_count := (
			SELECT 	COUNT(*) 
			FROM 	pg_tables
			WHERE 	schemaname = 'webapi'
					AND tablename  in ('sec_user', 'sec_role', 'sec_user_role')
		);
   	end loop;

	raise notice 'All tables are ready.';

	while roles_count <> 3 loop
		raise notice 'Waiting for application security roles to become ready...';
	 	PERFORM pg_sleep(10);
	  	roles_count := (
			SELECT 	COUNT(*) 
			FROM 	webapi.sec_role
			WHERE 	id in (1, 2, 10)
		);
   	end loop;
	
	raise notice 'All roles are ready.';

   	raise notice 'Done.';

end$$;
