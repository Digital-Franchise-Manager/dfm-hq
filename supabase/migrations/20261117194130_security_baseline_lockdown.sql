BEGIN;

CREATE SCHEMA IF NOT EXISTS dfm_private AUTHORIZATION postgres;
REVOKE ALL ON SCHEMA dfm_private
FROM PUBLIC, anon, authenticated, service_role;

REVOKE ALL PRIVILEGES ON TABLE public.franchises
FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE public.franchises
TO authenticated;

REVOKE ALL PRIVILEGES ON TABLE public.franchise_public_profiles
FROM PUBLIC, anon, authenticated, service_role;
GRANT SELECT
ON TABLE public.franchise_public_profiles
TO authenticated, service_role;

ALTER DEFAULT PRIVILEGES
FOR ROLE postgres IN SCHEMA public
REVOKE ALL PRIVILEGES ON TABLES
FROM PUBLIC, anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES
FOR ROLE postgres IN SCHEMA public
REVOKE ALL PRIVILEGES ON SEQUENCES
FROM PUBLIC, anon, authenticated, service_role;

ALTER DEFAULT PRIVILEGES
FOR ROLE postgres IN SCHEMA public
REVOKE EXECUTE ON FUNCTIONS
FROM PUBLIC, anon, authenticated, service_role;

REVOKE ALL PRIVILEGES
ON FUNCTION public.rls_auto_enable()
FROM PUBLIC, anon, authenticated, service_role;

ALTER FUNCTION public.rls_auto_enable()
SET SCHEMA dfm_private;

REVOKE ALL PRIVILEGES
ON FUNCTION dfm_private.rls_auto_enable()
FROM PUBLIC, anon, authenticated, service_role;

COMMIT;
