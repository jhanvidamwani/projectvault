-- ProjectVault — Deadlines, Checklists, Health Override
-- Run this in the Supabase SQL editor after the base schema.

-- ============================================================
-- PROJECTS: deadline + manual health override
-- ============================================================
ALTER TABLE projects ADD COLUMN IF NOT EXISTS deadline DATE;
ALTER TABLE projects ADD COLUMN IF NOT EXISTS health_status_override TEXT
  CHECK (health_status_override IN ('green', 'yellow', 'red'));

-- ============================================================
-- CHECKLISTS — per-project to-do items with optional deadlines
-- ============================================================
CREATE TABLE IF NOT EXISTS checklists (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  is_done BOOLEAN DEFAULT FALSE,
  deadline DATE,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_checklists_project ON checklists(project_id);
CREATE INDEX IF NOT EXISTS idx_checklists_deadline ON checklists(deadline) WHERE is_done = FALSE;
CREATE INDEX IF NOT EXISTS idx_projects_deadline ON projects(deadline) WHERE status IN ('active','paused');

-- ============================================================
-- REMINDER LOG — prevent duplicate deadline emails
-- ============================================================
CREATE TABLE IF NOT EXISTS reminder_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  target_type TEXT NOT NULL CHECK (target_type IN ('project', 'checklist')),
  target_id UUID NOT NULL,
  days_before INTEGER NOT NULL,
  sent_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (target_type, target_id, days_before)
);

CREATE INDEX IF NOT EXISTS idx_reminder_log_target ON reminder_log(target_type, target_id);

-- ============================================================
-- RLS for checklists — accessible to anyone with project access
-- ============================================================
ALTER TABLE checklists ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Checklists: accessible via project access" ON checklists
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM projects
      WHERE projects.id = checklists.project_id
        AND (projects.owner_id = auth.uid() OR EXISTS (
          SELECT 1 FROM collaborators c
          WHERE c.project_id = projects.id AND c.user_id = auth.uid()
        ))
    )
  );

CREATE POLICY "Checklists: editors and owners can write" ON checklists
  FOR ALL USING (
    EXISTS (
      SELECT 1 FROM projects
      WHERE projects.id = checklists.project_id
        AND (projects.owner_id = auth.uid() OR EXISTS (
          SELECT 1 FROM collaborators c
          WHERE c.project_id = projects.id AND c.user_id = auth.uid() AND c.role IN ('owner','editor')
        ))
    )
  );
