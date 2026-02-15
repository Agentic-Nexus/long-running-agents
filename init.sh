#!/bin/bash
# 初始化脚本 - 启动开发服务器

set -e

echo "========================================="
echo "大模型驱动的股票分析系统 - 开发环境启动"
echo "========================================="

# 检查 Python 版本
echo "[1/5] 检查 Python 环境..."
python3 --version || { echo "Error: Python3 not found"; exit 1; }

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "[2/5] 创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "[3/5] 激活虚拟环境..."
source venv/bin/activate

# 安装依赖（如果需要）
if [ -f "requirements.txt" ]; then
    echo "[4/5] 安装依赖..."
    pip install -r requirements.txt --quiet
fi

# 启动开发服务器
echo "[5/5] 启动开发服务器..."
echo ""
echo "后端服务: http://localhost:8000"
echo "API 文档: http://localhost:8000/docs"
echo ""

# 根据项目类型选择启动命令
if [ -f "main.py" ]; then
    uvicorn main:app --reload --host 0.0.0.0 --port 8000
elif [ -f "app/main.py" ]; then
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
else:
    echo "Warning: 未找到 main.py，请手动启动服务"
fi
