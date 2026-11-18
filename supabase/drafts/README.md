# DRL persistence migration drafts

The files in this directory are design drafts and must not be applied directly.

## Required generation sequence

1. Validate \`drl_mode_persistence.sql\` and \`drl_mode_persistence_rpc.sql\`
   together against a disposable local PostgreSQL 17 / Supabase stack.
2. Run the security and integration SQL tests under
   \`supabase/tests/database/\`.
3. Generate the registered migration filename using
   \`supabase migration new drl_mode_persistence\`.
4. Concatenate the reviewed schema and RPC drafts into that generated file.
5. Review the exact diff and run repository CI.
6. Obtain separate approval before applying any migration to hosted JARVIS.

Do not manually re-apply \`20261117024400_create_franchises_and_public_profiles\`;
it is already applied in the live project and is restored only to repair Git
migration history.

## Design boundary

- All 14 mode-specific tables remain inside \`dfm_private\`.
- Classic and Draft have separate tables and separate server-only RPC wrappers.
- No API role receives direct access to the private schema or its tables.
- Only the eight \`public.dfm_*_persist_*\` wrappers grant EXECUTE to
  \`service_role\`; wrappers are not executable by PUBLIC, anon or authenticated.
- No service-role credential, database password or privileged URL belongs in
  source code or browser-visible configuration.
- The server adapter receives a preconfigured RPC executor from trusted server
  composition; it does not construct or expose credentials.
- No paid service or Cloudflare resource is required.
