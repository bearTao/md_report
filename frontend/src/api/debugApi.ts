// 独立的调试API文件，不导出到 index.ts 以避免循环依赖
import client from './client';

export interface DebugRenderRequest {
  template_content: string;
  metadata_yaml: string;
  user_inputs: Record<string, any>;
}

export interface DebugVariableResult {
  variable_name: string;
  status: string;
  value: any;
  duration_ms: number;
  error_message?: string;
}

export interface DebugRenderResponse {
  success: boolean;
  rendered_markdown?: string;
  variables: DebugVariableResult[];
  error?: string;
}

export const debugRender = async (
  data: DebugRenderRequest
): Promise<DebugRenderResponse> => {
  const response = await client.post('/api/debug/render', data);
  return response.data;
};


