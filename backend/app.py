#!/usr/bin/env python3
"""
卡丁车圈速计算器 - Flask 后端 API
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
from pathlib import Path
import traceback
from datetime import datetime
import json

# 添加后端模块路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lap_counter_core import LapCounter

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# 存储活跃的 LapCounter 实例
active_counters = {}
counter_id_counter = 0

# 帧请求计数器，用于监控并发
frame_request_count = 0
max_concurrent_frame_requests = 3

# 获取视频目录
VIDEOS_DIR = Path("/home/wtc/Project/lapCounter/example")
OUTPUT_DIR = Path("/home/wtc/Project/lapCounter_web/results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class APIResponse:
    """API 响应格式化"""
    
    @staticmethod
    def success(data=None, message="success"):
        return jsonify({
            "status": "success",
            "message": message,
            "data": data or {}
        }), 200
    
    @staticmethod
    def error(error, message=None, status_code=400):
        return jsonify({
            "status": "error",
            "message": message or str(error),
            "error": str(error)
        }), status_code


# ============ 初始化 API ============

@app.route('/api/init', methods=['POST'])
def init_counter():
    """初始化圈速计算器"""
    global counter_id_counter
    
    try:
        data = request.json
        video_path = data.get('video_path')
        min_lap_time = data.get('min_lap_time', 18)
        
        if not video_path:
            return APIResponse.error("缺少视频路径", "Missing video_path")
        
        # 创建新实例
        counter_id_counter += 1
        counter_id = f"counter_{counter_id_counter}"
        
        counter = LapCounter(video_path, min_lap_time)
        counter.load_model()
        
        active_counters[counter_id] = counter
        
        video_info = counter.get_video_info()
        
        return APIResponse.success({
            "counter_id": counter_id,
            "video_info": video_info
        }, "计算器初始化成功")
    
    except Exception as e:
        traceback.print_exc()
        return APIResponse.error(e, "初始化失败", 500)


@app.route('/api/videos', methods=['GET'])
def list_videos():
    """列出可用的视频文件"""
    try:
        videos = []
        for video_file in VIDEOS_DIR.glob("*.mp4"):
            videos.append({
                "name": video_file.name,
                "path": str(video_file),
                "size": video_file.stat().st_size
            })
        
        return APIResponse.success({
            "videos": videos
        }, "获取视频列表成功")
    
    except Exception as e:
        return APIResponse.error(e, "获取视频列表失败", 500)


# ============ 帧管理 API ============

@app.route('/api/frame/<counter_id>/<int:frame_idx>', methods=['GET'])
def get_frame(counter_id, frame_idx):
    """获取指定帧的 Base64 数据"""
    global frame_request_count
    
    try:
        # 简单的并发控制
        if frame_request_count >= max_concurrent_frame_requests:
            return APIResponse.error("请求过于频繁，请稍后再试", "Too many concurrent requests", 429)
        
        frame_request_count += 1
        
        counter = active_counters.get(counter_id)
        if not counter:
            frame_request_count -= 1
            return APIResponse.error("计算器不存在", "Invalid counter_id", 404)
        
        frame = counter.get_frame(frame_idx)
        if frame is None:
            frame_request_count -= 1
            return APIResponse.error("无法读取帧", "Cannot read frame", 400)
        
        # 转换为 Base64
        img_base64 = counter.frame_to_base64(frame)
        time_sec = frame_idx / counter.fps
        
        frame_request_count -= 1
        
        return APIResponse.success({
            "frame_idx": frame_idx,
            "time_sec": time_sec,
            "formatted_time": counter.format_time(time_sec),
            "image_base64": img_base64
        }, "获取帧成功")
    
    except Exception as e:
        frame_request_count -= 1
        traceback.print_exc()
        return APIResponse.error(e, "获取帧失败", 500)


@app.route('/api/frame-info/<counter_id>', methods=['GET'])
def get_frame_info(counter_id):
    """获取帧信息"""
    try:
        counter = active_counters.get(counter_id)
        if not counter:
            return APIResponse.error("计算器不存在", "Invalid counter_id", 404)
        
        return APIResponse.success({
            "total_frames": counter.total_frames,
            "fps": counter.fps,
            "duration": counter.duration
        })
    
    except Exception as e:
        return APIResponse.error(e, "获取帧信息失败", 500)


# ============ 参考帧 API ============

@app.route('/api/set-ref-frame/<counter_id>/<int:frame_idx>', methods=['POST'])
def set_ref_frame(counter_id, frame_idx):
    """设置参考帧"""
    try:
        counter = active_counters.get(counter_id)
        if not counter:
            return APIResponse.error("计算器不存在", "Invalid counter_id", 404)
        
        frame = counter.set_reference_frame(frame_idx)
        img_base64 = counter.frame_to_base64(frame)
        time_sec = frame_idx / counter.fps
        
        return APIResponse.success({
            "ref_frame_idx": frame_idx,
            "time_sec": time_sec,
            "formatted_time": counter.format_time(time_sec),
            "image_base64": img_base64
        }, "参考帧设置成功")
    
    except Exception as e:
        traceback.print_exc()
        return APIResponse.error(e, "设置参考帧失败", 500)


# ============ 搜索 API ============

@app.route('/api/search-lap/<counter_id>', methods=['POST'])
def search_lap(counter_id):
    """搜索下一圈"""
    try:
        counter = active_counters.get(counter_id)
        if not counter:
            return APIResponse.error("计算器不存在", "Invalid counter_id", 404)
        
        data = request.json
        search_range = data.get('search_range', 10)  # 搜索范围（秒）
        
        if counter.ref_frame_idx is None:
            return APIResponse.error("未设置参考帧", "Reference frame not set", 400)
        
        # 确定搜索范围
        # 如果已有圈速记录，从最后一圈的终点开始搜索
        if counter.lap_frame_indices:
            start_frame = counter.lap_frame_indices[-1]  # 最后一圈的终点
        else:
            start_frame = counter.ref_frame_idx  # 第一圈从参考帧开始
            
        min_frame = start_frame + int(counter.min_lap_time * counter.fps)
        max_frame = min(
            min_frame + int(search_range * counter.fps),
            counter.total_frames - 1
        )

        # 检查搜索范围是否超出视频长度
        if min_frame >= counter.total_frames:
            return APIResponse.error(
                "已到达视频末尾，无法继续搜索", 
                "Reached end of video", 
                400
            )
        
        # 如果搜索的最小帧已经接近视频末尾，调整搜索范围
        if max_frame <= min_frame:
            # 尝试在剩余帧中搜索
            max_frame = counter.total_frames - 1
            if max_frame <= min_frame:
                return APIResponse.error(
                    "视频剩余时长不足以完成一圈", 
                    "Insufficient remaining video duration", 
                    400
                )

        # 采样帧（每0.1秒一个）
        sample_interval = int(0.1 * counter.fps)
        sampled_frames = list(range(min_frame, max_frame, sample_interval))
        
        if not sampled_frames:
            return APIResponse.error(
                "搜索范围无效或视频已结束", 
                "Invalid search range or video ended", 
                400
            )
        
        # 找最相似的5个帧
        candidates = counter.find_top_k_similar_frames(sampled_frames, k=5)
        
        # 转换为 Base64 图像
        candidate_images = []
        for frame_idx, frame, similarity in candidates:
            img_base64 = counter.frame_to_base64(frame)
            time_sec = frame_idx / counter.fps
            candidate_images.append({
                "frame_idx": frame_idx,
                "time_sec": time_sec,
                "formatted_time": counter.format_time(time_sec),
                "similarity": float(similarity),
                "image_base64": img_base64
            })
        
        return APIResponse.success({
            "candidates": candidate_images
        }, "搜索成功")
    
    except Exception as e:
        traceback.print_exc()
        return APIResponse.error(e, "搜索失败", 500)


@app.route('/api/refine-search/<counter_id>/<int:center_frame_idx>', methods=['POST'])
def refine_search(counter_id, center_frame_idx):
    """微调搜索（±5帧）"""
    try:
        counter = active_counters.get(counter_id)
        if not counter:
            return APIResponse.error("计算器不存在", "Invalid counter_id", 404)
        
        # 获取±5帧的预览
        frames_range = []
        for offset in range(-5, 6):
            frame_idx = center_frame_idx + offset
            if 0 <= frame_idx < counter.total_frames:
                frames_range.append(frame_idx)
        
        preview_images = []
        for frame_idx in frames_range:
            frame = counter.get_frame(frame_idx)
            if frame is not None:
                img_base64 = counter.frame_to_base64(frame)
                time_sec = frame_idx / counter.fps
                preview_images.append({
                    "frame_idx": frame_idx,
                    "time_sec": time_sec,
                    "formatted_time": counter.format_time(time_sec),
                    "is_center": frame_idx == center_frame_idx,
                    "image_base64": img_base64
                })
        
        return APIResponse.success({
            "previews": preview_images
        }, "微调搜索成功")
    
    except Exception as e:
        traceback.print_exc()
        return APIResponse.error(e, "微调搜索失败", 500)


# ============ 圈速确认 API ============

@app.route('/api/confirm-lap/<counter_id>/<int:frame_idx>', methods=['POST'])
def confirm_lap(counter_id, frame_idx):
    """确认圈速"""
    try:
        counter = active_counters.get(counter_id)
        if not counter:
            return APIResponse.error("计算器不存在", "Invalid counter_id", 404)
        
        lap_time = counter.record_lap(frame_idx)
        stats = counter.get_lap_statistics()
        
        return APIResponse.success({
            "lap_time": lap_time,
            "formatted_lap_time": counter.format_time(lap_time),
            "statistics": stats
        }, "圈速已确认")
    
    except Exception as e:
        return APIResponse.error(e, "确认圈速失败", 500)


# ============ 统计 API ============

@app.route('/api/statistics/<counter_id>', methods=['GET'])
def get_statistics(counter_id):
    """获取统计信息"""
    try:
        counter = active_counters.get(counter_id)
        if not counter:
            return APIResponse.error("计算器不存在", "Invalid counter_id", 404)
        
        stats = counter.get_lap_statistics()
        
        return APIResponse.success({
            "statistics": stats
        }, "获取统计成功")
    
    except Exception as e:
        return APIResponse.error(e, "获取统计失败", 500)


# ============ 保存结果 API ============

@app.route('/api/save-results/<counter_id>', methods=['POST'])
def save_results(counter_id):
    """保存结果"""
    try:
        counter = active_counters.get(counter_id)
        if not counter:
            return APIResponse.error("计算器不存在", "Invalid counter_id", 404)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = OUTPUT_DIR / f"lap_times_{timestamp}.json"
        
        counter.save_results(output_path)
        
        return APIResponse.success({
            "output_path": str(output_path)
        }, "结果已保存")
    
    except Exception as e:
        traceback.print_exc()
        return APIResponse.error(e, "保存结果失败", 500)


# ============ 清理 API ============

@app.route('/api/close/<counter_id>', methods=['POST'])
def close_counter(counter_id):
    """关闭计算器"""
    try:
        counter = active_counters.pop(counter_id, None)
        if counter:
            counter.close()
        
        return APIResponse.success({}, "计算器已关闭")
    
    except Exception as e:
        return APIResponse.error(e, "关闭计算器失败", 500)


# ============ 前端路由 ============

@app.route('/')
def index():
    """主页"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """提供静态文件"""
    if os.path.isfile(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')


# ============ 健康检查 ============

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return APIResponse.success({
        "status": "running",
        "active_counters": len(active_counters)
    })


@app.errorhandler(404)
def not_found(e):
    """404 处理"""
    return APIResponse.error(e, "资源不存在", 404)


@app.errorhandler(500)
def internal_error(e):
    """500 处理"""
    return APIResponse.error(e, "内部错误", 500)


if __name__ == '__main__':
    print("🚀 启动卡丁车圈速计算器 Web 服务")
    print("📡 API 服务: http://localhost:5000")
    print("🌐 前端服务: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
