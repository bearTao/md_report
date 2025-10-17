import client from './client';
import type {
  GenerateReportRequest,
  GenerateReportResponse,
  Report,
  TaskStatus,
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

// 获取任务状态
export const getTaskStatus = async (taskId: string): Promise<TaskStatus> => {
  const response = await client.get<TaskStatus>(`/api/reports/tasks/${taskId}/status`);
  return response.data;
};

