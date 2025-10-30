import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
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
  Tooltip,
  Popconfirm,
  Typography,
} from 'antd';
import {
  EyeOutlined,
  ReloadOutlined,
  SearchOutlined,
  ClockCircleOutlined,
  RedoOutlined,
  FileWordOutlined,
  DeleteOutlined,
  EditOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { getReportList, convertReportToWord, deleteReport, updateReportTitle } from '../../api';
import type { ReportListItem } from '../../types';

const { Option } = Select;

const ReportList = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [statusFilter, setStatusFilter] = useState<string | undefined>();
  const [templateFilter, setTemplateFilter] = useState<string | undefined>();
  const [convertingReportId, setConvertingReportId] = useState<string | null>(null);
  const [editingReportId, setEditingReportId] = useState<string | null>(null);

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

  // 处理转换为Word
  const handleConvertToWord = async (reportId: string) => {
    try {
      setConvertingReportId(reportId);
      await convertReportToWord(reportId);
      message.success('Word文档已下载');
    } catch (error: any) {
      console.error('转换失败:', error);
      const errorMsg = error?.response?.data?.detail || '转换失败，请重试';
      message.error(errorMsg);
    } finally {
      setConvertingReportId(null);
    }
  };

  // 删除报告 mutation
  const deleteReportMutation = useMutation({
    mutationFn: (reportId: string) => deleteReport(reportId),
    onSuccess: (data) => {
      message.success(data.message || '报告已删除');
      refetch(); // 刷新列表
    },
    onError: (error: any) => {
      const errorMsg = error?.response?.data?.detail || '删除失败，请重试';
      message.error(errorMsg);
    },
  });

  // 更新报告标题 mutation
  const updateTitleMutation = useMutation({
    mutationFn: ({ reportId, title }: { reportId: string; title: string }) =>
      updateReportTitle(reportId, { title }),
    onSuccess: () => {
      message.success('标题已更新');
      refetch(); // 刷新列表
    },
    onError: (error: any) => {
      const errorMsg = error?.response?.data?.detail || '更新失败，请重试';
      message.error(errorMsg);
    },
  });

  const columns = [
    {
      title: '报告标题',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: ReportListItem) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {editingReportId === record.id ? (
            <Typography.Text
              editable={{
                editing: true,
                onChange: (newTitle) => {
                  if (newTitle && newTitle.trim() && newTitle !== text) {
                    updateTitleMutation.mutate({
                      reportId: record.id,
                      title: newTitle.trim(),
                    });
                  }
                  setEditingReportId(null);
                },
                onCancel: () => setEditingReportId(null),
                maxLength: 200,
              }}
              style={{ flex: 1 }}
            >
              {text || record.id}
            </Typography.Text>
          ) : (
            <>
              <a 
                onClick={() => navigate(`/reports/${record.id}`)}
                style={{ flex: 1 }}
              >
                {text || record.id}
              </a>
              <Tooltip title="编辑标题">
                <Button
                  type="text"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditingReportId(record.id);
                  }}
                />
              </Tooltip>
            </>
          )}
        </div>
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
      width: 120,
      render: (_: any, record: ReportListItem) => (
        <Space size="small">
          {/* 成功状态：显示查看报告按钮 */}
          {record.status === 'success' && (
            <Tooltip title="查看报告">
              <Button
                type="link"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => navigate(`/reports/${record.id}`)}
              />
            </Tooltip>
          )}
          
          {/* 成功状态：显示转换Word按钮 */}
          {record.status === 'success' && (
            <Tooltip title="转换Word">
              <Button
                type="link"
                size="small"
                icon={<FileWordOutlined />}
                onClick={() => handleConvertToWord(record.id)}
                loading={convertingReportId === record.id}
              />
            </Tooltip>
          )}
          
          {/* 所有状态：显示查看生成过程按钮（只要有task_id） */}
          {record.task_id && (
            <Tooltip title="查看生成过程">
              <Button
                type="link"
                size="small"
                icon={<ClockCircleOutlined />}
                onClick={() => navigate(`/generate/${record.task_id}`)}
              />
            </Tooltip>
          )}
          
          {/* 失败状态：显示重新生成按钮 */}
          {record.status === 'failed' && record.task_id && (
            <Tooltip title="重新生成">
              <Button
                type="link"
                size="small"
                icon={<RedoOutlined />}
                onClick={() => {
                  message.info('跳转到生成页面，您可以重新生成报告');
                  navigate(`/generate/${record.task_id}`);
                }}
              />
            </Tooltip>
          )}
          
          {/* 所有状态：显示删除按钮 */}
          <Popconfirm
            title="确定要删除此报告吗？"
            description="删除后将无法恢复，包括任务和执行记录"
            onConfirm={() => deleteReportMutation.mutate(record.id)}
            okText="确定"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Tooltip title="删除报告">
              <Button
                type="link"
                size="small"
                danger
                icon={<DeleteOutlined />}
                loading={deleteReportMutation.isPending}
              />
            </Tooltip>
          </Popconfirm>
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

