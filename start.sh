#!/bin/bash

# 卡丁车圈速计算器 - Web 版启动脚本

set -e

echo "🏎️ 启动卡丁车圈速计算器 Web 版"
echo "=================================="

# 检查虚拟环境
VENV_PATH="/home/wtc/Project/lapCounter_web/venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "📦 创建虚拟环境..."
    python3 -m venv "$VENV_PATH"
fi

echo "🔧 激活虚拟环境..."
source "$VENV_PATH/bin/activate"

echo "📥 安装依赖..."
pip install --upgrade pip setuptools wheel -q
pip install -r /home/wtc/Project/lapCounter_web/backend/requirements.txt -q


echo "Enable CUDA Support"
export CUDA_HOME=/usr/local/cuda-12.8
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

echo "✅ 环境准备完成"
echo ""
echo "🚀 启动 Flask 服务器..."
echo "📡 API 地址: http://localhost:5000"
echo "🌐 前端地址: http://localhost:5000"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

cd /home/wtc/Project/lapCounter_web/backend
python app.py
