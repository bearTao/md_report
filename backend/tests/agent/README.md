# Agent模式测试指南

使用Postman测试报告修改Agent功能。

## 📦 文件说明

- `Agent测试.postman_collection.json` - Postman测试集合（符合字段说明文档规范）
- `clean_test_data.sql` - 清理测试数据的SQL脚本

## 🚀 快速开始

### 1. 导入Postman Collection

1. 打开Postman
2. 点击Import
3. 选择 `Agent测试.postman_collection.json`
4. 创建环境（或使用现有环境），设置变量：
   - `base_url` = `http://localhost:8000`（你的后端地址）

### 2. 按顺序执行测试

#### 步骤1：准备工作
1. **创建测试模板** - 创建一个简单的模板（包含6个变量，符合字段规范）
   - 4个user_input变量：report_title、project_name、time_range、status
   - 2个constant变量：record_count、analysis_content
   - ⚠️ 运行后记得在Collection变量中填入返回的`template_id`

2. **生成测试报告** - 使用模板生成报告
   - 自动保存task_id到环境变量

3. **查询报告状态** - 确认报告生成成功
   - 自动保存report_id到环境变量

4. **查看报告详情** - 查看初始报告内容

#### 步骤2：Agent修改测试
1. **修改单个参数** - 测试修改项目名称
   - 自动保存session_id，用于多轮对话
2. **修改多个参数** - 测试同时修改多个字段
3. **修改数值** - 测试修改数值类型变量
4. **添加新章节** - 测试Agent添加新章节（需要LLM）
5. **修改现有章节** - 测试Agent修改章节内容
6. **删除章节** - 测试删除章节

#### 步骤3：查看结果
1. **查看修改后的报告** - 查看最终报告
2. **查看对话历史** - 查看完整对话记录

#### 步骤4：SQL数据源测试（可选）

**前提条件**：test_db中需要有微网格数据表
- `microgrid.micro_grid_overview_w`
- `microgrid.micro_grid_index_score_w`

测试步骤：
1. 先配置数据库连接（见下方"配置SQL数据源"）
2. **创建带SQL变量的模板** - 包含3个user_input + 2个SQL变量
   - ⚠️ 运行后记得在Collection变量中填入返回的`sql_template_id`
3. **生成带SQL的报告** - 系统会自动查询test_db
4. **Agent修改SQL报告** - 测试修改SQL变量参数

## 🔧 配置SQL数据源

如果要测试SQL变量，需要先配置数据库连接。

### 方法1: 通过API创建连接

```http
POST {{base_url}}/api/db-connections
Content-Type: application/json

{
  "name": "test_db_connection",
  "engine": "postgresql",
  "host": "10.10.20.10",
  "port": 14632,
  "database": "test_db",
  "username": "microgrid",
  "password": "microgrid123"
}
```

### 方法2: 直接在数据库中插入

```sql
INSERT INTO db_connections (name, engine, host, port, database, username, password_encrypted)
VALUES ('test_db_connection', 'postgresql', '10.10.20.10', 14632, 'test_db', 'microgrid', 'microgrid123');
```

⚠️ **注意**：创建模板时使用的`connection`字段值必须与这里的`name`一致。

## 🧹 清理测试数据

测试完成后，可以运行清理脚本：

```bash
psql -h 10.10.20.10 -p 14632 -U microgrid -d <你的数据库> -f clean_test_data.sql
```

## 📝 注意事项

### 1. 字段规范要求
- ✅ 所有`user_input`变量必须包含`ui_config`字段（已在模板中配置）
- ✅ 所有`sql`变量必须包含`sql_config`字段（已在模板中配置）
- ✅ 所有变量必须有`type`、`source`、`required`、`description`字段

### 2. OpenAI API密钥
添加章节、修改章节等功能需要配置OpenAI API密钥：
```bash
# 环境变量方式
export OPENAI_API_KEY=sk-your-key-here
export OPENAI_API_BASE=https://api.openai.com/v1
```

### 3. 变量填写
- **template_id**：创建模板后手动填入Collection变量
- **sql_template_id**：创建SQL模板后手动填入Collection变量
- **task_id、report_id、session_id**：自动保存到环境变量

### 4. 字典方法名冲突
SQL模板已处理字典方法名冲突：
- 原来：`{{item.index}}` ❌（会访问dict.index()方法）
- 修正：`{{item["index"]}}` ✅（直接访问键值）
- 或使用SQL别名：`"index" AS index_name` ✅

## 🎯 测试要点

### 基础功能
- ✅ 模板创建是否成功（符合字段规范）
- ✅ 报告生成是否正常
- ✅ 参数修改是否生效

### Agent功能
- ✅ 单参数修改
- ✅ 多参数同时修改
- ✅ 添加新章节（LLM生成）
- ✅ 修改现有章节
- ✅ 删除章节

### 对话管理
- ✅ 多轮对话是否保持上下文
- ✅ session_id是否正确传递
- ✅ 对话历史是否正确记录
- ✅ 版本号是否正确递增

### SQL数据源
- ✅ SQL变量是否正确查询
- ✅ 修改参数后SQL是否重新执行
- ✅ 字典方法名冲突是否已解决

## 📋 变量字段说明

完整的字段说明请参考：`字段说明文档.md`

### user_input 变量必需字段
```json
{
  "name": "变量名",
  "type": "string|number|boolean|array|object",
  "source": "user_input",
  "required": true|false,
  "description": "变量描述",
  "default": "默认值",
  "ui_config": {
    "input_type": "text|textarea|number|select|checkbox|date",
    "placeholder": "输入提示"
  }
}
```

### sql 变量必需字段
```json
{
  "name": "变量名",
  "type": "string|number|object|array",
  "source": "sql",
  "required": true|false,
  "description": "变量描述",
  "default": null|{}|[],
  "dependencies": ["依赖的变量"],
  "sql_config": {
    "connection": "数据库连接名",
    "query": "SQL查询语句",
    "parameters": ["参数列表"],
    "timeout": 10,
    "result_mode": "first_row|all_rows|first_value|first_column|auto"
  }
}
```

祝测试顺利！🚀
