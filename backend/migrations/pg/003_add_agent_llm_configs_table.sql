-- Agent LLM Configuration Table Migration
-- Created: 2025-11-18
-- Description: Add table for storing independent LLM configurations for each Agent component

-- ============================================================================
-- agent_llm_configs 表
-- ============================================================================
-- 为每个Agent组件存储独立的LLM配置
-- 每个组件可以配置不同的模型、API密钥、base URL等参数
CREATE TABLE IF NOT EXISTS agent_llm_configs (
    id SERIAL PRIMARY KEY,
    component VARCHAR(50) NOT NULL UNIQUE,  -- 组件类型：intent_parser, explanation_generator, ai_refinement
    model VARCHAR(100) NOT NULL,  -- 模型名称，如 gpt-4, gpt-3.5-turbo, claude-3
    api_key TEXT,  -- API密钥（可选，如果为空则使用全局配置）
    api_base VARCHAR(500),  -- API Base URL（可选）
    organization VARCHAR(100),  -- 组织ID（可选，用于OpenAI）
    temperature NUMERIC(3, 2) NOT NULL DEFAULT 0.7,  -- 生成温度
    max_tokens INTEGER,  -- 最大生成token数（可选）
    timeout INTEGER NOT NULL DEFAULT 60,  -- 请求超时时间（秒）
    enabled BOOLEAN NOT NULL DEFAULT TRUE,  -- 是否启用该组件
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引：按组件类型快速查询
CREATE INDEX IF NOT EXISTS idx_agent_llm_configs_component 
    ON agent_llm_configs(component);

-- 索引：查询已启用的配置
CREATE INDEX IF NOT EXISTS idx_agent_llm_configs_enabled 
    ON agent_llm_configs(enabled);

-- 添加说明注释
COMMENT ON TABLE agent_llm_configs IS 'Agent组件的独立LLM配置表';
COMMENT ON COLUMN agent_llm_configs.component IS '组件类型：intent_parser（意图解析器）、explanation_generator（响应生成器）、ai_refinement（AI内容优化）';
COMMENT ON COLUMN agent_llm_configs.model IS '使用的LLM模型名称';
COMMENT ON COLUMN agent_llm_configs.api_key IS 'API密钥（可选，为空时使用全局AI配置）';
COMMENT ON COLUMN agent_llm_configs.api_base IS 'API Base URL（可选，为空时使用全局AI配置）';
COMMENT ON COLUMN agent_llm_configs.organization IS 'OpenAI组织ID（可选）';
COMMENT ON COLUMN agent_llm_configs.temperature IS '生成温度，控制随机性（0.0-2.0）';
COMMENT ON COLUMN agent_llm_configs.max_tokens IS '最大生成token数（可选）';
COMMENT ON COLUMN agent_llm_configs.timeout IS '请求超时时间（秒）';
COMMENT ON COLUMN agent_llm_configs.enabled IS '是否启用该组件的配置';

-- ============================================================================
-- 插入默认配置（可选）
-- ============================================================================
-- 这些默认配置会在表创建后自动插入
-- 用户可以在Web界面中修改这些配置

-- 意图解析器默认配置
INSERT INTO agent_llm_configs (component, model, temperature, timeout, enabled)
VALUES ('intent_parser', 'gpt-4', 0.1, 60, TRUE)
ON CONFLICT (component) DO NOTHING;

-- 响应生成器默认配置（默认不启用LLM生成）
INSERT INTO agent_llm_configs (component, model, temperature, timeout, enabled)
VALUES ('explanation_generator', 'gpt-3.5-turbo', 0.7, 30, FALSE)
ON CONFLICT (component) DO NOTHING;

-- AI内容优化默认配置
INSERT INTO agent_llm_configs (component, model, temperature, timeout, enabled)
VALUES ('ai_refinement', 'gpt-4', 0.7, 90, TRUE)
ON CONFLICT (component) DO NOTHING;
