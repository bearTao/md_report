import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Button,
  Table,
  Space,
  Input,
  Modal,
  message,
  Popconfirm,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { getTemplates, deleteTemplate } from '../../api';
import type { TemplateListItem } from '../../types';

const TemplateList = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchText, setSearchText] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 20;

  // 查询模板列表
  const { data, isLoading } = useQuery({
    queryKey: ['templates', page, searchText],
    queryFn: () => getTemplates({ page, page_size: pageSize, q: searchText }),
  });

  // 删除模板
  const deleteMutation = useMutation({
    mutationFn: deleteTemplate,
    onSuccess: () => {
      message.success('模板删除成功');
      queryClient.invalidateQueries({ queryKey: ['templates'] });
    },
  });

  const handleDelete = (id: string) => {
    deleteMutation.mutate(id);
  };

  const columns = [
    {
      title: '模板ID',
      dataIndex: 'id',
      key: 'id',
      width: 150,
      render: (text: string) => (
        <span style={{ fontFamily: 'monospace', fontSize: '12px' }}>{text}</span>
      ),
    },
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
      width: '25%',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      width: '35%',
      ellipsis: true,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: '20%',
      render: (text: string) => dayjs(text).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_: any, record: TemplateListItem) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => navigate(`/templates/${record.id}/edit`)}
            title="编辑"
          />
          <Popconfirm
            title="确定要删除这个模板吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
              title="删除"
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Space>
          <Input
            placeholder="搜索模板名称或描述"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onPressEnter={() => setPage(1)}
            style={{ width: 300 }}
          />
          <Button onClick={() => setPage(1)}>搜索</Button>
        </Space>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => navigate('/templates/new/edit')}
        >
          创建模板
        </Button>
      </div>

      <Table
        columns={columns}
        dataSource={data?.items || []}
        rowKey="id"
        loading={isLoading}
        pagination={{
          current: page,
          pageSize,
          total: data?.total || 0,
          onChange: setPage,
          showSizeChanger: false,
          showTotal: (total) => `共 ${total} 个模板`,
        }}
      />
    </div>
  );
};

export default TemplateList;

