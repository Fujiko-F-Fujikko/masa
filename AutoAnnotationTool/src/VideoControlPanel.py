from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider
)
from PyQt6.QtCore import Qt, pyqtSignal
from RangeSlider import RangeSlider

class VideoControlPanel(QWidget):  
    """動画制御パネル"""  
      
    frame_changed = pyqtSignal(int)  
    range_changed = pyqtSignal(int, int)  
    range_frame_preview = pyqtSignal(int)  # 範囲選択中のフレームプレビュー用  
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.total_frames = 0  
        self.current_frame = 0  
        self.range_selection_mode = False  
        self.setup_ui()  
          
    def setup_ui(self):  
        layout = QVBoxLayout()  
        layout.setContentsMargins(5, 5, 5, 5)  
          
        # フレーム情報  
        self.frame_info_label = QLabel("Frame: 0 / 0")  
        self.frame_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        layout.addWidget(self.frame_info_label)  
          
        # 範囲選択スライダー  
        self.range_slider = RangeSlider()  
        self.range_slider.range_changed.connect(self.on_range_changed)  
        self.range_slider.current_frame_changed.connect(self.on_range_frame_preview)
        layout.addWidget(QLabel("Frame Range:"))  
        layout.addWidget(self.range_slider)  
          
        # 通常のフレーム制御  
        control_layout = QHBoxLayout()  
          
        self.prev_btn = QPushButton("◀")  
        self.prev_btn.setFixedSize(30, 30)  
        self.prev_btn.clicked.connect(self.prev_frame)  
        control_layout.addWidget(self.prev_btn)  
          
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)  
        self.frame_slider.setMinimum(0)  
        self.frame_slider.valueChanged.connect(self.on_frame_changed)  
        control_layout.addWidget(self.frame_slider)  
          
        self.next_btn = QPushButton("▶")  
        self.next_btn.setFixedSize(30, 30)  
        self.next_btn.clicked.connect(self.next_frame)  
        control_layout.addWidget(self.next_btn)  
          
        layout.addLayout(control_layout)  
          
        # 範囲選択モード切り替え  
        self.range_mode_btn = QPushButton("Range Selection Mode")  
        self.range_mode_btn.setCheckable(True)  
        self.range_mode_btn.clicked.connect(self.toggle_range_mode)  
        layout.addWidget(self.range_mode_btn)  
        
        
        self.setLayout(layout)  

    def on_range_frame_preview(self, frame_id: int):  
        """範囲選択中のフレームプレビュー"""  
        self.range_frame_preview.emit(frame_id)  
      
    def on_range_changed(self, start_frame: int, end_frame: int):  
        """範囲変更イベント"""  
        self.range_changed.emit(start_frame, end_frame)

    def set_total_frames(self, total_frames: int):  
        """総フレーム数を設定"""  
        self.total_frames = total_frames  
        self.frame_slider.setMaximum(total_frames - 1)  
        self.range_slider.set_range(0, total_frames - 1)  
        self.update_frame_info()  
      
    def set_current_frame(self, frame_id: int):  
        """現在のフレームを設定"""  
        self.current_frame = frame_id  
        self.frame_slider.setValue(frame_id)  
        self.update_frame_info()  
      
    def toggle_range_mode(self, enabled: bool):  
        """範囲選択モードの切り替え"""  
        self.range_selection_mode = enabled  
        self.range_slider.setVisible(enabled)  
          
        if enabled:  
            # 現在のフレームを中心とした範囲を初期設定  
            start = max(0, self.current_frame - 50)  
            end = min(self.total_frames - 1, self.current_frame + 50)  
            self.range_slider.set_values(start, end)  
      
    def on_frame_changed(self, frame_id: int):  
        """フレーム変更イベント"""  
        self.current_frame = frame_id  
        self.update_frame_info()  
        self.frame_changed.emit(frame_id)  
      
    def on_range_changed(self, start_frame: int, end_frame: int):  
        """範囲変更イベント"""  
        self.range_changed.emit(start_frame, end_frame)  
      
    def prev_frame(self):  
        """前のフレームに移動"""  
        if self.current_frame > 0:  
            self.set_current_frame(self.current_frame - 1)  
      
    def next_frame(self):  
        """次のフレームに移動"""  
        if self.current_frame < self.total_frames - 1:  
            self.set_current_frame(self.current_frame + 1)  
      
    def update_frame_info(self):  
        """フレーム情報を更新"""  
        self.frame_info_label.setText(f"Frame: {self.current_frame} / {self.total_frames - 1}")  
      
    def get_selected_range(self) -> tuple:  
        """選択された範囲を取得"""  
        if self.range_selection_mode:  
            return self.range_slider.get_values()  
        else:  
            return (0, self.total_frames - 1)
