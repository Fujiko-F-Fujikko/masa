# 改善されたVideoPlaybackController.py  
from PyQt6.QtCore import QTimer, pyqtSignal, QObject  
from ErrorHandler import ErrorHandler  
  
class VideoPlaybackController(QObject):  
    """動画再生制御クラス（改善版）"""  
      
    frame_updated = pyqtSignal(int)  # 再生中のフレーム更新  
    playback_finished = pyqtSignal()  # 再生完了  
      
    def __init__(self, video_manager):  
        super().__init__()  
        self.video_manager = video_manager  
        self.timer = QTimer()  
        self.timer.timeout.connect(self.next_frame)  
          
        self.current_frame = 0  
        self.is_playing = False  
        self.fps = 30.0  # デフォルトFPS  
          
    def set_fps(self, fps: float):  
        """FPSを設定"""  
        self.fps = fps  
        if self.is_playing:  
            self.timer.setInterval(int(1000 / fps))  
      
    @ErrorHandler.handle_with_dialog("Playback Error")  
    def play(self, start_frame: int = None):  
        """再生開始"""  
        if start_frame is not None:  
            self.current_frame = start_frame  
          
        if not self.is_playing:  
            self.is_playing = True  
            self.timer.start(int(1000 / self.fps))  
      
    def pause(self):  
        """一時停止"""  
        if self.is_playing:  
            self.is_playing = False  
            self.timer.stop()  
      
    def stop(self):  
        """停止"""  
        if self.is_playing:  
            self.timer.stop()  
            self.is_playing = False  
        self.current_frame = 0  
        self.frame_updated.emit(self.current_frame)  
        self.playback_finished.emit() # 再生終了シグナルも発行
      
    def next_frame(self):  
        """次のフレームに進む"""  
        if self.video_manager and self.current_frame < self.video_manager.get_total_frames() - 1:  
            self.current_frame += 1  
            self.frame_updated.emit(self.current_frame)  
        else:  
            # 再生完了  
            self.pause()  
            self.playback_finished.emit()  
      
    def set_frame(self, frame_id: int):  
        """フレーム位置を設定"""  
        self.current_frame = max(0, min(frame_id, self.video_manager.get_total_frames() - 1))  
        if not self.is_playing:  
            self.frame_updated.emit(self.current_frame)  