import client from './client';
import type {
  GenerateReportRequest,
  GenerateReportResponse,
  Report,
  TaskStatusResponse,
  ReportListResponse,
  DeleteReportResponse,
  UpdateReportRequest,
} from '../types';

// 启动报告生成
export const generateReport = async (
  data: GenerateReportRequest
): Promise<GenerateReportResponse> => {
  const response = await client.post<GenerateReportResponse>('/api/reports/generate', data);
  return response.data;
};

// 获取报告详情
export const getReport = async (reportId: string): Promise<Report> => {
  const response = await client.get<Report>(`/api/reports/${reportId}`);
  return response.data;
};

// 下载报告
export const downloadReport = async (reportId: string): Promise<void> => {
  const response = await client.get(`/api/reports/${reportId}/download`, {
    responseType: 'blob',
  });
  
  // 创建下载链接
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `report_${reportId}.md`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// 转换报告为Word
export const convertReportToWord = async (reportId: string): Promise<void> => {
  const response = await client.get(`/api/reports/${reportId}/convert/word`, {
    responseType: 'blob',
  });
  
  // 创建下载链接
  const url = window.URL.createObjectURL(new Blob([response.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', `report_${reportId}.docx`);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

// 获取任务状态
export const getTaskStatus = async (taskId: string): Promise<TaskStatusResponse> => {
  const response = await client.get<TaskStatusResponse>(`/api/reports/tasks/${taskId}/status`);
  return response.data;
};

// 获取报告历史列表
export const getReportList = async (params?: {
  page?: number;
  page_size?: number;
  status?: string;
  template_id?: string;
}): Promise<ReportListResponse> => {
  const response = await client.get<ReportListResponse>('/api/reports/', { params });
  return response.data;
};

// 取消任务
export const cancelTask = async (
  taskId: string,
  reason?: string
): Promise<{ task_id: string; status: string; cancelled_at: string }> => {
  const response = await client.post(`/api/reports/tasks/${taskId}/cancel`, {
    reason,
  });
  return response.data;
};

// 重试变量
export const retryVariable = async (
  taskId: string,
  variableName: string
): Promise<{ task_id: string; variable_name: string; retry_status: string }> => {
  const response = await client.post(
    `/api/reports/tasks/${taskId}/variables/${variableName}/retry`
  );
  return response.data;
};

// 获取执行日志
export const getTaskLogs = async (params: {
  taskId: string;
  level?: string;
  variable_name?: string;
  limit?: number;
  offset?: number;
}): Promise<{
  logs: Array<{
    id: number;
    task_id: string;
    variable_name: string | null;
    level: string;
    message: string;
    context: any;
    created_at: string;
  }>;
  total: number;
}> => {
  const { taskId, ...queryParams } = params;
  const response = await client.get(`/api/reports/tasks/${taskId}/logs`, {
    params: queryParams,
  });
  return response.data;
};

// 删除报告
export const deleteReport = async (reportId: string): Promise<DeleteReportResponse> => {
  const response = await client.delete<DeleteReportResponse>(`/api/reports/${reportId}`);
  return response.data;
};

// 更新报告标题
export const updateReportTitle = async (
  reportId: string,
  data: UpdateReportRequest
): Promise<Report> => {
  const response = await client.patch<Report>(`/api/reports/${reportId}`, data);
  return response.data;
};

// 获取对话历史
export const getConversationHistory = async (
  reportId: string,
  sessionId?: string
): Promise<{
  session_id: string;
  report_id: string;
  turns: Array<{
    turn_number: number;
    user_request: string;
    system_response: string;
    timestamp: string;
    operations: any[];
  }>;
  context_summary: any;
  current_version: number;
}> => {
  const params = sessionId ? { session_id: sessionId } : {};
  const response = await client.get(`/api/reports/${reportId}/conversation`, { params });
  return response.data;
};

// 获取会话列表
export const getConversationSessions = async (
  reportId: string
): Promise<{
  sessions: Array<{
    session_id: string;
    report_id: string;
    created_at: string;
    last_activity_at: string;
    turn_count: number;
    preview: string;
    status: string;
  }>;
  total: number;
}> => {
  const response = await client.get(`/api/reports/${reportId}/sessions`);
  return response.data;
};

