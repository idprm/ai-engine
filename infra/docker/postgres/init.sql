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

-- =====================================================
-- CRM Chatbot Tables
-- =====================================================

-- Tenants table (multi-tenant businesses)
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    wa_session VARCHAR(100) NOT NULL UNIQUE,
    llm_config_name VARCHAR(255) NOT NULL,
    agent_prompt TEXT NOT NULL,
    payment_provider VARCHAR(50) NOT NULL,
    payment_config JSONB NOT NULL DEFAULT '{}',
    business_hours JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Customers table
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    phone_number VARCHAR(20) NOT NULL,
    wa_chat_id VARCHAR(100) NOT NULL,
    name VARCHAR(255),
    email VARCHAR(255),
    address JSONB,
    tags TEXT[] DEFAULT '{}',
    total_orders INTEGER DEFAULT 0,
    total_spent BIGINT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, wa_chat_id)
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100),
    base_price BIGINT NOT NULL,
    currency VARCHAR(3) DEFAULT 'IDR',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Product Variants table
CREATE TABLE IF NOT EXISTS product_variants (
    id SERIAL PRIMARY KEY,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku VARCHAR(100) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    price BIGINT NOT NULL,
    stock INTEGER DEFAULT 0,
    attributes JSONB DEFAULT '{}'
);

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    subtotal BIGINT NOT NULL,
    shipping_cost BIGINT DEFAULT 0,
    total BIGINT NOT NULL,
    currency VARCHAR(3) DEFAULT 'IDR',
    shipping_address JSONB,
    payment_id VARCHAR(255),
    payment_status VARCHAR(50) DEFAULT 'PENDING',
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Order Items table
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    product_name VARCHAR(255) NOT NULL,
    variant_sku VARCHAR(100),
    quantity INTEGER NOT NULL,
    unit_price BIGINT NOT NULL,
    subtotal BIGINT NOT NULL
);

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    id VARCHAR(255) PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    amount BIGINT NOT NULL,
    currency VARCHAR(3) DEFAULT 'IDR',
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    payment_method VARCHAR(50),
    payment_type VARCHAR(100),
    payment_url VARCHAR(500),
    qr_code TEXT,
    paid_at TIMESTAMP WITH TIME ZONE,
    expired_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- CRM Indexes
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_tenants_wa_session ON tenants(wa_session);
CREATE INDEX IF NOT EXISTS idx_tenants_active ON tenants(is_active);
CREATE INDEX IF NOT EXISTS idx_customers_tenant ON customers(tenant_id);
CREATE INDEX IF NOT EXISTS idx_customers_chat_id ON customers(wa_chat_id);
CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone_number);
CREATE INDEX IF NOT EXISTS idx_products_tenant ON products(tenant_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active);
CREATE INDEX IF NOT EXISTS idx_variants_sku ON product_variants(sku);
CREATE INDEX IF NOT EXISTS idx_orders_tenant ON orders(tenant_id);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_payment_status ON orders(payment_status);
CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

-- =====================================================
-- AI Engine Indexes
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_llm_configs_name ON llm_configs(name);
CREATE INDEX IF NOT EXISTS idx_llm_configs_provider ON llm_configs(provider);
CREATE INDEX IF NOT EXISTS idx_llm_configs_active ON llm_configs(is_active);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_name ON prompt_templates(name);

-- =====================================================
-- Default Data
-- =====================================================

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
    ('creative-writer', 'You are a creative writing assistant. Help with storytelling, content creation, and creative ideation.', 'Creative writing assistant prompt'),
    -- Multi-agent system prompts
    ('main-agent', 'You are a helpful AI assistant. Provide clear, accurate, and thoughtful responses. Be concise but thorough, and always aim to be helpful and informative.', 'Primary agent for handling user requests'),
    ('fallback-agent', 'You are a backup assistant. Provide simple, safe, and helpful responses when the primary system encounters issues. Be polite and offer to help with alternative approaches.', 'Fallback agent for error recovery'),
    ('followup-agent', 'You are a conversational assistant specialized in handling follow-up questions. Maintain context from previous messages and provide coherent, connected responses. Help users explore topics in depth.', 'Agent for conversation continuity'),
    ('moderation-agent', 'You are a content moderation assistant. Analyze messages for potential policy violations including harassment, hate speech, self-harm, sexual content, violence, and spam. Respond with structured assessments.', 'Agent for content moderation'),
    -- CRM Chatbot prompts
    ('crm-default', 'You are a helpful customer service assistant for a WhatsApp-based business. Help customers with product inquiries, orders, and payments. Be friendly, professional, and efficient.', 'Default CRM chatbot prompt')
ON CONFLICT (name) DO NOTHING;

-- Insert a demo tenant for testing
INSERT INTO tenants (name, wa_session, llm_config_name, agent_prompt, payment_provider, payment_config, business_hours) VALUES
    ('Demo Store', 'demo-session', 'default-smart', 'You are a helpful customer service assistant for Demo Store. Help customers browse products, place orders, and process payments. Be friendly and professional.', 'midtrans', '{"server_key": "SB-Mid-server-xxx"}', '{"mon": "09:00-17:00", "tue": "09:00-17:00", "wed": "09:00-17:00", "thu": "09:00-17:00", "fri": "09:00-17:00"}')
ON CONFLICT (wa_session) DO NOTHING;

-- =====================================================
-- Triggers
-- =====================================================

-- Create update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to all tables with updated_at
CREATE TRIGGER update_llm_configs_updated_at
    BEFORE UPDATE ON llm_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_prompt_templates_updated_at
    BEFORE UPDATE ON prompt_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tenants_updated_at
    BEFORE UPDATE ON tenants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at
    BEFORE UPDATE ON orders
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_payments_updated_at
    BEFORE UPDATE ON payments
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
