#!/bin/bash
# OpenAI库升级脚本 - 用于远程服务器

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  OpenAI库升级脚本"
echo "=========================================="
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 错误: 未找到venv虚拟环境"
    echo "请先创建虚拟环境: python3 -m venv venv"
    exit 1
fi

echo "1️⃣ 激活虚拟环境..."
source venv/bin/activate

echo "2️⃣ 检查当前OpenAI版本..."
current_version=$(python -c "import openai; print(openai.__version__)" 2>/dev/null || echo "未安装")
echo "   当前版本: $current_version"

if [[ "$current_version" == 0.* ]]; then
    echo "   ⚠️  版本过旧，需要升级"
elif [[ "$current_version" == "未安装" ]]; then
    echo "   ⚠️  OpenAI未安装"
else
    echo "   ✅ 版本符合要求"
fi

echo ""
echo "3️⃣ 升级OpenAI库到2.x版本..."
pip install --upgrade "openai>=2.0.0" -q

echo ""
echo "4️⃣ 验证升级结果..."
python << 'EOF'
import openai
print(f"   ✅ OpenAI 版本: {openai.__version__}")
print(f"   ✅ 支持 OpenAI 类: {hasattr(openai, 'OpenAI')}")
print(f"   ✅ 支持 RateLimitError: {hasattr(openai, 'RateLimitError')}")

# 额外检查
if not hasattr(openai, 'OpenAI'):
    print("   ❌ 升级失败：仍然不支持OpenAI类")
    exit(1)
EOF

echo ""
echo "5️⃣ 重启服务..."
if [ -f "start_service.sh" ]; then
    ./start_service.sh stop
    sleep 3
    ./start_service.sh start 30 5 20
    echo "   ✅ 服务已重启"
else
    echo "   ⚠️  未找到start_service.sh，请手动重启服务"
fi

echo ""
echo "=========================================="
echo "  ✅ 修复完成！"
echo "=========================================="
echo ""
echo "📋 后续步骤："
echo "1. 查看服务状态: ./start_service.sh status"
echo "2. 查看实时日志: tail -f service.log"
echo "3. 检查是否有速率限制错误: tail -100 service.log | grep RateLimitError"
echo ""
