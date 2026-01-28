---
description: Git sync - commit and push all changes
---

# Git Sync

Commit en push alle lokale wijzigingen naar de repository.

## Stappen

// turbo-all
1. Navigate to project root:
   ```bash
   cd /Users/roelsmelt/Antigravity/AI4A/ai4a-platform-git
   ```

2. Stage all changes:
   ```bash
   git add -A
   ```

3. Check status:
   ```bash
   git status
   ```

4. Commit with descriptive message:
   ```bash
   git commit -m "feat: [beschrijving van wijzigingen]"
   ```

5. Pull latest (rebase):
   ```bash
   git pull --rebase
   ```

6. Push:
   ```bash
   git push
   ```

## Commit Message Conventies

| Prefix | Gebruik |
|--------|---------|
| `feat:` | Nieuwe feature |
| `fix:` | Bug fix |
| `docs:` | Documentatie |
| `refactor:` | Code refactoring |
| `style:` | UI/styling changes |
| `chore:` | Maintenance |
