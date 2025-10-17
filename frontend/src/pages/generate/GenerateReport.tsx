import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import {
  Steps,
  Card,
  Select,
  Form,
  Input,
  InputNumber,
  Checkbox,
  Button,
  Space,
  message,
  Spin,
} from 'antd';
import { getTemplates, getTemplate, generateReport } from '../../api';
import type { Template, VariableConfig } from '../../types';

const { TextArea } = Input;
const { Step } = Steps;

const GenerateReport = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);

  // 查询模板列表
  const { data: templateList, isLoading: isLoadingList } = useQuery({
    queryKey: ['templates'],
    queryFn: () => getTemplates({ page: 1, page_size: 100 }),
  });

  // 查询选中模板详情
  const { data: template, isLoading: isLoadingTemplate } = useQuery({
    queryKey: ['template', selectedTemplateId],
    queryFn: () => getTemplate(selectedTemplateId!),
    enabled: !!selectedTemplateId,
  });

  // 生成报告
  const generateMutation = useMutation({
    mutationFn: generateReport,
    onSuccess: (data) => {
      message.success('报告生成任务已启动');
      navigate(`/generate/${data.task_id}`);
    },
  });

  const handleTemplateSelect = (templateId: string) => {
    setSelectedTemplateId(templateId);
    setCurrentStep(1);
    form.resetFields();
  };

  const handleSubmit = async (values: any) => {
    if (!selectedTemplateId) {
      message.error('请先选择模板');
      return;
    }

    generateMutation.mutate({
      template_id: selectedTemplateId,
      inputs: values,
    });
  };

  // 渲染表单项
  const renderFormItem = (varName: string, varConfig: VariableConfig) => {
    const { type, description, required, ui_config } = varConfig;

    const commonProps = {
      label: description || varName,
      name: varName,
      rules: [{ required, message: `请输入${description || varName}` }],
    };

    switch (ui_config?.input_type) {
      case 'textarea':
        return (
          <Form.Item key={varName} {...commonProps}>
            <TextArea
              rows={4}
              placeholder={ui_config.placeholder}
            />
          </Form.Item>
        );

      case 'number':
        return (
          <Form.Item key={varName} {...commonProps}>
            <InputNumber
              style={{ width: '100%' }}
              placeholder={ui_config.placeholder}
            />
          </Form.Item>
        );

      case 'checkbox':
        return (
          <Form.Item
            key={varName}
            name={varName}
            valuePropName="checked"
            {...commonProps}
          >
            <Checkbox>{description || varName}</Checkbox>
          </Form.Item>
        );

      case 'select':
        return (
          <Form.Item key={varName} {...commonProps}>
            <Select
              placeholder={ui_config.placeholder}
              options={ui_config.options}
            />
          </Form.Item>
        );

      default:
        return (
          <Form.Item key={varName} {...commonProps}>
            <Input placeholder={ui_config?.placeholder} />
          </Form.Item>
        );
    }
  };

  // 获取需要用户输入的变量
  const getUserInputVariables = (template: Template) => {
    const metadata = template.metadata_json;
    return Object.entries(metadata)
      .filter(([_, config]) => config.source === 'user_input')
      .map(([name, config]) => ({ name, config }));
  };

  return (
    <div>
      <Card>
        <Steps current={currentStep} style={{ marginBottom: 32 }}>
          <Step title="选择模板" />
          <Step title="填写数据" />
        </Steps>

        {currentStep === 0 && (
          <div>
            <h3 style={{ marginBottom: 16 }}>选择报告模板</h3>
            {isLoadingList ? (
              <div style={{ textAlign: 'center', padding: '50px 0' }}>
                <Spin />
              </div>
            ) : (
              <Select
                style={{ width: '100%' }}
                placeholder="请选择模板"
                size="large"
                onChange={handleTemplateSelect}
                options={templateList?.items.map(item => ({
                  label: item.name,
                  value: item.id,
                  description: item.description,
                }))}
                optionRender={(option) => (
                  <div>
                    <div style={{ fontWeight: 'bold' }}>{option.label}</div>
                    <div style={{ fontSize: 12, color: '#999' }}>
                      {option.data.description}
                    </div>
                  </div>
                )}
              />
            )}
          </div>
        )}

        {currentStep === 1 && (
          <div>
            {isLoadingTemplate ? (
              <div style={{ textAlign: 'center', padding: '50px 0' }}>
                <Spin />
              </div>
            ) : template ? (
              <>
                <h3 style={{ marginBottom: 16 }}>
                  填写数据 - {template.name}
                </h3>
                
                {getUserInputVariables(template).length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '50px 0' }}>
                    <p>该模板不需要用户输入数据</p>
                    <Button
                      type="primary"
                      onClick={() => handleSubmit({})}
                      loading={generateMutation.isPending}
                    >
                      直接生成报告
                    </Button>
                  </div>
                ) : (
                  <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSubmit}
                  >
                    {getUserInputVariables(template).map(({ name, config }) =>
                      renderFormItem(name, config)
                    )}

                    <Form.Item>
                      <Space>
                        <Button
                          type="primary"
                          htmlType="submit"
                          loading={generateMutation.isPending}
                        >
                          开始生成
                        </Button>
                        <Button onClick={() => {
                          setCurrentStep(0);
                          setSelectedTemplateId(null);
                        }}>
                          重新选择模板
                        </Button>
                      </Space>
                    </Form.Item>
                  </Form>
                )}
              </>
            ) : null}
          </div>
        )}
      </Card>
    </div>
  );
};

export default GenerateReport;

