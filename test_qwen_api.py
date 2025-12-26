#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Qwen API配置
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from src.api.chatgpt_client import ChatGPTClient

def test_qwen_api():
    """测试Qwen API是否正常工作"""
    print("=" * 60)
    print("🧪 测试 Qwen API 配置")
    print("=" * 60)

    try:
        # 初始化客户端
        print("\n1️⃣ 初始化 AI 客户端...")
        client = ChatGPTClient()

        # 测试简单请求
        print("\n2️⃣ 发送测试请求...")
        test_messages = [
            {"role": "system", "content": "你是一个helpful的助手。请用简短的中文回答问题。"},
            {"role": "user", "content": "你好，请用一句话介绍一下比特币。"}
        ]

        response = client._make_request(test_messages)

        if response:
            print("\n✅ API 请求成功!")
            print(f"\n📝 回复内容:\n{response}")
            print("\n" + "=" * 60)
            print("✅ Qwen API 配置正确，可以正常使用!")
            print("=" * 60)
            return True
        else:
            print("\n❌ API 返回空响应")
            return False

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_qwen_api()
    sys.exit(0 if success else 1)
