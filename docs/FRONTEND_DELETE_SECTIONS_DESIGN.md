# 前端删除章节功能设计文档

## 📋 目录
- [功能概述](#功能概述)
- [用户交互流程](#用户交互流程)
- [UI组件设计](#ui组件设计)
- [API对接](#api对接)
- [状态管理](#状态管理)
- [错误处理](#错误处理)

---

## 功能概述

### 核心功能
用户可以通过自然语言请求删除报告中的章节，系统提供：
- 智能识别要删除的章节
- 逐个确认删除操作
- 报告锁定机制（保持数据时间一致性）
- 替代方案（重新生成报告）

### 设计原则
1. **安全第一**：每个删除操作都需要用户明确确认
2. **透明清晰**：显示完整的章节路径和内容预览
3. **可撤销**：用户可以跳过或拒绝单个章节的删除
4. **状态可见**：清晰展示报告的锁定状态和限制

---

## 用户交互流程

### 阶段1：发起删除请求

```
用户输入删除请求
      ↓
系统解析并生成删除计划
      ↓
展示待确认的章节列表
```

**示例输入**：
- "删除网格评分分析章节"
- "删除所有包含表格的章节"
- "删除除了概述以外的所有章节"

### 阶段2：逐个确认章节

```
展示章节列表（带预览）
      ↓
用户逐个决策（执行/跳过/拒绝）
      ↓
选择执行模式
```

**用户可见信息**：
- 章节完整路径（如：预分析报告->1、网格概述->1.1 网格评分分析）
- 内容预览（前200字）
- 行号范围

**用户决策选项**：
- ✅ **执行** - 删除此章节
- ⏭️ **跳过** - 不删除，继续下一个
- ❌ **拒绝** - 取消整个删除计划

### 阶段3：选择执行模式

用户必须在两种模式中选择一种：

#### 模式A：删除并锁定（推荐）
- **适用场景**：需要保持当前数据状态
- **效果**：
  - 删除指定章节
  - 报告锁定为静态版本
  - 保留原始生成时间的数据
  - 无法再修改参数
- **后续操作**：
  - ✅ 可以删除其他章节
  - ✅ 可以修改文本内容
  - ❌ 不能修改参数

#### 模式B：重新生成（排除章节）
- **适用场景**：需要最新数据
- **效果**：
  - 使用最新数据重新生成报告
  - 排除指定章节
  - 保持可编辑状态
  - 可以继续修改参数
- **注意**：数据会更新到最新状态

### 阶段4：执行并展示结果

```
执行删除操作
      ↓
更新报告内容
      ↓
展示执行结果
```

**结果信息**：
- 已删除章节列表
- 跳过的章节列表
- 报告锁定状态
- 可用/不可用的操作列表

---

## UI组件设计

### 1. 删除计划对话框 (`DeletePlanDialog`)

#### 组件结构
```tsx
<DeletePlanDialog>
  <DialogHeader>
    <AlertIcon />
    <Title>确认删除章节</Title>
    <Subtitle>共 {count} 个章节待删除</Subtitle>
  </DialogHeader>
  
  <LockWarning>
    ⚠️ 删除章节后，报告将锁定为静态版本（数据时间：{timestamp}），无法再修改参数。
  </LockWarning>
  
  <SectionList>
    {sections.map(section => (
      <SectionCard key={section.section_id}>
        <SectionPath>{section.section_path}</SectionPath>
        <ContentPreview>{section.content_preview}</ContentPreview>
        <LineInfo>行 {section.start_line} - {section.end_line}</LineInfo>
        <ActionButtons>
          <Button variant="danger">执行删除</Button>
          <Button variant="secondary">跳过</Button>
        </ActionButtons>
      </SectionCard>
    ))}
  </SectionList>
  
  <AlternativeOptions>
    <AlternativeCard>
      <Icon>🔄</Icon>
      <Title>重新生成（排除这些章节）</Title>
      <Description>使用最新数据重新生成报告，但排除指定章节</Description>
      <Button>选择此方案</Button>
    </AlternativeCard>
  </AlternativeOptions>
  
  <DialogFooter>
    <Button variant="secondary" onClick={handleCancel}>取消</Button>
    <Button variant="primary" onClick={handleConfirm}>确认删除</Button>
  </DialogFooter>
</DeletePlanDialog>
```

#### 状态管理
```typescript
interface DeletePlanState {
  plan: BatchDeletePlan | null;
  decisions: Map<string, 'execute' | 'skip' | 'reject'>;
  selectedMode: 'delete_and_lock' | 'regenerate_without';
  isSubmitting: boolean;
}
```

#### 交互行为
- **全选/全不选**：快速选择所有章节
- **实时统计**：显示已选择/跳过的数量
- **智能提示**：根据选择动态更新警告信息
- **键盘导航**：支持 Tab、Enter、Esc 快捷键

### 2. 章节卡片 (`SectionCard`)

#### 视觉设计
```css
.section-card {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  transition: border-color 0.2s;
}

.section-card:hover {
  border-color: #2196F3;
}

.section-card.selected-delete {
  border-color: #f44336;
  background: #fff5f5;
}

.section-card.selected-skip {
  border-color: #ff9800;
  background: #fff8e1;
}
```

#### 内容布局
```
┌─────────────────────────────────────────┐
│ 📄 预分析报告->1、网格概述->1.1 网格评分分析  │
├─────────────────────────────────────────┤
│ # 1.1 网格评分分析                        │
│                                          │
│ 本次分析涵盖XX个网格，整体评分如下：        │
│ | 指标 | 评分 |                           │
│ |------|------|                          │
│ | 可靠性 | 85 |...                        │
│                                          │
│ 行 15-45 (共 30 行)                       │
├─────────────────────────────────────────┤
│ [✅ 执行删除]  [⏭️ 跳过]                   │
└─────────────────────────────────────────┘
```

### 3. 执行结果提示 (`DeleteResultToast`)

#### 成功提示
```tsx
<Toast variant="success">
  <Icon>✅</Icon>
  <Message>
    已成功删除 {deletedCount} 个章节
    {skippedCount > 0 && `，跳过 ${skippedCount} 个章节`}
  </Message>
  <LockBadge>🔒 报告已锁定</LockBadge>
</Toast>
```

#### 错误提示
```tsx
<Toast variant="error">
  <Icon>❌</Icon>
  <Message>删除失败：{errorMessage}</Message>
  <Button onClick={handleRetry}>重试</Button>
</Toast>
```

### 4. 报告状态指示器 (`ReportStatusBadge`)

#### 模板模式（可编辑）
```tsx
<Badge variant="success">
  <Icon>📝</Icon>
  <Text>模板模式 - 可修改参数</Text>
</Badge>
```

#### 锁定模式（静态）
```tsx
<Badge variant="warning">
  <Icon>🔒</Icon>
  <Text>已锁定 - {lockReason}</Text>
  <Tooltip>
    数据时间：{generatedAt}
    锁定时间：{lockedAt}
    
    当前限制：
    ❌ 不能修改参数
    ✅ 可以删除章节
    ✅ 可以修改文本
  </Tooltip>
</Badge>
```

---

## API对接

### API 1: 生成删除计划

#### 请求
```typescript
POST /api/reports/agent/plan-delete

interface PlanDeleteRequest {
  user_message: string;      // 用户删除请求
  conversation_id: string;   // 会话ID
}

// 示例
{
  "user_message": "删除所有包含表格的章节",
  "conversation_id": "conv_abc123"
}
```

#### 响应
```typescript
interface BatchDeletePlan {
  plan_id: string;
  conversation_id: string;
  sections: SectionDeleteConfirmation[];
  total_count: number;
  will_lock_report: boolean;
  lock_warning: string;
  alternatives: Array<{
    action: string;
    label: string;
    description: string;
  }>;
}

interface SectionDeleteConfirmation {
  section_path: string;       // 章节完整路径
  content_preview: string;    // 内容预览（前200字）
  section_id: string;         // 内部ID (如 L15)
  start_line: number;         // 起始行号
  end_line: number;           // 结束行号
}
```

#### 错误处理
```typescript
// 400 - 参数错误
{
  "detail": "无法定位任何章节。LLM 识别了 2 个路径，但后端都无法精确定位。"
}

// 500 - 服务器错误
{
  "detail": "生成删除计划失败: LLM 服务暂时不可用"
}
```

### API 2: 执行删除计划

#### 请求
```typescript
POST /api/reports/agent/execute-delete

interface ExecuteDeleteRequest {
  plan_id: string;
  action: 'delete_and_lock' | 'regenerate_without';
  decisions: UserDecision[];
}

interface UserDecision {
  section_id: string;
  decision: 'execute' | 'skip' | 'reject';
}

// 示例
{
  "plan_id": "plan_abc123",
  "action": "delete_and_lock",
  "decisions": [
    { "section_id": "L15", "decision": "execute" },
    { "section_id": "L45", "decision": "skip" }
  ]
}
```

#### 响应
```typescript
interface DeleteExecutionResult {
  success: boolean;
  action_taken: string;
  deleted_sections: string[];      // 已删除章节路径列表
  skipped_sections: string[];      // 跳过的章节路径列表
  report_state: {
    edit_mode: 'template' | 'locked';
    generated_at: string;
    locked_at: string | null;
    lock_reason: string | null;
    version: number;
  };
  message: string;
  available_operations: string[];     // 可用操作
  unavailable_operations: string[];   // 不可用操作
}
```

---

## 状态管理

### 全局状态（Redux/Zustand）

```typescript
interface ReportState {
  // 报告基本信息
  reportId: string;
  version: number;
  
  // 编辑模式和锁定状态
  editMode: 'template' | 'locked';
  generatedAt: Date | null;
  lockedAt: Date | null;
  lockReason: string | null;
  
  // 删除计划
  currentDeletePlan: BatchDeletePlan | null;
  deletePlanDecisions: Map<string, 'execute' | 'skip' | 'reject'>;
  
  // UI 状态
  isDeleteDialogOpen: boolean;
  isDeletingInProgress: boolean;
}

// Actions
const reportActions = {
  // 删除计划相关
  fetchDeletePlan: (userMessage: string) => Promise<void>;
  setDecision: (sectionId: string, decision: 'execute' | 'skip' | 'reject') => void;
  executeDeletePlan: (action: string) => Promise<void>;
  cancelDeletePlan: () => void;
  
  // 状态更新
  updateReportState: (state: Partial<ReportState>) => void;
  lockReport: (reason: string) => void;
};
```

### 组件本地状态

```typescript
// DeletePlanDialog 组件
const [localDecisions, setLocalDecisions] = useState<Map<string, Decision>>(new Map());
const [selectedMode, setSelectedMode] = useState<'delete_and_lock' | 'regenerate_without'>('delete_and_lock');
const [showWarning, setShowWarning] = useState(true);

// 计算统计信息
const stats = useMemo(() => ({
  toDelete: Array.from(localDecisions.values()).filter(d => d === 'execute').length,
  toSkip: Array.from(localDecisions.values()).filter(d => d === 'skip').length,
  total: sections.length
}), [localDecisions, sections]);
```

---

## 错误处理

### 错误类型

#### 1. 网络错误
```typescript
try {
  await fetchDeletePlan(userMessage);
} catch (error) {
  if (error.code === 'NETWORK_ERROR') {
    showToast({
      variant: 'error',
      message: '网络连接失败，请检查网络后重试',
      action: { label: '重试', onClick: retry }
    });
  }
}
```

#### 2. 验证错误（400）
```typescript
catch (error) {
  if (error.status === 400) {
    showToast({
      variant: 'warning',
      message: error.detail,
      duration: 5000
    });
  }
}
```

#### 3. 服务器错误（500）
```typescript
catch (error) {
  if (error.status >= 500) {
    showToast({
      variant: 'error',
      message: '服务器错误，请稍后重试',
      action: { label: '联系支持', onClick: contactSupport }
    });
  }
}
```

### 用户友好的错误信息映射

```typescript
const errorMessages = {
  'SECTION_NOT_FOUND': '无法找到指定的章节，请重新描述或选择其他章节',
  'REPORT_ALREADY_LOCKED': '报告已锁定，无法继续删除章节',
  'PLAN_EXPIRED': '删除计划已过期，请重新生成',
  'LLM_SERVICE_UNAVAILABLE': 'AI 服务暂时不可用，请稍后重试',
  'INVALID_DECISION': '请为所有章节选择操作（执行/跳过）'
};
```

---

## 实现示例代码

### React + TypeScript 示例

```tsx
// DeletePlanDialog.tsx
import React, { useState, useMemo } from 'react';
import { Dialog, Button, Alert, Badge } from '@/components/ui';
import { useReportStore } from '@/stores/reportStore';

interface DeletePlanDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DeletePlanDialog: React.FC<DeletePlanDialogProps> = ({
  isOpen,
  onClose
}) => {
  const { currentDeletePlan, executeDeletePlan, cancelDeletePlan } = useReportStore();
  const [decisions, setDecisions] = useState<Map<string, Decision>>(new Map());
  const [selectedMode, setSelectedMode] = useState<'delete_and_lock' | 'regenerate_without'>('delete_and_lock');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // 计算统计信息
  const stats = useMemo(() => {
    const toDelete = Array.from(decisions.values()).filter(d => d === 'execute').length;
    const toSkip = Array.from(decisions.values()).filter(d => d === 'skip').length;
    return { toDelete, toSkip, total: currentDeletePlan?.sections.length || 0 };
  }, [decisions, currentDeletePlan]);

  // 处理决策变更
  const handleDecisionChange = (sectionId: string, decision: Decision) => {
    setDecisions(prev => new Map(prev).set(sectionId, decision));
  };

  // 全选/全不选
  const handleSelectAll = () => {
    const newDecisions = new Map<string, Decision>();
    currentDeletePlan?.sections.forEach(section => {
      newDecisions.set(section.section_id, 'execute');
    });
    setDecisions(newDecisions);
  };

  const handleDeselectAll = () => {
    const newDecisions = new Map<string, Decision>();
    currentDeletePlan?.sections.forEach(section => {
      newDecisions.set(section.section_id, 'skip');
    });
    setDecisions(newDecisions);
  };

  // 提交执行
  const handleSubmit = async () => {
    if (stats.toDelete === 0) {
      alert('请至少选择一个章节执行删除');
      return;
    }

    setIsSubmitting(true);
    try {
      await executeDeletePlan({
        plan_id: currentDeletePlan!.plan_id,
        action: selectedMode,
        decisions: Array.from(decisions.entries()).map(([section_id, decision]) => ({
          section_id,
          decision
        }))
      });
      
      onClose();
    } catch (error) {
      console.error('执行删除失败:', error);
      alert('执行失败，请重试');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!currentDeletePlan) return null;

  return (
    <Dialog isOpen={isOpen} onClose={onClose} size="large">
      <Dialog.Header>
        <Dialog.Title>
          确认删除章节
        </Dialog.Title>
        <Dialog.Subtitle>
          共 {currentDeletePlan.total_count} 个章节待删除
        </Dialog.Subtitle>
      </Dialog.Header>

      <Dialog.Body>
        {/* 警告信息 */}
        {currentDeletePlan.will_lock_report && (
          <Alert variant="warning" className="mb-4">
            ⚠️ {currentDeletePlan.lock_warning}
          </Alert>
        )}

        {/* 快速操作 */}
        <div className="flex justify-between items-center mb-4">
          <div className="text-sm text-gray-600">
            将删除 <Badge variant="danger">{stats.toDelete}</Badge> 个章节，
            跳过 <Badge variant="secondary">{stats.toSkip}</Badge> 个章节
          </div>
          <div className="space-x-2">
            <Button size="sm" variant="ghost" onClick={handleSelectAll}>
              全选
            </Button>
            <Button size="sm" variant="ghost" onClick={handleDeselectAll}>
              全不选
            </Button>
          </div>
        </div>

        {/* 章节列表 */}
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {currentDeletePlan.sections.map(section => (
            <SectionCard
              key={section.section_id}
              section={section}
              decision={decisions.get(section.section_id)}
              onDecisionChange={handleDecisionChange}
            />
          ))}
        </div>

        {/* 替代方案 */}
        <div className="mt-6">
          <h3 className="text-sm font-medium mb-2">选择执行模式</h3>
          <div className="space-y-2">
            <ModeCard
              icon="🔒"
              title="删除并锁定（推荐）"
              description="保持当前数据状态，报告将锁定为静态版本"
              isSelected={selectedMode === 'delete_and_lock'}
              onClick={() => setSelectedMode('delete_and_lock')}
            />
            <ModeCard
              icon="🔄"
              title="重新生成（排除章节）"
              description="使用最新数据重新生成，排除选定章节"
              isSelected={selectedMode === 'regenerate_without'}
              onClick={() => setSelectedMode('regenerate_without')}
              badge="暂未实现"
              disabled
            />
          </div>
        </div>
      </Dialog.Body>

      <Dialog.Footer>
        <Button variant="secondary" onClick={onClose} disabled={isSubmitting}>
          取消
        </Button>
        <Button 
          variant="danger" 
          onClick={handleSubmit} 
          disabled={isSubmitting || stats.toDelete === 0}
          loading={isSubmitting}
        >
          确认删除 {stats.toDelete > 0 && `(${stats.toDelete})`}
        </Button>
      </Dialog.Footer>
    </Dialog>
  );
};
```

---

## 响应式设计

### 桌面端（>1024px）
- 对话框宽度：800px
- 章节卡片：单列布局
- 内容预览：完整显示（200字）

### 平板端（768px - 1024px）
- 对话框宽度：90%
- 章节卡片：单列布局
- 内容预览：缩短至150字

### 移动端（<768px）
- 对话框全屏显示
- 章节路径：换行显示
- 内容预览：缩短至100字
- 按钮：堆叠布局

---

## 可访问性（A11y）

### 键盘导航
- `Tab`: 在章节卡片间切换
- `Space/Enter`: 切换当前章节的决策
- `Esc`: 关闭对话框
- `Ctrl+A`: 全选
- `Ctrl+D`: 全不选

### 屏幕阅读器
```tsx
<button 
  aria-label={`删除章节：${section.section_path}`}
  aria-pressed={decision === 'execute'}
>
  执行删除
</button>
```

### 焦点管理
- 对话框打开时，焦点自动移到第一个章节卡片
- 执行完成后，焦点返回到触发按钮

---

## 性能优化

### 虚拟滚动
当章节数量超过20个时，使用虚拟滚动：
```tsx
import { VirtualList } from 'react-virtual';

<VirtualList
  height={400}
  itemCount={sections.length}
  itemSize={120}
  renderItem={({ index, style }) => (
    <div style={style}>
      <SectionCard section={sections[index]} />
    </div>
  )}
/>
```

### 防抖优化
```tsx
const debouncedSearch = useMemo(
  () => debounce((query: string) => {
    // 搜索章节
  }, 300),
  []
);
```

---

## 测试要点

### 单元测试
- ✅ 决策状态管理
- ✅ 统计信息计算
- ✅ API 请求和响应处理
- ✅ 错误处理逻辑

### 集成测试
- ✅ 完整删除流程
- ✅ 模式切换
- ✅ 锁定状态同步

### E2E测试
- ✅ 从发起请求到删除完成的完整流程
- ✅ 不同设备的响应式表现
- ✅ 错误场景和恢复

---

## 总结

本设计文档涵盖了删除章节功能的完整前端实现方案，包括：
- 🎨 **3个核心UI组件**：删除计划对话框、章节卡片、状态指示器
- 🔄 **2个API接口**：生成计划、执行删除
- 📊 **清晰的状态管理**：全局状态和组件本地状态
- ✅ **完善的错误处理**：网络错误、验证错误、服务器错误
- ♿ **可访问性支持**：键盘导航、屏幕阅读器
- 📱 **响应式设计**：桌面、平板、移动端适配

请根据项目实际使用的前端框架（React/Vue/Angular）进行具体实现。
