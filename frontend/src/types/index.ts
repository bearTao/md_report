// 通用类型定义

export interface APIResponse<T = any> {
  success?: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
  } | null;
}

// 模板相关类型
export interface Template {
  id: string;
  name: string;
  description: string;
  template_content: string;
  metadata_json: VariableMetadata;
  created_at: string;
  updated_at: string;
}

export interface TemplateListItem {
  id: string;
  name: string;
  description: string;
  created_at: string;
}

export interface TemplateList {
  items: TemplateListItem[];
  total: number;
}

export interface CreateTemplateRequest {
  name: string;
  description: string;
  template_content: string;
  metadata: VariableMetadata;
}

export interface UpdateTemplateRequest {
  name?: string;
  description?: string;
  template_content?: string;
  metadata?: VariableMetadata;
}

// 变量元数据类型
export type VariableSource = 'user_input' | 'sql' | 'api' | 'ai_generation' | 'system';
export type VariableType = 'string' | 'number' | 'boolean' | 'object' | 'array';

export interface VariableMetadata {
  [key: string]: VariableConfig;
}

export interface VariableConfig {
  type: VariableType;
  source: VariableSource;
  required: boolean;
  description: string;
  default?: any;
  dependencies?: string[];
  ui_config?: UIConfig;
  sql_config?: SQLConfig;
  api_config?: APIConfig;
  ai_config?: AIConfig;
  system_config?: SystemConfig;
  schema?: any;
}

export interface UIConfig {
  input_type?: 'text' | 'textarea' | 'number' | 'select' | 'checkbox';
  placeholder?: string;
  options?: Array<{ label: string; value: any }>;
}

export interface SQLConfig {
  connection_name?: string;
  query: string;
  params?: Record<string, string>;
}

export interface APIConfig {
  url: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  headers?: Record<string, string>;
  body?: any;
  mapping?: string;
}

export interface AIConfig {
  model: string;
  prompt_template: string;
  temperature?: number;
}

export interface SystemConfig {
  fields: Record<string, SystemFieldConfig>;
}

export interface SystemFieldConfig {
  generator: 'datetime' | 'uuid' | 'constant';
  format?: string;
  value?: any;
}

// 报告相关类型
export interface GenerateReportRequest {
  template_id: string;
  inputs: Record<string, any>;
}

export interface GenerateReportResponse {
  task_id: string;
  status: TaskStatus;
}

export type TaskStatus = 'pending' | 'running' | 'success' | 'failed' | 'cancelled';

export interface Report {
  id: string;
  template_id: string;
  task_id: string;
  title: string;
  status: TaskStatus;
  markdown_content: string;
  cost_usd: number | null;
  duration_ms: number;
  created_at: string;
  updated_at: string;
}

// WebSocket 事件类型
export type WSEventType = 
  | 'task_started'
  | 'variable_started'
  | 'variable_progress'
  | 'variable_completed'
  | 'variable_failed'
  | 'task_completed'
  | 'task_failed';

export interface WSEvent {
  type: WSEventType;
  task_id: string;
  [key: string]: any;
}

export interface TaskStartedEvent extends WSEvent {
  type: 'task_started';
  template_id: string;
  queued_at: string;
  started_at: string;
}

export interface VariableStartedEvent extends WSEvent {
  type: 'variable_started';
  variable_name: string;
  source: VariableSource;
  dependencies: string[];
  started_at: string;
}

export interface VariableProgressEvent extends WSEvent {
  type: 'variable_progress';
  variable_name: string;
  progress: number;
  info?: Record<string, any>;
}

export interface VariableCompletedEvent extends WSEvent {
  type: 'variable_completed';
  variable_name: string;
  duration_ms: number;
  result_preview: any;
}

export interface VariableFailedEvent extends WSEvent {
  type: 'variable_failed';
  variable_name: string;
  error: {
    code: string;
    message: string;
  };
  duration_ms: number;
}

export interface TaskCompletedEvent extends WSEvent {
  type: 'task_completed';
  report_id: string;
  summary: {
    duration_ms: number;
    ai_cost_usd?: number;
  };
}

export interface TaskFailedEvent extends WSEvent {
  type: 'task_failed';
  summary: {
    duration_ms: number;
  };
  error: {
    code: string;
    message: string;
  };
}

// 任务状态类型
export type VariableStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped';

export interface TaskVariableDetail {
  variable_name: string;
  source: VariableSource;
  status: VariableStatus;
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  error_message: string | null;
  result_preview: Record<string, any> | null;
}

export interface TaskStatus {
  task_id: string;
  template_id: string;
  status: TaskStatus;
  inputs_json: Record<string, any>;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
  report_id: string | null;
  variables: TaskVariableDetail[];
}

// AI配置类型
export interface AIConfigResponse {
  configured: boolean;
  provider: string;
  api_base?: string;
}

export interface UpdateAIConfigRequest {
  provider: string;
  api_key: string;
  api_base?: string;
}

