-- Active Context Table (L1 Memory)
CREATE TABLE IF NOT EXISTS active_context (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    turn_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ttl_expires_at TIMESTAMP,
    CONSTRAINT unique_session_turn UNIQUE (session_id, turn_id)
);

CREATE INDEX idx_session_turn ON active_context(session_id, turn_id);
CREATE INDEX idx_expires ON active_context(ttl_expires_at) WHERE ttl_expires_at IS NOT NULL;

-- Working Memory Table (L2 Memory)
CREATE TABLE IF NOT EXISTS working_memory (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    fact_type VARCHAR(50) NOT NULL,  -- 'entity', 'preference', 'constraint', etc.
    content TEXT NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    source_turn_ids INTEGER[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    ttl_expires_at TIMESTAMP
);

CREATE INDEX idx_working_session ON working_memory(session_id);
CREATE INDEX idx_working_type ON working_memory(fact_type);
CREATE INDEX idx_working_expires ON working_memory(ttl_expires_at) WHERE ttl_expires_at IS NOT NULL;
