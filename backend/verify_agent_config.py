"""
验证Agent配置系统

运行此脚本验证配置是否正确加载。
"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from app.core.agent_config import get_config, get_llm_kwargs


def verify_config():
    """验证配置"""
    print("=" * 60)
    print("Agent配置验证")
    print("=" * 60)
    
    try:
        # 加载配置
        config = get_config()
        print("\n✓ 配置加载成功\n")
        
        # API配置
        print("【API配置】")
        print(f"  API Key: {'✓ 已配置' if config.api.api_key else '✗ 未配置'}")
        print(f"  API Base: {config.api.api_base or '默认'}")
        print(f"  Organization: {config.api.organization or '无'}")
        
        # 意图解析器配置
        print("\n【意图解析器】")
        print(f"  启用状态: {'✓ 已启用' if config.intent_parser.enabled else '✗ 已禁用'}")
        print(f"  模型: {config.intent_parser.llm.model}")
        print(f"  温度: {config.intent_parser.llm.temperature}")
        print(f"  超时: {config.intent_parser.llm.timeout}秒")
        print(f"  最大重试: {config.intent_parser.max_retries}次")
        
        # 响应生成器配置
        print("\n【响应生成器】")
        print(f"  使用LLM: {'✓ 是' if config.explanation_generator.use_llm else '✗ 否(模板模式)'}")
        print(f"  模型: {config.explanation_generator.llm.model}")
        print(f"  温度: {config.explanation_generator.llm.temperature}")
        print(f"  最大token: {config.explanation_generator.llm.max_tokens or '无限制'}")
        
        # AI内容优化配置
        print("\n【AI内容优化】")
        print(f"  Fallback: {'✓ 已启用' if config.ai_refinement.fallback_enabled else '✗ 已禁用'}")
        print(f"  模型: {config.ai_refinement.llm.model}")
        print(f"  温度: {config.ai_refinement.llm.temperature}")
        print(f"  超时: {config.ai_refinement.llm.timeout}秒")
        
        # 通用配置
        print("\n【通用配置】")
        print(f"  日志级别: {config.log_level}")
        print(f"  性能追踪: {'✓ 已启用' if config.enable_performance_tracking else '✗ 已禁用'}")
        
        # LLM参数获取测试
        print("\n【LLM参数测试】")
        components = ["intent_parser", "explanation_generator", "ai_refinement"]
        for component in components:
            try:
                kwargs = get_llm_kwargs(component)
                print(f"  {component}: ✓ 参数获取成功")
                print(f"    - model: {kwargs.get('model')}")
                print(f"    - temperature: {kwargs.get('temperature')}")
                print(f"    - api_key: {'✓ 已设置' if kwargs.get('api_key') else '✗ 未设置'}")
            except Exception as e:
                print(f"  {component}: ✗ 失败 - {e}")
        
        # 环境变量检查
        print("\n【环境变量】")
        env_vars = [
            "OPENAI_API_KEY",
            "OPENAI_API_BASE",
            "AGENT_CONFIG_PATH",
            "AGENT_LOG_LEVEL",
            "INTENT_PARSER_MODEL",
            "AI_REFINEMENT_MODEL"
        ]
        for var in env_vars:
            value = os.getenv(var)
            if value:
                # 隐藏API密钥
                if "KEY" in var:
                    value = f"{value[:8]}...{value[-4:]}" if len(value) > 12 else "***"
                print(f"  {var}: {value}")
            else:
                print(f"  {var}: 未设置")
        
        # 配置文件路径
        print("\n【配置文件】")
        config_paths = [
            Path("config/agent_config.yaml"),
            Path("config/agent_config.yml"),
        ]
        custom_path = os.getenv("AGENT_CONFIG_PATH")
        if custom_path:
            config_paths.insert(0, Path(custom_path))
        
        found = False
        for path in config_paths:
            if path.exists():
                print(f"  ✓ {path} (已找到)")
                found = True
                break
        
        if not found:
            print("  ✗ 未找到配置文件，使用默认配置")
        
        # 验证结果
        print("\n" + "=" * 60)
        if config.api.api_key:
            print("✓ 配置验证通过！Agent可以正常使用。")
        else:
            print("⚠ 警告：API密钥未配置，Agent将无法正常工作。")
            print("\n请通过以下方式之一设置API密钥：")
            print("  1. 环境变量: export OPENAI_API_KEY='your-key'")
            print("  2. 配置文件: 在 config/agent_config.yaml 中设置")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ 配置验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = verify_config()
    sys.exit(0 if success else 1)
