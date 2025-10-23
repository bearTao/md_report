# prompt_template 双重插值问题修复总结

## 修复日期
2025-10-22

## 问题描述

### 核心问题

系统对 `prompt_template` 进行了**两次变量插值处理**，导致第一次渲染生成的内容（如JSON字符串）被误判为变量，在第二次插值时报错。

### 问题场景

#### 场景1：prompt 中包含 JSON 格式示例

**输入**：
```yaml
prompt_template: |
  请生成JSON格式的分析，示例：
  {"name": "示例", "score": 90}
  
  实际数据：工单ID = {{wgid}}
```

**错误**：
```
DependencyError: Variable '"name": "示例", "score": 90' not found for interpolation
```

**原因**：系统把 JSON 示例中的 `{"name": "示例"}` 当作待插值变量。

#### 场景2：使用 | tojson 过滤器

**输入**：
```yaml
prompt_template: |
  基于以下数据生成分析：
  {{ overview | tojson }}
```

**第一次渲染后生成**：
```
基于以下数据生成分析：
{"micro_grid_name": "某微网", "capacity": 100}
```

**错误**：
```
DependencyError: Variable '"micro_grid_name": "某微网", "capacity": 100' not found
```

**原因**：第一次渲染生成的 JSON 字符串在第二次插值时被误判为变量。

#### 场景3：使用 Jinja2 循环语法

**输入**：
```yaml
prompt_template: |
  分析以下站点：
  {% for site in plan_sites %}
  - {{ site.name }}
  {% endfor %}
```

**错误**：
```
DependencyError: Variable '% for site in plan_sites %' not found
```

**原因**：Jinja2 的循环语法没有被正确解析，循环变量在第二次插值时找不到。

---

## 问题根源

### 错误的处理流程（修复前）

**文件**：`backend/app/services/context.py` 的 `interpolate_string` 方法

```python
# 第 153 行：第一次替换 {{variable}}
template_str = re.sub(r'\{\{([^}]+)\}\}', replace_var, template_str)

# 第 156 行：第二次替换 {variable}  <-- 问题所在！
template_str = re.sub(r'\{([^{}]+)\}', replace_var, template_str)
```

**问题分析**：

1. **第一次替换**：`{{wgid}}` → `"ZQGY0174"`
2. **第二次替换**：如果变量值包含 JSON（如 `{"key": "value"}`），会被插入字符串
3. **错误匹配**：正则 `\{([^{}]+)\}` 会匹配 JSON 中的单花括号 `{...}`
4. **查找失败**：尝试查找变量 `"key": "value"`，报错

### 正确的处理流程应该是

1. **使用 Jinja2 模板引擎**：一次性渲染，不是简单的正则替换
2. **支持完整语法**：循环、条件、过滤器、宏等
3. **避免二次插值**：渲染后的内容不应再被当作模板处理

---

## 修复方案

### 核心改动

将 AI 和 Vision AI executor 中的 `context.interpolate_string()` 改为 `template_renderer.render()`。

### 修改1：AI Executor

**文件**：`backend/app/executors/ai.py`（第51-77行）

**修改前**：
```python
# Interpolate prompt template with dependencies
try:
    logger.debug(f"🔄 开始插值提示词模板")
    # ...
    prompt_text = self.context.interpolate_string(config.prompt_template)
    logger.debug(f"✅ 提示词插值成功，长度: {len(prompt_text)} 字符")
    # ...
except Exception as e:
    logger.error(f"❌ 提示词插值失败: {str(e)}", exc_info=True)
    raise AiGenerationError(
        self.variable_name,
        f"Failed to interpolate prompt: {str(e)}",
        e
    )
```

**修改后**：
```python
# Render prompt template with Jinja2 (supports full syntax)
try:
    logger.debug(f"🔄 开始渲染提示词模板")
    # ...
    
    # 使用 Jinja2 渲染 prompt_template（支持完整语法：循环、条件、过滤器等）
    from app.services.renderer import template_renderer
    prompt_text = template_renderer.render(
        config.prompt_template, 
        self.context.get_all_variables()
    )
    logger.debug(f"✅ 提示词渲染成功，长度: {len(prompt_text)} 字符")
    # ...
except Exception as e:
    logger.error(f"❌ 提示词渲染失败: {str(e)}", exc_info=True)
    raise AiGenerationError(
        self.variable_name,
        f"Failed to render prompt template: {str(e)}",
        e
    )
```

### 修改2：Vision AI Executor

**文件**：`backend/app/executors/vision_ai.py`（第61-67行）

**修改前**：
```python
# 3. 插值提示词模板
prompt_text = self.context.interpolate_string(vision_config.prompt_template)
logger.debug(f"[{self.variable_name}] Prompt: {prompt_text[:100]}...")
```

**修改后**：
```python
# 3. 渲染提示词模板（使用 Jinja2，支持完整语法）
from app.services.renderer import template_renderer
prompt_text = template_renderer.render(
    vision_config.prompt_template,
    self.context.get_all_variables()
)
logger.debug(f"[{self.variable_name}] Prompt: {prompt_text[:100]}...")
```

---

## 修复效果

### ✅ 支持的功能

修复后，用户可以在 `prompt_template` 中使用：

#### 1. JSON 格式示例

```yaml
prompt_template: |
  请生成JSON格式的数据，示例：
  {"name": "{{wgid}}", "count": 10, "items": [1, 2, 3]}
  
  要求：字段必须包含...
```

✅ **正常工作**：JSON 不会被误判为变量

#### 2. tojson 过滤器

```yaml
prompt_template: |
  基于以下数据生成分析：
  {{ overview | tojson }}
  
  请分析其中的关键指标。
```

✅ **正常工作**：`overview` 被正确转换为 JSON 字符串

#### 3. 循环语法

```yaml
prompt_template: |
  分析以下{{ plan_sites | length }}个站点：
  {% for site in plan_sites %}
  {{ loop.index }}. {{ site.name }} - {{ site.type }}
  {% endfor %}
  
  请识别其中的高风险站点。
```

✅ **正常工作**：正确循环，生成编号列表

#### 4. 条件语法

```yaml
prompt_template: |
  {% if index_scores | length > 5 %}
  数据充足（{{ index_scores | length }}条记录），请进行详细分析。
  {% else %}
  数据不足（仅{{ index_scores | length }}条记录），请进行简要分析。
  {% endif %}
  
  关键指标如下：
  {% for score in index_scores %}
  - {{ score.name }}: {{ score.value }}
  {% endfor %}
```

✅ **正常工作**：根据条件选择不同文本

#### 5. 嵌套数据访问

```yaml
prompt_template: |
  微网名称：{{ overview.micro_grid_name }}
  容量：{{ overview.capacity }}kW
  
  {% if overview.status == "正常" %}
  运行正常，请进行常规分析。
  {% else %}
  发现异常（{{ overview.status }}），请重点关注。
  {% endif %}
```

✅ **正常工作**：支持对象属性访问

#### 6. 过滤器链

```yaml
prompt_template: |
  站点列表（共{{ plan_sites | length }}个）：
  {{ plan_sites | selectattr('type', 'equalto', '室分站点') | list | length }}个室分站点
  {{ plan_sites | selectattr('type', 'search', '室外') | list | length }}个室外站点
```

✅ **正常工作**：支持多个过滤器组合

#### 7. 所有 Jinja2 内置功能

- ✅ 变量：`{{ variable }}`
- ✅ 过滤器：`{{ variable | filter }}`
- ✅ 测试：`{% if variable is defined %}`
- ✅ 循环：`{% for item in items %}`
- ✅ 条件：`{% if condition %}`
- ✅ 宏：`{% macro name() %}`
- ✅ 注释：`{# comment #}`
- ✅ 空白控制：`{{- variable -}}`

---

## 技术细节

### 为什么使用 Jinja2？

| 方面 | 正则替换（旧方案） | Jinja2 模板引擎（新方案） |
|------|-------------------|------------------------|
| **语法支持** | 仅支持简单变量替换 | 支持完整 Jinja2 语法 |
| **循环** | ❌ 不支持 | ✅ 支持 |
| **条件** | ❌ 不支持 | ✅ 支持 |
| **过滤器** | ⚠️ 部分支持（手动实现） | ✅ 完整支持 |
| **测试函数** | ❌ 不支持 | ✅ 支持（search, match等） |
| **安全性** | ⚠️ 需手动处理 | ✅ SandboxedEnvironment |
| **JSON 处理** | ❌ 误判为变量 | ✅ 正确处理 |
| **性能** | 快（但功能有限） | 快（轻微开销） |
| **一致性** | 与报告模板不一致 | ✅ 与报告模板一致 |

### 性能影响

- **Jinja2 渲染开销**：通常 < 1ms（对于几KB的模板）
- **AI 调用时间**：通常 10-60秒
- **相对开销**：几乎可忽略（< 0.1%）

### 安全性

使用的是 `SandboxedEnvironment`，具有以下安全保护：
- ❌ 不能访问私有属性（`__xxx__`）
- ❌ 不能执行任意代码
- ❌ 不能导入模块
- ❌ 不能访问文件系统
- ✅ 只能使用已注册的过滤器和测试函数

---

## 不受影响的功能

### `interpolate_string` 仍然保留

`context.interpolate_string()` 方法仍然保留，用于：

1. **SQL 查询**（`backend/app/executors/sql.py`）
   ```python
   query = self.context.interpolate_string(config.query)
   ```
   - ✅ 仍使用正则替换（SQL 中不需要 Jinja2 循环等）

2. **API URL**（`backend/app/executors/api.py`）
   ```python
   url = self.context.interpolate_string(config.endpoint)
   ```
   - ✅ 仍使用正则替换（URL 中不需要复杂语法）

3. **系统变量**（`backend/app/executors/system.py`）
   ```python
   value = self.context.interpolate_string(config.value_template)
   ```
   - ✅ 仍使用正则替换（简单字符串插值）

**原因**：这些场景不需要完整的 Jinja2 功能，简单的正则替换即可，且性能更好。

---

## 向后兼容性

### 现有模板仍然可用

**旧格式**（仍然支持）：
```yaml
prompt_template: "分析工单 {{wgid}} 的数据"
```

**新格式**（推荐）：
```yaml
prompt_template: |
  分析工单 {{wgid}} 的数据：
  {% for site in plan_sites %}
  - {{ site.name }}
  {% endfor %}
```

### 需要注意的变化

1. **单花括号 `{variable}` 需要改为双花括号 `{{variable}}`**
   - 旧：`分析 {wgid}` → 可能不工作
   - 新：`分析 {{wgid}}` → ✅ 正常工作

2. **转义 JSON 示例（不再需要）**
   - 旧：需要避免在 prompt 中使用 `{...}`
   - 新：✅ 可以直接使用 JSON 示例

---

## 测试验证

### 测试1：JSON 示例（已验证）

**输入**：
```yaml
prompt_template: |
  请生成JSON格式的分析，示例：
  {"name": "示例", "score": 90}
  
  实际数据：工单ID = {{wgid}}
```

**预期**：正常渲染，不报错  
**结果**：✅ 通过

### 测试2：tojson 过滤器（已验证）

**输入**：
```yaml
prompt_template: |
  基于以下数据生成分析：
  {{ overview | tojson }}
```

**预期**：`overview` 被正确转换为 JSON 字符串  
**结果**：✅ 通过

### 测试3：循环语法（已验证）

**输入**：
```yaml
prompt_template: |
  分析以下{{ plan_sites | length }}个站点：
  {% for site in plan_sites %}
  {{ loop.index }}. {{ site.name }}
  {% endfor %}
```

**预期**：正确循环，生成编号列表  
**结果**：✅ 通过

### 测试4：条件语法（已验证）

**输入**：
```yaml
prompt_template: |
  {% if index_scores | length > 5 %}
  数据充足，进行详细分析
  {% else %}
  数据不足，进行简要分析
  {% endif %}
```

**预期**：根据条件选择不同文本  
**结果**：✅ 通过

---

## 相关文件

### 已修改

- ✅ `backend/app/executors/ai.py` - AI 执行器（第51-77行）
- ✅ `backend/app/executors/vision_ai.py` - Vision AI 执行器（第61-67行）

### 未修改（保持原样）

- ⏺️ `backend/app/services/context.py` - 上下文管理器（`interpolate_string` 保留）
- ⏺️ `backend/app/executors/sql.py` - SQL 执行器（仍使用 `interpolate_string`）
- ⏺️ `backend/app/executors/api.py` - API 执行器（仍使用 `interpolate_string`）
- ⏺️ `backend/app/executors/system.py` - 系统执行器（仍使用 `interpolate_string`）

### 依赖

- 📦 `backend/app/services/renderer.py` - Jinja2 渲染器（已有，直接使用）

---

## 后续优化建议

### 1. 添加更多 Jinja2 过滤器

可以在 `renderer.py` 中添加自定义过滤器：

```python
# 添加自定义过滤器
self.env.filters['format_number'] = lambda x: f"{x:,.2f}"
self.env.filters['truncate_text'] = lambda x, n=50: x[:n] + '...' if len(x) > n else x
```

使用：
```jinja2
容量：{{ capacity | format_number }}kW
描述：{{ description | truncate_text(100) }}
```

### 2. 添加自定义函数

可以添加全局函数：

```python
# 添加全局函数
self.env.globals['range'] = range
self.env.globals['enumerate'] = enumerate
```

使用：
```jinja2
{% for i in range(5) %}
第 {{ i+1 }} 项
{% endfor %}
```

### 3. 模板继承和包含

未来可以支持模板片段复用：

```jinja2
{# 定义可重用的分析片段 #}
{% macro analyze_site(site) %}
站点 {{ site.name }}：
- 类型：{{ site.type }}
- 容量：{{ site.capacity }}kW
{% endmacro %}

{# 使用 #}
{% for site in plan_sites %}
{{ analyze_site(site) }}
{% endfor %}
```

---

## 总结

### 修复成果

✅ **解决了核心问题**：不再有双重插值  
✅ **支持完整 Jinja2**：循环、条件、过滤器、测试等  
✅ **向后兼容**：现有模板仍然可用  
✅ **性能无忧**：渲染开销 < 1ms  
✅ **安全可靠**：使用 `SandboxedEnvironment`  
✅ **一致性好**：与报告模板使用相同机制  

### 用户受益

1. ✅ 可以在 prompt 中使用 JSON 格式示例
2. ✅ 可以使用 `| tojson` 等 Jinja2 过滤器
3. ✅ 可以使用 `{% for %}` 循环动态生成内容
4. ✅ 可以使用 `{% if %}` 条件根据数据调整 prompt
5. ✅ prompt 编写更灵活、更强大

---

**修复完成** ✅

现在用户可以充分利用 Jinja2 的强大功能来编写更灵活、更强大的 AI prompt 模板了！

