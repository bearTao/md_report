-- ========================================
-- 修复枚举类型以支持新的变量源
-- ========================================
-- 功能: 扩展 generation_task_variables 表的 source 字段
--       以支持 'image' 和 'vision_ai' 类型
-- 影响: 只扩展枚举值，不影响现有数据
-- ========================================

-- 修改 source 字段的枚举类型（使用大写以匹配现有枚举值）
ALTER TABLE generation_task_variables 
MODIFY COLUMN source 
ENUM('USER_INPUT', 'SQL', 'API', 'AI_GENERATION', 'SYSTEM', 'IMAGE', 'VISION_AI') 
NOT NULL;

-- 验证修改结果
SHOW COLUMNS FROM generation_task_variables LIKE 'source';

-- 显示成功消息
SELECT '✅ 枚举类型修改成功！现在支持 image 和 vision_ai 类型' AS status;

