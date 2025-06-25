# VideoManager.py  
import cv2  
import numpy as np  
import threading
from typing import Optional  
from ErrorHandler import ErrorHandler  
  
class VideoManager:  
    """動画管理専用クラス"""  
      
    def __init__(self, video_path: str):  
        self.video_path = video_path  
        self.video_reader: Optional[cv2.VideoCapture] = None  
        self.total_frames = 0  
        self.fps = 30.0  
        self.lock = threading.Lock()
      
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
        
        with self.lock: # ロックを取得
            self.video_reader.set(cv2.CAP_PROP_POS_FRAMES, frame_id)  
            ret, frame = self.video_reader.read()  
            if not ret:  
                return None  
            return frame
      
    def get_fps(self) -> float:  
        """FPSを取得"""  
        return self.fps  
      
    def get_total_frames(self) -> int:  
        """総フレーム数を取得"""  
        return self.total_frames  
      

    def get_video_width(self) -> int:  
        """動画の幅を返す"""  
        if self.video_reader and self.video_reader.isOpened():  
            return int(self.video_reader.get(cv2.CAP_PROP_FRAME_WIDTH))  
        return 0  
  
    def get_video_height(self) -> int:  
        """動画の高さを返す"""  
        if self.video_reader and self.video_reader.isOpened():  
            return int(self.video_reader.get(cv2.CAP_PROP_FRAME_HEIGHT))  
        return 0

    def release(self):  
        """リソースを解放"""  
        if self.video_reader:  
            self.video_reader.release()  
            self.video_reader = None  