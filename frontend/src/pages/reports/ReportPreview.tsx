import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Card,
  Button,
  Space,
  Descriptions,
  Tag,
  Spin,
  Alert,
} from 'antd';
import {
  DownloadOutlined,
  ArrowLeftOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import dayjs from 'dayjs';
import { getReport, downloadReport } from '../../api';

const ReportPreview = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();

  // 查询报告详情
  const { data: report, isLoading } = useQuery({
    queryKey: ['report', reportId],
    queryFn: () => getReport(reportId!),
    enabled: !!reportId,
  });

  const handleDownload = async () => {
    if (reportId) {
      await downloadReport(reportId);
    }
  };

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

  if (!report) {
    return (
      <Alert
        message="报告不存在"
        description="找不到指定的报告"
        type="error"
        showIcon
      />
    );
  }

  return (
    <div>
      {/* 操作栏 */}
      <div style={{ marginBottom: 16 }}>
        <Space>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/generate')}
          >
            返回
          </Button>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            onClick={handleDownload}
          >
            下载报告
          </Button>
        </Space>
      </div>

      {/* 报告信息 */}
      <Card style={{ marginBottom: 16 }}>
        <Descriptions column={2} title="报告信息">
          <Descriptions.Item label="报告ID">
            {report.id}
          </Descriptions.Item>
          <Descriptions.Item label="状态">
            {getStatusTag(report.status)}
          </Descriptions.Item>
          <Descriptions.Item label="标题">
            {report.title || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="模板ID">
            {report.template_id}
          </Descriptions.Item>
          <Descriptions.Item label="生成时间">
            {dayjs(report.created_at).format('YYYY-MM-DD HH:mm:ss')}
          </Descriptions.Item>
          <Descriptions.Item label="耗时">
            <Space>
              <ClockCircleOutlined />
              {formatDuration(report.duration_ms)}
            </Space>
          </Descriptions.Item>
          {report.cost_usd && (
            <Descriptions.Item label="AI成本">
              ${report.cost_usd.toFixed(4)}
            </Descriptions.Item>
          )}
        </Descriptions>
      </Card>

      {/* Markdown内容预览 */}
      <Card title="报告预览">
        <div
          style={{
            padding: '24px',
            background: '#fafafa',
            borderRadius: '4px',
            minHeight: '400px',
          }}
        >
          <div
            style={{
              background: 'white',
              padding: '24px',
              borderRadius: '4px',
              maxWidth: '900px',
              margin: '0 auto',
            }}
            className="markdown-body"
          >
            <ReactMarkdown>{report.markdown_content}</ReactMarkdown>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default ReportPreview;

