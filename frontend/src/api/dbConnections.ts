import client from './client';
import type {
  DBConnection,
  DBConnectionCreate,
  DBConnectionUpdate,
  DBConnectionListResponse,
  DBConnectionTestResponse,
} from '../types';

// 获取数据库连接列表
export const getDBConnections = async (): Promise<DBConnectionListResponse> => {
  const response = await client.get<DBConnectionListResponse>('/api/config/db-connections/');
  return response.data;
};

// 创建数据库连接
export const createDBConnection = async (
  data: DBConnectionCreate
): Promise<DBConnection> => {
  const response = await client.post<DBConnection>('/api/config/db-connections/', data);
  return response.data;
};

// 获取数据库连接详情
export const getDBConnection = async (id: string): Promise<DBConnection> => {
  const response = await client.get<DBConnection>(`/api/config/db-connections/${id}`);
  return response.data;
};

// 更新数据库连接
export const updateDBConnection = async (
  id: string,
  data: DBConnectionUpdate
): Promise<DBConnection> => {
  const response = await client.put<DBConnection>(`/api/config/db-connections/${id}`, data);
  return response.data;
};

// 删除数据库连接
export const deleteDBConnection = async (id: string): Promise<void> => {
  await client.delete(`/api/config/db-connections/${id}`);
};

// 测试数据库连接
export const testDBConnection = async (id: string): Promise<DBConnectionTestResponse> => {
  const response = await client.post<DBConnectionTestResponse>(
    `/api/config/db-connections/${id}/test`
  );
  return response.data;
};

