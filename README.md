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
│   ├── index.html             # 单页应用
│   └── dist/                  # 构建输出（可选）
│
├── start.sh                   # 启动脚本
├── README.md                  # 本文件
└── .gitignore                 # Git 忽略文件
```

## 🚀 快速开始

### 1. 启动应用

```bash
chmod +x /home/wtc/Project/lapCounter_web/start.sh
bash /home/wtc/Project/lapCounter_web/start.sh
```

### 2. 访问应用

打开浏览器访问：`http://localhost:5000`

## 🎯 功能流程

### 阶段1：初始化
- 选择视频文件
- 设置最小圈速
- 加载 BoQ 模型
- 显示视频信息

### 阶段2：设置参考帧
- 拖动滑块浏览视频
- 快速跳转到指定帧
- 选择冲线时刻作为参考帧

### 阶段3：搜索与确认
- 自动搜索下一圈（粗搜索）
- 点击选择最相似的候选帧
- 微调选择（±5帧）
- 确认圈速
- 查看实时统计信息
- 保存结果

## 📡 API 文档

### 初始化

**POST** `/api/init`
```json
{
  "video_path": "/path/to/video.mp4",
  "min_lap_time": 18
}
```

**响应**：
```json
{
  "status": "success",
  "data": {
    "counter_id": "counter_1",
    "video_info": {
      "fps": 59.94,
      "total_frames": 27791,
      "duration": 463.5,
      "device": "cuda"
    }
  }
}
```

### 获取帧

**GET** `/api/frame/{counter_id}/{frame_idx}`

返回指定帧的 Base64 图像数据

### 设置参考帧

**POST** `/api/set-ref-frame/{counter_id}/{frame_idx}`

### 搜索圈速

**POST** `/api/search-lap/{counter_id}`
```json
{
  "search_range": 10
}
```

返回相似度最高的 5 个候选帧

### 微调搜索

**POST** `/api/refine-search/{counter_id}/{center_frame_idx}`

返回中心帧周围 ±5 帧的预览

### 确认圈速

**POST** `/api/confirm-lap/{counter_id}/{frame_idx}`

### 获取统计

**GET** `/api/statistics/{counter_id}`

### 保存结果

**POST** `/api/save-results/{counter_id}`

### 关闭计算器

**POST** `/api/close/{counter_id}`

## 🎨 前端特性

- ✨ 现代深色主题
- 📱 完全响应式设计
- 🎯 直观的交互流程
- 📊 实时统计显示
- 🚀 流畅的动画效果
- ♿ 无障碍设计支持

## ⚙️ 技术栈

### 后端
- **框架**: Flask 2.3+
- **深度学习**: PyTorch 2.0+
- **视频处理**: OpenCV 4.8+
- **模型**: BoQ (Bag of Queries)
- **硬件加速**: CUDA（可选）

### 前端
- **语言**: HTML5 + CSS3 + JavaScript (ES6+)
- **样式**: 现代 CSS Grid + Flexbox
- **通信**: Fetch API (REST)

## 🔧 配置

### 环境变量

在 `backend/app.py` 中修改：
- `VIDEOS_DIR`: 视频文件目录
- `OUTPUT_DIR`: 结果输出目录
- Flask 服务器地址和端口

## 📊 结果格式

保存的 JSON 文件包含：

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

## 🐛 故障排查

### 问题：无法连接到服务器

**解决**：
- 确保 Flask 服务已启动：`bash start.sh`
- 检查防火墙设置
- 确保端口 5000 未被占用

### 问题：视频加载失败

**解决**：
- 检查视频路径是否正确
- 确保视频格式支持（MP4、AVI 等）
- 检查文件权限

### 问题：模型加载很慢

**解决**：
- 首次加载需要下载模型（~100MB）
- 检查网络连接
- 如果使用 CUDA，确保 GPU 驱动正确安装

## 📈 性能优化

1. **帧缓存**：最近 100 个访问的帧保存在内存中
2. **智能寻帧**：三层策略确保准确快速的帧定位
3. **异步处理**：前端异步加载数据，UI 保持响应
4. **GPU 加速**：支持 CUDA 和 ROCm 加速

## 🔐 安全性

- CORS 已启用，仅在开发环境
- 生产环境请配置正确的 CORS 策略
- 文件路径验证已实现
- 输入数据验证已实现

## 📝 日志

### 后端日志

Flask 服务的日志输出到控制台：
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

### 前端调试

在浏览器开发者工具中查看：
- Console：JavaScript 日志
- Network：API 请求/响应
- Performance：性能分析

## 🎓 扩展开发

### 添加新的 API 端点

在 `backend/app.py` 中添加：

```python
@app.route('/api/custom', methods=['POST'])
def custom_endpoint():
    try:
        counter = active_counters.get(counter_id)
        # 你的逻辑
        return APIResponse.success(data, "消息")
    except Exception as e:
        return APIResponse.error(e, "错误消息", 500)
```

### 修改前端样式

在 `frontend/index.html` 中编辑 `<style>` 部分

### 添加新功能

1. 后端：在 `lap_counter_core.py` 中添加方法
2. API：在 `app.py` 中创建路由
3. 前端：在 `index.html` 中添加 JavaScript 函数


## 👨‍💻 贡献

欢迎提交 Bug 报告和功能建议！

## 📧 联系方式

有任何问题或建议，请联系开发者


