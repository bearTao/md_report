-- 添加 'constant' 到 VariableSourceType ENUM
-- 用于支持常量变量类型
-- 日期: 2025-10-29

-- 对于 MySQL，修改 ENUM 类型
ALTER TABLE generation_task_variables 
MODIFY COLUMN source ENUM(
    'user_input', 
    'sql', 
    'api', 
    'ai_generation', 
    'system',
    'constant',  -- 新增
    'image',
    'vision_ai'
) NOT NULL;

-- 验证修改
SELECT COLUMN_TYPE 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_NAME = 'generation_task_variables' 
AND COLUMN_NAME = 'source';

