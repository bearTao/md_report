import client from './client';
import type { AIConfigResponse, UpdateAIConfigRequest } from '../types';

// 获取AI配置状态
export const getAIConfig = async (): Promise<AIConfigResponse> => {
  const response = await client.get<AIConfigResponse>('/api/config/ai');
  return response.data;
};

// 更新AI配置
export const updateAIConfig = async (data: UpdateAIConfigRequest): Promise<AIConfigResponse> => {
  const response = await client.put<AIConfigResponse>('/api/config/ai', data);
  return response.data;
};

