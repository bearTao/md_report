# API 功能增强说明

## 更新日期
2025-10-28

## 概述

本次更新对 API 变量功能进行了三项重大增强：

1. **引入 JMESPath** - 强大的路径提取能力
2. **重试机制** - 提高对不稳定 API 的容错性
3. **融合 response_mapping** - 支持三种模式，更灵活的数据映射

---

## 功能 1：JMESPath 路径提取

### 概述
集成 JMESPath 库，提供强大的 JSON 数据提取和转换能力。

### 支持的功能

| 功能 | 语法示例 | 说明 |
|------|---------|------|
| 简单路径 | `"data.items"` | 提取嵌套字段 |
| 数组索引 | `"items[0]"` | 访问数组元素 |
| 数组切片 | `"items[:3]"` | 提取数组的前3个元素 |
| 投影 | `"items[*].name"` | 提取所有元素的 name 字段 |
| 过滤 | `"items[?price > \`100\`]"` | 筛选价格大于100的项 |
| 函数 | `"length(items)"` | 计算数组长度 |

### 示例

```yaml
# 提取所有产品名称
product_names:
  type: array
  source: api
  api_config:
    endpoint: "http://api.shop.com/products"
    response_mapping: "data.items[*].name"

# 筛选高价产品
expensive_items:
  type: array
  source: api
  api_config:
    endpoint: "http://api.shop.com/products"
    response_mapping: "data.items[?price > `100`]"
```

### 向后兼容
保留简单点号解析作为降级方案，现有配置无需修改。

---

## 功能 2：重试机制

### 新增配置字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `retry_count` | number | 0 | 重试次数，0表示不重试 |
| `retry_status_codes` | array | [429, 500, 502, 503, 504] | 触发重试的HTTP状态码 |
| `retry_backoff` | number | 1.0 | 重试间隔基数（秒） |

### 重试策略

- **线性退避**：第 n 次重试等待 `retry_backoff * n` 秒
- **状态码判断**：仅对指定的 HTTP 状态码重试
- **超时重试**：请求超时也会触发重试
- **日志记录**：每次重试都会记录警告日志

### 示例

```yaml
unstable_api:
  type: object
  source: api
  api_config:
    endpoint: "http://api.external.com/data"
    retry_count: 3  # 最多重试3次
    retry_status_codes: [429, 500, 503]
    retry_backoff: 2.0  # 等待时间：2秒、4秒、6秒
```

### 使用场景

- 调用不稳定的第三方 API
- 处理限流（429 Too Many Requests）
- 应对临时服务器错误
- 网络不稳定的环境

---

## 功能 3：融合 response_mapping

### 三种模式

#### 模式 1：完整响应（无映射）

**配置**：
```yaml
api_config:
  endpoint: "http://api.example.com/data"
  # 不写 response_mapping 或设为 null
```

**用途**：API 返回的结构已经符合需求，直接使用

---

#### 模式 2：单路径提取（字符串）

**配置**：
```yaml
# 提取数组
products:
  type: array
  api_config:
    endpoint: "http://api.shop.com/products"
    response_mapping: "data.items"  # 字符串

# 提取对象
weather:
  type: object
  api_config:
    endpoint: "http://api.weather.com/current"
    response_mapping: "data.current"

# 提取基础类型
version:
  type: string
  api_config:
    endpoint: "http://api.app.com/version"
    response_mapping: "version"  # 返回 "2.5.1"
```

**用途**：提取 API 响应中某个嵌套路径的完整值，返回值可以是任意类型

**优势**：
- ✅ 支持返回数组（解决之前只能返回对象的限制）
- ✅ 保持原始数据结构
- ✅ 配置简洁

---

#### 模式 3：多字段映射（字典）

**配置**：
```yaml
weather_summary:
  type: object
  api_config:
    endpoint: "http://api.weather.com/forecast"
    response_mapping:  # 字典：重组数据
      temperature: "data.current.temp"
      condition: "data.current.condition"
      latitude: "coord.lat"
      longitude: "coord.lon"
```

**用途**：从不同路径提取多个字段并重组为新对象

**优势**：
- ✅ 重命名字段
- ✅ 从不同层级组合数据
- ✅ 精简返回数据

---

### 对比表

| 模式 | response_mapping 值 | 返回类型 | 使用场景 |
|------|-------------------|---------|---------|
| 完整响应 | `null` 或省略 | 原始响应 | API结构已完美 |
| 单路径提取 | 字符串 `"path"` | 任意类型 | 提取某个嵌套结构 |
| 多字段映射 | 对象 `{key: "path"}` | 对象 | 重组和重命名数据 |

---

## 参数类型增强

### 变更
`api_config.parameters` 从 `Dict[str, str]` 改为 `Dict[str, Any]`

### 好处
支持传递任意类型的参数：

```yaml
api_config:
  parameters:
    page: 1           # 数字
    limit: 20         # 数字
    active: true      # 布尔
    tags: ["a", "b"]  # 数组
    query: "search"   # 字符串
```

---

## 代码变更清单

### 修改的文件

1. **backend/requirements.txt**
   - 添加 `jmespath>=1.0.1`

2. **backend/app/core/models.py**
   - `ApiConfig.parameters`: `Dict[str, str]` → `Dict[str, Any]`
   - `ApiConfig.response_mapping`: `Dict[str, str]` → `Optional[Union[str, Dict[str, str]]]`
   - 新增字段：`retry_count`, `retry_status_codes`, `retry_backoff`

3. **backend/app/connectors/api.py**
   - 集成 JMESPath
   - 增强 `_extract_path()` 方法
   - 新增 `_simple_dot_extract()` 降级方法
   - `request()` 方法添加重试逻辑

4. **backend/app/executors/api.py**
   - 处理三种 response_mapping 模式
   - 传递重试配置到 connector

5. **字段说明文档.md**
   - 更新 API 配置说明
   - 添加 JMESPath 语法说明
   - 添加重试机制说明
   - 添加完整示例

6. **backend/example_usage.py**
   - 更新示例展示新功能

7. **backend/tests/test_api_enhancements.py**
   - 新增测试文件
   - 测试 JMESPath 功能
   - 测试三种 response_mapping 模式
   - 测试重试逻辑
   - 测试向后兼容性

---

## 向后兼容性

✅ **完全向后兼容**

- 现有的 `response_mapping: {}` 配置继续工作（返回完整响应）
- 现有的字典映射配置完全兼容
- 简单点号路径继续支持
- 默认不启用重试（`retry_count=0`）
- `parameters` 支持字符串值（Any 类型包含 str）

---

## 测试

运行测试：

```bash
cd backend
pytest tests/test_api_enhancements.py -v
```

测试覆盖：
- ✅ JMESPath 各种语法
- ✅ 三种 response_mapping 模式
- ✅ 重试逻辑（成功、失败、部分重试）
- ✅ 向后兼容性

---

## 使用建议

### 何时使用重试？

- ✅ 调用外部第三方 API
- ✅ 存在网络不稳定的情况
- ✅ API 有限流机制
- ❌ 内网稳定服务（无需重试）

### 如何选择 response_mapping 模式？

1. **API 返回结构很好** → 不写 `response_mapping`
2. **需要某个嵌套字段** → 用字符串 `"path.to.field"`
3. **需要重组数据** → 用字典 `{newKey: "old.path"}`

### JMESPath 最佳实践

- 简单场景用简单路径：`"data.items"`
- 需要过滤时用条件：`"items[?price > \`100\`]"`
- 需要提取多个字段时用投影：`"items[*].name"`
- 复杂逻辑可以组合使用

---

## 相关资源

- [JMESPath 官方文档](https://jmespath.org/)
- [JMESPath 教程](https://jmespath.org/tutorial.html)
- [JMESPath 在线测试](https://jmespath.org/)

---

## 常见问题

### Q: JMESPath 语法错误会怎样？
A: 自动降级到简单点号解析，并记录调试日志。

### Q: 重试会增加响应时间吗？
A: 仅在失败时重试，成功请求无影响。

### Q: 可以对所有状态码重试吗？
A: 可以，但不建议。应只对临时性错误重试（5xx、429）。

### Q: 旧配置需要更新吗？
A: 不需要，完全向后兼容。

---

## 总结

本次更新显著增强了 API 变量的灵活性和可靠性：

1. **JMESPath** - 解锁强大的数据提取能力
2. **重试机制** - 提高系统稳定性
3. **融合 response_mapping** - 简化配置，支持更多场景

所有改进都保持完全向后兼容，现有配置无需修改即可继续使用。


