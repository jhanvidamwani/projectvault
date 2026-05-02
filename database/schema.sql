-- ProjectVault Database Schema
-- Run this in your Supabase SQL editor

-- Enable pgvector extension for semantic search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT,
  avatar_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- PROJECTS
-- ============================================================
CREATE TABLE IF NOT EXISTS projects (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'archived')),
  health_score INTEGER CHECK (health_score BETWEEN 0 AND 100),
  health_explanation TEXT,
  tags TEXT[],
  github_repo_url TEXT,
  share_token UUID DEFAULT gen_random_uuid(),
  share_password_hash TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SNAPSHOTS (Time Machine)
-- ============================================================
CREATE TABLE IF NOT EXISTS snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  created_by UUID REFERENCES users(id),
  title TEXT NOT NULL,
  description TEXT,
  ai_narrative TEXT,
  snapshot_data JSONB NOT NULL DEFAULT '{}',
  trigger TEXT DEFAULT 'manual' CHECK (trigger IN ('manual', 'auto', 'milestone', 'integration')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- UPDATES / ACTIVITY LOG
-- ============================================================
CREATE TABLE IF NOT EXISTS updates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id),
  content TEXT NOT NULL,
  update_type TEXT DEFAULT 'note' CHECK (update_type IN ('note', 'decision', 'milestone', 'blocker', 'pivot')),
  ai_summary TEXT,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INTEGRATIONS
-- ============================================================
CREATE TABLE IF NOT EXISTS integrations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id),
  integration_type TEXT NOT NULL CHECK (integration_type IN ('github', 'claude', 'chatgpt', 'gemini')),
  config JSONB DEFAULT '{}',
  status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'error')),
  last_synced_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- VECTOR EMBEDDINGS (Semantic Search)
-- ============================================================
CREATE TABLE IF NOT EXISTS embeddings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL CHECK (source_type IN ('update', 'snapshot', 'github_commit', 'ai_conversation')),
  source_id UUID NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(1536),
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for fast cosine similarity search
CREATE INDEX IF NOT EXISTS idx_embeddings_vector
  ON embeddings USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

-- ============================================================
-- RETROSPECTIVES
-- ============================================================
CREATE TABLE IF NOT EXISTS retrospectives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  generated_by UUID REFERENCES users(id),
  trigger TEXT DEFAULT 'manual' CHECK (trigger IN ('manual', 'milestone', 'scheduled')),
  content JSONB NOT NULL DEFAULT '{}',
  ai_model_used TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- COLLABORATORS
-- ============================================================
CREATE TABLE IF NOT EXISTS collaborators (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  user_id UUID REFERENCES users(id),
  role TEXT DEFAULT 'viewer' CHECK (role IN ('owner', 'editor', 'viewer')),
  invited_by UUID REFERENCES users(id),
  joined_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(project_id, user_id)
);

-- ============================================================
-- VECTOR SEARCH FUNCTION
-- ============================================================
CREATE OR REPLACE FUNCTION search_embeddings(
  query_embedding VECTOR(1536),
  p_project_ids UUID[],
  match_threshold FLOAT DEFAULT 0.75,
  match_count INT DEFAULT 10
)
RETURNS TABLE(id UUID, content TEXT, source_type TEXT, source_id UUID, project_id UUID, similarity FLOAT, metadata JSONB)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    e.id,
    e.content,
    e.source_type,
    e.source_id,
    e.project_id,
    1 - (e.embedding <=> query_embedding) AS similarity,
    e.metadata
  FROM embeddings e
  WHERE e.project_id = ANY(p_project_ids)
    AND 1 - (e.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE updates ENABLE ROW LEVEL SECURITY;
ALTER TABLE integrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE retrospectives ENABLE ROW LEVEL SECURITY;
ALTER TABLE collaborators ENABLE ROW LEVEL SECURITY;

-- Projects: owner can do anything; collaborators can read
CREATE POLICY "Projects: owner full access" ON projects
  FOR ALL USING (auth.uid() = owner_id);

CREATE POLICY "Projects: collaborators can read" ON projects
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM collaborators
      WHERE collaborators.project_id = projects.id
        AND collaborators.user_id = auth.uid()
    )
  );

-- Snapshots: accessible if user can access the project
CREATE POLICY "Snapshots: accessible via project access" ON snapshots
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM projects
      WHERE projects.id = snapshots.project_id
        AND (projects.owner_id = auth.uid() OR EXISTS (
          SELECT 1 FROM collaborators
          WHERE collaborators.project_id = projects.id
            AND collaborators.user_id = auth.uid()
        ))
    )
  );

CREATE POLICY "Snapshots: owner can insert" ON snapshots
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM projects
      WHERE projects.id = project_id AND projects.owner_id = auth.uid()
    )
  );

-- Updates: accessible via project access
CREATE POLICY "Updates: accessible via project access" ON updates
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM projects
      WHERE projects.id = updates.project_id
        AND (projects.owner_id = auth.uid() OR EXISTS (
          SELECT 1 FROM collaborators c
          WHERE c.project_id = projects.id AND c.user_id = auth.uid()
        ))
    )
  );

CREATE POLICY "Updates: editors and owners can insert" ON updates
  FOR INSERT WITH CHECK (
    EXISTS (
      SELECT 1 FROM projects
      WHERE projects.id = project_id
        AND (projects.owner_id = auth.uid() OR EXISTS (
          SELECT 1 FROM collaborators c
          WHERE c.project_id = project_id AND c.user_id = auth.uid() AND c.role IN ('owner', 'editor')
        ))
    )
  );
