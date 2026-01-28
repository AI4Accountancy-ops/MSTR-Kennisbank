---
description: Deploy an Edge Function to Supabase production
---

# Deploy Edge Function

Deployt een Supabase Edge Function naar productie.

## Stappen

// turbo-all
1. Navigate to project root:
   ```bash
   cd /Users/roelsmelt/Antigravity/AI4A/ai4a-platform-git
   ```

2. Deploy the function (replace `[function-name]` with actual name):
   ```bash
   npx supabase functions deploy [function-name] --project-ref esnhjfyohimafbgrngfh
   ```

3. Verify deployment in Supabase Dashboard:
   - https://supabase.com/dashboard/project/esnhjfyohimafbgrngfh/functions

## Veelgebruikte Functions

| Function | Doel |
|----------|------|
| `send-auth-email` | Custom auth emails (login, invite, recovery) |
| `invite-user` | Kantoor user invites |
| `invite-admin` | Platform admin invites |
| `invantive-sync` | Exact Online data sync |
| `exact-oauth-start` | Exact OAuth flow start |
| `exact-oauth-callback` | Exact OAuth callback |

## Troubleshooting

- **Docker warning**: Negeren - we gebruiken geen lokale Docker
- **CORS errors**: Check corsHeaders in de function
- **Auth errors**: Check Supabase logs in dashboard
