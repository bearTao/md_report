import { useState } from 'react';
import { Card, Table, Tag, Select, Button, Space, Empty, Spin, Modal, Descriptions, Typography } from 'antd';
import { ReloadOutlined, FilterOutlined, EyeOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { getTaskLogs } from '../api';
import type { ExecutionLogItem } from '../types';

const { Text, Paragraph } = Typography;

interface TaskLogsProps {
  taskId: string;
}

const TaskLogs = ({ taskId }: TaskLogsProps) => {
  const [levelFilter, setLevelFilter] = useState<string | undefined>(undefined);
  const [variableFilter, setVariableFilter] = useState<string | undefined>(undefined);
  const [selectedLog, setSelectedLog] = useState<ExecutionLogItem | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);

  const { data: logsData, isLoading, refetch } = useQuery({
    queryKey: ['taskLogs', taskId, levelFilter, variableFilter],
    queryFn: () => getTaskLogs({
      taskId,
      level: levelFilter,
      variable_name: variableFilter,
      limit: 500,
    }),
    enabled: !!taskId,
    refetchInterval: false,
  });

  // 打开详情弹窗
  const showLogDetail = (log: ExecutionLogItem) => {
    setSelectedLog(log);
    setDetailModalVisible(true);
  };

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm:ss.SSS'),
    },
    {
      title: '级别',
      dataIndex: 'level',
      key: 'level',
      width: 80,
      render: (level: string) => {
        const colorMap: Record<string, string> = {
          DEBUG: 'default',
          INFO: 'blue',
          WARNING: 'orange',
          ERROR: 'red',
        };
        return <Tag color={colorMap[level] || 'default'}>{level}</Tag>;
      },
    },
    {
      title: '变量/模块',
      dataIndex: 'variable_name',
      key: 'variable_name',
      width: 150,
      render: (name: string | null) => {
        if (!name) return <span style={{ color: '#999' }}>-</span>;
        if (name === '[渲染引擎]') {
          return <Tag color="purple" icon={<FilterOutlined />}>{name}</Tag>;
        }
        return <span>{name}</span>;
      },
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
      render: (text: string, record: ExecutionLogItem) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ 
            flex: 1, 
            wordBreak: 'break-word', 
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}>
            {text}
          </div>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => showLogDetail(record)}
            style={{ flexShrink: 0 }}
          >
            详情
          </Button>
        </div>
      ),
    },
  ];

  // 提取所有唯一的变量名用于筛选
  const uniqueVariables = Array.from(
    new Set(
      (logsData?.logs || [])
        .map((log: ExecutionLogItem) => log.variable_name)
        .filter(Boolean)
    )
  );

  return (
    <>
      <Card
        title="执行日志"
        extra={
          <Space>
            <Select
              style={{ width: 120 }}
              placeholder="级别筛选"
              allowClear
              value={levelFilter}
              onChange={setLevelFilter}
              options={[
                { label: 'DEBUG', value: 'DEBUG' },
                { label: 'INFO', value: 'INFO' },
                { label: 'WARNING', value: 'WARNING' },
                { label: 'ERROR', value: 'ERROR' },
              ]}
            />
            <Select
              style={{ width: 150 }}
              placeholder="变量筛选"
              allowClear
              value={variableFilter}
              onChange={setVariableFilter}
              options={uniqueVariables.map((v) => ({
                label: v,
                value: v,
              }))}
              showSearch
            />
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
              刷新
            </Button>
          </Space>
        }
      >
        {isLoading ? (
          <div style={{ textAlign: 'center', padding: '40px 0' }}>
            <Spin size="large" tip="加载日志中..." />
          </div>
        ) : logsData && logsData.logs.length > 0 ? (
          <Table
            columns={columns}
            dataSource={logsData.logs}
            rowKey={(record) => `${record.id}-${record.created_at}`}
            pagination={{
              defaultPageSize: 20,
              showSizeChanger: true,
              showTotal: (total) => `共 ${total} 条日志`,
            }}
            size="small"
          />
        ) : (
          <Empty description="暂无日志记录" />
        )}
      </Card>

      {/* 日志详情弹窗 */}
      <Modal
        title="日志详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        {selectedLog && (
          <div>
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="时间">
                {dayjs(selectedLog.created_at).format('YYYY-MM-DD HH:mm:ss.SSS')}
              </Descriptions.Item>
              <Descriptions.Item label="级别">
                <Tag color={
                  selectedLog.level === 'ERROR' ? 'red' :
                  selectedLog.level === 'WARNING' ? 'orange' :
                  selectedLog.level === 'INFO' ? 'blue' : 'default'
                }>
                  {selectedLog.level}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="变量/模块">
                {selectedLog.variable_name || '-'}
              </Descriptions.Item>
            </Descriptions>

            <div style={{ marginTop: 16 }}>
              <Text strong>消息内容：</Text>
              <Paragraph
                copyable
                style={{
                  marginTop: 8,
                  padding: 12,
                  background: '#f5f5f5',
                  borderRadius: 4,
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  maxHeight: 400,
                  overflow: 'auto'
                }}
              >
                {selectedLog.message}
              </Paragraph>
            </div>

            {selectedLog.context && (
              <div style={{ marginTop: 16 }}>
                <Text strong>上下文信息：</Text>
                <Paragraph
                  copyable
                  style={{
                    marginTop: 8,
                    padding: 12,
                    background: '#f5f5f5',
                    borderRadius: 4,
                    fontFamily: 'monospace',
                    fontSize: 12,
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                    maxHeight: 300,
                    overflow: 'auto'
                  }}
                >
                  {JSON.stringify(selectedLog.context, null, 2)}
                </Paragraph>
              </div>
            )}
          </div>
        )}
      </Modal>
    </>
  );
};

export default TaskLogs;

