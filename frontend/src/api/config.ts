import client from './client';
import type { 
  AIConfigResponse, 
  UpdateAIConfigRequest,
  AgentConfigResponse,
  UpdateAgentConfigRequest
} from '../types';

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

// 获取Agent配置
export const getAgentConfig = async (): Promise<AgentConfigResponse> => {
  const response = await client.get<AgentConfigResponse>('/api/config/agent');
  return response.data;
};

// 更新Agent配置
export const updateAgentConfig = async (data: UpdateAgentConfigRequest): Promise<AgentConfigResponse> => {
  const response = await client.put<AgentConfigResponse>('/api/config/agent', data);
  return response.data;
};

