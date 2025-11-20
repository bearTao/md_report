# 删除章节功能快速入门

## 📚 概览

本文档帮助你快速理解和部署删除章节功能。

### 功能特点
- ✅ 智能识别删除目标（支持自然语言）
- ✅ 逐个确认机制（安全可控）
- ✅ 报告锁定机制（保持数据时间一致性）
- ✅ 后端精确定位（不依赖 LLM 数值）

---

## 🚀 快速部署

### 步骤1：执行数据库迁移

```bash
# 进入 conda 环境
conda activate test_md

# 方式A：使用 Python 脚本（推荐）
cd backend
python migrations/run_migration.py --migration 002 --env dev

# 方式B：直接使用 psql
psql -h localhost -U your_user -d your_database -f migrations/pg/002_add_report_lock_fields.sql
```

**验证迁移**：
```sql
SELECT column_name, data_type 
FROM information_schema.columns
WHERE table_name = 'report_states'
AND column_name IN ('edit_mode', 'variable_snapshot', 'generated_at', 'locked_at', 'lock_reason');
```

### 步骤2：重启后端服务

```bash
# 如果后端正在运行，重启以加载新代码
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### 步骤3：测试 API

使用 Postman 或 curl 测试：

**生成删除计划**：
```bash
curl -X POST http://localhost:8000/api/reports/agent/plan-delete \
  -H "Content-Type: application/json" \
  -d '{
    "user_message": "删除网格评分分析章节",
    "conversation_id": "test_conv_001"
  }'
```

**执行删除**：
```bash
curl -X POST http://localhost:8000/api/reports/agent/execute-delete \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "plan_abc123",
    "action": "delete_and_lock",
    "decisions": [
      {"section_id": "L15", "decision": "execute"}
    ]
  }'
```

---

## 📖 核心概念

### 1. 编辑模式

| 模式 | 说明 | 可修改参数 | 可删除章节 |
|-----|------|-----------|-----------|
| **template** | 模板模式（默认） | ✅ | ✅ |
| **locked** | 锁定模式 | ❌ | ✅ |

### 2. 删除流程

```
用户请求 
  ↓
生成删除计划（LLM 识别 + 后端定位）
  ↓
用户逐个确认
  ↓
执行删除 + 锁定报告
  ↓
完成
```

### 3. 数据一致性

当用户删除章节后：
- 报告自动锁定为 `locked` 模式
- 保存当前变量快照到 `variable_snapshot`
- 记录生成时间 `generated_at` 和锁定时间 `locked_at`
- 后续无法修改参数（保持数据时间点一致）

---

## 🎯 使用示例

### 示例1：删除单个章节

**用户请求**：
```
"删除网格评分分析章节"
```

**系统响应**：
```json
{
  "plan_id": "plan_xyz789",
  "sections": [
    {
      "section_path": "预分析报告->1、网格概述->1.1 网格评分分析",
      "content_preview": "# 1.1 网格评分分析\n\n本次分析涵盖XX个网格...",
      "section_id": "L15",
      "start_line": 15,
      "end_line": 45
    }
  ],
  "total_count": 1,
  "lock_warning": "删除章节后，报告将锁定为静态版本..."
}
```

**用户确认**：
```json
{
  "plan_id": "plan_xyz789",
  "action": "delete_and_lock",
  "decisions": [
    {"section_id": "L15", "decision": "execute"}
  ]
}
```

**执行结果**：
```json
{
  "success": true,
  "action_taken": "delete_and_lock",
  "deleted_sections": ["预分析报告->1、网格概述->1.1 网格评分分析"],
  "message": "已删除 1 个章节。报告已锁定为静态版本..."
}
```

### 示例2：基于内容特征删除

**用户请求**：
```
"删除所有包含表格的章节"
```

**系统行为**：
1. LLM 分析报告内容，识别包含表格（`|` 符号）的章节
2. 返回所有匹配的章节列表
3. 用户逐个确认

### 示例3：条件删除

**用户请求**：
```
"删除除了概述以外的所有章节"
```

**系统行为**：
1. LLM 识别"概述"章节
2. 返回除"概述"外的所有章节
3. 用户确认并删除

---

## 🧪 测试清单

### 功能测试

- [ ] 删除单个章节
- [ ] 删除多个章节
- [ ] 跳过某些章节
- [ ] 取消删除计划
- [ ] 基于内容特征删除
- [ ] 条件删除（排除某些章节）

### 状态测试

- [ ] 验证报告锁定状态
- [ ] 验证变量快照保存
- [ ] 尝试修改锁定报告的参数（应失败）
- [ ] 验证锁定后仍可删除章节
- [ ] 验证时间戳记录

### 边界测试

- [ ] 删除不存在的章节
- [ ] 章节路径不唯一
- [ ] 空报告
- [ ] 所有章节都跳过
- [ ] LLM 服务不可用

---

## 🔧 故障排查

### 问题1：无法找到章节

**错误信息**：
```
"无法定位任何章节。LLM 识别了 2 个路径，但后端都无法精确定位。"
```

**原因**：
- LLM 返回的路径格式不标准
- 章节标题不匹配

**解决**：
- 检查 Markdown 格式是否正确
- 使用更明确的章节名称
- 查看后端日志了解详细定位过程

### 问题2：参数修改被阻止

**错误信息**：
```
"报告已锁定为静态版本，无法修改参数。"
```

**原因**：
- 报告已被锁定（`edit_mode = 'locked'`）

**解决**：
- 这是预期行为
- 如需修改参数，使用"重新生成"功能（待实现）

### 问题3：迁移失败

**错误信息**：
```
"column 'edit_mode' already exists"
```

**原因**：
- 迁移已执行过

**解决**：
```sql
-- 检查字段是否存在
SELECT column_name FROM information_schema.columns
WHERE table_name = 'report_states';
```

---

## 📁 相关文档

- [前端设计文档](./FRONTEND_DELETE_SECTIONS_DESIGN.md) - UI/UX 设计详情
- [数据库迁移文档](../backend/migrations/pg/README.md) - 迁移执行指南
- [API 文档](../backend/docs/API_REPORT_MODIFICATION.md) - 完整 API 规范

---

## 🤝 开发团队

如有问题，请联系：
- 后端开发：[你的名字]
- 前端开发：[前端负责人]
- 数据库管理：[DBA]

---

## 📝 更新日志

### 2025-11-18
- ✅ 完成后端开发
- ✅ 创建数据库迁移脚本
- ✅ 编写前端设计文档
- ⏳ 待办：前端实现
- ⏳ 待办：端到端测试

---

## ⚡ 快速命令参考

```bash
# 1. 执行迁移
python migrations/run_migration.py --migration 002 --env dev

# 2. 演练模式（不实际执行）
python migrations/run_migration.py --migration 002 --dry-run

# 3. 回滚迁移（⚠️ 会丢失数据）
psql -h localhost -U user -d db -f migrations/pg/002_rollback.sql

# 4. 启动后端
cd backend && python -m uvicorn app.main:app --reload

# 5. 测试 API
curl -X POST http://localhost:8000/api/reports/agent/plan-delete \
  -H "Content-Type: application/json" \
  -d '{"user_message": "删除XX章节", "conversation_id": "test"}'
```

---

## 🎉 完成！

现在你已经了解了删除章节功能的所有核心概念。开始体验吧！
