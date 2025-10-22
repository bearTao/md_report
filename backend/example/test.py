"""ImageExecutor使用示例"""

import asyncio
from app.executors.image import ImageExecutor
from app.core.models import VariableMetadata, ImageConfig, VariableSource
from app.services.context import ExecutionContext


async def example_1_fetch_single_image():
    """示例1：获取单张图片 (base64格式)"""
    print("\n" + "="*60)
    print("示例1：获取单张图片（base64格式）")
    print("="*60)
    
    # 1. 创建变量元数据
    metadata = VariableMetadata(
        type="image",
        source=VariableSource.IMAGE,
        description="测试图片",
        image_config=ImageConfig(
            endpoint="https://picsum.photos/400/300",  # 随机图片API
            output_format="base64"
        )
    )
    
    # 2. 创建执行上下文
    context = ExecutionContext(
        task_id="test_task_001",
        template_id="test_template",
        user_inputs={},
        metadata={"test_image": metadata}
    )
    
    # 3. 创建执行器并执行
    executor = ImageExecutor("test_image", metadata, context)
    
    try:
        exec_result = await executor.execute()
        
        if exec_result.status != "success":
            print(f"❌ 执行失败: {exec_result.error}")
            return
        
        result = exec_result.value
        
        print(f"✅ 获取成功!")
        print(f"   执行耗时: {exec_result.duration_ms}ms")
        print(f"   URL: {result['url']}")
        print(f"   MIME类型: {result['mime_type']}")
        print(f"   大小: {result['size']} bytes")
        print(f"   Base64数据长度: {len(result['data'])} 字符")
        print(f"   Base64数据: {result['data']}")
        print("***"*50)
        print(f"   Markdown: {result['markdown']}")
        
        # 保存到context
        print(f"\n✅ 变量已保存到上下文")
        print(f"   context.get_variable('test_image'): {context.get_variable('test_image') is not None}")
        
    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")


async def example_2_fetch_image_as_url():
    """示例2：获取图片URL格式"""
    print("\n" + "="*60)
    print("示例2：获取图片（URL格式）")
    print("="*60)
    
    metadata = VariableMetadata(
        type="image",
        source=VariableSource.IMAGE,
        description="Logo图片",
        image_config=ImageConfig(
            endpoint="https://picsum.photos/200/200",
            output_format="url"
        )
    )
    
    context = ExecutionContext(
        task_id="test_task_002",
        template_id="test_template",
        user_inputs={},
        metadata={"logo": metadata}
    )
    
    executor = ImageExecutor("logo", metadata, context)
    
    try:
        exec_result = await executor.execute()
        
        if exec_result.status != "success":
            print(f"❌ 执行失败: {exec_result.error}")
            return
        
        result = exec_result.value
        
        print(f"✅ 获取成功!")
        print(f"   执行耗时: {exec_result.duration_ms}ms")
        print(f"   原始URL: {result['url']}")
        print(f"   数据: {result['data']}")
        print(f"   MIME类型: {result['mime_type']}")
        print(f"   大小: {result['size']} bytes")
        print(f"   Markdown: {result['markdown']}")
        
    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")


async def example_3_fetch_with_headers():
    """示例3：带认证头的图片获取"""
    print("\n" + "="*60)
    print("示例3：带认证头的图片获取")
    print("="*60)
    
    metadata = VariableMetadata(
        type="image",
        source=VariableSource.IMAGE,
        description="需要认证的图片",
        image_config=ImageConfig(
            endpoint="https://picsum.photos/300/300",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "image/*"
            },
            output_format="url"
        )
    )
    
    context = ExecutionContext(
        task_id="test_task_003",
        template_id="test_template",
        user_inputs={},
        metadata={"secure_image": metadata}
    )
    
    executor = ImageExecutor("secure_image", metadata, context)
    
    try:
        exec_result = await executor.execute()
        
        if exec_result.status != "success":
            print(f"❌ 执行失败: {exec_result.error}")
            return
        
        result = exec_result.value
        
        print(f"✅ 获取成功!")
        print(f"   执行耗时: {exec_result.duration_ms}ms")
        print(f"   URL: {result['url']}")
        print(f"   大小: {result['size']} bytes")
        
    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")


async def example_4_fetch_multiple_images():
    """示例4：获取多张图片"""
    print("\n" + "="*60)
    print("示例4：获取多张图片")
    print("="*60)
    
    # 先设置图片URL列表
    image_urls = [
        "https://picsum.photos/200/200?random=1",
        "https://picsum.photos/200/200?random=2",
        "https://picsum.photos/200/200?random=3"
    ]
    
    metadata = VariableMetadata(
        type="array",
        source=VariableSource.IMAGE,
        description="多张图片",
        image_config=ImageConfig(
            endpoint="{{image_urls}}",
            multiple=True,
            output_format="url"
        )
    )
    
    context = ExecutionContext(
        task_id="test_task_004",
        template_id="test_template",
        user_inputs={},
        metadata={"gallery": metadata}
    )
    
    # 先设置图片URLs到上下文
    context.set_variable("image_urls", image_urls)
    
    executor = ImageExecutor("gallery", metadata, context)
    
    try:
        exec_result = await executor.execute()
        
        if exec_result.status != "success":
            print(f"❌ 执行失败: {exec_result.error}")
            return
        
        result = exec_result.value
        
        print(f"✅ 获取成功! 共 {len(result)} 张图片")
        print(f"   执行耗时: {exec_result.duration_ms}ms")
        for i, img in enumerate(result, 1):
            if img.get('error'):
                print(f"   图片 {i}: ❌ {img['error']}")
            else:
                print(f"   图片 {i}: ✅ {img['url']} ({img['size']} bytes)")
        
    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")


async def example_5_with_variable_interpolation():
    """示例5：使用变量插值"""
    print("\n" + "="*60)
    print("示例5：使用变量插值动态构建URL")
    print("="*60)
    
    metadata = VariableMetadata(
        type="image",
        source=VariableSource.IMAGE,
        description="动态尺寸图片",
        image_config=ImageConfig(
            endpoint="https://picsum.photos/{{width}}/{{height}}",
            output_format="url"
        )
    )
    
    context = ExecutionContext(
        task_id="test_task_005",
        template_id="test_template",
        user_inputs={},
        metadata={"dynamic_image": metadata}
    )
    
    # 设置变量
    context.set_variable("width", 500)
    context.set_variable("height", 300)
    
    executor = ImageExecutor("dynamic_image", metadata, context)
    
    try:
        exec_result = await executor.execute()
        
        if exec_result.status != "success":
            print(f"❌ 执行失败: {exec_result.error}")
            return
        
        result = exec_result.value
        
        print(f"✅ 获取成功!")
        print(f"   执行耗时: {exec_result.duration_ms}ms")
        print(f"   URL: {result['url']}")
        print(f"   期望尺寸: 500x300")
        print(f"   大小: {result['size']} bytes")
        
    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")


async def example_6_error_handling():
    """示例6：错误处理"""
    print("\n" + "="*60)
    print("示例6：错误处理 - 无效的URL")
    print("="*60)
    
    metadata = VariableMetadata(
        type="image",
        source=VariableSource.IMAGE,
        description="无效图片",
        image_config=ImageConfig(
            endpoint="https://invalid-url-that-does-not-exist.com/image.png",
            output_format="url"
        )
    )
    
    context = ExecutionContext(
        task_id="test_task_006",
        template_id="test_template",
        user_inputs={},
        metadata={"bad_image": metadata}
    )
    
    executor = ImageExecutor("bad_image", metadata, context)
    
    try:
        exec_result = await executor.execute()
        
        if exec_result.status != "success":
            print(f"✅ 正确捕获了错误!")
            print(f"   执行状态: {exec_result.status}")
            print(f"   错误信息: {exec_result.error}")
            print(f"   执行耗时: {exec_result.duration_ms}ms")
        else:
            print(f"   结果: {exec_result.value}")
        
    except Exception as e:
        print(f"✅ 正确捕获了异常!")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   错误信息: {str(e)}")


async def main():
    """运行所有示例"""
    print("\n" + "#"*60)
    print("# ImageExecutor 使用示例")
    print("#"*60)
    
    # 运行所有示例
    await example_1_fetch_single_image()
    await example_2_fetch_image_as_url()
    await example_3_fetch_with_headers()
    await example_4_fetch_multiple_images()
    await example_5_with_variable_interpolation()
    await example_6_error_handling()
    
    print("\n" + "#"*60)
    print("# 所有示例运行完成!")
    print("#"*60 + "\n")


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())