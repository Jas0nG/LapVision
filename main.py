#!/usr/bin/env python3
"""
LapVision 启动脚本 - 适用于Render部署
"""

import os
import sys
from pathlib import Path

# 确保后端模块路径
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

if __name__ == '__main__':
    from app import app
    
    port = int(os.environ.get('PORT', 10000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    print("🏎️ LapVision Server Starting...")
    print(f"Environment: {'Production' if not debug else 'Development'}")
    print(f"Port: {port}")
    
    app.run(debug=debug, host='0.0.0.0', port=port)