-- Run with the Supabase SQL editor or psql after applying the security migrations.
-- This script raises an exception if a required security invariant is not met.

DO $security_tests$
BEGIN
  IF has_table_privilege('authenticated', 'public.franchises', 'TRUNCATE') THEN
    RAISE EXCEPTION 'authenticated must not have TRUNCATE on franchises';
  END IF;
  IF has_table_privilege('authenticated', 'public.franchises', 'TRIGGER') THEN
    RAISE EXCEPTION 'authenticated must not have TRIGGER on franchises';
  END IF;
  IF has_table_privilege('anon', 'public.franchises', 'SELECT') THEN
    RAISE EXCEPTION 'anon must not read franchises';
  END IF;

  IF NOT has_table_privilege('authenticated', 'public.franchise_public_profiles', 'SELECT') THEN
    RAISE EXCEPTION 'authenticated must read public franchise branding';
  END IF;
  IF has_table_privilege('authenticated', 'public.franchise_public_profiles', 'INSERT')
     OR has_table_privilege('authenticated', 'public.franchise_public_profiles', 'UPDATE')
     OR has_table_privilege('authenticated', 'public.franchise_public_profiles', 'DELETE')
     OR has_table_privilege('authenticated', 'public.franchise_public_profiles', 'TRUNCATE') THEN
    RAISE EXCEPTION 'authenticated must have read-only access to public franchise branding';
  END IF;
  IF has_table_privilege('anon', 'public.franchise_public_profiles', 'SELECT') THEN
    RAISE EXCEPTION 'anon must not read public franchise branding';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_class
    WHERE oid = 'public.franchise_public_profiles'::regclass
      AND relrowsecurity
      AND relkind = 'r'
  ) THEN
    RAISE EXCEPTION 'public franchise branding must be an RLS-protected table';
  END IF;

  IF to_regprocedure('public.rls_auto_enable()') IS NOT NULL
     OR to_regprocedure('dfm_private.rls_auto_enable()') IS NULL THEN
    RAISE EXCEPTION 'rls_auto_enable must exist only in dfm_private';
  END IF;
  IF has_function_privilege('anon', 'dfm_private.rls_auto_enable()', 'EXECUTE')
     OR has_function_privilege('authenticated', 'dfm_private.rls_auto_enable()', 'EXECUTE')
     OR has_function_privilege('service_role', 'dfm_private.rls_auto_enable()', 'EXECUTE') THEN
    RAISE EXCEPTION 'rls_auto_enable must not be directly executable by API roles';
  END IF;
  IF has_schema_privilege('anon', 'dfm_private', 'USAGE')
     OR has_schema_privilege('authenticated', 'dfm_private', 'USAGE')
     OR has_schema_privilege('service_role', 'dfm_private', 'USAGE') THEN
    RAISE EXCEPTION 'dfm_private must not be exposed to API roles';
  END IF;

  IF has_function_privilege('anon', 'dfm_private.sync_franchise_public_profile()', 'EXECUTE')
     OR has_function_privilege('authenticated', 'dfm_private.sync_franchise_public_profile()', 'EXECUTE')
     OR has_function_privilege('service_role', 'dfm_private.sync_franchise_public_profile()', 'EXECUTE') THEN
    RAISE EXCEPTION 'projection sync function must not be directly executable by API roles';
  END IF;
  IF NOT EXISTS (
    SELECT 1
    FROM pg_trigger
    WHERE tgname = 'sync_franchise_public_profile'
      AND tgrelid = 'public.franchises'::regclass
      AND NOT tgisinternal
  ) THEN
    RAISE EXCEPTION 'franchise branding synchronisation trigger is missing';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'franchise_public_profiles'
      AND column_name IN ('user_id', 'wizard_config', 'regeneration_count', 'is_locked')
  ) THEN
    RAISE EXCEPTION 'private franchise fields must not exist in the public projection';
  END IF;
END;
$security_tests$;
