# ProjectVault

> AI-powered project management that remembers, understands, and learns from your projects.

## What it does

ProjectVault is built for PMs and technical leads managing 10–20+ simultaneous projects. It turns your entire project history — updates, GitHub commits, AI conversations, decisions — into an intelligent, searchable knowledge base.

**Key features:**
- **Time Machine Snapshots** — version control for your project with AI-generated narratives explaining what changed and why
- **Temporal Semantic Search** — natural language search across all projects, all time, all sources
- **AI Retrospectives** — auto-generated structured retrospectives backed by actual project data
- **GitHub Integration** — sync commits, PRs, and issues; everything becomes searchable
- **AI Health Scores** — Claude analyzes your project and scores it 0–100 with explanations
- **Per-project AI Chat** — ask anything about a project, grounded in its actual data
- **Collaboration** — share projects via link with role-based permissions (owner/editor/viewer)

## Stack

- **Frontend:** Streamlit
- **Database & Auth:** Supabase (PostgreSQL + pgvector + Auth + Storage)
- **Primary AI:** Anthropic Claude (`claude-sonnet-4-6`)
- **Embeddings:** OpenAI `text-embedding-3-small`
- **Long-context:** Google Gemini 1.5 Pro
- **GitHub:** PyGitHub

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/your-username/projectvault
cd projectvault
pip install -r requirements.txt
```

### 2. Set up Supabase

1. Create a project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** and run the full schema:
   ```
   database/schema.sql
   ```
3. Copy your project URL and anon key

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env with your keys
```

Required:
- `SUPABASE_URL` — from Supabase project settings
- `SUPABASE_KEY` — anon/public key
- `ANTHROPIC_API_KEY` — from [console.anthropic.com](https://console.anthropic.com)

Optional (enables more features):
- `OPENAI_API_KEY` — for semantic search embeddings
- `GEMINI_API_KEY` — for long-context analysis
- `GITHUB_TOKEN` — for GitHub sync

### 4. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501)

### 5. Seed demo data (optional)

```bash
python scripts/seed_demo.py
```

This creates 3 realistic projects with 6 months of history. Login with `demo@projectvault.app` / `demo1234`.

## Project Structure

```
projectvault/
├── app.py                    # Entry point
├── pages/
│   ├── 1_login.py            # Auth (sign in / sign up)
│   ├── 2_dashboard.py        # All projects overview
│   ├── 3_project.py          # Project detail (6 tabs)
│   ├── 4_search.py           # Semantic search
│   ├── 5_shared_project.py   # Public shared view
│   └── 6_settings.py         # Account & API keys
├── services/
│   ├── auth_service.py       # Supabase auth
│   ├── db_service.py         # All DB operations
│   ├── ai_service.py         # Claude / OpenAI / Gemini
│   ├── snapshot_service.py   # Time machine snapshots
│   ├── github_service.py     # GitHub sync
│   ├── search_service.py     # Embeddings + vector search
│   └── retrospective_service.py
├── components/
│   ├── timeline.py           # Plotly snapshot timeline
│   ├── ai_chat.py            # Per-project AI chat
│   ├── snapshot_compare.py   # Side-by-side diff
│   ├── collaborators.py      # Team management
│   ├── share_modal.py        # Sharing UI
│   └── search_results.py     # Search result cards
├── utils/
│   ├── formatting.py
│   ├── validators.py
│   └── encryption.py
├── database/
│   └── schema.sql            # Full Supabase schema
└── scripts/
    └── seed_demo.py          # Demo data seeder
```

## Deploy to Streamlit Cloud

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo, set `app.py` as main file
4. Add all environment variables in the Secrets section

## Feature Flags

API keys can be added globally via `.env` or per-session in **Settings → API Keys**. Session keys take precedence, so users can bring their own.

---

*Built by Jhanvi Damwani · Powered by Anthropic Claude, Supabase, and Streamlit*
