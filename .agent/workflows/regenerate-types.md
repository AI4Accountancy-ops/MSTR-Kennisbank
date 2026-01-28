---
description: Regenerate TypeScript types after database schema changes
---

# Regenerate Supabase Types

Na elke database schema wijziging (migrations, nieuwe tabellen, etc.) moeten de TypeScript types worden geregenereerd.

## Stappen

// turbo-all
1. Navigate to project root:
   ```bash
   cd /Users/roelsmelt/Antigravity/AI4A/ai4a-platform-git
   ```

2. Generate types:
   ```bash
   npx supabase gen types typescript --project-id esnhjfyohimafbgrngfh > src/integrations/supabase/types.ts
   ```

3. Verify the types file was updated:
   ```bash
   head -20 src/integrations/supabase/types.ts
   ```

## Wanneer Nodig?

- Na `apply_migration` via MCP
- Na handmatige schema wijzigingen in Supabase Dashboard
- Na toevoegen van enum values
- Na wijzigen van table/column names

## Let Op

- Types worden direct overschreven
- Commit altijd na type regeneration
