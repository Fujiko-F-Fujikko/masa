# 改善されたDialog.py  
from PyQt6.QtWidgets import (  
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,  
    QLineEdit, QComboBox, QDialogButtonBox,  
    QFormLayout, QSpinBox  
)  
from DataClass import BoundingBox  
from typing import List  
  
class AnnotationInputDialog(QDialog):  
    """アノテーション追加ダイアログ（改善版）"""  
    def __init__(self, bbox: BoundingBox, parent=None, existing_labels: List[str] = None, default_label: str = ""):  
        super().__init__(parent)  
        self.setWindowTitle("アノテーション追加")  
        self.bbox = bbox  
        self.label = ""  
        self.default_label = default_label
          
        self.setup_ui(existing_labels)
      
    def setup_ui(self, existing_labels: List[str] = None):  
        layout = QVBoxLayout()  
          
        if self.bbox is not None:
            bbox_info_label = QLabel(f"BBox: ({self.bbox.x1:.2f}, {self.bbox.y1:.2f}) - ({self.bbox.x2:.2f}, {self.bbox.y2:.2f})")  
            layout.addWidget(bbox_info_label)  
          
        label_layout = QHBoxLayout()  
        label_layout.addWidget(QLabel("ラベル:"))  
        self.label_input = QLineEdit()  
        label_layout.addWidget(self.label_input)  
        layout.addLayout(label_layout)  
          
        preset_layout = QHBoxLayout()  
        preset_layout.addWidget(QLabel("プリセット:"))  
        self.preset_combo = QComboBox()  
        self.preset_combo.setEditable(True)  
          
        if existing_labels:  
            self.preset_combo.addItems(sorted(existing_labels))  
          
        self.preset_combo.currentIndexChanged.connect(self._on_preset_selected)  
        self.preset_combo.editTextChanged.connect(self._on_preset_text_changed)  
        preset_layout.addWidget(self.preset_combo)  
        layout.addLayout(preset_layout)  
          
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)  
        button_box.accepted.connect(self.accept)  
        button_box.rejected.connect(self.reject)  
        layout.addWidget(button_box)  
          
        self.setLayout(layout)  
          
        # デフォルトラベルが指定されている場合はそれを使用
        if self.default_label:
            # デフォルトラベルがプリセットに含まれている場合は選択
            if existing_labels and self.default_label in existing_labels:
                index = self.preset_combo.findText(self.default_label)
                if index >= 0:
                    self.preset_combo.setCurrentIndex(index)
            else:
                # プリセットに含まれていない場合は直接設定
                self.preset_combo.setEditText(self.default_label)
            self.label_input.setText(self.default_label)
        elif existing_labels:  
            self.preset_combo.setCurrentIndex(0)  
            self.label_input.setText(self.preset_combo.currentText())  
        else:  
            self.label_input.setText("")
      
    def _on_preset_selected(self, index: int):  
        self.label_input.setText(self.preset_combo.currentText())  
      
    def _on_preset_text_changed(self, text: str):  
        self.label_input.setText(text)  
      
    def get_label(self) -> str:  
        return self.label_input.text().strip()
