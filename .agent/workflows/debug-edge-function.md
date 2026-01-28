---
description: Steps to debug and fix 500 errors in Supabase Edge Functions
---

1. **Check Logs**: 
   - Use `mcp_get_logs` for the `edge-function` service.
   - Look for specific Deno or Postgres errors.
2. **Local Validation**:
   - Check if the function uses unsupported Deno features (e.g., certain node polyfills).
   - Verify environment variables are set in the Supabase dashboard.
3. **RLS & Permissions**:
   - Verify if the `anon` or `service_role` key has enough permissions for the queried tables.
   - Check if RLS policies are blocking the edge function's service role (if applicable).
4. **Common Fixes**:
   - Use `AbortController` for manual timeouts.
   - Use `Web Crypto API` (or simple JS hashing) instead of certain Node `crypto` modules if Deno compatibility is an issue.
5. **Redeploy**:
   - Use `npx supabase functions deploy [name] --project-ref esnhjfyohimafbgrngfh`.
6. **Verify**:
   - Trigger the function via the UI and monitor logs again.
