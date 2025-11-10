#!/bin/bash
# RM-01 CFe-B存储卡制作工具启动脚本

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 检查Python3是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python3，请先安装Python3"
    exit 1
fi

# 检查并安装依赖
echo "检查Python依赖..."
python3 -c "import yaml" 2>/dev/null || {
    echo "安装PyYAML依赖..."
    pip3 install PyYAML
}

python3 -c "import tqdm" 2>/dev/null || {
    echo "安装tqdm依赖..."
    pip3 install tqdm
}

# 运行主程序
echo "启动RM-01 CFe-B存储卡制作工具..."
cd "$SCRIPT_DIR"
python3 main.py

echo "程序已退出"

