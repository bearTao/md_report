import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useState, useRef, useEffect } from 'react';
import {
  Card,
  Button,
  Space,
  Descriptions,
  Tag,
  Spin,
  Alert,
  Input,
  List,
  message,
  Tooltip,
  Timeline,
  Divider,
  Popover,
} from 'antd';
import {
  DownloadOutlined,
  ArrowLeftOutlined,
  ClockCircleOutlined,
  RobotOutlined,
  ArrowUpOutlined,
  PlusOutlined,
  MessageOutlined,
  CloseOutlined,
  HistoryOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons';
import { useMarkdownToHtml } from '../../hooks/useMarkdownToHtml';
import dayjs from 'dayjs';
import { getReport, downloadReport, getConversationHistory, getConversationSessions } from '../../api';

interface ConversationTurn {
  turn_number: number;
  user_request: string;
  system_response: string;
  timestamp: string;
  operations: string[];
}

interface HistorySession {
  session_id: string;
  report_id: string;
  created_at: string;
  last_activity_at: string;
  turn_count: number;
  preview: string;
}

const ReportPreview = () => {
  const { reportId } = useParams<{ reportId: string }>();
  const navigate = useNavigate();
  
  // Markdown 转 HTML
  
  // Agent 对话状态
  const [agentOpen, setAgentOpen] = useState(false);
  const [historyPopoverOpen, setHistoryPopoverOpen] = useState(false);
  const [userInput, setUserInput] = useState('');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [conversationHistory, setConversationHistory] = useState<ConversationTurn[]>([]);
  const [historySessions, setHistorySessions] = useState<HistorySession[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);
  
  // 分隔条拖动状态
  const [agentWidth, setAgentWidth] = useState(400); // 右侧面板宽度
  const isResizing = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(0);

  // 查询报告详情
  const { data: report, isLoading, refetch: refetchReport } = useQuery({
    queryKey: ['report', reportId],
    queryFn: () => getReport(reportId!),
    enabled: !!reportId,
  });
  
  // 转换 Markdown 为 HTML
  const reportHtml = useMarkdownToHtml(report?.markdown_content || '');
  
  // Agent 修改报告
  const modifyReportMutation = useMutation({
    mutationFn: async (userRequest: string) => {
      // 构建Query参数
      const params = new URLSearchParams({
        user_request: userRequest,
        ...(sessionId && { session_id: sessionId }),
      });
      
      const response = await fetch(`http://localhost:8000/api/reports/${reportId}/modify?${params}`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('修改失败');
      return response.json();
    },
    onSuccess: (data) => {
      message.success('修改成功!');
      setSessionId(data.session_id);
      
      setConversationHistory(prev => [
        ...prev,
        {
          turn_number: prev.length + 1,
          user_request: userInput,
          system_response: data.explanation,
          timestamp: new Date().toISOString(),
          operations: data.operations_summary || [],
        },
      ]);
      
      setUserInput('');
      refetchReport();
    },
    onError: (error: any) => {
      message.error(`修改失败: ${error.message}`);
    },
  });

  const handleDownload = async () => {
    if (reportId) {
      await downloadReport(reportId);
    }
  };
  
  const handleSendRequest = () => {
    if (!userInput.trim()) {
      message.warning('请输入修改请求');
      return;
    }
    modifyReportMutation.mutate(userInput);
  };
  
  const handleNewSession = () => {
    if (sessionId && conversationHistory.length > 0) {
      const newHistorySession: HistorySession = {
        session_id: sessionId,
        report_id: reportId!,
        created_at: conversationHistory[0].timestamp,
        last_activity_at: conversationHistory[conversationHistory.length - 1].timestamp,
        turn_count: conversationHistory.length,
        preview: conversationHistory[0].user_request.substring(0, 50) + '...',
      };
      setHistorySessions(prev => [newHistorySession, ...prev]);
    }
    
    setSessionId(null);
    setConversationHistory([]);
    message.success('已创建新会话');
  };
  
  const handleSwitchSession = async (session: HistorySession) => {
    // 保存当前会话（如果存在）
    if (sessionId && conversationHistory.length > 0) {
      const currentSession: HistorySession = {
        session_id: sessionId,
        report_id: reportId!,
        created_at: conversationHistory[0].timestamp,
        last_activity_at: conversationHistory[conversationHistory.length - 1].timestamp,
        turn_count: conversationHistory.length,
        preview: conversationHistory[0].user_request.substring(0, 50) + '...',
      };
      setHistorySessions(prev => {
        const filtered = prev.filter(s => s.session_id !== sessionId);
        return [currentSession, ...filtered];
      });
    }
    
    // 切换到新会话
    setSessionId(session.session_id);
    setHistoryPopoverOpen(false);
    
    // 从后端加载对话历史
    setLoadingHistory(true);
    try {
      const history = await getConversationHistory(reportId!, session.session_id);
      
      console.log('切换会话 - 加载的历史:', history);
      console.log('切换会话 - 对话轮数:', history.turns?.length || 0);
      
      // 将后端返回的数据转换为前端格式
      const turns: ConversationTurn[] = history.turns.map(turn => {
        console.log('切换会话 - 处理对话轮次:', turn);
        return {
          turn_number: turn.turn_number,
          user_request: turn.user_request,
          system_response: turn.system_response,
          timestamp: turn.timestamp,
          operations: Array.isArray(turn.operations)
            ? turn.operations.map((op: any) => 
                op.details?.variable_name || op.operation_type || 'Unknown'
              )
            : [],
        };
      });
      
      console.log('切换会话 - 转换后的对话:', turns);
      
      setConversationHistory(turns);
      message.success(`已切换到历史会话，加载了 ${turns.length} 条对话`);
    } catch (error: any) {
      console.error('加载对话历史失败:', error);
      console.error('错误详情:', error.response?.data || error.message);
      message.error(`加载对话历史失败: ${error.message || '未知错误'}`);
      setConversationHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  };
  
  const handleCloseAgent = () => {
    setAgentOpen(false);
  };
  
  // 分隔条拖动处理
  const handleMouseDown = (e: React.MouseEvent) => {
    isResizing.current = true;
    startX.current = e.clientX;
    startWidth.current = agentWidth;
    e.preventDefault();
  };
  
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing.current) return;
      
      const delta = startX.current - e.clientX;
      const newWidth = Math.max(300, Math.min(800, startWidth.current + delta));
      setAgentWidth(newWidth);
    };
    
    const handleMouseUp = () => {
      isResizing.current = false;
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);
  
  // 当 Agent 面板打开时，自动加载会话列表和最新的会话历史
  useEffect(() => {
    const loadSessionData = async () => {
      // 只在首次打开且没有会话时加载
      if (!agentOpen || sessionId || conversationHistory.length > 0) {
        return;
      }
      
      setLoadingHistory(true);
      try {
        // 并行加载会话列表和最新会话历史
        const [sessionsData, historyData] = await Promise.all([
          getConversationSessions(reportId!).catch(() => ({ sessions: [], total: 0 })),
          getConversationHistory(reportId!).catch(() => ({ 
            session_id: '', 
            turns: [], 
            report_id: reportId!, 
            context_summary: null, 
            current_version: 1 
          }))
        ]);
        
        console.log('加载的会话列表:', sessionsData);
        console.log('加载的最新会话历史:', historyData);
        
        // 设置会话列表（排除当前会话）
        const otherSessions: HistorySession[] = sessionsData.sessions
          .filter(s => s.session_id !== historyData.session_id)
          .map(s => ({
            session_id: s.session_id,
            report_id: s.report_id,
            created_at: s.created_at,
            last_activity_at: s.last_activity_at,
            turn_count: s.turn_count,
            preview: s.preview,
          }));
        
        setHistorySessions(otherSessions);
        console.log('设置历史会话列表:', otherSessions);
        
        // 设置当前会话的对话历史
        if (historyData.turns && historyData.turns.length > 0) {
          const turns: ConversationTurn[] = historyData.turns.map(turn => ({
            turn_number: turn.turn_number,
            user_request: turn.user_request,
            system_response: turn.system_response,
            timestamp: turn.timestamp,
            operations: Array.isArray(turn.operations) 
              ? turn.operations.map((op: any) => 
                  op.details?.variable_name || op.operation_type || 'Unknown'
                )
              : [],
          }));
          
          setSessionId(historyData.session_id);
          setConversationHistory(turns);
          console.log('设置当前会话对话:', turns);
          message.info(`已加载最新会话，共 ${turns.length} 条对话，${otherSessions.length} 个历史会话`);
        } else {
          console.log('没有对话历史');
        }
      } catch (error: any) {
        console.log('加载会话数据失败:', error);
        console.error('错误详情:', error.response?.data || error.message);
      } finally {
        setLoadingHistory(false);
      }
    };
    
    if (agentOpen && reportId) {
      loadSessionData();
    }
  }, [agentOpen, reportId]);

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
    <div style={{ display: 'flex', height: 'calc(100vh - 64px)', overflow: 'hidden' }}>
      {/* 左侧:报告预览区域 */}
      <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
        {/* 操作栏 */}
        <div style={{ padding: '16px', borderBottom: '1px solid #f0f0f0', background: '#fff' }}>
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
            {!agentOpen && (
              <Button
                icon={<RobotOutlined />}
                onClick={() => setAgentOpen(true)}
                style={{
                  background: 'linear-gradient(78deg, #8054f2 7%, #3895da 95%)',
                  color: '#fff',
                  border: 'none',
                }}
              >
                ✨ AI Copilot
              </Button>
            )}
          </Space>
        </div>

        {/* 报告内容区域 */}
        <div style={{ flex: 1, padding: 16, background: '#f5f5f5' }}>
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
            <div dangerouslySetInnerHTML={{ __html: reportHtml }} />
          </div>
        </div>
      </Card>
        </div>
      </div>
      
      {/* 右侧:Agent 对话助手 */}
      {agentOpen && (
        <>
          {/* 可拖动的分隔条 */}
          <div
            onMouseDown={handleMouseDown}
            style={{
              width: 4,
              height: '100%',
              cursor: 'col-resize',
              background: isResizing.current ? '#1890ff' : 'transparent',
              position: 'relative',
              transition: isResizing.current ? 'none' : 'background 0.2s',
              flexShrink: 0,
            }}
            onMouseEnter={(e) => {
              if (!isResizing.current) {
                e.currentTarget.style.background = '#e6e6e6';
              }
            }}
            onMouseLeave={(e) => {
              if (!isResizing.current) {
                e.currentTarget.style.background = 'transparent';
              }
            }}
          >
            {/* 视觉指示线 */}
            <div style={{
              position: 'absolute',
              left: '50%',
              top: '50%',
              transform: 'translate(-50%, -50%)',
              width: 2,
              height: 40,
              background: '#d9d9d9',
              borderRadius: 1,
            }} />
          </div>
          
          <div style={{
            width: agentWidth,
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            borderLeft: '1px solid #f0f0f0',
            background: '#fff',
            flexShrink: 0,
          }}>
          {/* Agent 标题栏 */}
          <div style={{
            height: 52,
            padding: '0 12px',
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <Space>
              <RobotOutlined style={{ fontSize: 18, color: '#1890ff' }} />
              <span style={{ fontSize: 16, fontWeight: 600 }}>✨ AI Copilot</span>
              {sessionId && (
                <Tag color="blue" style={{ fontSize: 11 }}>会话中</Tag>
              )}
            </Space>
            <Space size={0}>
              <Tooltip title="新建会话">
                <Button
                  type="text"
                  size="small"
                  icon={<PlusOutlined style={{ fontSize: 16 }} />}
                  onClick={handleNewSession}
                />
              </Tooltip>
              <Popover
                placement="bottomRight"
                open={historyPopoverOpen}
                onOpenChange={setHistoryPopoverOpen}
                trigger="click"
                content={
                  <div style={{ width: 300, maxHeight: 400, overflow: 'auto' }}>
                    {historySessions.length === 0 ? (
                      <div style={{ textAlign: 'center', padding: '40px 20px', color: '#999' }}>
                        <MessageOutlined style={{ fontSize: 32, marginBottom: 12, color: '#d9d9d9' }} />
                        <p style={{ margin: 0 }}>暂无历史会话</p>
                      </div>
                    ) : (
                      <List
                        size="small"
                        dataSource={historySessions}
                        renderItem={(session) => (
                          <List.Item
                            onClick={() => handleSwitchSession(session)}
                            style={{
                              cursor: 'pointer',
                              padding: '8px 12px',
                              background: session.session_id === sessionId ? '#e6f7ff' : 'transparent',
                              borderRadius: 4,
                            }}
                          >
                            <List.Item.Meta
                              title={
                                <div style={{ fontSize: 13, marginBottom: 4 }}>
                                  {session.session_id === sessionId && '[current] '}
                                  {session.preview}
                                </div>
                              }
                              description={
                                <div style={{ fontSize: 11, color: '#999' }}>
                                  {session.turn_count} 轮对话 • {dayjs(session.last_activity_at).format('MM-DD HH:mm')}
                                </div>
                              }
                            />
                          </List.Item>
                        )}
                      />
                    )}
                  </div>
                }
              >
                <Tooltip title="历史会话">
                  <Button
                    type="text"
                    size="small"
                    icon={<MessageOutlined style={{ fontSize: 16 }} />}
                  />
                </Tooltip>
              </Popover>
              <Tooltip title="关闭">
                <Button
                  type="text"
                  size="small"
                  icon={<CloseOutlined style={{ fontSize: 16 }} />}
                  onClick={handleCloseAgent}
                />
              </Tooltip>
            </Space>
          </div>
          {/* Agent 对话内容 */}
          <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0, overflow: 'hidden' }}>
          {/* 对话历史区域 */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '16px 16px 0 16px' }}>
            {loadingHistory ? (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: '#999' }}>
                <LoadingOutlined style={{ fontSize: 48, marginBottom: 16, color: '#1890ff' }} />
                <p style={{ margin: 0, fontSize: 14 }}>正在加载对话历史...</p>
              </div>
            ) : conversationHistory.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '60px 20px', color: '#999' }}>
                <RobotOutlined style={{ fontSize: 48, marginBottom: 16, color: '#d9d9d9' }} />
                <p style={{ margin: 0, fontSize: 14 }}>还没有对话记录</p>
                <p style={{ margin: '8px 0 0 0', fontSize: 12, color: '#bfbfbf' }}>在下方输入框中告诉 AI 你想如何修改报告</p>
              </div>
            ) : (
              <Timeline
                items={conversationHistory.map((turn) => ({
                  key: turn.turn_number,
                  dot: <HistoryOutlined style={{ fontSize: 16 }} />,
                  children: (
                    <div style={{ marginBottom: 24 }}>
                      <div style={{ marginBottom: 12 }}>
                        <div style={{
                          background: '#e6f7ff',
                          padding: '8px 12px',
                          borderRadius: 8,
                          marginBottom: 4,
                        }}>
                          <strong style={{ color: '#1890ff' }}>👤 你:</strong>
                          <div style={{ marginTop: 4 }}>{turn.user_request}</div>
                        </div>
                        <div style={{ fontSize: 11, color: '#999', marginLeft: 4 }}>
                          {dayjs(turn.timestamp).format('HH:mm:ss')}
                        </div>
                      </div>
                      
                      <div>
                        <div style={{
                          background: '#f6ffed',
                          padding: '8px 12px',
                          borderRadius: 8,
                          marginBottom: 4,
                        }}>
                          <strong style={{ color: '#52c41a' }}>🤖 Agent:</strong>
                          <AgentResponseRenderer response={turn.system_response} />
                          
                          {turn.operations && turn.operations.length > 0 && (
                            <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px dashed #d9f7be' }}>
                              <div style={{ fontSize: 12, color: '#52c41a', marginBottom: 4 }}>
                                <CheckCircleOutlined /> 执行的操作:
                              </div>
                              {turn.operations.map((op, idx) => (
                                <div key={idx} style={{ fontSize: 12, color: '#666', marginLeft: 16 }}>
                                  • {op}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ),
                }))}
              />
            )}
            
            {modifyReportMutation.isPending && (
              <div style={{
                background: '#f0f0f0',
                padding: '12px',
                borderRadius: 8,
                textAlign: 'center',
              }}>
                <LoadingOutlined style={{ marginRight: 8 }} />
                Agent 正在处理你的请求...
              </div>
            )}
          </div>
          
          <Divider style={{ margin: 0 }} />
          
          {/* 输入区域 */}
          <div style={{ padding: 12, flexShrink: 0 }}>
            {/* 建议操作按钮组 */}
            {conversationHistory.length === 0 && (
              <div style={{ marginBottom: 12, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                <Button
                  size="small"
                  type="default"
                  onClick={() => setUserInput('修改参数: 把 wgid 改成 ZQGY0175')}
                  style={{
                    borderRadius: 16,
                    fontSize: 12,
                    height: 28,
                    padding: '0 12px',
                    border: '1px solid #d9d9d9',
                    background: '#fff',
                  }}
                >
                  修改参数
                </Button>
                <Button
                  size="small"
                  type="default"
                  onClick={() => setUserInput('优化内容: 让分析部分更详细')}
                  style={{
                    borderRadius: 16,
                    fontSize: 12,
                    height: 28,
                    padding: '0 12px',
                    border: '1px solid #d9d9d9',
                    background: '#fff',
                  }}
                >
                  优化内容
                </Button>
                <Button
                  size="small"
                  type="default"
                  onClick={() => setUserInput('添加章节: 添加竞争对手分析章节')}
                  style={{
                    borderRadius: 16,
                    fontSize: 12,
                    height: 28,
                    padding: '0 12px',
                    border: '1px solid #d9d9d9',
                    background: '#fff',
                  }}
                >
                  添加竞争对手分析章节
                </Button>
              </div>
            )}
            
            <div style={{ marginBottom: 8, position: 'relative' }}>
              <Input.TextArea
                value={userInput}
                onChange={(e) => setUserInput(e.target.value)}
                placeholder="告诉 AI Copilot 你想如何修改报告...\n例如: 修改参数: 把 wgid 改成 ZQGY0175"
                autoSize={{ minRows: 3, maxRows: 6 }}
                onPressEnter={(e) => {
                  if (e.ctrlKey || e.metaKey) {
                    handleSendRequest();
                  }
                }}
                style={{ resize: 'none', paddingRight: 40 }}
              />
              <Button
                type="primary"
                shape="circle"
                icon={<ArrowUpOutlined />}
                onClick={handleSendRequest}
                loading={modifyReportMutation.isPending}
                disabled={!userInput.trim()}
                size="large"
                style={{
                  position: 'absolute',
                  right: 8,
                  bottom: 8,
                }}
              />
            </div>
          </div>
          </div>
        </div>
        </>
      )}
    </div>
  );
};

// Agent 响应渲染组件（使用 memo 优化性能）
const AgentResponseRenderer = React.memo(({ response }: { response: string }) => {
  const html = useMarkdownToHtml(response);
  
  return (
    <div 
      className="markdown-body"
      style={{ 
        marginTop: 4,
        maxHeight: '400px',
        overflowY: 'auto',
        padding: '8px',
        background: 'white',
        borderRadius: 4,
      }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
});

AgentResponseRenderer.displayName = 'AgentResponseRenderer';

export default ReportPreview;

