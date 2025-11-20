"""
查询和通用对话功能演示

演示如何使用新添加的查询和通用对话功能。
"""
import asyncio
from datetime import datetime

from app.schemas.modification_schemas import (
    ModificationIntent,
    IntentType,
    ConversationMemory,
    ReportState,
    VariableInfo,
    VariableType,
    OperationStep,
    OperationType
)
from app.services.agent.operation_planner import OperationPlanner


def create_sample_memory() -> ConversationMemory:
    """创建示例对话记忆"""
    return ConversationMemory(
        session_id="demo_session",
        report_id="demo_report_001",
        report_state=ReportState(
            report_id="demo_report_001",
            template_id="demo_template",
            variables={
                "time_range": VariableInfo(
                    name="time_range",
                    value="最近一个月",
                    source="user_input",
                    variable_type=VariableType.TEMPLATE,
                    metadata={}
                ),
                "wgid": VariableInfo(
                    name="wgid",
                    value="ZQGY0175",
                    source="user_input",
                    variable_type=VariableType.TEMPLATE,
                    metadata={}
                ),
                "summary": VariableInfo(
                    name="summary",
                    value="这是一份关于ZQGY0175的综合分析报告，涵盖了最近一个月的数据...",
                    source="ai_generation",
                    variable_type=VariableType.TEMPLATE,
                    metadata={
                        "prompt": "生成报告摘要",
                        "model": "gpt-4"
                    }
                )
            },
            markdown_content="""# 综合分析报告

## 1. 概述

这是一份关于ZQGY0175的综合分析报告。

## 2. 数据分析

### 2.1 时间范围
最近一个月

### 2.2 关键指标
- 指标1: 100
- 指标2: 200
- 指标3: 300

## 3. 结论

报告结论内容...
"""
        )
    )


def demo_query_intents():
    """演示查询意图"""
    print("=" * 60)
    print("查询意图演示")
    print("=" * 60)
    
    planner = OperationPlanner()
    memory = create_sample_memory()
    
    # 1. 显示报告内容
    print("\n1️⃣  查询: 显示报告内容")
    intent = ModificationIntent(
        intent_type=IntentType.QUERY,
        query_type="show_content",
        confidence=1.0
    )
    steps = planner.create_plan([intent], memory)
    print(f"   意图类型: {intent.intent_type}")
    print(f"   查询类型: {intent.query_type}")
    print(f"   操作步骤: {steps[0].description}")
    
    # 2. 列出所有变量
    print("\n2️⃣  查询: 列出所有变量")
    intent = ModificationIntent(
        intent_type=IntentType.QUERY,
        query_type="list_variables",
        confidence=1.0
    )
    steps = planner.create_plan([intent], memory)
    print(f"   意图类型: {intent.intent_type}")
    print(f"   查询类型: {intent.query_type}")
    print(f"   操作步骤: {steps[0].description}")
    
    # 3. 显示参数列表
    print("\n3️⃣  查询: 显示参数列表")
    intent = ModificationIntent(
        intent_type=IntentType.QUERY,
        query_type="show_parameters",
        confidence=1.0
    )
    steps = planner.create_plan([intent], memory)
    print(f"   意图类型: {intent.intent_type}")
    print(f"   查询类型: {intent.query_type}")
    print(f"   操作步骤: {steps[0].description}")
    
    # 4. 获取统计信息
    print("\n4️⃣  查询: 获取统计信息")
    intent = ModificationIntent(
        intent_type=IntentType.QUERY,
        query_type="get_statistics",
        confidence=1.0
    )
    steps = planner.create_plan([intent], memory)
    print(f"   意图类型: {intent.intent_type}")
    print(f"   查询类型: {intent.query_type}")
    print(f"   操作步骤: {steps[0].description}")
    
    # 5. 显示章节结构
    print("\n5️⃣  查询: 显示章节结构")
    intent = ModificationIntent(
        intent_type=IntentType.QUERY,
        query_type="show_sections",
        confidence=1.0
    )
    steps = planner.create_plan([intent], memory)
    print(f"   意图类型: {intent.intent_type}")
    print(f"   查询类型: {intent.query_type}")
    print(f"   操作步骤: {steps[0].description}")


def demo_conversation_intents():
    """演示通用对话意图"""
    print("\n" + "=" * 60)
    print("通用对话意图演示")
    print("=" * 60)
    
    planner = OperationPlanner()
    memory = create_sample_memory()
    
    # 1. 问候
    print("\n1️⃣  对话: 问候")
    intent = ModificationIntent(
        intent_type=IntentType.GENERAL_CONVERSATION,
        conversation_context="你好",
        query_details={"type": "greeting"},
        confidence=1.0
    )
    steps = planner.create_plan([intent], memory)
    print(f"   意图类型: {intent.intent_type}")
    print(f"   对话上下文: {intent.conversation_context}")
    print(f"   操作步骤: {steps[0].description}")
    
    # 2. 感谢
    print("\n2️⃣  对话: 感谢")
    intent = ModificationIntent(
        intent_type=IntentType.GENERAL_CONVERSATION,
        conversation_context="谢谢",
        query_details={"type": "thanks"},
        confidence=1.0
    )
    steps = planner.create_plan([intent], memory)
    print(f"   意图类型: {intent.intent_type}")
    print(f"   对话上下文: {intent.conversation_context}")
    print(f"   操作步骤: {steps[0].description}")
    
    # 3. 请求建议
    print("\n3️⃣  对话: 请求建议")
    intent = ModificationIntent(
        intent_type=IntentType.GENERAL_CONVERSATION,
        conversation_context="有什么建议吗",
        query_details={"type": "suggestion_request"},
        confidence=1.0
    )
    steps = planner.create_plan([intent], memory)
    print(f"   意图类型: {intent.intent_type}")
    print(f"   对话上下文: {intent.conversation_context}")
    print(f"   操作步骤: {steps[0].description}")


def demo_mixed_intents():
    """演示混合意图（修改 + 查询）"""
    print("\n" + "=" * 60)
    print("混合意图演示（修改 + 查询）")
    print("=" * 60)
    
    planner = OperationPlanner()
    memory = create_sample_memory()
    
    # 修改参数 + 查询参数
    print("\n📝 场景: 修改参数后查询参数列表")
    intents = [
        ModificationIntent(
            intent_type=IntentType.UPDATE_PARAMETER,
            target_variable="time_range",
            new_value="最近一周",
            confidence=0.9
        ),
        ModificationIntent(
            intent_type=IntentType.QUERY,
            query_type="show_parameters",
            confidence=0.85
        )
    ]
    
    steps = planner.create_plan(intents, memory)
    
    print(f"\n   识别到 {len(intents)} 个意图:")
    for i, intent in enumerate(intents, 1):
        print(f"   {i}. {intent.intent_type}")
    
    print(f"\n   生成 {len(steps)} 个执行步骤:")
    for i, step in enumerate(steps, 1):
        print(f"   {i}. {step.description}")


def demo_api_request_examples():
    """演示API请求示例"""
    print("\n" + "=" * 60)
    print("API 请求示例")
    print("=" * 60)
    
    examples = [
        {
            "name": "查询报告内容",
            "request": {
                "report_id": "report_123",
                "user_request": "输出当前报告内容",
                "session_id": "session_456"
            }
        },
        {
            "name": "查询统计信息",
            "request": {
                "report_id": "report_123",
                "user_request": "当前报告有多少字",
                "session_id": "session_456"
            }
        },
        {
            "name": "列出参数",
            "request": {
                "report_id": "report_123",
                "user_request": "显示所有参数",
                "session_id": "session_456"
            }
        },
        {
            "name": "问候",
            "request": {
                "report_id": "report_123",
                "user_request": "你好",
                "session_id": "session_456"
            }
        },
        {
            "name": "请求建议",
            "request": {
                "report_id": "report_123",
                "user_request": "有什么建议吗",
                "session_id": "session_456"
            }
        },
        {
            "name": "混合操作",
            "request": {
                "report_id": "report_123",
                "user_request": "将时间范围改为一周，然后显示所有参数",
                "session_id": "session_456"
            }
        }
    ]
    
    import json
    for i, example in enumerate(examples, 1):
        print(f"\n{i}️⃣  {example['name']}")
        print("   请求:")
        print("   " + json.dumps(example['request'], ensure_ascii=False, indent=6))


def main():
    """主函数"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "查询和通用对话功能演示" + " " * 24 + "║")
    print("╚" + "=" * 58 + "╝")
    
    # 演示查询意图
    demo_query_intents()
    
    # 演示对话意图
    demo_conversation_intents()
    
    # 演示混合意图
    demo_mixed_intents()
    
    # 演示API请求
    demo_api_request_examples()
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)
    print("\n📚 更多信息请参考: backend/docs/QUERY_AND_CONVERSATION_GUIDE.md")
    print("🧪 运行测试: pytest tests/agent/test_query_and_conversation.py -v")
    print()


if __name__ == "__main__":
    main()
