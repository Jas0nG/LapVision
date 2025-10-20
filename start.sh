#!/bin/bash

set -e

echo "🏎️ Welcome to LapVision"
echo "=================================="

# working directory
PROJECT_DIR=$(pwd)

# 检查虚拟环境
VENV_PATH="$PROJECT_DIR/venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "创建虚拟环境..."
    python3 -m venv "$VENV_PATH"
fi

echo "激活虚拟环境..."
source "$VENV_PATH/bin/activate"

echo "安装依赖..."
pip install --upgrade pip setuptools wheel -q
pip install -r "$PROJECT_DIR/backend/requirements.txt" -q


echo "Enable CUDA Support"
export CUDA_HOME=/usr/local/cuda-12.8
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

echo "✅ 环境准备完成"
echo ""
echo "启动 Flask 服务器..."
echo "API 与前端地址: http://localhost:5000"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

cd $PROJECT_DIR/backend
FLASK_ENV=development flask run --host=0.0.0.0
