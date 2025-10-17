#!/usr/bin/env python3
"""
卡丁车圈速计算器 - 核心逻辑
使用BoQ (Bag of Queries) VPR模型进行视频帧匹配，计算卡丁车圈速
"""

import cv2
import numpy as np
from pathlib import Path
import json
from datetime import datetime
from PIL import Image
import base64
from io import BytesIO
import threading

# 尝试导入torch相关模块，如果失败则提示
try:
    import torch
    import torch.nn.functional as F
    import torchvision.transforms as T
    TORCH_AVAILABLE = True
except ImportError as e:
    print(f"PyTorch导入失败: {e}")
    print("请确保正确安装了PyTorch")
    TORCH_AVAILABLE = False


class LapCounter:
    """卡丁车圈速计算器核心类"""
    
    def __init__(self, video_path, min_lap_time, backbone_name="resnet50", output_dim=16384):
        """
        初始化圈速计算器
        
        Args:
            video_path: 视频文件路径
            min_lap_time: 最小圈速（秒）
            backbone_name: BoQ模型骨干网络
            output_dim: BoQ模型输出维度
        """
        self.video_path = Path(video_path)
        self.min_lap_time = min_lap_time
        self.backbone_name = backbone_name
        self.output_dim = output_dim
        
        # 初始化视频
        self.cap = cv2.VideoCapture(str(video_path))
        if not self.cap.isOpened():
            raise ValueError(f"无法打开视频文件，路径: {video_path}")
        
        # 设置更稳定的解码参数
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 减少缓冲，提高定位准确性
        
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.duration = self.total_frames / self.fps
        
        # 验证视频参数的有效性
        if self.fps <= 0 or self.total_frames <= 0:
            raise ValueError(f"视频参数异常: FPS={self.fps}, 总帧数={self.total_frames}")
            
        print(f"视频编解码器: {self.cap.get(cv2.CAP_PROP_FOURCC)}")
        
        # 检查PyTorch可用性
        if not TORCH_AVAILABLE:
            raise ImportError("PyTorch未正确安装，无法使用BoQ模型进行特征提取")
        
        try:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception as e:
            print(f"CUDA初始化失败，使用CPU模式: {e}")
            self.device = "cpu"
        
        # 加载BoQ模型
        self.model = None
        self.image_size = (384, 384) if backbone_name == "resnet50" else (322, 322)
        
        # 存储数据
        self.ref_frame_idx = None
        self.ref_feature = None
        self.lap_times = []
        self.lap_frame_indices = []
        
        # 缓存最近访问的帧，提高性能
        self.frame_cache = {}
        self.last_frame_idx = -1
        
        # 添加线程锁保护视频访问
        self.video_lock = threading.Lock()
        
        print(f"视频信息: FPS={self.fps:.2f}, 总帧数={self.total_frames}, 时长={self.duration:.2f}秒")
        print(f"使用设备: {self.device}")
    

    
    def load_model(self):
        """加载BoQ模型"""
        if self.model is None:
            print("正在加载BoQ模型...")
            self.model = torch.hub.load(
                "amaralibey/bag-of-queries", 
                "get_trained_boq", 
                backbone_name=self.backbone_name,
                output_dim=self.output_dim
            )
            self.model = self.model.to(self.device)
            self.model.eval()
            print("✅ BoQ模型加载成功")
    
    def get_frame(self, frame_idx):
        """
        获取指定索引的帧（带缓存和智能定位）
        
        对于H.264/H.265等视频，CAP_PROP_POS_FRAMES可能不准确，
        特别是非关键帧。此方法使用多种策略确保准确性。
        """
        # 检查缓存
        if frame_idx in self.frame_cache:
            return self.frame_cache[frame_idx].copy()
        
        # 使用锁保护视频访问
        with self.video_lock:
            # 策略1: 如果是顺序访问（相差1帧），直接读取
            if frame_idx == self.last_frame_idx + 1:
                ret, frame = self.cap.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.last_frame_idx = frame_idx
                    # 缓存帧（限制缓存大小）
                    if len(self.frame_cache) < 100:
                        self.frame_cache[frame_idx] = frame_rgb.copy()
                    return frame_rgb
            
            # 策略2: 尝试直接定位
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            actual_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
            
            # 策略3: 如果定位不准确或实际位置异常（如返回-3），从头逐帧读取
            if actual_pos != frame_idx or actual_pos < 0:
                # 对于小帧号（<200），从第0帧开始更可靠
                if frame_idx < 200:
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.last_frame_idx = -1
                    
                    # 逐帧读取到目标帧
                    for i in range(frame_idx + 1):
                        ret, frame = self.cap.read()
                        if not ret:
                            return None
                        
                        # 缓存经过的帧
                        if i == frame_idx:
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            self.last_frame_idx = frame_idx
                            if len(self.frame_cache) < 100:
                                self.frame_cache[frame_idx] = frame_rgb.copy()
                            return frame_rgb
                        elif len(self.frame_cache) < 100 and i % 10 == 0:
                            # 每隔10帧缓存一次
                            self.frame_cache[i] = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).copy()
                else:
                    # 对于大帧号，回退到更早的位置
                    safe_start = max(0, frame_idx - 50)
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, safe_start)
                    
                    # 逐帧读取直到目标帧
                    for i in range(frame_idx - safe_start + 1):
                        ret, frame = self.cap.read()
                        if not ret:
                            return None
                        current_idx = safe_start + i
                        
                        if current_idx == frame_idx:
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            self.last_frame_idx = frame_idx
                            if len(self.frame_cache) < 100:
                                self.frame_cache[frame_idx] = frame_rgb.copy()
                            return frame_rgb
            else:
                # 定位准确，直接读取
                ret, frame = self.cap.read()
                if not ret:
                    return None
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.last_frame_idx = frame_idx
                if len(self.frame_cache) < 100:
                    self.frame_cache[frame_idx] = frame_rgb.copy()
                return frame_rgb
            
            return None

    
    def frame_to_base64(self, frame):
        """将 OpenCV 帧转换为 Base64 字符串"""
        pil_image = Image.fromarray(frame)
        buffered = BytesIO()
        pil_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str
    
    def extract_frame_feature(self, frame):
        """提取帧的 BoQ 特征"""
        if self.model is None:
            self.load_model()
        
        # 预处理
        pil_image = Image.fromarray(frame)
        transform = T.Compose([
            T.Resize(self.image_size),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406],
                       std=[0.229, 0.224, 0.225])
        ])
        
        img_tensor = transform(pil_image).unsqueeze(0).to(self.device)
        
        # 提取特征
        with torch.no_grad():
            result = self.model(img_tensor)
            
            # BoQ模型可能返回元组，需要获取主要特征输出
            if isinstance(result, tuple):
                features = result[0]  # 通常主要特征在第一个位置
            else:
                features = result
        
        return F.normalize(features, p=2, dim=1).cpu().numpy()
    
    def find_top_k_similar_frames(self, frame_indices, k=5):
        """找到与参考帧最相似的k个帧"""
        if self.ref_feature is None:
            raise ValueError("请先设置参考帧")
        
        similarities = []
        
        for idx in frame_indices:
            frame = self.get_frame(idx)
            if frame is not None:
                feature = self.extract_frame_feature(frame)
                # 计算余弦相似度
                similarity = np.dot(self.ref_feature[0], feature[0])
                similarities.append((idx, frame, similarity))
        
        # 按相似度排序，返回 top-k
        similarities.sort(key=lambda x: x[2], reverse=True)
        return similarities[:k]
    
    def format_time(self, seconds):
        """格式化时间"""
        minutes = int(seconds) // 60
        secs = int(seconds) % 60
        millis = int((seconds - int(seconds)) * 1000)
        return f"{minutes:02d}:{secs:02d}.{millis:03d}"
    
    def get_video_info(self):
        """获取视频信息"""
        return {
            "fps": self.fps,
            "total_frames": self.total_frames,
            "duration": self.duration,
            "formatted_duration": self.format_time(self.duration),
            "device": self.device
        }
    
    def set_reference_frame(self, frame_idx):
        """设置参考帧"""
        frame = self.get_frame(frame_idx)
        if frame is None:
            raise ValueError(f"无法读取帧 {frame_idx}")
        
        self.ref_frame_idx = frame_idx
        self.ref_feature = self.extract_frame_feature(frame)
        return frame
    
    def record_lap(self, end_frame_idx):
        """记录一圈"""
        if self.ref_frame_idx is None:
            raise ValueError("请先设置参考帧")
        
        lap_time = (end_frame_idx - self.ref_frame_idx) / self.fps
        
        if lap_time < self.min_lap_time:
            raise ValueError(f"圈速过短 ({self.format_time(lap_time)} < {self.format_time(self.min_lap_time)})")
        
        self.lap_times.append(lap_time)
        self.lap_frame_indices.append(end_frame_idx)
        
        # 更新参考帧为当前圈的终点，用于下一圈的搜索
        self.ref_frame_idx = end_frame_idx
        
        return lap_time
    
    def get_lap_statistics(self):
        """获取圈速统计"""
        if not self.lap_times:
            return {
                "total_laps": 0,
                "laps": []
            }
        
        lap_times_array = np.array(self.lap_times)
        
        return {
            "total_laps": len(self.lap_times),
            "laps": [
                {
                    "lap_number": i + 1,
                    "time": lap_time,
                    "formatted_time": self.format_time(lap_time),
                    "frame_index": self.lap_frame_indices[i]
                }
                for i, lap_time in enumerate(self.lap_times)
            ],
            "best_lap": self.format_time(np.min(lap_times_array)),
            "worst_lap": self.format_time(np.max(lap_times_array)),
            "average_lap": self.format_time(np.mean(lap_times_array)),
            "total_time": self.format_time(np.sum(lap_times_array))
        }
    
    def save_results(self, output_path):
        """保存结果为 JSON"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "video_path": str(self.video_path),
            "video_info": self.get_video_info(),
            "min_lap_time": self.min_lap_time,
            "reference_frame_idx": self.ref_frame_idx,
            "statistics": self.get_lap_statistics(),
            "created_at": datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 结果已保存: {output_path}")
        return output_path
    
    def close(self):
        """关闭视频并清理资源"""
        with self.video_lock:
            if self.cap:
                self.cap.release()
                self.cap = None
            
            # 清理缓存
            self.frame_cache.clear()
            
        print("✅ 资源已清理")


if __name__ == "__main__":
    # 示例使用
    counter = LapCounter("/home/wtc/Project/lapCounter/example/v001.mp4", min_lap_time=18)
    print(counter.get_video_info())
