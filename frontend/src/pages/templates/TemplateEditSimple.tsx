import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Form,
  Input,
  Button,
  Card,
  message,
} from 'antd';
import { SaveOutlined, ArrowLeftOutlined } from '@ant-design/icons';

const { TextArea } = Input;

const TemplateEditSimple = () => {
  const navigate = useNavigate();
  const { templateId } = useParams<{ templateId: string }>();
  const isNew = templateId === 'new';
  
  const [form] = Form.useForm();
  const [templateContent, setTemplateContent] = useState('');
  const [metadataYaml, setMetadataYaml] = useState('');

  console.log('页面加载成功！', { templateId, isNew });

  const handleSubmit = (values: any) => {
    console.log('提交表单', values);
    message.success('测试成功！');
  };

  return (
    <div style={{ padding: 24 }}>
      <h1>简化版模板编辑页面（测试）</h1>
      <p>模板ID: {templateId}</p>
      <p>是否新建: {isNew ? '是' : '否'}</p>

      <div style={{ marginBottom: 16 }}>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/templates')}
        >
          返回列表
        </Button>
      </div>

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
          <TextArea
            rows={10}
            value={templateContent}
            onChange={(e) => setTemplateContent(e.target.value)}
            placeholder="在这里输入Jinja2模板内容..."
          />
        </Card>

        <Card title="变量元数据 (YAML)" style={{ marginBottom: 16 }}>
          <TextArea
            rows={10}
            value={metadataYaml}
            onChange={(e) => setMetadataYaml(e.target.value)}
            placeholder="在这里输入YAML元数据..."
          />
        </Card>

        <Form.Item>
          <Button type="primary" htmlType="submit" icon={<SaveOutlined />}>
            保存模板（测试）
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
};

export default TemplateEditSimple;

