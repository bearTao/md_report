import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Table,
  Button,
  Space,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Switch,
  message,
  Tag,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import {
  getDBConnections,
  createDBConnection,
  updateDBConnection,
  deleteDBConnection,
  testDBConnection,
} from '../../api';
import type { DBConnection, DBConnectionCreate, DBConnectionListItem } from '../../types';

const { Option } = Select;

const DBSettings = () => {
  const queryClient = useQueryClient();
  const [form] = Form.useForm();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingConnection, setEditingConnection] = useState<DBConnectionListItem | null>(null);
  const [testingId, setTestingId] = useState<string | null>(null);

  // 获取连接列表
  const { data, isLoading } = useQuery({
    queryKey: ['dbConnections'],
    queryFn: getDBConnections,
  });

  // 创建连接
  const createMutation = useMutation({
    mutationFn: createDBConnection,
    onSuccess: () => {
      message.success('数据库连接创建成功');
      setIsModalOpen(false);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['dbConnections'] });
    },
    onError: (error: any) => {
      message.error(`创建失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // 更新连接
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      updateDBConnection(id, data),
    onSuccess: () => {
      message.success('数据库连接更新成功');
      setIsModalOpen(false);
      setEditingConnection(null);
      form.resetFields();
      queryClient.invalidateQueries({ queryKey: ['dbConnections'] });
    },
    onError: (error: any) => {
      message.error(`更新失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // 删除连接
  const deleteMutation = useMutation({
    mutationFn: deleteDBConnection,
    onSuccess: () => {
      message.success('数据库连接删除成功');
      queryClient.invalidateQueries({ queryKey: ['dbConnections'] });
    },
    onError: (error: any) => {
      message.error(`删除失败: ${error.response?.data?.detail || error.message}`);
    },
  });

  // 测试连接
  const testMutation = useMutation({
    mutationFn: testDBConnection,
    onSuccess: (data) => {
      if (data.success) {
        message.success('连接测试成功！');
      } else {
        message.error(`连接测试失败: ${data.message}`);
      }
      setTestingId(null);
    },
    onError: (error: any) => {
      message.error(`测试失败: ${error.message}`);
      setTestingId(null);
    },
  });

  // 打开创建/编辑对话框
  const handleOpenModal = (connection?: DBConnectionListItem) => {
    if (connection) {
      setEditingConnection(connection);
      form.setFieldsValue(connection);
    } else {
      setEditingConnection(null);
      form.resetFields();
    }
    setIsModalOpen(true);
  };

  // 提交表单
  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      
      if (editingConnection) {
        // 更新连接
        updateMutation.mutate({ id: editingConnection.id, data: values });
      } else {
        // 创建连接
        createMutation.mutate(values as DBConnectionCreate);
      }
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  // 测试连接
  const handleTestConnection = (id: string) => {
    setTestingId(id);
    testMutation.mutate(id);
  };

  // 数据库引擎选项
  const engineOptions = [
    { value: 'postgresql', label: 'PostgreSQL' },
    { value: 'mysql', label: 'MySQL' },
    { value: 'sqlserver', label: 'SQL Server' },
    { value: 'oracle', label: 'Oracle' },
  ];

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '数据库类型',
      dataIndex: 'engine',
      key: 'engine',
      width: 150,
      render: (engine: string) => (
        <Tag color="blue">{engine.toUpperCase()}</Tag>
      ),
    },
    {
      title: '主机',
      dataIndex: 'host',
      key: 'host',
      width: 200,
    },
    {
      title: '端口',
      dataIndex: 'port',
      key: 'port',
      width: 100,
    },
    {
      title: '数据库',
      dataIndex: 'database',
      key: 'database',
      width: 150,
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      render: (isActive: boolean) =>
        isActive ? (
          <Tag icon={<CheckCircleOutlined />} color="success">
            启用
          </Tag>
        ) : (
          <Tag icon={<CloseCircleOutlined />} color="default">
            禁用
          </Tag>
        ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: DBConnectionListItem) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<ApiOutlined />}
            loading={testingId === record.id}
            onClick={() => handleTestConnection(record.id)}
          >
            测试
          </Button>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleOpenModal(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定删除此连接吗?"
            onConfirm={() => deleteMutation.mutate(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="数据库连接管理"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => handleOpenModal()}
          >
            新建连接
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={data?.items || []}
          rowKey="id"
          loading={isLoading}
          pagination={false}
        />
      </Card>

      {/* 创建/编辑对话框 */}
      <Modal
        title={editingConnection ? '编辑数据库连接' : '新建数据库连接'}
        open={isModalOpen}
        onOk={handleSubmit}
        onCancel={() => {
          setIsModalOpen(false);
          setEditingConnection(null);
          form.resetFields();
        }}
        width={600}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            port: 3306,
            is_active: true,
          }}
        >
          <Form.Item
            label="连接名称"
            name="name"
            rules={[{ required: true, message: '请输入连接名称' }]}
          >
            <Input placeholder="例如: 生产数据库" />
          </Form.Item>

          <Form.Item
            label="数据库类型"
            name="engine"
            rules={[{ required: true, message: '请选择数据库类型' }]}
          >
            <Select placeholder="选择数据库类型">
              {engineOptions.map((option) => (
                <Option key={option.value} value={option.value}>
                  {option.label}
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Space style={{ width: '100%' }} size="middle">
            <Form.Item
              label="主机地址"
              name="host"
              rules={[{ required: true, message: '请输入主机地址' }]}
              style={{ flex: 1, marginBottom: 0 }}
            >
              <Input placeholder="例如: localhost" />
            </Form.Item>

            <Form.Item
              label="端口"
              name="port"
              rules={[{ required: true, message: '请输入端口' }]}
              style={{ width: 120, marginBottom: 0 }}
            >
              <InputNumber min={1} max={65535} style={{ width: '100%' }} />
            </Form.Item>
          </Space>

          <Form.Item
            label="数据库名"
            name="database"
            rules={[{ required: true, message: '请输入数据库名' }]}
          >
            <Input placeholder="例如: mydb" />
          </Form.Item>

          <Form.Item
            label="用户名"
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="数据库用户名" />
          </Form.Item>

          <Form.Item
            label="密码"
            name="password"
            rules={[
              {
                required: !editingConnection,
                message: '请输入密码',
              },
            ]}
          >
            <Input.Password
              placeholder={
                editingConnection ? '留空表示不修改密码' : '数据库密码'
              }
            />
          </Form.Item>

          <Form.Item label="启用连接" name="is_active" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DBSettings;

