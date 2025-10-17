import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Form,
  Input,
  Button,
  Space,
  Card,
  message,
  Spin,
  Alert,
} from 'antd';
import { SaveOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import yaml from 'js-yaml';
import { getTemplate, createTemplate, updateTemplate } from '../../api';
import type { VariableMetadata } from '../../types';

const { TextArea } = Input;

const TemplateEdit = () => {
  const navigate = useNavigate();
  const { templateId } = useParams<{ templateId: string }>();
  const isNew = templateId === 'new';
  
  const [form] = Form.useForm();
  const [templateContent, setTemplateContent] = useState('');
  const [metadataYaml, setMetadataYaml] = useState('');
  const [yamlError, setYamlError] = useState<string | null>(null);
  const [editorReady, setEditorReady] = useState(false);

  // 查询模板详情
  const { data: template, isLoading, error, isError } = useQuery({
    queryKey: ['template', templateId],
    queryFn: async () => {
      console.log('🔍 正在获取模板:', templateId);
      const result = await getTemplate(templateId!);
      console.log('✅ 获取模板成功:', result);
      return result;
    },
    enabled: !isNew,
    retry: 1,
  });

  // 创建模板
  const createMutation = useMutation({
    mutationFn: createTemplate,
    onSuccess: () => {
      message.success('模板创建成功');
      navigate('/templates');
    },
  });

  // 更新模板
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      updateTemplate(id, data),
    onSuccess: () => {
      message.success('模板更新成功');
      navigate('/templates');
    },
  });

  useEffect(() => {
    console.log('📌 useEffect触发', { template, isNew });
    if (template) {
      console.log('📝 设置表单数据');
      form.setFieldsValue({
        name: template.name,
        description: template.description,
      });
      setTemplateContent(template.template_content);
      setMetadataYaml(yaml.dump(template.metadata_json));
    } else if (isNew) {
      console.log('🆕 新建模板，设置默认值');
      // 设置默认示例
      setTemplateContent('# {{title}}\n\n{{content}}');
      setMetadataYaml(`# 变量元数据示例
title:
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
    }
  }, [template, form, isNew]);

  const handleSubmit = async (values: any) => {
    // 验证YAML
    let metadata: VariableMetadata;
    try {
      metadata = yaml.load(metadataYaml) as VariableMetadata;
      setYamlError(null);
    } catch (error: any) {
      setYamlError(error.message);
      message.error('元数据YAML格式错误');
      return;
    }

    const data = {
      name: values.name,
      description: values.description,
      template_content: templateContent,
      metadata,
    };

    if (isNew) {
      createMutation.mutate(data);
    } else {
      updateMutation.mutate({ id: templateId!, data });
    }
  };

  // Monaco编辑器挂载时
  const handleEditorDidMount = () => {
    console.log('✅ Monaco编辑器已就绪');
    setEditorReady(true);
  };

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: '100px 0' }}>
        <Spin size="large" tip="正在加载模板..." />
        <div style={{ marginTop: 16, color: '#999' }}>
          模板ID: {templateId}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div style={{ padding: '50px' }}>
        <Alert
          message="加载失败"
          description={`无法加载模板: ${error instanceof Error ? error.message : '未知错误'}`}
          type="error"
          showIcon
          action={
            <Button onClick={() => navigate('/templates')}>
              返回列表
            </Button>
          }
        />
      </div>
    );
  }

  console.log('🎨 渲染页面', { isNew, templateId, hasTemplate: !!template, editorReady });

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/templates')}
        >
          返回列表
        </Button>
      </div>

      {!editorReady && (
        <Alert
          message="正在加载代码编辑器..."
          description="首次加载Monaco编辑器可能需要几秒钟，请稍候"
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        <Card title="基本信息" style={{ marginBottom: 16 }}>
          <Form.Item
            name="name"
            label="模板名称"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="请输入模板名称" />
          </Form.Item>

          <Form.Item
            name="description"
            label="模板描述"
          >
            <TextArea
              rows={3}
              placeholder="请输入模板描述"
            />
          </Form.Item>
        </Card>

        <Card title="模板内容 (Jinja2)" style={{ marginBottom: 16 }}>
          <div style={{ border: '1px solid #d9d9d9', borderRadius: 4, minHeight: 400 }}>
            <Editor
              height="400px"
              language="jinja2"
              value={templateContent}
              onChange={(value) => setTemplateContent(value || '')}
              onMount={handleEditorDidMount}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                automaticLayout: true,
                wordWrap: 'on',
              }}
              loading={
                <div style={{ padding: 100, textAlign: 'center' }}>
                  <Spin size="large" tip="正在加载编辑器..." />
                </div>
              }
            />
          </div>
        </Card>

        <Card title="变量元数据 (YAML)" style={{ marginBottom: 16 }}>
          <div style={{ border: '1px solid #d9d9d9', borderRadius: 4, minHeight: 400 }}>
            <Editor
              height="400px"
              language="yaml"
              value={metadataYaml}
              onChange={(value) => setMetadataYaml(value || '')}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                automaticLayout: true,
                wordWrap: 'on',
              }}
              loading={
                <div style={{ padding: 100, textAlign: 'center' }}>
                  <Spin size="large" tip="正在加载编辑器..." />
                </div>
              }
            />
          </div>
          {yamlError && (
            <div style={{ color: 'red', marginTop: 8 }}>
              YAML格式错误: {yamlError}
            </div>
          )}
        </Card>

        <Form.Item>
          <Space>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={createMutation.isPending || updateMutation.isPending}
            >
              保存模板
            </Button>
            <Button onClick={() => navigate('/templates')}>
              取消
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </div>
  );
};

export default TemplateEdit;
