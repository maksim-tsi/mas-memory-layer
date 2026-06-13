-- Add provenance/project metadata to L2 working_memory records.
ALTER TABLE working_memory
ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}';

CREATE INDEX IF NOT EXISTS idx_working_metadata_project
ON working_memory ((metadata->>'project_id'));
