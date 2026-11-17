-- Transaction-scoped integration test for the private franchise branding projection.
-- Run as the database owner in the Supabase SQL Editor.
-- The test account and franchise are always rolled back.

BEGIN;

DO $projection_test$
DECLARE
  test_user_id uuid := gen_random_uuid();
  test_franchise_id uuid;
BEGIN
  INSERT INTO auth.users (
    id, aud, role, email, raw_app_meta_data, raw_user_meta_data
  ) VALUES (
    test_user_id,
    'authenticated',
    'authenticated',
    'dfm-security-test-' || replace(test_user_id::text, '-', '') || '@example.invalid',
    '{}'::jsonb,
    '{}'::jsonb
  );

  INSERT INTO public.franchises (
    user_id,
    primary_name,
    secondary_name,
    abbreviated_name,
    primary_colour,
    secondary_colour,
    wizard_config,
    primary_logo_url,
    wordmark_logo_url,
    simplified_logo_url
  ) VALUES (
    test_user_id,
    'Security Test',
    'Original',
    'TEST',
    '#B7FF00',
    '#080A08',
    '{}'::jsonb,
    'test/primary.png',
    'test/wordmark.png',
    'test/simplified.png'
  )
  RETURNING id INTO test_franchise_id;

  IF NOT EXISTS (
    SELECT 1
    FROM public.franchise_public_profiles
    WHERE franchise_id = test_franchise_id
      AND primary_name = 'Security Test'
      AND secondary_name = 'Original'
  ) THEN
    RAISE EXCEPTION 'Projection insert synchronisation failed';
  END IF;

  UPDATE public.franchises
  SET secondary_name = 'Updated'
  WHERE id = test_franchise_id;

  IF NOT EXISTS (
    SELECT 1
    FROM public.franchise_public_profiles
    WHERE franchise_id = test_franchise_id
      AND secondary_name = 'Updated'
  ) THEN
    RAISE EXCEPTION 'Projection update synchronisation failed';
  END IF;

  DELETE FROM public.franchises
  WHERE id = test_franchise_id;

  IF EXISTS (
    SELECT 1
    FROM public.franchise_public_profiles
    WHERE franchise_id = test_franchise_id
  ) THEN
    RAISE EXCEPTION 'Projection cascade delete failed';
  END IF;

  DELETE FROM auth.users
  WHERE id = test_user_id;
END;
$projection_test$;

ROLLBACK;

SELECT 'franchise_projection_trigger: PASS (test data rolled back)' AS result;
