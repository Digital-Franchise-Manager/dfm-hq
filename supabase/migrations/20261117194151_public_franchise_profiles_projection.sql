BEGIN;

DROP VIEW public.franchise_public_profiles;

CREATE TABLE public.franchise_public_profiles (
  franchise_id uuid PRIMARY KEY
    REFERENCES public.franchises(id) ON DELETE CASCADE,
  primary_name text NOT NULL,
  secondary_name text NOT NULL,
  abbreviated_name varchar(4) NOT NULL,
  primary_colour varchar(7) NOT NULL,
  secondary_colour varchar(7) NOT NULL,
  tertiary_colour varchar(7),
  accent_colour varchar(7),
  primary_logo_url text NOT NULL,
  wordmark_logo_url text NOT NULL,
  simplified_logo_url text NOT NULL
);

ALTER TABLE public.franchise_public_profiles
  ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Authenticated users can read public franchise branding"
ON public.franchise_public_profiles
FOR SELECT
TO authenticated
USING (true);

REVOKE ALL PRIVILEGES
ON TABLE public.franchise_public_profiles
FROM PUBLIC, anon, authenticated, service_role;

GRANT SELECT
ON TABLE public.franchise_public_profiles
TO authenticated, service_role;

CREATE OR REPLACE FUNCTION dfm_private.sync_franchise_public_profile()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $function$
BEGIN
  IF TG_OP = 'DELETE' THEN
    DELETE FROM public.franchise_public_profiles
    WHERE franchise_id = OLD.id;
    RETURN OLD;
  END IF;

  INSERT INTO public.franchise_public_profiles (
    franchise_id,
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
  )
  VALUES (
    NEW.id,
    NEW.primary_name,
    NEW.secondary_name,
    NEW.abbreviated_name,
    NEW.primary_colour,
    NEW.secondary_colour,
    NEW.tertiary_colour,
    NEW.accent_colour,
    NEW.primary_logo_url,
    NEW.wordmark_logo_url,
    NEW.simplified_logo_url
  )
  ON CONFLICT (franchise_id) DO UPDATE SET
    primary_name = EXCLUDED.primary_name,
    secondary_name = EXCLUDED.secondary_name,
    abbreviated_name = EXCLUDED.abbreviated_name,
    primary_colour = EXCLUDED.primary_colour,
    secondary_colour = EXCLUDED.secondary_colour,
    tertiary_colour = EXCLUDED.tertiary_colour,
    accent_colour = EXCLUDED.accent_colour,
    primary_logo_url = EXCLUDED.primary_logo_url,
    wordmark_logo_url = EXCLUDED.wordmark_logo_url,
    simplified_logo_url = EXCLUDED.simplified_logo_url;

  RETURN NEW;
END;
$function$;

REVOKE ALL PRIVILEGES
ON FUNCTION dfm_private.sync_franchise_public_profile()
FROM PUBLIC, anon, authenticated, service_role;

CREATE TRIGGER sync_franchise_public_profile
AFTER INSERT OR UPDATE OF
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
ON public.franchises
FOR EACH ROW
EXECUTE FUNCTION dfm_private.sync_franchise_public_profile();

INSERT INTO public.franchise_public_profiles (
  franchise_id,
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
)
SELECT
  id,
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
FROM public.franchises
ON CONFLICT (franchise_id) DO UPDATE SET
  primary_name = EXCLUDED.primary_name,
  secondary_name = EXCLUDED.secondary_name,
  abbreviated_name = EXCLUDED.abbreviated_name,
  primary_colour = EXCLUDED.primary_colour,
  secondary_colour = EXCLUDED.secondary_colour,
  tertiary_colour = EXCLUDED.tertiary_colour,
  accent_colour = EXCLUDED.accent_colour,
  primary_logo_url = EXCLUDED.primary_logo_url,
  wordmark_logo_url = EXCLUDED.wordmark_logo_url,
  simplified_logo_url = EXCLUDED.simplified_logo_url;

COMMIT;
