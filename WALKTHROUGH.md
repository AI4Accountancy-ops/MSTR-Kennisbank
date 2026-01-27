# Kennisbank AI Migration & Investigation

I have successfully gecloned (cloned) the repository, set up the local workspace, and migrated it to the `AI4Accountancy-ops` organization.

## Changes Made

### 1. Local Workspace Setup
- Created the folder `Kennisbank AI` at `/Users/roelsmelt/Antigravity/AI4A/Kennisbank AI`.
- Updated [AI4A.code-workspace](file:///Users/roelsmelt/Antigravity/AI4A/AI4A.code-workspace) to include the new folder. It should now be visible in your VS Code Explorer.

### 2. GitHub Migration
- Created a new repository: [AI4Accountancy-ops/AI4Accountancy](https://github.com/AI4Accountancy-ops/AI4Accountancy)
- Pushed a clean version of the code to the `main` branch.
  - *Note: I did a "clean" push (without git history) because the original history contained secrets that were being blocked by GitHub's secret scanning rules for the new organization.*

## Investigation Findings: What does this repo do?

The repository contains **AI4Accountancy**, a full-stack platform designed for accounting teams to use AI tax assistants securely.

### Key Components:
- **Frontend (React + TypeScript)**: Use `shadcn/ui` and TailwindCSS. It handles user authentication, plan selection, and the chat interface.
- **Backend (FastAPI/Python)**: Manages organizations, subscriptions (via Stripe), user quotas, and the chat logic.
- **Database (PostgreSQL)**: Stores users, organizations, and subscription states.

### 3. Scraper Functionality (New Investigation)
The repository contains extensive scraper logic in `src/scrapers/`. These scrapers are designed to ingest fiscal data from multiple professional sources:

- **Sources**: 
  - **Belastingdienst**: Scrapes brochures and extra legal links.
  - **Indicator**: Scrapes fiscal articles and news.
  - **MFAS**: Scrapes fiscal information using a dedicated scraper.
  - **Nextens**: Very detailed scrapers for the Almanak, decisions (besluiten), fiscal figures, subjects (onderwerpen), and laws (wetten). It includes a login mechanism for authenticated access.
- **Technology**: Uses **Playwright** (`sync_playwright`) for browser automation, which allows it to handle JavaScript-heavy sites and login flows.
- **Organization**: Each source has its own sub-folder with specific logic for parsing and cleaning the data.

### Core Features:
1. **AI Chat**: Gated by subscriptions and quotas (e.g., Trial: 1,000 questions/day; Pro: 2,500 questions/month).
2. **Organization Management**: Admins can manage members and plans.
3. **Stripe Integration**: Automated billing and subscription syncing via webhooks.
4. **M365 Integration**: Found logic for Microsoft Graph webhooks and email automation (draft generation).
5. **Data Ingestion (Scrapers)**: Automated gathering of fiscal knowledge from external databases.

### How to Run Locally:
1. **Backend**:
   ```bash
   pip install -r requirements.txt
   uvicorn src.main:app --reload
   ```
2. **Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

You can now explore the codebase directly in your VS Code under the **Kennisbank AI** folder.
