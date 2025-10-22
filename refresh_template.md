# 解决 Vision AI 错误的步骤

## 问题原因

代码已修复，但你可能在使用**旧模板**（修复前创建的），需要重新创建模板。

## 解决步骤

### 方案A: 通过前端操作

1. **删除旧模板**
   - 进入模板管理页面
   - 找到你的模板
   - 点击删除

2. **重新创建模板**
   - 使用相同的配置重新创建模板
   - 确保 `output_format: url` 设置正确

### 方案B: 通过API操作

```bash
# 1. 列出所有模板，找到你的模板ID
curl http://localhost:8000/api/templates/

# 2. 删除旧模板（替换YOUR_TEMPLATE_ID）
curl -X DELETE http://localhost:8000/api/templates/YOUR_TEMPLATE_ID

# 3. 重新创建模板（使用你的配置）
```

### 方案C: 刷新浏览器缓存

1. 按 `Ctrl+Shift+R` (Windows/Linux) 或 `Cmd+Shift+R` (Mac) 强制刷新
2. 或清除浏览器缓存后重新登录

---

## 验证修复

使用以下配置创建新模板应该可以正常工作：

```yaml
product_photo:
  type: image
  source: image
  description: 产品照片
  dependencies:
    - product_id
  image_config:
    method: GET
    timeout: 30
    endpoint: https://picsum.photos/400/300
    output_format: url  # ✅ URL格式现在完全支持

quality_check:
  type: string
  source: vision_ai
  description: 质量检测报告
  dependencies:
    - product_photo
  vision_ai_config:
    model: THUDM/GLM-4.1V-9B-Thinking
    max_tokens: 999999
    temperature: 0.3
    image_source: product_photo  # ✅ 不需要 {{}}
    prompt_template: |
      请对这个产品进行质量检测：
      1. 外观评价
      2. 可见缺陷
      3. 质量评分（1-10分）
```

---

## 如果问题仍然存在

请提供以下信息：

1. **模板ID** - 使用的模板ID
2. **创建时间** - 模板是什么时候创建的？
3. **前端截图** - 错误提示的截图
4. **任务ID** - 失败任务的task_id

我可以帮你查看后台日志找出具体原因。

