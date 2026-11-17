import { describe, expect, it } from "vitest";
import { FRANCHISE_PUBLIC_PROFILE_FIELDS } from "../../packages/contracts/src/index";

describe("franchise public profile contract", () => {
  it("matches the approved public branding projection", () => {
    expect(FRANCHISE_PUBLIC_PROFILE_FIELDS).toEqual([
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
    ]);
  });

  it("does not expose ownership or private wizard state", () => {
    expect(FRANCHISE_PUBLIC_PROFILE_FIELDS).not.toContain("user_id");
    expect(FRANCHISE_PUBLIC_PROFILE_FIELDS).not.toContain("wizard_config");
    expect(FRANCHISE_PUBLIC_PROFILE_FIELDS).not.toContain("regeneration_count");
    expect(FRANCHISE_PUBLIC_PROFILE_FIELDS).not.toContain("is_locked");
  });
});
