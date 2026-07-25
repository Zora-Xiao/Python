#!/usr/bin/env python3
"""
测试各平台登录流程配置是否正确
"""
import asyncio
from src.adapters.deepseek import DeepseekAdapter
from src.adapters.qwen import QwenAdapter
from src.adapters.doubao import DoubaoAdapter
from src.adapters.yuanbao import YuanbaoAdapter
from src.adapters.ernie import ErnieAdapter


async def test_platform_methods():
    """测试各平台方法存在性和行为"""
    
    print("=" * 60)
    print("测试各平台适配器方法存在性")
    print("=" * 60)
    
    # DeepSeek - 自动登录平台
    deepseek = DeepseekAdapter({'name': 'DeepSeek', 'username': 'test', 'password': 'test'})
    assert hasattr(deepseek, '_execute_login'), 'DeepSeek缺少_execute_login方法'
    assert hasattr(deepseek, '_load_cookies'), 'DeepSeek缺少_load_cookies方法'
    assert hasattr(deepseek, '_save_cookies'), 'DeepSeek缺少_save_cookies方法'
    print("✓ DeepSeek: 方法检查通过")
    
    # Qwen - 自动登录平台
    qwen = QwenAdapter({'name': 'Qwen', 'username': 'test', 'password': 'test'})
    assert hasattr(qwen, '_execute_login'), 'Qwen缺少_execute_login方法'
    assert hasattr(qwen, '_load_cookies'), 'Qwen缺少_load_cookies方法'
    assert hasattr(qwen, '_save_cookies'), 'Qwen缺少_save_cookies方法'
    print("✓ Qwen: 方法检查通过")
    
    # 豆包 - 手动登录平台
    doubao = DoubaoAdapter({'name': '豆包', 'username': 'test', 'password': 'test'})
    assert hasattr(doubao, '_execute_login'), '豆包缺少_execute_login方法'
    assert hasattr(doubao, '_load_cookies'), '豆包缺少_load_cookies方法'
    assert hasattr(doubao, '_save_cookies'), '豆包缺少_save_cookies方法'
    print("✓ 豆包: 方法检查通过")
    
    # 元宝 - 手动登录平台
    yuanbao = YuanbaoAdapter({'name': '元宝', 'username': 'test', 'password': 'test'})
    assert hasattr(yuanbao, '_execute_login'), '元宝缺少_execute_login方法'
    assert hasattr(yuanbao, '_load_cookies'), '元宝缺少_load_cookies方法'
    assert hasattr(yuanbao, '_save_cookies'), '元宝缺少_save_cookies方法'
    print("✓ 元宝: 方法检查通过")
    
    # 文心一言 - 手动登录平台
    ernie = ErnieAdapter({'name': '文心一言', 'username': 'test', 'password': 'test'})
    assert hasattr(ernie, '_execute_login'), '文心一言缺少_execute_login方法'
    assert hasattr(ernie, '_load_cookies'), '文心一言缺少_load_cookies方法'
    assert hasattr(ernie, '_save_cookies'), '文心一言缺少_save_cookies方法'
    print("✓ 文心一言: 方法检查通过")
    
    print()
    print("=" * 60)
    print("测试手动登录平台的_execute_login行为")
    print("=" * 60)
    
    # 测试手动登录平台的_execute_login应返回False
    result = await doubao._execute_login()
    assert result == False, '豆包_execute_login应返回False'
    print("✓ 豆包: _execute_login返回False正确")
    
    result = await yuanbao._execute_login()
    assert result == False, '元宝_execute_login应返回False'
    print("✓ 元宝: _execute_login返回False正确")
    
    result = await ernie._execute_login()
    assert result == False, '文心一言_execute_login应返回False'
    print("✓ 文心一言: _execute_login返回False正确")
    
    print()
    print("=" * 60)
    print("所有测试通过！")
    print("=" * 60)
    print()
    print("各平台登录策略总结：")
    print("-" * 60)
    print("DeepSeek:   自动登录 (需配置username/password) + Cookie保存 + 失败时手动重新登录")
    print("Qwen:       自动登录 (需配置username/password) + Cookie保存 + 失败时手动重新登录")
    print("豆包:       手动登录 + Cookie保存 + Cookie验证失败时手动重新登录")
    print("元宝:       手动登录 + Cookie保存 + Cookie验证失败时手动重新登录")
    print("文心一言:   手动登录 + Cookie保存 + Cookie验证失败时手动重新登录")


if __name__ == "__main__":
    asyncio.run(test_platform_methods())