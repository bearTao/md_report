# Markdown 报告生成平台 - 前端

## 项目简介

基于 React + TypeScript + Vite + Ant Design 构建的 Markdown 报告自动生成平台前端应用。

## 技术栈

- **框架**: React 19
- **语言**: TypeScript
- **构建工具**: Vite
- **UI组件库**: Ant Design 5
- **路由**: React Router 7
- **状态管理**: TanStack Query (React Query)
- **HTTP客户端**: Axios
- **代码编辑器**: Monaco Editor
- **Markdown渲染**: react-markdown
- **YAML解析**: js-yaml

## 功能模块（P0核心）

### 1. 模板管理
- 模板列表（分页、搜索）
- 创建模板（Jinja2 + 元数据 YAML）
- 编辑模板（Monaco编辑器）
- 删除模板

### 2. 报告生成
- 选择模板
- 动态表单（根据元数据生成）
- 启动生成任务

### 3. 进度监控
- 实时进度展示（轮询）
- 任务状态查询
- 变量执行详情
- 成功/失败提示

### 4. 报告预览
- Markdown 渲染
- 报告信息展示
- 下载为 .md 文件

### 5. AI配置
- OpenAI API Key 配置
- 配置状态查看

## 快速开始

### 前置要求

- Node.js >= 18
- npm >= 9

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

前端将运行在 http://localhost:5173

### 生产构建

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 环境变量

创建 `.env.development` 文件：

```env
VITE_API_BASE_URL=http://localhost:8000
```

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API客户端
│   │   ├── client.ts     # Axios实例
│   │   ├── templates.ts  # 模板API
│   │   ├── reports.ts    # 报告API
│   │   ├── config.ts     # 配置API
│   │   └── index.ts
│   ├── components/       # 公共组件
│   │   └── Layout.tsx    # 布局组件
│   ├── pages/            # 页面组件
│   │   ├── templates/    # 模板管理页面
│   │   │   ├── TemplateList.tsx
│   │   │   └── TemplateEdit.tsx
│   │   ├── generate/     # 报告生成页面
│   │   │   ├── GenerateReport.tsx
│   │   │   └── ReportProgress.tsx
│   │   ├── reports/      # 报告预览页面
│   │   │   └── ReportPreview.tsx
│   │   └── settings/     # 设置页面
│   │       └── AISettings.tsx
│   ├── types/            # TypeScript类型定义
│   │   └── index.ts
│   ├── App.tsx           # 应用根组件
│   ├── main.tsx          # 应用入口
│   └── index.css         # 全局样式
├── public/               # 静态资源
├── .env.development      # 开发环境变量
├── package.json
├── tsconfig.json
├── vite.config.ts
└── README.md
```

## 路由说明

- `/` - 重定向到 `/templates`
- `/templates` - 模板列表
- `/templates/:templateId/edit` - 模板编辑（:templateId='new' 为新建）
- `/generate` - 报告生成（选择模板+填写表单）
- `/generate/:taskId` - 报告生成进度
- `/reports/:reportId` - 报告预览
- `/settings/ai` - AI配置

## API集成

后端API基础URL：`http://localhost:8000`

主要端点：

- `GET /api/templates` - 获取模板列表
- `POST /api/templates` - 创建模板
- `GET /api/templates/:id` - 获取模板详情
- `PUT /api/templates/:id` - 更新模板
- `DELETE /api/templates/:id` - 删除模板
- `POST /api/reports/generate` - 启动报告生成
- `GET /api/reports/:id` - 获取报告详情
- `GET /api/reports/:id/download` - 下载报告
- `GET /api/reports/tasks/:taskId/status` - 获取任务状态
- `GET /api/config/ai` - 获取AI配置
- `PUT /api/config/ai` - 更新AI配置

## 测试

详见 `测试说明.md`

## 开发规范

- 使用 TypeScript 严格模式
- 使用 ESLint 进行代码检查
- 组件使用函数式组件 + Hooks
- 使用 TanStack Query 管理服务器状态
- 遵循 Ant Design 设计规范

## 待实现功能（P1）

- [ ] WebSocket 实时进度推送
- [ ] 报告历史列表
- [ ] 任务取消功能
- [ ] 变量重试功能
- [ ] 数据库连接管理
- [ ] 模板验证
- [ ] 执行日志查看
- [ ] 成本统计展示

## 许可证

内部项目
