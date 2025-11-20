import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Form,
  Input,
  Button,
  Space,
  message,
  Spin,
  Typography,
  Divider,
  InputNumber,
  Switch,
  AutoComplete,
  Collapse,
} from 'antd';
import {
  SaveOutlined,
  RobotOutlined,
} from '@ant-design/icons';
import { getAgentConfig, updateAgentConfig } from '../../api';
import { useState } from 'react';
import type { AgentLLMConfigItem } from '../../types';

const { Paragraph, Title } = Typography;
const { Panel } = Collapse;

const AgentSettings = () => {
  const queryClient = useQueryClient();
  const [activeKey, setActiveKey] = useState<string[]>(['ai_refinement']);

  // 查询Agent配置
  const { data: config, isLoading } = useQuery({
    queryKey: ['agentConfig'],
    queryFn: getAgentConfig,
  });

  // 更新Agent配置
  const updateMutation = useMutation({
    mutationFn: updateAgentConfig,
    onSuccess: () => {
      message.success('Agent配置已更新');
      queryClient.invalidateQueries({ queryKey: ['agentConfig'] });
    },
    onError: (error: any) => {
      message.error(`更新失败: ${error.message}`);
    },
  });

  const handleSubmit = (component: string, values: any) => {
    const currentConfig = config?.configs[component];
    
    // 将空字符串转换为null，避免后端验证错误
    const cleanValue = (val: any) => {
      if (val === '' || val === undefined) return null;
      return val;
    };
    
    updateMutation.mutate({
      component,
      model: values.model.trim(), // 移除首尾空格
      api_key: cleanValue(values.api_key),
      api_base: cleanValue(values.api_base),
      organization: cleanValue(values.organization),
      temperature: values.temperature,
      max_tokens: cleanValue(values.max_tokens),
      timeout: values.timeout,
      enabled: values.enabled !== undefined ? values.enabled : currentConfig?.enabled ?? true,
    });
  };

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" />
      </div>
    );
  }

  const componentLabels: Record<string, { title: string; description: string }> = {
    intent_parser: {
      title: '意图解析器',
      description: '用于解析用户的修改意图，将自然语言转换为结构化操作',
    },
    explanation_generator: {
      title: '响应生成器',
      description: '用于生成对用户的响应说明（当前未启用LLM生成）',
    },
    ai_refinement: {
      title: 'AI内容优化',
      description: '用于优化和改进报告内容，提供高质量的AI生成内容',
    },
  };

  // 常用模型选项（用于自动完成提示）
  const modelOptions = [
    // OpenAI 模型
    { value: 'gpt-4', label: 'GPT-4 (OpenAI)' },
    { value: 'gpt-4-turbo', label: 'GPT-4 Turbo (OpenAI)' },
    { value: 'gpt-4-turbo-preview', label: 'GPT-4 Turbo Preview (OpenAI)' },
    { value: 'gpt-4-32k', label: 'GPT-4 32K (OpenAI)' },
    { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo (OpenAI)' },
    { value: 'gpt-3.5-turbo-16k', label: 'GPT-3.5 Turbo 16K (OpenAI)' },
    // Anthropic Claude 模型
    { value: 'claude-3-opus-20240229', label: 'Claude 3 Opus (Anthropic)' },
    { value: 'claude-3-sonnet-20240229', label: 'Claude 3 Sonnet (Anthropic)' },
    { value: 'claude-3-haiku-20240307', label: 'Claude 3 Haiku (Anthropic)' },
    { value: 'claude-2.1', label: 'Claude 2.1 (Anthropic)' },
    { value: 'claude-2.0', label: 'Claude 2.0 (Anthropic)' },
    // Google 模型
    { value: 'gemini-pro', label: 'Gemini Pro (Google)' },
    { value: 'gemini-pro-vision', label: 'Gemini Pro Vision (Google)' },
    // Azure OpenAI
    { value: 'gpt-4-azure', label: 'GPT-4 (Azure OpenAI)' },
    { value: 'gpt-35-turbo', label: 'GPT-3.5 Turbo (Azure OpenAI)' },
    // 其他提供商
    { value: 'deepseek-chat', label: 'DeepSeek Chat' },
    { value: 'qwen-max', label: 'Qwen Max (阿里云)' },
    { value: 'moonshot-v1-8k', label: 'Moonshot v1 8K (月之暗面)' },
  ];

  const renderComponentConfig = (component: string, componentConfig: AgentLLMConfigItem) => {
    const labels = componentLabels[component];
    
    return (
      <Panel
        header={
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <RobotOutlined style={{ marginRight: 8 }} />
              <strong>{labels.title}</strong>
            </div>
            <Switch
              checked={componentConfig.enabled}
              onChange={(checked) => {
                handleSubmit(component, {
                  ...componentConfig,
                  enabled: checked,
                });
              }}
              onClick={(_, e) => e.stopPropagation()}
            />
          </div>
        }
        key={component}
      >
        <Paragraph type="secondary" style={{ marginBottom: 16 }}>
          {labels.description}
        </Paragraph>

        <Form
          layout="vertical"
          initialValues={{
            model: componentConfig.model,
            api_key: componentConfig.api_key || '',
            api_base: componentConfig.api_base || '',
            organization: componentConfig.organization || '',
            temperature: componentConfig.temperature,
            max_tokens: componentConfig.max_tokens || undefined,
            timeout: componentConfig.timeout,
            enabled: componentConfig.enabled,
          }}
          onFinish={(values) => handleSubmit(component, values)}
        >
          <Form.Item
            name="model"
            label="模型"
            rules={[{ required: true, message: '请输入模型名称' }]}
            extra="可以从列表中选择常用模型，或直接输入自定义模型名称"
          >
            <AutoComplete
              options={modelOptions}
              placeholder="输入或选择模型名称，如：gpt-4, claude-3-opus-20240229"
              size="large"
              filterOption={(inputValue, option) =>
                option!.value.toLowerCase().indexOf(inputValue.toLowerCase()) !== -1 ||
                option!.label.toLowerCase().indexOf(inputValue.toLowerCase()) !== -1
              }
            />
          </Form.Item>

          <Form.Item
            name="api_key"
            label="API Key（可选）"
            extra="如果不填写，将使用全局AI配置中的API Key"
          >
            <Input.Password
              placeholder="sk-..."
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="api_base"
            label="API Base URL（可选）"
            extra="如果不填写，将使用全局AI配置中的API Base URL"
          >
            <Input
              placeholder="https://api.openai.com/v1"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="organization"
            label="Organization ID（可选）"
            extra="用于OpenAI的组织ID"
          >
            <Input
              placeholder="org-..."
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="temperature"
            label="Temperature"
            extra="控制生成的随机性，0.0-2.0之间，值越大越随机"
            rules={[
              { required: true, message: '请输入temperature' },
              { type: 'number', min: 0, max: 2, message: '必须在0.0到2.0之间' },
            ]}
          >
            <InputNumber
              min={0}
              max={2}
              step={0.1}
              style={{ width: '100%' }}
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="max_tokens"
            label="Max Tokens（可选）"
            extra="最大生成token数，留空表示无限制"
          >
            <InputNumber
              min={1}
              style={{ width: '100%' }}
              placeholder="留空表示无限制"
              size="large"
            />
          </Form.Item>

          <Form.Item
            name="timeout"
            label="Timeout（秒）"
            rules={[
              { required: true, message: '请输入超时时间' },
              { type: 'number', min: 1, message: '必须大于0' },
            ]}
          >
            <InputNumber
              min={1}
              style={{ width: '100%' }}
              size="large"
            />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={updateMutation.isPending}
            >
              保存配置
            </Button>
          </Form.Item>
        </Form>
      </Panel>
    );
  };

  return (
    <div style={{ maxWidth: 1000 }}>
      <Card>
        <Space direction="vertical" style={{ width: '100%' }} size="large">
          <div>
            <Title level={2}>Agent 配置</Title>
            <Paragraph type="secondary">
              为每个Agent组件配置独立的LLM模型和参数。每个组件可以使用不同的模型和API配置。
            </Paragraph>
            <Paragraph type="secondary">
              如果某个组件未配置API Key或Base URL，将自动使用全局AI配置中的值。
            </Paragraph>
          </div>

          <Divider />

          {config && (
            <Collapse 
              activeKey={activeKey} 
              onChange={(keys) => setActiveKey(keys as string[])}
            >
              {Object.entries(config.configs).map(([component, componentConfig]) =>
                renderComponentConfig(component, componentConfig)
              )}
            </Collapse>
          )}
        </Space>
      </Card>
    </div>
  );
};

export default AgentSettings;
