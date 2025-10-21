import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Table,
  Tag,
  Button,
  Space,
  Input,
  Select,
  message,
} from 'antd';
import {
  EyeOutlined,
  ReloadOutlined,
  SearchOutlined,
  ClockCircleOutlined,
  RedoOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { getReportList } from '../../api';
import type { ReportListItem } from '../../types';

const { Search } = Input;
const { Option } = Select;

const ReportList = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [templateFilter, setTemplateFilter] = useState<string | undefined>();

  // 获取报告列表
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['reportList', page, pageSize, statusFilter, templateFilter],
    queryFn: () => getReportList({
      page,
      page_size: pageSize,
      status: statusFilter,
      template_id: templateFilter,
    }),
  });

  // 获取状态标签
  const getStatusTag = (status: string) => {
    const statusMap: Record<string, { color: string; text: string }> = {
      pending: { color: 'default', text: '等待中' },
      running: { color: 'processing', text: '执行中' },
      success: { color: 'success', text: '成功' },
      failed: { color: 'error', text: '失败' },
      cancelled: { color: 'warning', text: '已取消' },
    };
    
    const config = statusMap[status] || statusMap.pending;
    return <Tag color={config.color}>{config.text}</Tag>;
  };

  const columns = [
    {
      title: '报告标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: ReportListItem) => (
        <a onClick={() => navigate(`/reports/${record.id}`)}>
          {text || record.id}
        </a>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => getStatusTag(status),
    },
    {
      title: '模板ID',
      dataIndex: 'template_id',
      key: 'template_id',
      width: 200,
      ellipsis: true,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 200,
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: ReportListItem) => (
        <Space size="small">
          {/* 成功状态：显示查看报告按钮 */}
          {record.status === 'success' && (
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/reports/${record.id}`)}
            >
              查看报告
            </Button>
          )}
          
          {/* 所有状态：显示查看生成过程按钮（只要有task_id） */}
          {record.task_id && (
            <Button
              type="link"
              size="small"
              icon={<ClockCircleOutlined />}
              onClick={() => navigate(`/generate/${record.task_id}`)}
            >
              查看生成过程
            </Button>
          )}
          
          {/* 失败状态：显示重新生成按钮 */}
          {record.status === 'failed' && record.task_id && (
            <Button
              type="link"
              size="small"
              icon={<RedoOutlined />}
              onClick={() => {
                message.info('跳转到生成页面，您可以重新生成报告');
                navigate(`/generate/${record.task_id}`);
              }}
            >
              重新生成
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="报告历史"
        extra={
          <Button
            icon={<ReloadOutlined />}
            onClick={() => refetch()}
          >
            刷新
          </Button>
        }
      >
        {/* 筛选器 */}
        <Space style={{ marginBottom: 16 }} wrap>
          <Select
            placeholder="状态筛选"
            allowClear
            style={{ width: 150 }}
            value={statusFilter}
            onChange={(value) => {
              setStatusFilter(value);
              setPage(1);
            }}
          >
            <Option value="success">成功</Option>
            <Option value="failed">失败</Option>
            <Option value="running">执行中</Option>
            <Option value="pending">等待中</Option>
            <Option value="cancelled">已取消</Option>
          </Select>

          <Input
            placeholder="模板ID"
            allowClear
            style={{ width: 250 }}
            value={templateFilter}
            onChange={(e) => {
              setTemplateFilter(e.target.value || undefined);
              setPage(1);
            }}
            prefix={<SearchOutlined />}
          />
        </Space>

        {/* 报告列表表格 */}
        <Table
          columns={columns}
          dataSource={data?.items || []}
          rowKey="id"
          loading={isLoading}
          pagination={{
            current: page,
            pageSize: pageSize,
            total: data?.total || 0,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 条`,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              setPageSize(newPageSize);
            },
          }}
        />
      </Card>
    </div>
  );
};

export default ReportList;

