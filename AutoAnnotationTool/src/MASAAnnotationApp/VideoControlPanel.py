# VideoControlPanel.py    
from PyQt6.QtWidgets import (    
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,    
    QPushButton, QSlider, QLineEdit    
)    
from PyQt6.QtCore import Qt, pyqtSignal    
  
from RangeSlider import RangeSlider    
from CoordinateTransform import CoordinateTransform    
    
class VideoControlPanel(QWidget):    
    """動画制御パネル（軽量化版）"""    
        
    frame_changed = pyqtSignal(int)    
    range_changed = pyqtSignal(int, int)    
    range_frame_preview = pyqtSignal(int)    
    play_requested = pyqtSignal()  
    pause_requested = pyqtSignal()

    def __init__(self, main_widget, parent=None):    
        super().__init__(parent)    
        self.main_widget = main_widget  # MASAAnnotationWidgetへの参照  
        self.total_frames = 0    
        self.current_frame = 0    
        self.coordinate_transform = CoordinateTransform()  
        self.setup_ui()    
        self.range_slider.setVisible(False)    
            
    def setup_ui(self):    
        layout = QVBoxLayout()    
        layout.setContentsMargins(5, 5, 5, 5)    
            
        self.frame_info_label = QLabel("Frame: 0 / 0")    
        self.frame_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)    
        layout.addWidget(self.frame_info_label)    
            
        self.range_slider = RangeSlider()    
        self.range_slider.range_changed.connect(self.on_range_changed)    
        self.range_slider.current_frame_changed.connect(self.on_range_frame_preview)    
        layout.addWidget(self.range_slider)    
            
        control_layout = QHBoxLayout()    
            
        self.prev_btn = QPushButton("◀ (←)")    
        self.prev_btn.setFixedSize(60, 30)    
        self.prev_btn.clicked.connect(self.prev_frame)    
        control_layout.addWidget(self.prev_btn)    
            
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)    
        self.frame_slider.setMinimum(0)    
        self.frame_slider.valueChanged.connect(self.on_frame_changed)    
        control_layout.addWidget(self.frame_slider)    
            
        self.next_btn = QPushButton("▶ (→)")    
        self.next_btn.setFixedSize(60, 30)    
        self.next_btn.clicked.connect(self.next_frame)    
        control_layout.addWidget(self.next_btn)  
            
        layout.addLayout(control_layout)    
  
        # Play/Pauseボタン  
        playback_layout = QHBoxLayout()  
        
        self.play_btn = QPushButton("Play (Space)")  
        self.play_btn.setEnabled(False)  
        self.play_btn.clicked.connect(self._on_play_clicked)  
        playback_layout.addWidget(self.play_btn)  
        
        layout.addLayout(playback_layout)

        # フレーム番号入力機能を追加    
        jump_layout = QHBoxLayout()    
        jump_layout.addWidget(QLabel("Jump to frame (F):"))    
            
        self.frame_input = QLineEdit()    
        self.frame_input.setPlaceholderText("Frame number")    
        self.frame_input.setMaximumWidth(100)    
        self.frame_input.returnPressed.connect(self.jump_to_frame)    
        jump_layout.addWidget(self.frame_input)    
            
        self.jump_btn = QPushButton("Go (G)")    
        self.jump_btn.setMaximumWidth(50)    
        self.jump_btn.clicked.connect(self.jump_to_frame)    
        jump_layout.addWidget(self.jump_btn)  
            
        jump_layout.addStretch()    
        layout.addLayout(jump_layout)   
  
        self.setLayout(layout)    
                 
    def on_range_frame_preview(self, frame_id: int):    
        """範囲選択中のフレームプレビュー"""    
        self.range_frame_preview.emit(frame_id)    
            
    def on_range_changed(self, start_frame: int, end_frame: int):    
        """範囲変更イベント（内部処理版）"""    
        self.range_changed.emit(start_frame, end_frame)  
        # MenuPanelの範囲情報を直接更新  
        self.main_widget.menu_panel.update_range_info(start_frame, end_frame)  
            
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
            
        # 再生中の自動更新の場合はframe_changedシグナルを発行しない  
        if not (hasattr(self.main_widget, 'playback_controller') and   
                self.main_widget.playback_controller and   
                self.main_widget.playback_controller.is_playing):  
            self.frame_changed.emit(frame_id)
                
    def on_frame_changed(self, frame_id: int):    
        """フレーム変更イベント（手動操作時・内部処理版）"""                
        self.current_frame = frame_id    
        self.update_frame_info()    
        self.frame_changed.emit(frame_id)  
          
        # オブジェクト一覧を更新  
        if self.main_widget.annotation_repository:  
            frame_annotation = self.main_widget.annotation_repository.get_annotations(frame_id)  
            self.main_widget.menu_panel.update_current_frame_objects(frame_id, frame_annotation)  
            
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
        return self.range_slider.get_values()    
  
    def jump_to_frame(self):    
        """指定されたフレーム番号にジャンプ"""    
        try:    
            frame_text = self.frame_input.text().strip()    
            if not frame_text:    
                return    
                    
            target_frame = int(frame_text)    
                
            # フレーム番号の範囲チェック    
            if target_frame < 0:    
                target_frame = 0    
            elif target_frame >= self.total_frames:    
                target_frame = self.total_frames - 1    
                    
            self.set_current_frame(target_frame)    
            self.frame_input.clear()    
                
        except ValueError:    
            # 無効な入力の場合は何もしない    
            self.frame_input.clear()

    def _on_play_clicked(self):  
        """再生ボタンのクリックハンドラ"""  
        if self.play_btn.text() == "Play (Space)":  
            self.play_requested.emit()  
        else:  
            self.pause_requested.emit()  
    
    def set_play_button_state(self, is_playing: bool):  
        """再生ボタンの状態を設定"""  
        if is_playing:  
            self.play_btn.setText("Pause (Space)")  
        else:  
            self.play_btn.setText("Play (Space)")  
    
    def set_play_button_enabled(self, enabled: bool):  
        """再生ボタンの有効/無効を設定"""  
        self.play_btn.setEnabled(enabled)