# API 使用文档

## 概述

本文档说明Markdown报告自动生成平台的P0 REST API接口使用方法。

**基础URL**: `http://localhost:8000`

**API版本**: 1.0.0

---

## 认证

P0阶段暂无认证机制（P1将添加）

---

## 模板管理 API

### 1. 获取模板列表

**GET** `/api/templates`

**查询参数**:
- `page` (int, 可选): 页码，默认1
- `page_size` (int, 可选): 每页数量，默认20，最大100
- `q` (string, 可选): 搜索关键词

**响应示例**:
```json
{
  "items": [
    {
      "id": "tpl_abc123",
      "name": "项目周报模板",
      "description": "用于生成项目周报",
      "created_at": "2025-10-13T10:00:00Z"
    }
  ],
  "total": 1
}
```

---

### 2. 创建模板

**POST** `/api/templates`

**请求体**:
```json
{
  "name": "项目周报模板",
  "description": "用于生成项目周报",
  "template_content": "# {{report_title}}\n\n生成时间: {{generation_time}}\n\n{{content}}",
  "metadata": {
    "report_title": {
      "type": "string",
      "source": "user_input",
      "required": true,
      "description": "报告标题",
      "ui_config": {
        "input_type": "text",
        "placeholder": "请输入标题"
      }
    },
    "content": {
      "type": "string",
      "source": "user_input",
      "required": true,
      "description": "报告内容",
      "ui_config": {
        "input_type": "textarea"
      }
    },
    "generation_time": {
      "type": "string",
      "source": "system",
      "required": true,
      "description": "生成时间",
      "system_config": {
        "fields": {
          "timestamp": {
            "generator": "datetime",
            "format": "%Y-%m-%d %H:%M:%S"
          }
        }
      }
    }
  }
}
```

**响应** (201 Created):
```json
{
  "id": "tpl_abc123",
  "name": "项目周报模板",
  "description": "用于生成项目周报",
  "template_content": "...",
  "metadata_json": {...},
  "created_at": "2025-10-13T10:00:00Z",
  "updated_at": "2025-10-13T10:00:00Z"
}
```

---

### 3. 获取模板详情

**GET** `/api/templates/{template_id}`

**响应示例**:
```json
{
  "id": "tpl_abc123",
  "name": "项目周报模板",
  "description": "用于生成项目周报",
  "template_content": "# {{report_title}}...",
  "metadata_json": {...},
  "created_at": "2025-10-13T10:00:00Z",
  "updated_at": "2025-10-13T10:00:00Z"
}
```

---

### 4. 更新模板

**PUT** `/api/templates/{template_id}`

**请求体** (所有字段可选):
```json
{
  "name": "更新后的模板名称",
  "description": "更新后的描述",
  "template_content": "# {{new_title}}",
  "metadata": {...}
}
```

**响应**: 更新后的模板对象

---

### 5. 删除模板

**DELETE** `/api/templates/{template_id}`

**响应**: 204 No Content

---

## 报告生成 API

### 1. 启动报告生成

**POST** `/api/reports/generate`

**请求体**:
```json
{
  "template_id": "tpl_abc123",
  "inputs": {
    "report_title": "2025年Q3项目总结",
    "content": "本季度完成了以下工作..."
  }
}
```

**响应** (202 Accepted):
```json
{
  "task_id": "task_xyz789",
  "status": "pending"
}
```

**说明**: 报告生成是异步的，返回task_id后在后台执行

---

### 2. 获取报告详情

**GET** `/api/reports/{report_id}`

**响应示例**:
```json
{
  "id": "rpt_def456",
  "template_id": "tpl_abc123",
  "task_id": "task_xyz789",
  "title": "2025年Q3项目总结",
  "status": "success",
  "markdown_content": "# 2025年Q3项目总结\n\n生成时间: 2025-10-13 14:30:00\n\n本季度完成了以下工作...",
  "cost_usd": null,
  "duration_ms": 1250,
  "created_at": "2025-10-13T14:30:00Z",
  "updated_at": "2025-10-13T14:30:00Z"
}
```

**状态值**:
- `pending`: 等待执行
- `running`: 执行中
- `success`: 成功
- `failed`: 失败
- `cancelled`: 已取消

---

### 3. 下载报告

**GET** `/api/reports/{report_id}/download`

**响应**: Markdown文件下载（Content-Type: text/markdown）

---

## 系统配置 API

### 1. 获取AI配置状态

**GET** `/api/config/ai`

**响应示例**:
```json
{
  "configured": true,
  "provider": "openai"
}
```

---

### 2. 更新AI配置

**PUT** `/api/config/ai`

**请求体**:
```json
{
  "provider": "openai",
  "api_key": "sk-your-openai-api-key"
}
```

**响应**:
```json
{
  "configured": true,
  "provider": "openai"
}
```

---

## 错误响应

所有API错误返回以下格式:

```json
{
  "detail": "错误描述信息"
}
```

**常见HTTP状态码**:
- `200 OK`: 成功
- `201 Created`: 资源创建成功
- `202 Accepted`: 请求已接受（异步处理）
- `204 No Content`: 成功但无返回内容
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器错误

---

## 完整示例：生成报告工作流

### 步骤1: 创建模板

```bash
curl -X POST http://localhost:8000/api/templates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "简单报告",
    "description": "测试模板",
    "template_content": "# {{title}}\n\n{{content}}",
    "metadata": {
      "title": {
        "type": "string",
        "source": "user_input",
        "required": true,
        "description": "标题"
      },
      "content": {
        "type": "string",
        "source": "user_input",
        "required": true,
        "description": "内容"
      }
    }
  }'
```

**响应**: 获得 `template_id`

---

### 步骤2: 生成报告

```bash
curl -X POST http://localhost:8000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "template_id": "tpl_abc123",
    "inputs": {
      "title": "我的第一个报告",
      "content": "这是报告内容"
    }
  }'
```

**响应**: 获得 `task_id`

---

### 步骤3: 等待生成完成

报告生成是异步的，需要等待2-5秒（取决于变量复杂度）

---

### 步骤4: 下载报告

由于是异步生成，实际使用中需要通过数据库查询或建立轮询机制来获取report_id。

P0阶段可以直接等待几秒后，通过模板列表或数据库查询找到生成的报告。

```bash
curl -X GET http://localhost:8000/api/reports/{report_id}/download \
  -o report.md
```

---

## 运行API服务器

### 开发模式

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 生产模式

```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 测试API

使用pytest运行测试套件:

```bash
cd backend
pytest tests/test_api_*.py -v
```

**测试覆盖**:
- ✅ 模板CRUD (10个测试)
- ✅ 报告生成 (4个测试)
- ✅ 系统配置 (3个测试)
- ✅ 集成测试 (2个测试)

**总计**: 19个API测试 + 21个核心组件测试 = **40个测试**

---

## API交互工具

### 使用Postman

导入以下OpenAPI规范: http://localhost:8000/openapi.json

### 使用curl

参考上方示例

### 使用Python requests

```python
import requests

# 创建模板
response = requests.post(
    "http://localhost:8000/api/templates",
    json={
        "name": "Test Template",
        "template_content": "# {{title}}",
        "metadata": {...}
    }
)
template_id = response.json()["id"]

# 生成报告
response = requests.post(
    "http://localhost:8000/api/reports/generate",
    json={
        "template_id": template_id,
        "inputs": {"title": "My Report"}
    }
)
task_id = response.json()["task_id"]
```

---

## 下一步 (P1功能)

以下功能将在P1阶段实现：

1. **WebSocket进度推送** - 实时获取报告生成进度
2. **报告历史列表** - `GET /api/reports` 查询历史
3. **任务状态查询** - `GET /api/tasks/{task_id}` 查询任务状态
4. **变量执行详情** - 查看每个变量的执行结果
5. **模板验证API** - `POST /api/templates/{id}/validate`
6. **数据库连接管理** - `CRUD /api/config/db-connections`
7. **缓存管理** - API/AI结果缓存
8. **成本统计** - AI调用成本追踪

---

## 技术栈

- **框架**: FastAPI 0.109.0
- **ORM**: SQLAlchemy 2.0.25
- **数据库**: SQLite (开发) / PostgreSQL (生产)
- **异步**: asyncio + BackgroundTasks
- **测试**: pytest + TestClient

---

## 许可

本API为Markdown报告自动生成平台的一部分，仅供内部使用。

