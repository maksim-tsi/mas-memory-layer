-- L2 Working Memory Full-Text Search Support
-- Migration: Add tsvector column and GIN index for keyword/entity search
-- Language: 'simple' (no stemming) for exact SKU, container ID, error code matching

-- Add tsvector column for search
ALTER TABLE working_memory
ADD COLUMN IF NOT EXISTS content_tsv tsvector;

-- Populate tsvector from existing content
UPDATE working_memory
SET content_tsv = to_tsvector('simple', content)
WHERE content_tsv IS NULL;

-- Create trigger to auto-update tsvector on INSERT/UPDATE
CREATE OR REPLACE FUNCTION working_memory_content_tsv_trigger() RETURNS trigger AS $$
BEGIN
    NEW.content_tsv := to_tsvector('simple', COALESCE(NEW.content, ''));
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tsvectorupdate ON working_memory;
CREATE TRIGGER tsvectorupdate
BEFORE INSERT OR UPDATE OF content
ON working_memory
FOR EACH ROW
EXECUTE FUNCTION working_memory_content_tsv_trigger();

-- Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS idx_working_memory_content_tsv
ON working_memory USING GIN (content_tsv);

-- Create composite index for session + CIAR filtering
CREATE INDEX IF NOT EXISTS idx_working_memory_session_ciar
ON working_memory(session_id, ciar_score DESC)
WHERE ttl_expires_at IS NULL OR ttl_expires_at > NOW();

-- Add comment for documentation
COMMENT ON COLUMN working_memory.content_tsv IS 'Full-text search vector using simple config (no stemming) for exact entity matching in supply chain context';
