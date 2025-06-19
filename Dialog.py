from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QComboBox, QDialogButtonBox,
    QFormLayout, QSpinBox
)
from DataClass import BoundingBox

class AnnotationInputDialog(QDialog):  
    """アノテーション入力ダイアログ"""  
      
    def __init__(self, bbox: BoundingBox, parent=None):  
        super().__init__(parent)  
        self.bbox = bbox  
        self.label = ""  
        self.setup_ui()  
          
    def setup_ui(self):  
        self.setWindowTitle("Add Annotation")  
        self.setModal(True)  
          
        layout = QVBoxLayout()  
          
        # バウンディングボックス情報  
        bbox_info = QLabel(f"Bounding Box: ({self.bbox.x1:.0f}, {self.bbox.y1:.0f}) to ({self.bbox.x2:.0f}, {self.bbox.y2:.0f})")  
        layout.addWidget(bbox_info)  
          
        # ラベル入力  
        label_layout = QHBoxLayout()  
        label_layout.addWidget(QLabel("Label:"))  
          
        self.label_input = QLineEdit()  
        self.label_input.setPlaceholderText("Enter object label (e.g., person, car)")  
        label_layout.addWidget(self.label_input)  
          
        # プリセット  
        self.preset_combo = QComboBox()  
        self.preset_combo.addItems(["", "person", "car", "bicycle", "dog", "cat", "bird"])  
        self.preset_combo.currentTextChanged.connect(self.on_preset_selected)  
        label_layout.addWidget(self.preset_combo)  
          
        layout.addLayout(label_layout)  
          
        # ボタン  
        buttons = QDialogButtonBox(  
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel  
        )  
        buttons.accepted.connect(self.accept)  
        buttons.rejected.connect(self.reject)  
        layout.addWidget(buttons)  
          
        self.setLayout(layout)  
          
        # フォーカスをラベル入力に設定  
        self.label_input.setFocus()  
      
    def on_preset_selected(self, text):  
        if text:  
            self.label_input.setText(text)  
      
    def get_label(self) -> str:  
        return self.label_input.text().strip()

class TrackingSettingsDialog(QDialog):  
    """自動追跡設定ダイアログ"""  
      
    def __init__(self, total_frames: int, start_frame: int, parent=None):  
        super().__init__(parent)  
        self.total_frames = total_frames  
        self.start_frame = start_frame  
        self.setup_ui()  
          
    def setup_ui(self):  
        self.setWindowTitle("Auto Tracking Settings")  
        self.setModal(True)  
          
        layout = QFormLayout()  
          
        # 開始フレーム表示（読み取り専用）  
        self.start_frame_label = QLabel(str(self.start_frame))  
        layout.addRow("Start Frame:", self.start_frame_label)  
          
        # 終了フレーム指定  
        self.end_frame_spin = QSpinBox()  
        self.end_frame_spin.setMinimum(self.start_frame + 1)  
        self.end_frame_spin.setMaximum(self.total_frames - 1)  
        self.end_frame_spin.setValue(min(self.start_frame + 100, self.total_frames - 1))  
        layout.addRow("End Frame:", self.end_frame_spin)  
          
        # フレーム数表示  
        self.frame_count_label = QLabel()  
        self.update_frame_count()  
        self.end_frame_spin.valueChanged.connect(self.update_frame_count)  
        layout.addRow("Total Frames to Process:", self.frame_count_label)  
          
        # 推定処理時間表示  
        self.time_estimate_label = QLabel()  
        self.update_time_estimate()  
        self.end_frame_spin.valueChanged.connect(self.update_time_estimate)  
        layout.addRow("Estimated Time:", self.time_estimate_label)  
          
        # ボタン  
        buttons = QDialogButtonBox(  
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel  
        )  
        buttons.accepted.connect(self.accept)  
        buttons.rejected.connect(self.reject)  
        layout.addRow(buttons)  
          
        self.setLayout(layout)  
      
    def update_frame_count(self):  
        frame_count = self.end_frame_spin.value() - self.start_frame + 1  
        self.frame_count_label.setText(str(frame_count))  
      
    def update_time_estimate(self):  
        frame_count = self.end_frame_spin.value() - self.start_frame + 1  
        # 1フレームあたり約0.1-0.5秒と仮定  
        estimated_seconds = frame_count * 0.3  
        if estimated_seconds < 60:  
            time_text = f"{estimated_seconds:.1f} seconds"  
        else:  
            minutes = estimated_seconds / 60  
            time_text = f"{minutes:.1f} minutes"  
        self.time_estimate_label.setText(time_text)  
      
    def get_end_frame(self):  
        return self.end_frame_spin.value()
