import { useState, useEffect } from 'react';
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
  Collapse,
  Alert,
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
  const [includedTemplates, setIncludedTemplates] = useState<Template[]>([]);
  const [isScanning, setIsScanning] = useState(false);

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

  // 扫描模板中的 include 标签，加载所有被包含的模板
  useEffect(() => {
    const scanIncludedTemplates = async () => {
      if (!template) {
        setIncludedTemplates([]);
        return;
      }

      setIsScanning(true);
      try {
        const includePattern = /{%\s*include\s+"([^"]+)"\s*%}/g;
        const matches = [...template.template_content.matchAll(includePattern)];
        const templateIds = matches.map(m => m[1]);

        if (templateIds.length === 0) {
          setIncludedTemplates([]);
          setIsScanning(false);
          return;
        }

        // 加载所有被 include 的模板
        const includedTemps: Template[] = [];
        for (const tid of templateIds) {
          try {
            const temp = await getTemplate(tid);
            includedTemps.push(temp);
          } catch (error) {
            console.error(`Failed to load included template ${tid}:`, error);
          }
        }

        setIncludedTemplates(includedTemps);
      } catch (error) {
        console.error('Error scanning includes:', error);
      } finally {
        setIsScanning(false);
      }
    };

    scanIncludedTemplates();
  }, [template]);

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

    // 提取报告名称（如果提供）
    const reportName = values.report_name;
    
    // 从 values 中移除 report_name，只保留变量值
    const { report_name, ...variableValues } = values;

    // 构建嵌套的 inputs 结构
    let finalInputs: any;
    
    if (includedTemplates.length > 0) {
      // 有嵌套模板，构建嵌套结构
      finalInputs = {
        [selectedTemplateId]: {}, // 主模板的inputs
      };
      
      // 分配变量到对应的模板
      for (const [key, value] of Object.entries(variableValues)) {
        // key 格式: "template_id__var_name" 或 "var_name"
        if (key.includes('__')) {
          const [templateId, varName] = key.split('__', 2);
          if (!finalInputs[templateId]) {
            finalInputs[templateId] = {};
          }
          finalInputs[templateId][varName] = value;
        } else {
          // 没有前缀的变量属于主模板
          finalInputs[selectedTemplateId][key] = value;
        }
      }
    } else {
      // 没有嵌套模板，使用原来的扁平结构
      finalInputs = variableValues;
    }

    generateMutation.mutate({
      template_id: selectedTemplateId,
      inputs: finalInputs,
      report_name: reportName, // 包含报告名称（可能为 undefined）
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

                {isScanning && (
                  <Alert
                    message="正在扫描嵌套模板..."
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                )}

                {includedTemplates.length > 0 && (
                  <Alert
                    message={`检测到 ${includedTemplates.length} 个嵌套子模板`}
                    description="请分别填写每个模板的变量值"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                )}
                
                {getUserInputVariables(template).length === 0 && includedTemplates.length === 0 ? (
                  <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSubmit}
                    style={{ maxWidth: 600, margin: '0 auto' }}
                  >
                    <Alert
                      message="该模板不需要用户输入数据"
                      type="info"
                      showIcon
                      style={{ marginBottom: 16 }}
                    />
                    
                    {/* 报告名称输入框 */}
                    <Card
                      title="报告信息"
                      size="small"
                      style={{ marginBottom: 16 }}
                    >
                      <Form.Item
                        label="报告名称"
                        name="report_name"
                        tooltip="留空将自动生成：模板名称 - 日期时间"
                      >
                        <Input
                          placeholder="留空将自动生成：模板名称 - 日期时间"
                          maxLength={200}
                        />
                      </Form.Item>
                    </Card>

                    <Form.Item>
                      <Space>
                        <Button
                          type="primary"
                          htmlType="submit"
                          loading={generateMutation.isPending}
                        >
                          开始生成报告
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
                ) : (
                  <Form
                    form={form}
                    layout="vertical"
                    onFinish={handleSubmit}
                  >
                    {/* 报告名称输入框 */}
                    <Card
                      title="报告信息"
                      size="small"
                      style={{ marginBottom: 16 }}
                    >
                      <Form.Item
                        label="报告名称"
                        name="report_name"
                        tooltip="留空将自动生成：模板名称 - 日期时间"
                      >
                        <Input
                          placeholder="留空将自动生成：模板名称 - 日期时间"
                          maxLength={200}
                        />
                      </Form.Item>
                    </Card>

                    {/* 主模板的变量 */}
                    {getUserInputVariables(template).length > 0 && (
                      <Card
                        title={`主模板: ${template.name}`}
                        size="small"
                        style={{ marginBottom: 16 }}
                      >
                        {getUserInputVariables(template).map(({ name, config }) =>
                          renderFormItem(name, config)
                        )}
                      </Card>
                    )}

                    {/* 子模板的变量 */}
                    {includedTemplates.map((includedTemp) => (
                      <Card
                        key={includedTemp.id}
                        title={`子模板: ${includedTemp.name} (ID: ${includedTemp.id})`}
                        size="small"
                        style={{ marginBottom: 16 }}
                      >
                        {getUserInputVariables(includedTemp).map(({ name, config }) =>
                          renderFormItem(`${includedTemp.id}__${name}`, config)
                        )}
                      </Card>
                    ))}

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

