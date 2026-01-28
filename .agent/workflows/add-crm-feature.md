---
description: How to add a new tab or feature to the CRM system
---

1. **Check Existing Integration**: Read the `integrations` skill to see if the data source (e.g., Exact, KvK) is already documented.
2. **Update Database**: 
   - Add new columns or tables if needed.
   - Use the `database-rls` skill to ensure safe RLS policies (prevent recursion!).
   - Run `/regenerate-types` after DB changes.
3. **Add Integration Hub**: 
   - Add new API fetcher in `src/integrations/[provider]/`.
   - Update `src/integrations/supabase/types.ts` if not already handled.
4. **UI Component**:
   - Create a new component in `src/components/crm/Tabs/`.
   - Use the `ai4a-brand-guide` for standard card, button, and table layouts.
5. **Main CRM Page**:
   - Add the new tab to `src/pages/CRM.tsx`.
   - Ensure the administration selector correctly filters data for the new tab.
6. **Verify**:
   - Test with a mock division.
   - Verify RLS policies don't block access.
