/**
 * Public, non-sensitive contract for the franchise branding projection.
 * Keep this field list aligned with the database projection migration.
 */
export const FRANCHISE_PUBLIC_PROFILE_FIELDS = [
  "franchise_id",
  "primary_name",
  "secondary_name",
  "abbreviated_name",
  "primary_colour",
  "secondary_colour",
  "tertiary_colour",
  "accent_colour",
  "primary_logo_url",
  "wordmark_logo_url",
  "simplified_logo_url"
] as const;

export type FranchisePublicProfileField =
  (typeof FRANCHISE_PUBLIC_PROFILE_FIELDS)[number];

export interface FranchisePublicProfile {
  franchise_id: string;
  primary_name: string;
  secondary_name: string;
  abbreviated_name: string;
  primary_colour: string;
  secondary_colour: string;
  tertiary_colour: string | null;
  accent_colour: string | null;
  primary_logo_url: string;
  wordmark_logo_url: string;
  simplified_logo_url: string;
}
