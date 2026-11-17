-- Verify the relocated RLS event-trigger function remains active.
-- Run as the database owner in the Supabase SQL Editor.
-- The temporary public table is dropped and the transaction is rolled back.

BEGIN;

CREATE TABLE public.__dfm_rls_event_trigger_verification (
  id integer PRIMARY KEY
);

DO $event_trigger_test$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_class
    WHERE oid = 'public.__dfm_rls_event_trigger_verification'::regclass
      AND relrowsecurity
  ) THEN
    RAISE EXCEPTION 'RLS event trigger did not enable RLS on a newly created public table';
  END IF;

  IF has_table_privilege('anon', 'public.__dfm_rls_event_trigger_verification', 'SELECT')
     OR has_table_privilege('authenticated', 'public.__dfm_rls_event_trigger_verification', 'SELECT')
     OR has_table_privilege('service_role', 'public.__dfm_rls_event_trigger_verification', 'SELECT') THEN
    RAISE EXCEPTION 'new public table unexpectedly inherited API role privileges';
  END IF;
END;
$event_trigger_test$;

DROP TABLE public.__dfm_rls_event_trigger_verification;

ROLLBACK;

SELECT 'rls_event_trigger_and_default_privileges: PASS' AS result;
