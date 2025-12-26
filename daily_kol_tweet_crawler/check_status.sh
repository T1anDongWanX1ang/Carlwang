#!/bin/bash

# 快速检查所有服务状态

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Twitter KOL推文爬取服务状态 ===${NC}"
echo ""

# 检查服务状态
./start_service_kol_tweet.sh status

echo ""
echo -e "${BLUE}=== 监控状态 ===${NC}"
./start_service_kol_tweet.sh monitor
