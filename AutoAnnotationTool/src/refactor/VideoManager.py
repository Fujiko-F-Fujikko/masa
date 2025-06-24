# VideoManager.py  
import cv2  
import numpy as np  
from typing import Optional  
from ErrorHandler import ErrorHandler  
  
class VideoManager:  
    """動画管理専用クラス"""  
      
    def __init__(self, video_path: str):  
        self.video_path = video_path  
        self.video_reader: Optional[cv2.VideoCapture] = None  
        self.total_frames = 0  
        self.fps = 30.0  
      
    @ErrorHandler.handle_with_dialog("Video Loading Error")  
    def load_video(self) -> bool:  
        """動画ファイルを読み込み"""  
        self.video_reader = cv2.VideoCapture(self.video_path)  
        if not self.video_reader.isOpened():  
            raise RuntimeError(f"Failed to open video: {self.video_path}")  
          
        self.total_frames = int(self.video_reader.get(cv2.CAP_PROP_FRAME_COUNT))  
        self.fps = self.video_reader.get(cv2.CAP_PROP_FPS)  
          
        if self.fps <= 0:  
            self.fps = 30.0  # デフォルトFPS  
          
        print(f"Video loaded: {self.total_frames} frames at {self.fps} FPS")  
        return True  
      
    def get_frame(self, frame_id: int) -> Optional[np.ndarray]:  
        """指定フレームを取得"""  
        if self.video_reader is None:  
            return None  
          
        if not (0 <= frame_id < self.total_frames):  
            return None  
          
        self.video_reader.set(cv2.CAP_PROP_POS_FRAMES, frame_id)  
        ret, frame = self.video_reader.read()  
          
        return frame if ret else None  
      
    def get_fps(self) -> float:  
        """FPSを取得"""  
        return self.fps  
      
    def get_total_frames(self) -> int:  
        """総フレーム数を取得"""  
        return self.total_frames  
      
    def release(self):  
        """リソースを解放"""  
        if self.video_reader:  
            self.video_reader.release()  
            self.video_reader = None  