CREATE TABLE IF NOT EXISTS public.franchises (
  id uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL UNIQUE,
  primary_name text NOT NULL,
  secondary_name text NOT NULL,
  abbreviated_name varchar(4) NOT NULL,
  primary_colour varchar(7) NOT NULL,
  secondary_colour varchar(7) NOT NULL,
  tertiary_colour varchar(7),
  accent_colour varchar(7),
  wizard_config jsonb NOT NULL,
  primary_logo_url text NOT NULL,
  wordmark_logo_url text NOT NULL,
  simplified_logo_url text NOT NULL,
  regeneration_count int DEFAULT 0 NOT NULL,
  is_locked boolean DEFAULT true NOT NULL,
  created_at timestamptz DEFAULT timezone('utc'::text, now()) NOT NULL
);

ALTER TABLE public.franchises ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Owners have full control over their franchise data"
ON public.franchises;

CREATE POLICY "Owners have full control over their franchise data"
ON public.franchises
FOR ALL
TO authenticated
USING ((SELECT auth.uid()) = user_id)
WITH CHECK ((SELECT auth.uid()) = user_id);

-- Explicit table privileges: no anonymous access; authenticated operations remain subject to RLS.
REVOKE ALL ON TABLE public.franchises FROM anon;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.franchises TO authenticated;

-- This view deliberately uses the view owner's privileges (PostgreSQL's default
-- security-definer view behavior) so opponents can read only the projected branding
-- columns despite the base table's owner-only RLS. The projection excludes private fields.
CREATE OR REPLACE VIEW public.franchise_public_profiles
WITH (security_barrier = true)
AS
SELECT
  id AS franchise_id,
  primary_name,
  secondary_name,
  abbreviated_name,
  primary_colour,
  secondary_colour,
  tertiary_colour,
  accent_colour,
  primary_logo_url,
  wordmark_logo_url,
  simplified_logo_url
FROM public.franchises;

REVOKE ALL ON TABLE public.franchise_public_profiles FROM PUBLIC, anon;
GRANT SELECT ON TABLE public.franchise_public_profiles TO authenticated;
