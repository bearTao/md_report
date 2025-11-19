import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import {
  Row,
  Col,
  Card,
  Button,
  Space,
  Form,
  Input,
  message,
  Alert,
  Table,
  Spin,
  Typography,
} from 'antd';
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import loader from '@monaco-editor/loader';
import * as monaco from 'monaco-editor';
import yaml from 'js-yaml';
import { debugRender, type DebugVariableResult } from '../../api/debugApi';
import { useMarkdownToHtml } from '../../hooks/useMarkdownToHtml';

loader.config({ monaco });

const { Text } = Typography;

const DebugTest = () => {
  const location = useLocation();
  const [form] = Form.useForm();
  
  // Markdown 转 HTML

  const [templateContent, setTemplateContent] = useState('# {{title}}\n\n{{content}}');
  const [metadataYaml, setMetadataYaml] = useState(`title:
  type: string
  source: user_input
  required: true
  description: 标题
  ui_config:
    input_type: text
    placeholder: 请输入标题

content:
  type: string
  source: user_input
  required: true
  description: 内容
  ui_config:
    input_type: textarea
    placeholder: 请输入内容`);
  const [userInputFields, setUserInputFields] = useState<Array<{name: string, description: string, required: boolean}>>([]);
  const [renderedMarkdown, setRenderedMarkdown] = useState<string>('');
  
  // 转换渲染结果为 HTML
  const renderedHtml = useMarkdownToHtml(renderedMarkdown);
  const [variableResults, setVariableResults] = useState<DebugVariableResult[]>([]);
  const [yamlError, setYamlError] = useState<string | null>(null);

  // 从 location.state 加载模板内容（如果从模板编辑页跳转过来）
  useEffect(() => {
    const state = location.state as any;
    if (state?.templateContent) {
      setTemplateContent(state.templateContent);
    }
    if (state?.metadataYaml) {
      setMetadataYaml(state.metadataYaml);
    }
  }, [location]);

  // 解析元数据YAML，提取user_input字段
  useEffect(() => {
    try {
      const metadata = yaml.load(metadataYaml) as Record<string, any>;
      if (metadata && typeof metadata === 'object') {
        const inputs = Object.entries(metadata)
          .filter(([_, config]) => config.source === 'user_input')
          .map(([name, config]) => ({
            name,
            description: config.description || name,
            required: config.required || false,
          }));
        setUserInputFields(inputs);
        setYamlError(null);
      }
    } catch (error: any) {
      setYamlError(error.message);
      setUserInputFields([]);
    }
  }, [metadataYaml]);

  const debugMutation = useMutation({
    mutationFn: debugRender,
    onSuccess: (data) => {
      if (data.success && data.rendered_markdown) {
        setRenderedMarkdown(data.rendered_markdown);
        setVariableResults(data.variables);
        message.success('调试执行成功！');
      } else {
        message.error(`调试失败: ${data.error}`);
        setVariableResults(data.variables);
      }
    },
    onError: (error: any) => {
      message.error(`调试失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  const handleExecute = async (values: any) => {
    debugMutation.mutate({
      template_content: templateContent,
      metadata_yaml: metadataYaml,
      user_inputs: values,
    });
  };

  const handleClear = () => {
    setTemplateContent('# {{title}}\n\n{{content}}');
    setMetadataYaml(`title:
  type: string
  source: user_input
  required: true
  description: 标题

content:
  type: string
  source: user_input
  required: true
  description: 内容`);
    setRenderedMarkdown('');
    setVariableResults([]);
    form.resetFields();
    message.info('已重置');
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'running':
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const variableColumns = [
    {
      title: '变量名',
      dataIndex: 'variable_name',
      key: 'variable_name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Space>
          {getStatusIcon(status)}
        </Space>
      ),
    },
    {
      title: '执行时间',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      render: (ms: number) => `${ms}ms`,
    },
    {
      title: '结果',
      dataIndex: 'value',
      key: 'value',
      render: (value: any, record: DebugVariableResult) => {
        if (record.error_message) {
          return <Text type="danger">{record.error_message}</Text>;
        }
        if (value === null || value === undefined) {
          return <Text type="secondary">null</Text>;
        }
        const valueStr = typeof value === 'object' ? JSON.stringify(value) : String(value);
        return (
          <div style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {valueStr.length > 100 ? valueStr.substring(0, 100) + '...' : valueStr}
          </div>
        );
      },
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h2 style={{ margin: 0 }}>模板调试测试</h2>
          <Button icon={<ClearOutlined />} onClick={handleClear}>
            重置
          </Button>
        </div>

        <Alert
          message="调试说明"
          description="在此页面，您可以实时测试模板渲染效果。所有变量将使用真实的SQL/API/AI调用执行，请谨慎使用。"
          type="info"
          showIcon
        />

        <Row gutter={24}>
          {/* 左侧：编辑区 */}
          <Col span={12}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Card title="模板内容" size="small">
                <div style={{ border: '1px solid #d9d9d9', borderRadius: 4 }}>
                  <Editor
                    height="300px"
                    language="jinja2"
                    value={templateContent}
                    onChange={(value) => setTemplateContent(value || '')}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 14,
                      wordWrap: 'on',
                    }}
                  />
                </div>
              </Card>

              <Card title="变量元数据 (YAML)" size="small">
                {yamlError && (
                  <Alert
                    message="YAML 解析错误"
                    description={yamlError}
                    type="error"
                    showIcon
                    style={{ marginBottom: 12 }}
                  />
                )}
                <div style={{ border: '1px solid #d9d9d9', borderRadius: 4 }}>
                  <Editor
                    height="300px"
                    language="yaml"
                    value={metadataYaml}
                    onChange={(value) => setMetadataYaml(value || '')}
                    options={{
                      minimap: { enabled: false },
                      fontSize: 14,
                      wordWrap: 'on',
                    }}
                  />
                </div>
              </Card>

              <Card title="用户输入" size="small">
                {userInputFields.length === 0 ? (
                  <Alert
                    message="没有需要输入的变量"
                    description="当前元数据中没有user_input类型的变量"
                    type="info"
                    showIcon
                  />
                ) : (
                  <Form form={form} layout="vertical" onFinish={handleExecute}>
                    {userInputFields.map((field) => (
                      <Form.Item
                        key={field.name}
                        name={field.name}
                        label={field.description}
                        rules={[{ required: field.required, message: `请输入${field.description}` }]}
                      >
                        <Input.TextArea
                          placeholder={`请输入${field.description}`}
                          rows={2}
                        />
                      </Form.Item>
                    ))}
                    <Form.Item>
                      <Button
                        type="primary"
                        htmlType="submit"
                        icon={<PlayCircleOutlined />}
                        loading={debugMutation.isPending}
                        block
                        size="large"
                      >
                        执行调试
                      </Button>
                    </Form.Item>
                  </Form>
                )}
              </Card>
            </Space>
          </Col>

          {/* 右侧：结果展示区 */}
          <Col span={12}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Card
                title="渲染结果"
                size="small"
                extra={
                  debugMutation.isPending && (
                    <Space>
                      <Spin size="small" />
                      <span>执行中...</span>
                    </Space>
                  )
                }
              >
                {renderedMarkdown ? (
                  <div
                    style={{
                      border: '1px solid #d9d9d9',
                      borderRadius: 4,
                      padding: '16px',
                      minHeight: '300px',
                      maxHeight: '500px',
                      overflow: 'auto',
                      backgroundColor: '#fafafa',
                    }}
                  >
                    <div 
                      className="markdown-body"
                      dangerouslySetInnerHTML={{ __html: renderedHtml }} 
                    />
                  </div>
                ) : (
                  <Alert
                    message="暂无渲染结果"
                    description="点击「执行调试」按钮开始"
                    type="info"
                    showIcon
                  />
                )}
              </Card>

              <Card title="变量执行详情" size="small">
                {variableResults.length > 0 ? (
                  <Table
                    dataSource={variableResults}
                    columns={variableColumns}
                    rowKey="variable_name"
                    pagination={false}
                    size="small"
                  />
                ) : (
                  <Alert
                    message="暂无变量执行记录"
                    type="info"
                    showIcon
                  />
                )}
              </Card>
            </Space>
          </Col>
        </Row>
      </Space>
    </div>
  );
};

export default DebugTest;

