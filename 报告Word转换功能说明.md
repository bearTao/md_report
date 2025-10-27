# 报告Word转换功能说明

## 功能概述

本功能允许用户将成功生成的Markdown格式报告转换为Microsoft Word (docx)格式，方便用户在办公场景中使用和编辑。

### 核心特性

- **状态限制**：只有状态为"成功"的报告才能转换
- **即时下载**：点击按钮后立即触发转换并下载Word文档
- **文件命名**：转换后的文件名为报告标题，后缀为`.docx`
- **错误处理**：完善的错误提示，包括pandoc未安装、转换失败等情况

## 技术实现

### 后端实现 (Python + Pandoc)

#### 1. 转换工具类

**文件位置**：`backend/app/utils/document_converter.py`

**核心类**：`DocumentConverter`

**转换方法**：
```python
DocumentConverter.markdown_to_docx(markdown_content: str) -> bytes
```

**实现流程**：
1. 检查pandoc是否安装
2. 创建临时目录和临时Markdown文件
3. 调用pandoc命令行工具执行转换
4. 读取生成的docx文件为字节流
5. 清理临时文件
6. 返回docx文件字节

**关键命令**：
```bash
pandoc input.md -o output.docx --from markdown --to docx --standalone
```

#### 2. API端点

**路径**：`GET /api/reports/{report_id}/convert/word`

**文件位置**：`backend/app/api/reports.py` (line 704-779)

**验证逻辑**：
- 报告必须存在
- 报告状态必须为SUCCESS
- 报告内容不能为空

**响应类型**：
- Content-Type: `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
- Content-Disposition: `attachment; filename*=UTF-8''<filename>.docx`

**错误处理**：
- 404: 报告不存在
- 400: 报告状态非成功或内容为空
- 500: Pandoc未安装或转换失败

### 前端实现 (React + TypeScript)

#### 1. API调用

**文件位置**：`frontend/src/api/reports.ts` (line 41-56)

**函数**：`convertReportToWord(reportId: string)`

**实现方式**：
- 使用axios发送GET请求，responseType为'blob'
- 创建临时URL对象
- 触发浏览器下载
- 清理临时URL

#### 2. UI组件

**文件位置**：`frontend/src/pages/reports/ReportList.tsx`

**位置**：报告历史列表的操作列

**按钮特性**：
- 图标：`<FileWordOutlined />`（Word图标）
- 文本：转换Word
- 显示条件：`record.status === 'success'`
- 加载状态：转换中显示loading动画
- 错误提示：转换失败显示具体错误信息

## 使用说明

### 前提条件

**必须安装Pandoc**：

```bash
# Ubuntu/Debian系统
sudo apt-get update
sudo apt-get install pandoc

# CentOS/RHEL系统
sudo yum install pandoc

# 使用conda (推荐)
conda install -c conda-forge pandoc

# macOS
brew install pandoc

# 验证安装
pandoc --version
```

### 用户操作流程

1. 进入"报告历史"页面
2. 找到状态为"成功"的报告
3. 在操作列点击"转换Word"按钮
4. 等待转换完成（通常1-3秒）
5. 浏览器自动下载Word文档

### 文件命名规则

- 格式：`<报告标题>.docx`
- 特殊字符会被替换为下划线
- 示例：`微网格ZQGY0174覆盖分析报告.docx`

## 错误处理

### 常见错误及解决方案

#### 1. Pandoc未安装

**错误信息**：
```
Pandoc is not installed on the server. Please contact the administrator.
```

**解决方法**：
- 联系系统管理员安装pandoc
- 参考上方"前提条件"部分的安装命令

#### 2. 报告状态不正确

**错误信息**：
```
Cannot convert report with status 'failed'. Only successful reports can be converted.
```

**解决方法**：
- 确认报告已成功生成
- 失败、进行中或取消的报告无法转换

#### 3. 报告内容为空

**错误信息**：
```
Report has no content to convert
```

**解决方法**：
- 检查报告是否正确生成
- 重新生成报告

#### 4. 转换超时

**错误信息**：
```
Conversion timed out after 30 seconds
```

**可能原因**：
- 报告内容过大
- 服务器性能不足

**解决方法**：
- 检查服务器资源使用情况
- 考虑增加超时时间限制

## 系统架构

```
用户点击"转换Word"按钮
         ↓
前端: convertReportToWord(reportId)
         ↓
发送GET请求: /api/reports/{id}/convert/word
         ↓
后端: convert_report_to_word()
         ↓
查询数据库获取报告
         ↓
验证状态和内容
         ↓
调用DocumentConverter.markdown_to_docx()
         ↓
创建临时Markdown文件
         ↓
调用pandoc命令转换
         ↓
读取生成的docx文件
         ↓
清理临时文件
         ↓
返回docx字节流
         ↓
前端接收blob数据
         ↓
创建下载链接
         ↓
浏览器下载文件
```

## 性能考虑

### 转换速度

- 小型报告（<10KB）：<1秒
- 中型报告（10-100KB）：1-3秒
- 大型报告（>100KB）：3-10秒

### 并发处理

- 每次转换使用独立临时目录
- 支持多用户同时转换
- 临时文件自动清理

### 资源占用

- 磁盘空间：临时文件约为报告大小的2-3倍
- 内存：pandoc进程约占用50-200MB
- CPU：转换过程中短暂占用

## 安全考虑

### 已实施的安全措施

1. **权限验证**：需要数据库中存在对应报告
2. **状态检查**：只允许转换成功状态的报告
3. **内容验证**：检查报告内容非空
4. **文件名清理**：移除特殊字符，防止路径注入
5. **临时文件隔离**：每次转换使用独立临时目录
6. **超时保护**：30秒超时限制，防止资源耗尽
7. **错误隔离**：转换失败不影响其他功能

### 建议的额外措施

1. **速率限制**：限制单用户转换频率
2. **文件大小限制**：限制可转换报告的最大大小
3. **日志记录**：记录所有转换请求和结果
4. **监控告警**：监控转换失败率和响应时间

## 维护与监控

### 日志位置

转换相关日志记录在：
- 应用日志：`backend/logs/app.log`
- 关键字：`DocumentConverter`, `convert_report_to_word`

### 监控指标

建议监控以下指标：
- 转换请求总数
- 转换成功率
- 平均转换时间
- Pandoc进程数
- 临时文件清理情况

### 故障排查

#### 检查pandoc状态
```bash
# 检查是否安装
which pandoc

# 检查版本
pandoc --version

# 测试转换
echo "# Test" | pandoc -f markdown -t docx -o test.docx
```

#### 检查临时目录
```bash
# 查看临时文件
ls -la /tmp/

# 清理旧的临时文件（如果需要）
find /tmp -name "tmp*" -mtime +1 -exec rm -rf {} \;
```

#### 查看转换日志
```bash
# 查看最近的转换日志
tail -f backend/logs/app.log | grep -i "convert\|pandoc"
```

## 未来改进方向

### 短期改进

1. 添加转换历史记录
2. 支持批量转换
3. 优化大文件转换性能
4. 添加转换进度提示

### 长期改进

1. 支持更多格式（PDF、HTML、PowerPoint等）
2. 自定义Word模板样式
3. 添加水印和页眉页脚
4. 集成云存储服务

## 相关文档

- [API响应schema修复说明.md](./API响应schema修复说明.md)
- [报告历史列表显示修复说明.md](./报告历史列表显示修复说明.md)
- [变量重试功能修复说明.md](./变量重试功能修复说明.md)

## 版本历史

- **v1.0.0** (2025-10-24): 初始版本，支持Markdown到Word转换

## 联系方式

如有问题或建议，请联系开发团队。

