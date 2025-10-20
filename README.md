# 🏎️ LapVision

A modern web application based on Flask and Vue.js that automatically analyzes lap times from onboard driver videos. Utilizing Visual Place Recognition (VPR) , it delivers accurate and robust lap time results, significantly improving the efficiency of post-race data analysis.

## 📋 项目结构

```
lapCounter_web/
├── backend/                    # 后端 Flask 服务
│   ├── lap_counter_core.py    # 核心算法（独立于 UI）
│   ├── app.py                 # Flask API 服务
│   ├── requirements.txt        # Python 依赖
│   └── results/               # 输出结果目录
│
├── frontend/                   # 前端静态文件
│   └── index.html             # 单页应用
│
├── start.sh                   # 启动脚本
├── README.md                  # 本文件
└── .gitignore                 # Git 忽略文件
```

## 🚀 快速开始

### 1. 启动应用

```bash
chmod +x start.sh
bash start.sh
```

### 2. 访问应用

打开浏览器访问：`http://localhost:5000`

## Result

保存的 JSON 文件包含如下内容：

```json
{
  "video_path": "/path/to/video.mp4",
  "video_info": {
    "fps": 59.94,
    "total_frames": 27791,
    "duration": 463.5,
    "device": "cuda"
  },
  "min_lap_time": 18,
  "reference_frame_idx": 100,
  "statistics": {
    "total_laps": 5,
    "best_lap": "00:19.542",
    "worst_lap": "00:21.083",
    "average_lap": "00:20.123",
    "total_time": "01:40.615",
    "laps": [
      {
        "lap_number": 1,
        "time": 19.542,
        "formatted_time": "00:19.542",
        "frame_index": 1200
      }
    ]
  },
  "created_at": "2024-10-17T15:30:45.123456"
}
```
