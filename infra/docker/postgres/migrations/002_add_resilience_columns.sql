-- Migration: Add resilience columns for LLM Worker
-- This migration adds timeout and retry support to the AI Platform
-- Run this after the initial init.sql

-- =====================================================
-- Part 1: Add timeout_seconds to llm_configs table
-- =====================================================

-- Add timeout column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'llm_configs' AND column_name = 'timeout_seconds'
    ) THEN
        ALTER TABLE llm_configs ADD COLUMN timeout_seconds INTEGER DEFAULT 120;
        COMMENT ON COLUMN llm_configs.timeout_seconds IS 'Timeout in seconds for LLM API calls';
    END IF;
END $$;

-- =====================================================
-- Part 2: Create jobs table if it doesn't exist
-- =====================================================

CREATE TABLE IF NOT EXISTS jobs (
    id VARCHAR(36) PRIMARY KEY,
    prompt TEXT NOT NULL,
    config_name VARCHAR(255) NOT NULL,
    template_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'QUEUED',
    result TEXT,
    error TEXT,
    max_retries INTEGER DEFAULT 3,
    retry_count INTEGER DEFAULT 0,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Add retry columns to existing jobs table if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'jobs' AND column_name = 'max_retries'
    ) THEN
        ALTER TABLE jobs ADD COLUMN max_retries INTEGER DEFAULT 3;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'jobs' AND column_name = 'retry_count'
    ) THEN
        ALTER TABLE jobs ADD COLUMN retry_count INTEGER DEFAULT 0;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'jobs' AND column_name = 'next_retry_at'
    ) THEN
        ALTER TABLE jobs ADD COLUMN next_retry_at TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

-- =====================================================
-- Part 3: Create indexes for retry scheduling
-- =====================================================

-- Index for finding jobs by status
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);

-- Index for finding jobs by config
CREATE INDEX IF NOT EXISTS idx_jobs_config ON jobs(config_name);

-- Index for finding jobs by creation time
CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);

-- Partial index for retry scheduling (only jobs with next_retry_at set)
CREATE INDEX IF NOT EXISTS idx_jobs_next_retry ON jobs(next_retry_at)
    WHERE next_retry_at IS NOT NULL;

-- =====================================================
-- Part 4: Add update trigger for jobs table
-- =====================================================

-- Ensure trigger function exists
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add trigger for jobs table
DROP TRIGGER IF EXISTS update_jobs_updated_at ON jobs;
CREATE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- Part 5: Add job status types comment
-- =====================================================

COMMENT ON COLUMN jobs.status IS 'Job status: QUEUED, PROCESSING, COMPLETED, FAILED, RETRYING';
COMMENT ON COLUMN jobs.max_retries IS 'Maximum number of retry attempts';
COMMENT ON COLUMN jobs.retry_count IS 'Current number of retry attempts';
COMMENT ON COLUMN jobs.next_retry_at IS 'Scheduled time for next retry attempt';

-- =====================================================
-- Verification
-- =====================================================

-- Verify the migration
DO $$
DECLARE
    llm_timeout_exists INTEGER;
    jobs_max_retries_exists INTEGER;
BEGIN
    SELECT COUNT(*) INTO llm_timeout_exists
    FROM information_schema.columns
    WHERE table_name = 'llm_configs' AND column_name = 'timeout_seconds';

    SELECT COUNT(*) INTO jobs_max_retries_exists
    FROM information_schema.columns
    WHERE table_name = 'jobs' AND column_name = 'max_retries';

    IF llm_timeout_exists = 1 AND jobs_max_retries_exists = 1 THEN
        RAISE NOTICE 'Migration 002 completed successfully';
    ELSE
        RAISE WARNING 'Migration 002 may have issues. Please verify columns exist.';
    END IF;
END $$;
