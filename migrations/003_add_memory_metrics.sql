-- Add memory metrics to working_memory table
ALTER TABLE working_memory
ADD COLUMN IF NOT EXISTS ciar_score FLOAT DEFAULT 0.0,
ADD COLUMN IF NOT EXISTS certainty FLOAT DEFAULT 0.7,
ADD COLUMN IF NOT EXISTS impact FLOAT DEFAULT 0.5,
ADD COLUMN IF NOT EXISTS recency_boost FLOAT DEFAULT 1.0,
ADD COLUMN IF NOT EXISTS last_accessed TIMESTAMP,
ADD COLUMN IF NOT EXISTS access_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS age_decay FLOAT DEFAULT 1.0;

-- Create index on ciar_score for performance
CREATE INDEX IF NOT EXISTS idx_working_ciar ON working_memory(ciar_score);
CREATE INDEX IF NOT EXISTS idx_working_accessed ON working_memory(last_accessed);
