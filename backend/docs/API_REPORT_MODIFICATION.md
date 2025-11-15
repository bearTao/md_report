# 报告修改代理 API 文档

## 概述

报告修改代理系统提供了基于自然语言的报告修改能力,允许用户通过对话式交互来修改已生成的报告。本文档详细说明了所有相关的API端点、请求格式、响应格式和使用示例。

## 基本信息

- **基础URL**: `/api`
- **API版本**: v1.0
- **认证方式**: Bearer Token (待实现)
- **内容类型**: `application/json`
- **字符编码**: UTF-8

## 目录

1. [报告修改](#1-报告修改)
2. [对话历史](#2-对话历史)
3. [保存为模板](#3-保存为模板)
4. [错误处理](#4-错误处理)
5. [使用示例](#5-使用示例)
6. [WebSocket通知](#6-websocket通知)

---

## 1. 报告修改

### 1.1 修改报告

通过自然语言请求修改现有报告。

**端点**: `POST /api/reports/{report_id}/modify`

**路径参数**:
- `report_id` (string, required): 报告ID

**请求体**:
```json
{
  "report_id": "string",
  "user_request": "string",
  "session_id": "string (optional)"
}
```

**字段说明**:
- `report_id`: 要修改的报告ID
- `user_request`: 用户的自然语言修改请求
- `session_id`: 会话ID(可选,用于继续已有对话)

**响应体**:
```json
{
  "success": true,
  "session_id": "session_abc123",
  "report_id": "report-456",
  "new_version": 2,
  "explanation": "已成功完成3个操作:1. 将wgid更新为ZQGY0175 2. 重新执行了data_query 3. 重新生成了analysis",
  "operations_summary": [
    "更新参数wgid: ZQGY0001 -> ZQGY0175",
    "重新执行依赖变量: data_query",
    "重新执行依赖变量: analysis"
  ],
  "markdown_content": "# 更新后的报告内容...",
  "metadata": {
    "total_duration_ms": 2500,
    "total_cost_usd": 0.08,
    "operations_count": 3,
    "llm_calls_count": 2,
    "from_version": 1,
    "to_version": 2
  },
  "error": null
}
```

**状态码**:
- `200 OK`: 修改成功
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 报告不存在
- `500 Internal Server Error`: 服务器错误

---

### 1.2 修改请求示例

#### 示例 1: 参数更新

**请求**:
```bash
curl -X POST http://localhost:8000/api/reports/report-123/modify \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "report-123",
    "user_request": "把wgid改成ZQGY0175"
  }'
```

**响应**:
```json
{
  "success": true,
  "session_id": "session_abc123",
  "report_id": "report-123",
  "new_version": 2,
  "explanation": "已将wgid更新为ZQGY0175,并重新执行了2个依赖变量",
  "operations_summary": [
    "更新参数wgid: ZQGY0001 -> ZQGY0175",
    "重新执行data_query",
    "重新执行report_title"
  ],
  "markdown_content": "# 更新后的报告内容...",
  "metadata": {
    "total_duration_ms": 1500,
    "total_cost_usd": 0.02,
    "operations_count": 3,
    "llm_calls_count": 1,
    "from_version": 1,
    "to_version": 2
  }
}
```

#### 示例 2: AI内容优化

**请求**:
```bash
curl -X POST http://localhost:8000/api/reports/report-123/modify \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "report-123",
    "user_request": "让分析部分更详细,增加具体的数据支撑",
    "session_id": "session_abc123"
  }'
```

**响应**:
```json
{
  "success": true,
  "session_id": "session_abc123",
  "report_id": "report-123",
  "new_version": 3,
  "explanation": "已优化分析内容,增加了详细的数据支撑和具体案例",
  "operations_summary": [
    "优化AI内容: analysis (500字 -> 1200字)"
  ],
  "markdown_content": "# 报告内容...\n\n## 分析\n\n[更详细的分析内容]",
  "metadata": {
    "total_duration_ms": 3500,
    "total_cost_usd": 0.15,
    "operations_count": 1,
    "llm_calls_count": 1,
    "from_version": 2,
    "to_version": 3
  }
}
```

#### 示例 3: 添加新章节

**请求**:
```bash
curl -X POST http://localhost:8000/api/reports/report-123/modify \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "report-123",
    "user_request": "添加竞争对手分析章节",
    "session_id": "session_abc123"
  }'
```

**响应**:
```json
{
  "success": true,
  "session_id": "session_abc123",
  "report_id": "report-123",
  "new_version": 4,
  "explanation": "已添加'竞争对手分析'章节,包含主要竞争对手的市场表现数据",
  "operations_summary": [
    "添加章节: 竞争对手分析",
    "创建运行时变量: competitor_data",
    "创建运行时变量: competitor_analysis"
  ],
  "markdown_content": "# 报告内容...\n\n## 竞争对手分析\n\n[新增的竞争对手分析内容]",
  "metadata": {
    "total_duration_ms": 5000,
    "total_cost_usd": 0.25,
    "operations_count": 1,
    "llm_calls_count": 3,
    "from_version": 3,
    "to_version": 4
  }
}
```

#### 示例 4: 多意图请求

**请求**:
```bash
curl -X POST http://localhost:8000/api/reports/report-123/modify \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "report-123",
    "user_request": "把wgid改成ZQGY0175,同时让分析更详细,还要添加风险评估章节"
  }'
```

**响应**:
```json
{
  "success": true,
  "session_id": "session_def456",
  "report_id": "report-123",
  "new_version": 2,
  "explanation": "已完成3个操作:1. 更新wgid 2. 优化分析内容 3. 添加风险评估章节",
  "operations_summary": [
    "更新参数wgid: ZQGY0001 -> ZQGY0175",
    "优化AI内容: analysis",
    "添加章节: 风险评估"
  ],
  "markdown_content": "# 更新后的报告...",
  "metadata": {
    "total_duration_ms": 8000,
    "total_cost_usd": 0.35,
    "operations_count": 5,
    "llm_calls_count": 4,
    "from_version": 1,
    "to_version": 2
  }
}
```

---

## 2. 对话历史

### 2.1 获取对话历史

获取报告修改的完整对话历史。

**端点**: `GET /api/reports/{report_id}/conversation`

**路径参数**:
- `report_id` (string, required): 报告ID

**查询参数**:
- `session_id` (string, optional): 会话ID,如果不提供则返回最新活跃会话

**响应体**:
```json
{
  "session_id": "session_abc123",
  "report_id": "report-123",
  "turns": [
    {
      "turn_number": 1,
      "user_request": "把wgid改成ZQGY0175",
      "parsed_intents": [
        {
          "intent_type": "update_parameter",
          "target_variable": "wgid",
          "new_value": "ZQGY0175",
          "confidence": 0.95
        }
      ],
      "operations": [
        {
          "operation_type": "update_parameter",
          "details": {
            "variable_name": "wgid",
            "old_value": "ZQGY0001",
            "new_value": "ZQGY0175",
            "dependent_variables": ["data_query", "report_title"]
          },
          "success": true,
          "duration_ms": 150,
          "cost_usd": 0.02
        }
      ],
      "system_response": "已将wgid更新为ZQGY0175",
      "report_version": 2,
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "context_summary": "用户修改了报告参数,共进行了3次操作",
  "current_version": 4
}
```

**状态码**:
- `200 OK`: 成功
- `404 Not Found`: 报告或会话不存在

**示例**:
```bash
curl -X GET "http://localhost:8000/api/reports/report-123/conversation?session_id=session_abc123"
```

---

## 3. 保存为模板

### 3.1 将修改后的报告保存为模板

将修改后的报告(包括临时模板修改)保存为新的模板。

**端点**: `POST /api/reports/{report_id}/save-as-template`

**路径参数**:
- `report_id` (string, required): 报告ID

**请求体**:
```json
{
  "report_id": "report-123",
  "template_name": "自定义市场分析模板",
  "template_description": "包含竞争对手分析和风险评估的详细市场分析模板"
}
```

**响应体**:
```json
{
  "success": true,
  "template_id": "template-789",
  "message": "模板已成功保存"
}
```

**状态码**:
- `200 OK`: 保存成功
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 报告不存在

**示例**:
```bash
curl -X POST http://localhost:8000/api/reports/report-123/save-as-template \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "report-123",
    "template_name": "自定义市场分析模板",
    "template_description": "包含竞争对手分析的模板"
  }'
```

---

## 4. 错误处理

### 4.1 错误响应格式

所有错误响应遵循统一格式:

```json
{
  "success": false,
  "session_id": "session_abc123",
  "report_id": "report-123",
  "new_version": 1,
  "explanation": "操作失败",
  "operations_summary": [],
  "markdown_content": "",
  "metadata": {
    "total_duration_ms": 500,
    "total_cost_usd": 0.01,
    "operations_count": 0,
    "llm_calls_count": 1,
    "from_version": 1,
    "to_version": 1
  },
  "error": "错误详细信息"
}
```

### 4.2 常见错误

#### 报告不存在
```json
{
  "detail": "报告不存在: report-999"
}
```
**状态码**: 404

#### 请求不明确
```json
{
  "success": false,
  "error": "请求不够明确,需要更多信息: 您想要修改哪个变量?"
}
```
**状态码**: 200 (业务错误)

#### 变量不存在
```json
{
  "success": false,
  "error": "变量不存在: invalid_var。已知变量: wgid, title, analysis"
}
```
**状态码**: 200 (业务错误)

#### LLM调用失败
```json
{
  "success": false,
  "error": "LLM调用失败: API rate limit exceeded"
}
```
**状态码**: 200 (业务错误)

#### 会话不匹配
```json
{
  "detail": "会话 session-xxx 不属于报告 report-123"
}
```
**状态码**: 400

---

## 5. 使用示例

### 5.1 完整的对话流程

#### 步骤1: 创建初始会话并修改参数

```bash
# 第一次修改 - 系统自动创建会话
curl -X POST http://localhost:8000/api/reports/report-123/modify \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "report-123",
    "user_request": "把wgid改成ZQGY0175"
  }'

# 响应包含新创建的session_id
# {
#   "success": true,
#   "session_id": "session_abc123",
#   "new_version": 2,
#   ...
# }
```

#### 步骤2: 继续对话 - 优化内容

```bash
# 使用相同的session_id继续对话
curl -X POST http://localhost:8000/api/reports/report-123/modify \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "report-123",
    "user_request": "让分析更详细一些",
    "session_id": "session_abc123"
  }'

# 响应
# {
#   "success": true,
#   "session_id": "session_abc123",
#   "new_version": 3,
#   ...
# }
```

#### 步骤3: 使用代词引用

```bash
# 系统能理解"它"指的是最近操作的变量
curl -X POST http://localhost:8000/api/reports/report-123/modify \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "report-123",
    "user_request": "把它再延长一些",
    "session_id": "session_abc123"
  }'
```

#### 步骤4: 查看对话历史

```bash
curl -X GET "http://localhost:8000/api/reports/report-123/conversation?session_id=session_abc123"
```

#### 步骤5: 保存为模板

```bash
curl -X POST http://localhost:8000/api/reports/report-123/save-as-template \
  -H "Content-Type: application/json" \
  -d '{
    "report_id": "report-123",
    "template_name": "我的自定义模板"
  }'
```

### 5.2 Python客户端示例

```python
import requests
import json

class ReportModificationClient:
    """报告修改API客户端"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session_id = None
    
    def modify_report(self, report_id: str, user_request: str):
        """修改报告"""
        url = f"{self.base_url}/api/reports/{report_id}/modify"
        
        payload = {
            "report_id": report_id,
            "user_request": user_request
        }
        
        # 如果已有会话,继续使用
        if self.session_id:
            payload["session_id"] = self.session_id
        
        response = requests.post(url, json=payload)
        result = response.json()
        
        # 保存会话ID以便后续使用
        if result.get("success"):
            self.session_id = result["session_id"]
        
        return result
    
    def get_conversation_history(self, report_id: str):
        """获取对话历史"""
        url = f"{self.base_url}/api/reports/{report_id}/conversation"
        params = {"session_id": self.session_id} if self.session_id else {}
        
        response = requests.get(url, params=params)
        return response.json()
    
    def save_as_template(self, report_id: str, template_name: str, description: str = None):
        """保存为模板"""
        url = f"{self.base_url}/api/reports/{report_id}/save-as-template"
        
        payload = {
            "report_id": report_id,
            "template_name": template_name,
            "template_description": description
        }
        
        response = requests.post(url, json=payload)
        return response.json()

# 使用示例
client = ReportModificationClient()

# 修改1: 更新参数
result1 = client.modify_report(
    report_id="report-123",
    user_request="把wgid改成ZQGY0175"
)
print(f"版本: {result1['new_version']}, 说明: {result1['explanation']}")

# 修改2: 优化内容(自动使用同一会话)
result2 = client.modify_report(
    report_id="report-123",
    user_request="让分析更详细"
)
print(f"版本: {result2['new_version']}, 说明: {result2['explanation']}")

# 查看历史
history = client.get_conversation_history("report-123")
print(f"总共 {len(history['turns'])} 轮对话")

# 保存为模板
template_result = client.save_as_template(
    report_id="report-123",
    template_name="我的自定义模板",
    description="优化后的报告模板"
)
print(f"新模板ID: {template_result['template_id']}")
```

### 5.3 JavaScript/TypeScript客户端示例

```typescript
interface ModifyReportRequest {
  report_id: string;
  user_request: string;
  session_id?: string;
}

interface ModifyReportResponse {
  success: boolean;
  session_id: string;
  report_id: string;
  new_version: number;
  explanation: string;
  operations_summary: string[];
  markdown_content: string;
  metadata: {
    total_duration_ms: number;
    total_cost_usd: number;
    operations_count: number;
    llm_calls_count: number;
    from_version: number;
    to_version: number;
  };
  error?: string;
}

class ReportModificationClient {
  private baseUrl: string;
  private sessionId?: string;
  
  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl;
  }
  
  async modifyReport(reportId: string, userRequest: string): Promise<ModifyReportResponse> {
    const url = `${this.baseUrl}/api/reports/${reportId}/modify`;
    
    const payload: ModifyReportRequest = {
      report_id: reportId,
      user_request: userRequest,
    };
    
    if (this.sessionId) {
      payload.session_id = this.sessionId;
    }
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    
    const result: ModifyReportResponse = await response.json();
    
    if (result.success) {
      this.sessionId = result.session_id;
    }
    
    return result;
  }
  
  async getConversationHistory(reportId: string) {
    const url = new URL(`${this.baseUrl}/api/reports/${reportId}/conversation`);
    if (this.sessionId) {
      url.searchParams.append('session_id', this.sessionId);
    }
    
    const response = await fetch(url.toString());
    return await response.json();
  }
  
  async saveAsTemplate(reportId: string, templateName: string, description?: string) {
    const url = `${this.baseUrl}/api/reports/${reportId}/save-as-template`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        report_id: reportId,
        template_name: templateName,
        template_description: description,
      }),
    });
    
    return await response.json();
  }
}

// 使用示例
const client = new ReportModificationClient();

// 修改报告
const result = await client.modifyReport(
  'report-123',
  '把wgid改成ZQGY0175'
);
console.log(`新版本: ${result.new_version}`);
console.log(`说明: ${result.explanation}`);
```

---

## 6. WebSocket通知

报告修改过程支持WebSocket实时通知,用于长时间操作的进度更新。

### 6.1 连接WebSocket

**端点**: `ws://localhost:8000/ws/{session_id}`

**示例**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/session_abc123');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Progress:', data);
};

// 消息格式
// {
//   "type": "progress",
//   "message": "正在解析意图...",
//   "progress": 0.2
// }
// {
//   "type": "progress",
//   "message": "正在执行操作1/3...",
//   "progress": 0.4
// }
// {
//   "type": "complete",
//   "message": "修改完成",
//   "progress": 1.0
// }
```

---

## 7. 性能指标

### 7.1 响应时间

- **简单参数更新**: < 2秒
- **AI内容优化**: 3-10秒(取决于内容长度)
- **添加章节**: 5-15秒(取决于数据复杂度)
- **多意图请求**: 累计,通常< 30秒

### 7.2 成本估算

基于GPT-4定价:
- **意图解析**: ~$0.01-0.02/次
- **AI内容优化**: ~$0.05-0.15/次
- **添加章节**: ~$0.10-0.30/次(包含数据分析和Jinja2生成)

---

## 8. 最佳实践

### 8.1 请求优化

1. **使用明确的表述**: 
   - ✅ 好: "把wgid改成ZQGY0175"
   - ❌ 差: "改一下"

2. **合并相关操作**:
   - ✅ 好: "把wgid改成ZQGY0175,同时让分析更详细"
   - ❌ 差: 分两次请求

3. **利用会话上下文**:
   - ✅ 好: "把它改长一点" (在上下文中)
   - ❌ 差: 不提供上下文

### 8.2 错误处理

1. **检查success字段**
2. **处理clarification_needed情况**
3. **实现重试机制**(对于网络错误)
4. **记录error字段**用于调试

### 8.3 会话管理

1. **保存session_id**用于多轮对话
2. **合理的会话超时**(建议7天)
3. **定期清理不活跃会话**

---

## 9. 支持的自然语言模式

### 9.1 参数更新

- "把X改成Y"
- "将X修改为Y"
- "X改为Y"
- "更新X为Y"
- "X设为Y"

### 9.2 AI内容优化

- "让X更详细"
- "使X更简洁"
- "优化X"
- "X写得更专业一些"
- "增加X的数据支撑"

### 9.3 模板修改

- "添加X章节"
- "增加X部分"
- "删除X"
- "去掉X"
- "修改X的格式"

### 9.4 引用和相对值

- "把它改长一点" (代词引用)
- "延长一周" (相对时间)
- "增加10个" (相对数值)
- "再详细一些" (相对程度)

---

## 10. 限制和约束

### 10.1 系统限制

- 最大对话轮次: 无限制(但建议不超过50轮)
- 最大请求长度: 2000字符
- 会话过期时间: 7天不活跃
- 并发修改: 不支持同一报告的并发修改

### 10.2 功能限制

- 不支持回滚到历史版本(使用版本号重新生成)
- 临时模板修改需手动保存才能永久化
- 运行时变量不会保存到模板定义中

---

## 11. 常见问题

### Q1: 如何继续之前的对话?

**A**: 在请求中提供`session_id`参数。

### Q2: 系统如何理解"它"、"这个"等代词?

**A**: 系统根据对话历史中最近操作的变量/章节来推断引用对象。

### Q3: 修改是否会影响原始模板?

**A**: 不会。修改只影响当前报告实例。如需永久化,使用"保存为模板"功能。

### Q4: 可以撤销修改吗?

**A**: 当前版本不支持撤销。建议在修改前备份报告。

### Q5: 成本如何控制?

**A**: 系统已优化LLM使用,关键操作使用规则引擎。可通过`metadata.total_cost_usd`监控成本。

---

## 12. 变更日志

### v1.0.0 (2024-01-15)
- 初始版本发布
- 支持参数更新、AI优化、模板修改
- 支持多轮对话和上下文理解
- 提供WebSocket进度通知

---

## 13. 联系支持

如有问题或建议,请联系:
- 邮箱: support@example.com
- 问题追踪: https://github.com/yourproject/issues

