-- Report Modification Agent Database Migration
-- Created: 2025-11-13
-- Description: Add tables for conversation sessions, turns, report states, and modification history

-- ============================================================================
-- 1. conversation_sessions 表
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversation_sessions (
    id VARCHAR(50) PRIMARY KEY,
    report_id VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    context_summary TEXT,
    last_activity_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引：按报告ID查询会话
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_report_id 
    ON conversation_sessions(report_id);

-- 索引：按状态查询会话（用于清理不活跃会话）
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_status 
    ON conversation_sessions(status);

-- 索引：按最后活跃时间查询（用于清理过期会话）
CREATE INDEX IF NOT EXISTS idx_conversation_sessions_last_activity 
    ON conversation_sessions(last_activity_at);

-- ============================================================================
-- 2. conversation_turns 表
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversation_turns (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(50) NOT NULL,
    turn_number INTEGER NOT NULL,
    user_request TEXT NOT NULL,
    parsed_intents JSON,
    operations_executed JSON,
    system_response TEXT,
    report_version INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引：按会话ID查询所有轮次
CREATE INDEX IF NOT EXISTS idx_conversation_turns_session_id 
    ON conversation_turns(session_id);

-- 索引：按创建时间排序（用于获取对话历史）
CREATE INDEX IF NOT EXISTS idx_conversation_turns_created_at 
    ON conversation_turns(created_at);

-- 复合索引：按会话ID和轮次号查询
CREATE INDEX IF NOT EXISTS idx_conversation_turns_session_turn 
    ON conversation_turns(session_id, turn_number);

-- ============================================================================
-- 3. report_states 表
-- ============================================================================
CREATE TABLE IF NOT EXISTS report_states (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(50) NOT NULL,
    session_id VARCHAR(50) NOT NULL,
    version INTEGER NOT NULL,
    template_id VARCHAR(50) NOT NULL,
    template_content TEXT,
    template_metadata JSON,
    variables_state JSON NOT NULL,
    markdown_content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引：按报告ID查询所有版本
CREATE INDEX IF NOT EXISTS idx_report_states_report_id 
    ON report_states(report_id);

-- 索引：按会话ID查询状态
CREATE INDEX IF NOT EXISTS idx_report_states_session_id 
    ON report_states(session_id);

-- 复合索引：按报告ID和版本号查询特定版本
CREATE INDEX IF NOT EXISTS idx_report_states_report_version 
    ON report_states(report_id, version);

-- 唯一约束：同一会话和报告的版本号不能重复
CREATE UNIQUE INDEX IF NOT EXISTS idx_report_states_unique_version 
    ON report_states(report_id, session_id, version);

-- ============================================================================
-- 4. report_modification_history 表
-- ============================================================================
CREATE TABLE IF NOT EXISTS report_modification_history (
    id SERIAL PRIMARY KEY,
    report_id VARCHAR(50) NOT NULL,
    session_id VARCHAR(50) NOT NULL,
    turn_id INTEGER NOT NULL,
    operation_type VARCHAR(50) NOT NULL,
    operation_details JSON NOT NULL,
    affected_variables JSON,
    from_version INTEGER NOT NULL,
    to_version INTEGER NOT NULL,
    success BOOLEAN NOT NULL DEFAULT TRUE,
    error_message TEXT,
    duration_ms INTEGER,
    cost_usd NUMERIC(10, 4),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 索引：按报告ID查询修改历史
CREATE INDEX IF NOT EXISTS idx_modification_history_report_id 
    ON report_modification_history(report_id);

-- 索引：按会话ID查询修改历史
CREATE INDEX IF NOT EXISTS idx_modification_history_session_id 
    ON report_modification_history(session_id);

-- 索引：按操作类型统计
CREATE INDEX IF NOT EXISTS idx_modification_history_operation_type 
    ON report_modification_history(operation_type);

-- 索引：按创建时间排序
CREATE INDEX IF NOT EXISTS idx_modification_history_created_at 
    ON report_modification_history(created_at);

-- 索引：按成功状态过滤
CREATE INDEX IF NOT EXISTS idx_modification_history_success 
    ON report_modification_history(success);

-- ============================================================================
-- 5. 更新现有的 reports 表 (如果列不存在)
-- ============================================================================
-- 添加版本号和最后修改时间列
DO $$ 
BEGIN
    -- 添加 version 列（如果不存在）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='reports' AND column_name='version'
    ) THEN
        ALTER TABLE reports ADD COLUMN version INTEGER DEFAULT 1;
        COMMENT ON COLUMN reports.version IS '报告版本号,每次修改后递增';
    END IF;
    
    -- 添加 last_modified_at 列（如果不存在）
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='reports' AND column_name='last_modified_at'
    ) THEN
        ALTER TABLE reports ADD COLUMN last_modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
        COMMENT ON COLUMN reports.last_modified_at IS '报告最后修改时间';
    END IF;
END $$;

-- ============================================================================
-- 6. 添加注释说明
-- ============================================================================
COMMENT ON TABLE conversation_sessions IS '对话会话表:管理报告修改的对话会话生命周期';
COMMENT ON TABLE conversation_turns IS '对话轮次表:存储每一轮用户输入和系统响应';
COMMENT ON TABLE report_states IS '报告状态表:存储报告每个版本的完整状态快照';
COMMENT ON TABLE report_modification_history IS '报告修改历史表:详细记录每次修改操作的审计信息';

-- ============================================================================
-- 7. 验证迁移
-- ============================================================================
-- 显示新创建的表
SELECT 
    table_name, 
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_schema = 'public' 
    AND table_name IN (
        'conversation_sessions', 
        'conversation_turns', 
        'report_states', 
        'report_modification_history'
    )
ORDER BY table_name;

-- 显示每个表的索引数量
SELECT 
    tablename, 
    COUNT(*) as index_count
FROM pg_indexes
WHERE schemaname = 'public'
    AND tablename IN (
        'conversation_sessions', 
        'conversation_turns', 
        'report_states', 
        'report_modification_history'
    )
GROUP BY tablename
ORDER BY tablename;

