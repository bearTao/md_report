import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Form,
  Input,
  Button,
  Space,
  Alert,
  message,
  Spin,
  Typography,
} from 'antd';
import {
  SaveOutlined,
  CheckCircleOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { getAIConfig, updateAIConfig } from '../../api';

const { Paragraph, Text } = Typography;

const AISettings = () => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  // 查询AI配置
  const { data: config, isLoading } = useQuery({
    queryKey: ['aiConfig'],
    queryFn: getAIConfig,
  });

  // 更新AI配置
  const updateMutation = useMutation({
    mutationFn: updateAIConfig,
    onSuccess: () => {
      message.success('AI配置已更新');
      queryClient.invalidateQueries({ queryKey: ['aiConfig'] });
      form.resetFields(['api_key']); // Only reset api_key, keep api_base
    },
  });

  const handleSubmit = (values: any) => {
    updateMutation.mutate({
      provider: 'openai',
      api_key: values.api_key,
      api_base: values.api_base || undefined,
    });
  };

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 800 }}>
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          {/* 配置状态 */}
          <div>
            <h2>AI 配置</h2>
            {config?.configured ? (
              <Alert
                message="AI配置已完成"
                description="当前使用 OpenAI 作为AI服务提供商"
                type="success"
                icon={<CheckCircleOutlined />}
                showIcon
              />
            ) : (
              <Alert
                message="未配置AI服务"
                description="请配置 OpenAI API Key 以使用 AI 生成功能"
                type="warning"
                icon={<WarningOutlined />}
                showIcon
              />
            )}
          </div>

          {/* 配置表单 */}
          <div>
            <h3>OpenAI 配置</h3>
            <Paragraph type="secondary">
              请输入您的 OpenAI API Key 和 API Base URL（如使用代理或第三方服务）。
            </Paragraph>

            <Form
              form={form}
              layout="vertical"
              onFinish={handleSubmit}
              initialValues={{
                api_base: config?.api_base || '',
              }}
            >
              <Form.Item
                name="api_key"
                label="OpenAI API Key"
                rules={[
                  { required: true, message: '请输入 OpenAI API Key' },
                  { pattern: /^sk-/, message: 'API Key 应该以 sk- 开头' },
                ]}
              >
                <Input.Password
                  placeholder="sk-..."
                  size="large"
                />
              </Form.Item>

              <Form.Item
                name="api_base"
                label="API Base URL（可选）"
                extra="如果使用代理或第三方OpenAI兼容服务，请填写此项。例如：https://api.openai.com/v1"
              >
                <Input
                  placeholder="https://api.openai.com/v1"
                  size="large"
                />
              </Form.Item>

              <Form.Item>
                <Space>
                  <Button
                    type="primary"
                    htmlType="submit"
                    icon={<SaveOutlined />}
                    loading={updateMutation.isPending}
                  >
                    保存配置
                  </Button>
                </Space>
              </Form.Item>
            </Form>

            <Alert
              message="如何获取 OpenAI API Key？"
              description={
                <div>
                  <Paragraph>
                    1. 访问{' '}
                    <a
                      href="https://platform.openai.com/api-keys"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      OpenAI API Keys 页面
                    </a>
                  </Paragraph>
                  <Paragraph>2. 点击 "Create new secret key" 创建新的 API Key</Paragraph>
                  <Paragraph>3. 复制生成的 API Key 并粘贴到上方输入框</Paragraph>
                  <Paragraph>
                    <Text type="warning">
                      注意：API Key 只会显示一次，请妥善保管
                    </Text>
                  </Paragraph>
                </div>
              }
              type="info"
            />
          </div>
        </Space>
      </Card>
    </div>
  );
};

export default AISettings;

