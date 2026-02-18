-- AI Platform Database Schema
-- Initializes tables for LLM configurations and prompt templates

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- LLM Configurations table
CREATE TABLE IF NOT EXISTS llm_configs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    provider VARCHAR(100) NOT NULL,
    model_name VARCHAR(255) NOT NULL,
    api_key_env VARCHAR(255) NOT NULL,
    temperature REAL DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 4096,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Prompt Templates table
CREATE TABLE IF NOT EXISTS prompt_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    content TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_llm_configs_name ON llm_configs(name);
CREATE INDEX IF NOT EXISTS idx_llm_configs_provider ON llm_configs(provider);
CREATE INDEX IF NOT EXISTS idx_llm_configs_active ON llm_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_name ON prompt_templates(name);

-- Insert default LLM configurations
INSERT INTO llm_configs (name, provider, model_name, api_key_env, temperature, max_tokens) VALUES
    ('default-smart', 'openai', 'gpt-4-turbo-preview', 'OPENAI_API_KEY', 0.7, 4096),
    ('default-fast', 'openai', 'gpt-3.5-turbo', 'OPENAI_API_KEY', 0.7, 4096),
    ('claude-opus', 'anthropic', 'claude-3-opus-20240229', 'ANTHROPIC_API_KEY', 0.7, 4096),
    ('claude-sonnet', 'anthropic', 'claude-3-sonnet-20240229', 'ANTHROPIC_API_KEY', 0.7, 4096)
ON CONFLICT (name) DO NOTHING;

-- Insert default prompt templates
INSERT INTO prompt_templates (name, content, description) VALUES
    ('default-assistant', 'You are a helpful AI assistant. Please provide clear, accurate, and thoughtful responses.', 'Default assistant system prompt'),
    ('code-assistant', 'You are an expert software developer. Help with coding tasks, debugging, and best practices. Be concise and practical.', 'Code-focused assistant prompt'),
    ('creative-writer', 'You are a creative writing assistant. Help with storytelling, content creation, and creative ideation.', 'Creative writing assistant prompt')
ON CONFLICT (name) DO NOTHING;

-- Create update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
CREATE TRIGGER update_llm_configs_updated_at
    BEFORE UPDATE ON llm_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prompt_templates_updated_at
    BEFORE UPDATE ON prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
