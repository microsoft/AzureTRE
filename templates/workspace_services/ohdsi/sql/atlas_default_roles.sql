-- This gives each new user access to all sources plus 'Atlas User' role.

CREATE OR REPLACE FUNCTION function_default_user_roles() RETURNS TRIGGER AS
$BODY$
BEGIN
    INSERT INTO webapi.sec_user_role (role_id, user_id)
    SELECT r.id as role_id, new.id as user_id
    FROM webapi.sec_role as r
    WHERE r.name LIKE 'Source user%' OR r.name = 'Atlas users';

    RETURN new;
END;
$BODY$
language plpgsql;


DROP TRIGGER IF EXISTS trigger_sec_user_insert ON webapi.sec_user;

CREATE TRIGGER trigger_sec_user_insert
AFTER INSERT ON webapi.sec_user
FOR EACH ROW
EXECUTE PROCEDURE function_default_user_roles();

DO $$
BEGIN
  RAISE NOTICE 'Finished setting up default roles procedures.';
END $$;
