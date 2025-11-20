-- Add Report Lock Fields Migration
-- Created: 2025-11-18
-- Description: 为 report_states 表添加锁定和编辑模式相关字段，支持删除章节功能

-- ============================================================================
-- 迁移说明
-- ============================================================================
-- 本迁移脚本为 report_states 表添加以下字段：
-- 1. edit_mode: 编辑模式（template 可编辑参数 | locked 静态锁定）
-- 2. variable_snapshot: 变量快照（锁定时保存的变量值）
-- 3. generated_at: 报告生成时间
-- 4. locked_at: 锁定时间
-- 5. lock_reason: 锁定原因
--
-- 这些字段支持删除章节后的报告锁定机制，确保数据时间一致性

-- ============================================================================
-- 1. 添加 edit_mode 字段
-- ============================================================================
-- 编辑模式：template（可修改参数）或 locked（静态锁定）
ALTER TABLE report_states 
ADD COLUMN IF NOT EXISTS edit_mode VARCHAR(20) NOT NULL DEFAULT 'template';

-- 添加检查约束，确保只能是 template 或 locked
-- PostgreSQL 不支持 IF NOT EXISTS，所以使用 DO 块来避免重复创建
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'check_edit_mode' 
        AND conrelid = 'report_states'::regclass
    ) THEN
        ALTER TABLE report_states 
        ADD CONSTRAINT check_edit_mode 
        CHECK (edit_mode IN ('template', 'locked'));
    END IF;
END $$;

-- 创建索引，用于快速查询锁定状态的报告
CREATE INDEX IF NOT EXISTS idx_report_states_edit_mode 
ON report_states(edit_mode);

-- ============================================================================
-- 2. 添加 variable_snapshot 字段
-- ============================================================================
-- 变量快照：报告锁定时保存的所有变量值（JSON格式）
-- 示例：{"start_date": "2024-01-01", "end_date": "2024-01-31", "grid_id": 123}
ALTER TABLE report_states 
ADD COLUMN IF NOT EXISTS variable_snapshot JSON;

-- 添加注释
COMMENT ON COLUMN report_states.variable_snapshot IS '变量快照：报告锁定时保存的所有变量值，用于显示历史数据状态';

-- ============================================================================
-- 3. 添加 generated_at 字段
-- ============================================================================
-- 报告生成时间：记录报告首次生成的时间点
ALTER TABLE report_states 
ADD COLUMN IF NOT EXISTS generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP;

-- 创建索引，用于按生成时间查询
CREATE INDEX IF NOT EXISTS idx_report_states_generated_at 
ON report_states(generated_at);

-- 添加注释
COMMENT ON COLUMN report_states.generated_at IS '报告生成时间：记录报告首次生成的时间点，用于数据时间标记';

-- ============================================================================
-- 4. 添加 locked_at 字段
-- ============================================================================
-- 锁定时间：报告被锁定的时间（如果未锁定则为 NULL）
ALTER TABLE report_states 
ADD COLUMN IF NOT EXISTS locked_at TIMESTAMP WITH TIME ZONE;

-- 创建索引，用于查询锁定时间
CREATE INDEX IF NOT EXISTS idx_report_states_locked_at 
ON report_states(locked_at);

-- 添加注释
COMMENT ON COLUMN report_states.locked_at IS '锁定时间：报告被锁定为静态版本的时间';

-- ============================================================================
-- 5. 添加 lock_reason 字段
-- ============================================================================
-- 锁定原因：说明为什么锁定（例如："用户删除章节"）
ALTER TABLE report_states 
ADD COLUMN IF NOT EXISTS lock_reason TEXT;

-- 添加注释
COMMENT ON COLUMN report_states.lock_reason IS '锁定原因：说明报告为何被锁定，例如"用户删除章节"';

-- ============================================================================
-- 6. 更新现有数据（可选）
-- ============================================================================
-- 如果表中已有数据，可以根据需要更新默认值
-- 例如：将所有现有报告的 generated_at 设置为创建时间

-- 如果 report_states 表有 created_at 字段，可以用它来初始化 generated_at
-- UPDATE report_states 
-- SET generated_at = created_at 
-- WHERE generated_at = CURRENT_TIMESTAMP;

-- ============================================================================
-- 7. 验证迁移
-- ============================================================================
-- 运行以下查询验证迁移是否成功

-- 检查字段是否存在
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns
WHERE table_name = 'report_states'
AND column_name IN ('edit_mode', 'variable_snapshot', 'generated_at', 'locked_at', 'lock_reason')
ORDER BY ordinal_position;

-- 检查索引是否创建
SELECT 
    indexname, 
    indexdef
FROM pg_indexes
WHERE tablename = 'report_states'
AND indexname LIKE 'idx_report_states_%'
ORDER BY indexname;

-- 检查约束是否创建
SELECT 
    conname AS constraint_name,
    pg_get_constraintdef(oid) AS constraint_definition
FROM pg_constraint
WHERE conrelid = 'report_states'::regclass
AND conname = 'check_edit_mode';

-- ============================================================================
-- 8. 回滚脚本（如需要）
-- ============================================================================
-- 如果需要回滚此迁移，请运行以下命令：

/*
-- 删除字段（会丢失数据！）
ALTER TABLE report_states DROP COLUMN IF EXISTS lock_reason;
ALTER TABLE report_states DROP COLUMN IF EXISTS locked_at;
ALTER TABLE report_states DROP COLUMN IF EXISTS generated_at;
ALTER TABLE report_states DROP COLUMN IF EXISTS variable_snapshot;
ALTER TABLE report_states DROP COLUMN IF EXISTS edit_mode;

-- 删除索引
DROP INDEX IF EXISTS idx_report_states_locked_at;
DROP INDEX IF EXISTS idx_report_states_generated_at;
DROP INDEX IF EXISTS idx_report_states_edit_mode;

-- 删除约束
ALTER TABLE report_states DROP CONSTRAINT IF EXISTS check_edit_mode;
*/

-- ============================================================================
-- 迁移完成
-- ============================================================================
-- 执行时间：约 1-5 秒（取决于表大小）
-- 影响：为 report_states 表添加 5 个新字段和 3 个索引
-- 兼容性：PostgreSQL 10+
-- 风险：低（添加字段操作，不影响现有数据）
