-- ============================================================================
-- 清理Agent测试数据脚本
-- 用途：清理测试过程中产生的会话、对话历史、报告状态等数据
-- 使用：在需要重新测试时运行此脚本
-- ============================================================================

-- 注意：此脚本会删除所有Agent相关的测试数据，请谨慎使用！

-- 1. 清理对话轮次
DELETE FROM conversation_turns WHERE session_id IN (
    SELECT id FROM conversation_sessions WHERE report_id LIKE 'test_%' OR report_id IN (
        SELECT id FROM reports WHERE title LIKE '%测试%' OR title LIKE '%Agent%'
    )
);

-- 2. 清理对话会话
DELETE FROM conversation_sessions WHERE report_id LIKE 'test_%' OR report_id IN (
    SELECT id FROM reports WHERE title LIKE '%测试%' OR title LIKE '%Agent%'
);

-- 3. 清理报告修改历史
DELETE FROM report_modification_history WHERE report_id LIKE 'test_%' OR report_id IN (
    SELECT id FROM reports WHERE title LIKE '%测试%' OR title LIKE '%Agent%'
);

-- 4. 清理报告状态
DELETE FROM report_states WHERE report_id LIKE 'test_%' OR report_id IN (
    SELECT id FROM reports WHERE title LIKE '%测试%' OR title LIKE '%Agent%'
);

-- 5. 清理测试报告（可选，如果想保留报告但清理对话历史，注释掉这部分）
-- DELETE FROM reports WHERE id LIKE 'test_%' OR title LIKE '%测试%' OR title LIKE '%Agent%';

-- 6. 清理测试任务（可选）
-- DELETE FROM generation_tasks WHERE id LIKE 'test_%';

-- 7. 清理测试模板（可选，通常不需要删除）
-- DELETE FROM templates WHERE name LIKE '%测试%' OR name LIKE '%Agent%';

-- 显示清理结果
SELECT 'conversation_turns' as table_name, COUNT(*) as remaining_count FROM conversation_turns
UNION ALL
SELECT 'conversation_sessions', COUNT(*) FROM conversation_sessions
UNION ALL
SELECT 'report_modification_history', COUNT(*) FROM report_modification_history
UNION ALL
SELECT 'report_states', COUNT(*) FROM report_states
UNION ALL
SELECT 'reports', COUNT(*) FROM reports
UNION ALL
SELECT 'templates', COUNT(*) FROM templates;

-- 提交事务
COMMIT;
