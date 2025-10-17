#!/usr/bin/env node

/**
 * 前端P0核心模块端到端测试
 * 
 * 测试前确保：
 * 1. 后端服务运行在 http://localhost:8000
 * 2. 前端服务运行在 http://localhost:5173
 */

import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';
const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 测试结果统计
const results = {
  total: 0,
  passed: 0,
  failed: 0,
  tests: []
};

// 测试辅助函数
function test(name, fn) {
  return async () => {
    results.total++;
    try {
      await fn();
      results.passed++;
      results.tests.push({ name, status: 'PASS' });
      console.log(`✅ PASS: ${name}`);
      return true;
    } catch (error) {
      results.failed++;
      results.tests.push({ name, status: 'FAIL', error: error.message });
      console.log(`❌ FAIL: ${name}`);
      console.log(`   错误: ${error.message}`);
      return false;
    }
  };
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message || 'Assertion failed');
  }
}

// 延迟函数
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// ========== 测试用例 ==========

// 1. 健康检查
const testHealthCheck = test('1. 后端健康检查', async () => {
  const response = await client.get('/health');
  assert(response.status === 200, '健康检查失败');
  assert(response.data.status === 'healthy', '健康状态不正确');
});

// 2. AI配置测试
const testAIConfig = test('2. AI配置查询', async () => {
  const response = await client.get('/api/config/ai');
  assert(response.status === 200, 'AI配置查询失败');
  assert(typeof response.data.configured === 'boolean', '配置状态格式不正确');
});

// 3. 创建模板
let createdTemplateId = null;

const testCreateTemplate = test('3. 创建模板', async () => {
  const templateData = {
    name: 'E2E测试模板',
    description: '用于端到端测试的模板',
    template_content: '# {{title}}\n\n生成时间: {{generation_time}}\n\n{{content}}',
    metadata: {
      title: {
        type: 'string',
        source: 'user_input',
        required: true,
        description: '报告标题',
        ui_config: {
          input_type: 'text',
          placeholder: '请输入标题'
        }
      },
      content: {
        type: 'string',
        source: 'user_input',
        required: true,
        description: '报告内容',
        ui_config: {
          input_type: 'textarea',
          placeholder: '请输入内容'
        }
      },
      generation_time: {
        type: 'string',
        source: 'system',
        required: true,
        description: '生成时间',
        system_config: {
          fields: {
            timestamp: {
              generator: 'datetime',
              format: '%Y-%m-%d %H:%M:%S'
            }
          }
        }
      }
    }
  };

  const response = await client.post('/api/templates', templateData);
  assert(response.status === 200 || response.status === 201, '创建模板失败');
  assert(response.data.id, '模板ID不存在');
  assert(response.data.name === templateData.name, '模板名称不匹配');
  
  createdTemplateId = response.data.id;
  console.log(`   创建的模板ID: ${createdTemplateId}`);
});

// 4. 获取模板列表
const testGetTemplates = test('4. 获取模板列表', async () => {
  const response = await client.get('/api/templates');
  assert(response.status === 200, '获取模板列表失败');
  assert(Array.isArray(response.data.items), '模板列表格式不正确');
  assert(typeof response.data.total === 'number', '总数格式不正确');
  assert(response.data.items.length > 0, '模板列表为空');
  
  console.log(`   模板总数: ${response.data.total}`);
});

// 5. 获取模板详情
const testGetTemplate = test('5. 获取模板详情', async () => {
  assert(createdTemplateId, '没有可用的模板ID');
  
  const response = await client.get(`/api/templates/${createdTemplateId}`);
  assert(response.status === 200, '获取模板详情失败');
  assert(response.data.id === createdTemplateId, '模板ID不匹配');
  assert(response.data.template_content, '模板内容不存在');
  assert(response.data.metadata_json, '元数据不存在');
});

// 6. 更新模板
const testUpdateTemplate = test('6. 更新模板', async () => {
  assert(createdTemplateId, '没有可用的模板ID');
  
  const updateData = {
    description: 'E2E测试模板（已更新）'
  };
  
  const response = await client.put(`/api/templates/${createdTemplateId}`, updateData);
  assert(response.status === 200, '更新模板失败');
  assert(response.data.description === updateData.description, '描述未更新');
  
  console.log(`   更新后的描述: ${response.data.description}`);
});

// 7. 生成报告
let generatedTaskId = null;
let generatedReportId = null;

const testGenerateReport = test('7. 启动报告生成', async () => {
  assert(createdTemplateId, '没有可用的模板ID');
  
  const generateRequest = {
    template_id: createdTemplateId,
    inputs: {
      title: 'E2E测试报告',
      content: '这是一个自动化测试生成的报告内容。\n\n测试时间: ' + new Date().toISOString()
    }
  };
  
  const response = await client.post('/api/reports/generate', generateRequest);
  assert(response.status === 202, '启动报告生成失败');
  assert(response.data.task_id, '任务ID不存在');
  assert(response.data.status === 'pending', '任务状态不正确');
  
  generatedTaskId = response.data.task_id;
  console.log(`   任务ID: ${generatedTaskId}`);
});

// 8. 查询任务状态
const testGetTaskStatus = test('8. 查询任务状态', async () => {
  assert(generatedTaskId, '没有可用的任务ID');
  
  // 等待任务完成（最多30秒）
  let completed = false;
  let attempts = 0;
  const maxAttempts = 30;
  
  while (!completed && attempts < maxAttempts) {
    await sleep(1000);
    attempts++;
    
    const response = await client.get(`/api/reports/tasks/${generatedTaskId}/status`);
    assert(response.status === 200, '查询任务状态失败');
    assert(response.data.task_id === generatedTaskId, '任务ID不匹配');
    
    console.log(`   第${attempts}次查询 - 状态: ${response.data.status}, 变量数: ${response.data.variables.length}`);
    
    if (response.data.status === 'success') {
      completed = true;
      generatedReportId = response.data.report_id;
      console.log(`   报告生成成功! 报告ID: ${generatedReportId}`);
    } else if (response.data.status === 'failed') {
      throw new Error('任务执行失败');
    }
  }
  
  assert(completed, '任务未在规定时间内完成');
  assert(generatedReportId, '报告ID不存在');
});

// 9. 获取报告详情
const testGetReport = test('9. 获取报告详情', async () => {
  assert(generatedReportId, '没有可用的报告ID');
  
  const response = await client.get(`/api/reports/${generatedReportId}`);
  assert(response.status === 200, '获取报告详情失败');
  assert(response.data.id === generatedReportId, '报告ID不匹配');
  assert(response.data.status === 'success', '报告状态不正确');
  assert(response.data.markdown_content, 'Markdown内容不存在');
  assert(response.data.markdown_content.includes('E2E测试报告'), '报告内容不正确');
  
  console.log(`   报告标题: ${response.data.title}`);
  console.log(`   内容长度: ${response.data.markdown_content.length} 字符`);
  console.log(`   耗时: ${response.data.duration_ms}ms`);
});

// 10. 下载报告
const testDownloadReport = test('10. 下载报告', async () => {
  assert(generatedReportId, '没有可用的报告ID');
  
  const response = await client.get(`/api/reports/${generatedReportId}/download`, {
    responseType: 'blob'
  });
  
  assert(response.status === 200, '下载报告失败');
  assert(response.headers['content-type'].includes('markdown'), '内容类型不正确');
  assert(response.data, '报告内容为空');
  
  console.log(`   文件大小: ${response.data.size || response.data.length} 字节`);
});

// 11. 删除模板（清理）
const testDeleteTemplate = test('11. 删除测试模板', async () => {
  assert(createdTemplateId, '没有可用的模板ID');
  
  const response = await client.delete(`/api/templates/${createdTemplateId}`);
  assert(response.status === 200 || response.status === 204, '删除模板失败');
  
  console.log(`   已删除模板: ${createdTemplateId}`);
});

// ========== 运行测试 ==========

async function runTests() {
  console.log('\n========================================');
  console.log('🚀 开始运行前端P0核心模块端到端测试');
  console.log('========================================\n');
  
  const tests = [
    testHealthCheck,
    testAIConfig,
    testCreateTemplate,
    testGetTemplates,
    testGetTemplate,
    testUpdateTemplate,
    testGenerateReport,
    testGetTaskStatus,
    testGetReport,
    testDownloadReport,
    testDeleteTemplate,
  ];
  
  for (const testFn of tests) {
    await testFn();
  }
  
  console.log('\n========================================');
  console.log('📊 测试结果统计');
  console.log('========================================\n');
  console.log(`总测试数: ${results.total}`);
  console.log(`✅ 通过: ${results.passed}`);
  console.log(`❌ 失败: ${results.failed}`);
  console.log(`成功率: ${((results.passed / results.total) * 100).toFixed(2)}%`);
  console.log('\n');
  
  if (results.failed > 0) {
    console.log('失败的测试:');
    results.tests
      .filter(t => t.status === 'FAIL')
      .forEach(t => {
        console.log(`  - ${t.name}`);
        console.log(`    ${t.error}`);
      });
    process.exit(1);
  } else {
    console.log('🎉 所有测试通过！\n');
    process.exit(0);
  }
}

// 运行测试
runTests().catch(error => {
  console.error('\n❌ 测试运行失败:', error);
  process.exit(1);
});

