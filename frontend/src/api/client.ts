import axios, { type AxiosInstance, AxiosError } from 'axios';
import { message } from 'antd';

// 创建axios实例
const client: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://10.10.20.10:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
client.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
client.interceptors.response.use(
  (response) => {
    return response;
  },
  (error: AxiosError<{ detail?: string }>) => {
    const errorMessage = error.response?.data?.detail || error.message || '请求失败';
    message.error(errorMessage);
    return Promise.reject(error);
  }
);

export default client;

