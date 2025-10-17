import client from './client';
import type {
  Template,
  TemplateList,
  CreateTemplateRequest,
  UpdateTemplateRequest,
} from '../types';

// 获取模板列表
export const getTemplates = async (params?: {
  page?: number;
  page_size?: number;
  q?: string;
}): Promise<TemplateList> => {
  const response = await client.get<TemplateList>('/api/templates', { params });
  return response.data;
};

// 获取模板详情
export const getTemplate = async (templateId: string): Promise<Template> => {
  const response = await client.get<Template>(`/api/templates/${templateId}`);
  return response.data;
};

// 创建模板
export const createTemplate = async (data: CreateTemplateRequest): Promise<Template> => {
  const response = await client.post<Template>('/api/templates', data);
  return response.data;
};

// 更新模板
export const updateTemplate = async (
  templateId: string,
  data: UpdateTemplateRequest
): Promise<Template> => {
  const response = await client.put<Template>(`/api/templates/${templateId}`, data);
  return response.data;
};

// 删除模板
export const deleteTemplate = async (templateId: string): Promise<void> => {
  await client.delete(`/api/templates/${templateId}`);
};

