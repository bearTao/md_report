import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Card,
  Progress,
  Timeline,
  Tag,
  Button,
  Space,
  Descriptions,
  Collapse,
  Alert,
  Spin,
  Badge,
  message,
  Popconfirm,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ClockCircleOutlined,
  EyeOutlined,
  WifiOutlined,
  StopOutlined,
  ReloadOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { getTaskStatus, cancelTask, retryVariable } from '../../api';
import { useWebSocket } from '../../hooks/useWebSocket';
import type { TaskVariableDetail, WSEvent } from '../../types';

const { Panel } = Collapse;

const ReportProgress = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const [reportId, setReportId] = useState<string | null>(null);

  // 获取初始任务状态
  const { data: taskStatus, isLoading, refetch } = useQuery({
    queryKey: ['taskStatus', taskId],
    queryFn: () => getTaskStatus(taskId!),
    enabled: !!taskId,
    refetchOnWindowFocus: false,
  });

  // WebSocket实时更新
  const { isConnected, latestEvent } = useWebSocket(taskId || null, {
    onMessage: (event: WSEvent) => {
      console.log('WebSocket event:', event);
      
      // 处理任务完成事件
      if (event.type === 'task_completed' && event.report_id) {
        setReportId(event.report_id);
        // 刷新任务状态以获取最终数据
        refetch();
      }
      
      // 处理渲染失败事件
      if (event.type === 'render_failed') {
        message.error('模板渲染失败');
        refetch();
      }
      
      // 处理任务失败、取消或变量更新事件，刷新状态
      if (['task_failed', 'task_cancelled', 'variable_completed', 'variable_failed', 'variable_retry_started'].includes(event.type)) {
        refetch();
      }
    },
  });

  // 取消任务 mutation
  const cancelTaskMutation = useMutation({
    mutationFn: () => cancelTask(taskId!),
    onSuccess: () => {
      message.success('任务已取消');
      refetch();
    },
    onError: (error: any) => {
      message.error(`取消任务失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // 重试变量 mutation
  const retryVariableMutation = useMutation({
    mutationFn: (variableName: string) => retryVariable(taskId!, variableName),
    onSuccess: () => {
      message.success('变量重试已开始');
      refetch();
    },
    onError: (error: any) => {
      message.error(`重试失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // 处理取消任务
  const handleCancelTask = () => {
    cancelTaskMutation.mutate();
  };

  // 处理重试变量
  const handleRetryVariable = (variableName: string) => {
    retryVariableMutation.mutate(variableName);
  };

  // 计算进度
  const getProgress = () => {
    if (!taskStatus) return 0;
    const variables = taskStatus.variables;
    if (variables.length === 0) return 0;
    
    const completed = variables.filter(
      v => v.status === 'success' || v.status === 'failed' || v.status === 'skipped'
    ).length;
    
    return Math.round((completed / variables.length) * 100);
  };

  // 获取状态图标
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'running':
        return <SyncOutlined spin style={{ color: '#1890ff' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: '等待中' },
      running: { color: 'processing', text: '执行中' },
      success: { color: 'success', text: '成功' },
      failed: { color: 'error', text: '失败' },
      skipped: { color: 'warning', text: '跳过' },
    };
    
    const config = statusMap[status] || statusMap.pending;
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  // 格式化持续时间
  const formatDuration = (ms: number | null) => {
    if (!ms) return '-';
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!taskStatus) {
    return (
      <Alert
        message="任务不存在"
        description="找不到指定的任务"
        type="error"
        showIcon
      />
    );
  }

  const progress = getProgress();
  const isCompleted = taskStatus.status === 'success';
  const isFailed = taskStatus.status === 'failed';
  const finalReportId = reportId || taskStatus.report_id;

  return (
    <div>
      <Card 
        title={
          <Space>
            <span>报告生成进度</span>
            <Badge 
              status={isConnected ? 'processing' : 'default'} 
              text={isConnected ? '实时连接' : '已断开'}
            />
          </Space>
        } 
        style={{ marginBottom: 16 }}
      >
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 总体进度 */}
          <div>
            <div style={{ marginBottom: 8 }}>
              <Space>
                <span>任务ID: {taskStatus.task_id}</span>
                {getStatusTag(taskStatus.status)}
              </Space>
            </div>
            <Progress
              percent={progress}
              status={isFailed ? 'exception' : isCompleted ? 'success' : 'active'}
              strokeColor={isFailed ? '#ff4d4f' : undefined}
            />
          </div>

          {/* 任务信息 */}
          <Descriptions column={2} size="small">
            <Descriptions.Item label="创建时间">
              {dayjs(taskStatus.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            <Descriptions.Item label="开始时间">
              {taskStatus.started_at
                ? dayjs(taskStatus.started_at).format('YYYY-MM-DD HH:mm:ss')
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="完成时间">
              {taskStatus.finished_at
                ? dayjs(taskStatus.finished_at).format('YYYY-MM-DD HH:mm:ss')
                : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="总耗时">
              {taskStatus.started_at && taskStatus.finished_at
                ? formatDuration(
                    dayjs(taskStatus.finished_at).diff(dayjs(taskStatus.started_at))
                  )
                : '-'}
            </Descriptions.Item>
          </Descriptions>

          {/* 完成提示 */}
          {isCompleted && finalReportId && (
            <Alert
              message="报告生成成功！"
              description="点击下方按钮查看报告"
              type="success"
              showIcon
              action={
                <Button
                  size="small"
                  type="primary"
                  icon={<EyeOutlined />}
                  onClick={() => navigate(`/reports/${finalReportId}`)}
                >
                  查看报告
                </Button>
              }
            />
          )}

          {isFailed && (
            <Alert
              message="报告生成失败"
              description="请查看下方变量执行详情了解失败原因"
              type="error"
              showIcon
            />
          )}

          {taskStatus.status === 'cancelled' && (
            <Alert
              message="任务已取消"
              description="任务已被用户取消"
              type="warning"
              showIcon
            />
          )}

          {/* 操作按钮区域 */}
          <Space>
            {/* 取消任务按钮 */}
            {(taskStatus.status === 'pending' || taskStatus.status === 'running') && (
              <Popconfirm
                title="确定要取消此任务吗？"
                description="取消后任务将无法继续执行"
                onConfirm={handleCancelTask}
                okText="确定"
                cancelText="取消"
              >
                <Button
                  danger
                  icon={<StopOutlined />}
                  loading={cancelTaskMutation.isPending}
                >
                  取消任务
                </Button>
              </Popconfirm>
            )}

            {/* 查看日志按钮 */}
            <Button
              icon={<FileTextOutlined />}
              onClick={() => navigate(`/logs/${taskId}`)}
            >
              查看日志
            </Button>
          </Space>
        </Space>
      </Card>

      {/* 变量执行详情 */}
      <Card title="变量执行详情">
        {taskStatus.variables.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '50px 0', color: '#999' }}>
            暂无变量执行记录
          </div>
        ) : (
          <Timeline>
            {taskStatus.variables.map((variable: TaskVariableDetail) => (
              <Timeline.Item
                key={variable.variable_name}
                dot={getStatusIcon(variable.status)}
              >
                <Collapse ghost>
                  <Panel
                    header={
                      <Space>
                        <strong>{variable.variable_name}</strong>
                        <Tag>{variable.source}</Tag>
                        {getStatusTag(variable.status)}
                        {variable.duration_ms && (
                          <span style={{ color: '#999' }}>
                            {formatDuration(variable.duration_ms)}
                          </span>
                        )}
                      </Space>
                    }
                    key={variable.variable_name}
                  >
                    <Descriptions column={1} size="small">
                      <Descriptions.Item label="变量名称">
                        {variable.variable_name}
                      </Descriptions.Item>
                      <Descriptions.Item label="数据源">
                        {variable.source}
                      </Descriptions.Item>
                      <Descriptions.Item label="状态">
                        <Space>
                          {getStatusTag(variable.status)}
                          {/* 重试按钮 */}
                          {variable.status === 'failed' && (
                            <Button
                              type="link"
                              size="small"
                              icon={<ReloadOutlined />}
                              onClick={() => handleRetryVariable(variable.variable_name)}
                              loading={retryVariableMutation.isPending}
                            >
                              重试
                            </Button>
                          )}
                        </Space>
                      </Descriptions.Item>
                      <Descriptions.Item label="开始时间">
                        {variable.started_at
                          ? dayjs(variable.started_at).format('YYYY-MM-DD HH:mm:ss')
                          : '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="完成时间">
                        {variable.finished_at
                          ? dayjs(variable.finished_at).format('YYYY-MM-DD HH:mm:ss')
                          : '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="耗时">
                        {formatDuration(variable.duration_ms)}
                      </Descriptions.Item>
                      {variable.error_message && (
                        <Descriptions.Item label="错误信息">
                          <span style={{ color: '#ff4d4f' }}>
                            {variable.error_message}
                          </span>
                        </Descriptions.Item>
                      )}
                      {variable.result_preview && (
                        <Descriptions.Item label="结果预览">
                          <pre style={{
                            background: '#f5f5f5',
                            padding: '8px',
                            borderRadius: '4px',
                            maxHeight: '200px',
                            overflow: 'auto',
                          }}>
                            {JSON.stringify(variable.result_preview, null, 2)}
                          </pre>
                        </Descriptions.Item>
                      )}
                    </Descriptions>
                  </Panel>
                </Collapse>
              </Timeline.Item>
            ))}
            
            {/* 渲染日志 */}
            {taskStatus.render_error && (
              <Timeline.Item color="red" dot={<CloseCircleOutlined />}>
                <div>
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Space>
                      <strong>模板渲染</strong>
                      <Tag color="red">失败</Tag>
                    </Space>
                    <div style={{ marginTop: 8, color: '#ff4d4f' }}>
                      错误: {taskStatus.render_error.error_message}
                    </div>
                    {taskStatus.render_error.timestamp && (
                      <div style={{ color: '#999', fontSize: '12px' }}>
                        时间: {dayjs(taskStatus.render_error.timestamp).format('YYYY-MM-DD HH:mm:ss')}
                      </div>
                    )}
                  </Space>
                </div>
              </Timeline.Item>
            )}
            
            {/* 渲染成功提示 */}
            {isCompleted && !taskStatus.render_error && taskStatus.variables.length > 0 && (
              <Timeline.Item color="green" dot={<CheckCircleOutlined />}>
                <div>
                  <Space>
                    <strong>模板渲染</strong>
                    <Tag color="green">成功</Tag>
                  </Space>
                </div>
              </Timeline.Item>
            )}
          </Timeline>
        )}
      </Card>
    </div>
  );
};

export default ReportProgress;

