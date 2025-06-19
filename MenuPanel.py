class MenuPanel(QWidget):  
    """左側のメニューパネル"""  
      
    # シグナル定義  
    load_video_requested = pyqtSignal()  
    annotation_mode_requested = pyqtSignal(bool)  
    range_selection_requested = pyqtSignal(bool)  
    result_view_requested = pyqtSignal(bool)  
    tracking_requested = pyqtSignal()  
    export_requested = pyqtSignal(str)  # format  
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.setFixedWidth(250)  
        self.setStyleSheet("background-color: #f0f0f0; border-right: 1px solid #ccc;")  
        self.setup_ui()  
          
    def setup_ui(self):  
        layout = QVBoxLayout()  
        layout.setSpacing(10)  
        layout.setContentsMargins(10, 10, 10, 10)  
          
        # タイトル  
        title_label = QLabel("MASA Annotation Tool")  
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))  
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        layout.addWidget(title_label)  
          
        # 動画読み込みセクション  
        video_group = QGroupBox("Video")  
        video_layout = QVBoxLayout()  
          
        self.load_video_btn = QPushButton("Load Video")  
        self.load_video_btn.clicked.connect(self.load_video_requested.emit)  
        video_layout.addWidget(self.load_video_btn)  
          
        self.video_info_label = QLabel("No video loaded")  
        self.video_info_label.setWordWrap(True)  
        self.video_info_label.setStyleSheet("color: #666; font-size: 10px;")  
        video_layout.addWidget(self.video_info_label)  
          
        video_group.setLayout(video_layout)  
        layout.addWidget(video_group)  
          
        # アノテーションセクション  
        self.annotation_group = QGroupBox("Annotation")  
        annotation_layout = QVBoxLayout()  
          
        self.annotation_mode_btn = QPushButton("Manual Annotation Mode")  
        self.annotation_mode_btn.setCheckable(True)  
        self.annotation_mode_btn.clicked.connect(self._on_annotation_mode_clicked)  
        self.annotation_mode_btn.setEnabled(False)  
        annotation_layout.addWidget(self.annotation_mode_btn)  
          
        self.annotation_count_label = QLabel("Annotations: 0")  
        self.annotation_count_label.setStyleSheet("color: #666; font-size: 10px;")  
        annotation_layout.addWidget(self.annotation_count_label)  
          
        self.annotation_group.setLayout(annotation_layout)  
        layout.addWidget(self.annotation_group)  
          
        # 範囲選択セクション  
        range_group = QGroupBox("Frame Range")  
        range_layout = QVBoxLayout()  
          
        self.range_selection_btn = QPushButton("Select Range Mode")  
        self.range_selection_btn.setCheckable(True)  
        self.range_selection_btn.clicked.connect(self._on_range_selection_clicked)  
        self.range_selection_btn.setEnabled(False)  
        range_layout.addWidget(self.range_selection_btn)  
          
        self.range_info_label = QLabel("Range: Not selected")  
        self.range_info_label.setStyleSheet("color: #666; font-size: 10px;")  
        range_layout.addWidget(self.range_info_label)  
          
        range_group.setLayout(range_layout)  
        layout.addWidget(range_group)  
          
        # 自動追跡セクション  
        tracking_group = QGroupBox("Auto Tracking")  
        tracking_layout = QVBoxLayout()  
          
        self.tracking_btn = QPushButton("Start Auto Tracking")  
        self.tracking_btn.clicked.connect(self.tracking_requested.emit)  
        self.tracking_btn.setEnabled(False)  
        tracking_layout.addWidget(self.tracking_btn)  
          
        self.tracking_progress_label = QLabel("")  
        self.tracking_progress_label.setStyleSheet("color: #666; font-size: 10px;")  
        tracking_layout.addWidget(self.tracking_progress_label)  
          
        tracking_group.setLayout(tracking_layout)  
        layout.addWidget(tracking_group)  
          
        # 結果確認セクション  
        result_group = QGroupBox("Results")  
        result_layout = QVBoxLayout()  
          
        self.result_view_btn = QPushButton("View Results Mode")  
        self.result_view_btn.setCheckable(True)  
        self.result_view_btn.clicked.connect(self._on_result_view_clicked)  
        self.result_view_btn.setEnabled(False)  
        result_layout.addWidget(self.result_view_btn)  
          
        # 表示オプション  
        self.show_manual_cb = QCheckBox("Show Manual")  
        self.show_manual_cb.setChecked(True)  
        result_layout.addWidget(self.show_manual_cb)  
          
        self.show_auto_cb = QCheckBox("Show Auto")  
        self.show_auto_cb.setChecked(True)  
        result_layout.addWidget(self.show_auto_cb)  
          
        self.show_ids_cb = QCheckBox("Show IDs")  
        self.show_ids_cb.setChecked(True)  
        result_layout.addWidget(self.show_ids_cb)  
          
        self.show_confidence_cb = QCheckBox("Show Confidence")  
        self.show_confidence_cb.setChecked(True)  
        result_layout.addWidget(self.show_confidence_cb)  
        
        checkbox_style = """  
        QCheckBox {  
            color: #333333;  
            font-weight: bold;  
        }  
        QCheckBox::indicator {  
            width: 18px;  
            height: 18px;  
        }  
        QCheckBox::indicator:unchecked {  
            background-color: #ffffff;  
            border: 2px solid #cccccc;  
            border-radius: 3px;  
        }  
        QCheckBox::indicator:checked {  
            background-color: #4CAF50;  
            border: 2px solid #45a049;  
            border-radius: 3px;  
        }  
        QCheckBox::indicator:checked:hover {  
            background-color: #45a049;  
        }  
        QCheckBox::indicator:unchecked:hover {  
            border: 2px solid #999999;  
        }  
        """  
          
        # 各チェックボックスにスタイルを適用  
        self.show_manual_cb.setStyleSheet(checkbox_style)  
        self.show_auto_cb.setStyleSheet(checkbox_style)  
        self.show_ids_cb.setStyleSheet(checkbox_style)  
        self.show_confidence_cb.setStyleSheet(checkbox_style)
          
        result_group.setLayout(result_layout)  
        layout.addWidget(result_group)  
          
        # エクスポートセクション  
        export_group = QGroupBox("Export")  
        export_layout = QVBoxLayout()  
          
        self.export_json_btn = QPushButton("Export JSON")  
        self.export_json_btn.clicked.connect(lambda: self.export_requested.emit("json"))  
        self.export_json_btn.setEnabled(False)  
        export_layout.addWidget(self.export_json_btn)  
          
        self.export_coco_btn = QPushButton("Export COCO")  
        self.export_coco_btn.clicked.connect(lambda: self.export_requested.emit("coco"))  
        self.export_coco_btn.setEnabled(False)  
        export_layout.addWidget(self.export_coco_btn)  
          
        export_group.setLayout(export_layout)  
        layout.addWidget(export_group)  
          
        # スペーサー  
        layout.addStretch()  
          
        self.setLayout(layout)  
      
    def _on_annotation_mode_clicked(self, checked):  
        if checked:  
            self.range_selection_btn.setChecked(False)  
            self.result_view_btn.setChecked(False)  
        self.annotation_mode_requested.emit(checked)  
      
    def _on_range_selection_clicked(self, checked):  
        if checked:  
            self.annotation_mode_btn.setChecked(False)  
            self.result_view_btn.setChecked(False)  
        self.range_selection_requested.emit(checked)  
      
    def _on_result_view_clicked(self, checked):  
        if checked:  
            self.annotation_mode_btn.setChecked(False)  
            self.range_selection_btn.setChecked(False)  
        self.result_view_requested.emit(checked)  
      
    def update_video_info(self, video_path: str, total_frames: int):  
        """動画情報を更新"""  
        filename = Path(video_path).name  
        self.video_info_label.setText(f"{filename}\n{total_frames} frames")  
          
        # ボタンを有効化  
        self.annotation_mode_btn.setEnabled(True)  
        self.range_selection_btn.setEnabled(True)  
      
    def update_annotation_count(self, count: int):  
        """アノテーション数を更新"""  
        self.annotation_count_label.setText(f"Annotations: {count}")  
        self.tracking_btn.setEnabled(count > 0)  
      
    def update_range_info(self, start_frame: int, end_frame: int):  
        """範囲情報を更新"""  
        self.range_info_label.setText(f"Range: {start_frame} - {end_frame}")  
      
    def update_tracking_progress(self, progress_text: str):  
        """追跡進捗を更新"""  
        self.tracking_progress_label.setText(progress_text)  
      
    def enable_result_view(self, enabled: bool):  
        """結果確認モードを有効化"""  
        self.result_view_btn.setEnabled(enabled)  
        self.export_json_btn.setEnabled(enabled)  
        self.export_coco_btn.setEnabled(enabled)  
      
    def get_display_options(self) -> Dict[str, bool]:  
        """表示オプションを取得"""  
        return {  
            'show_manual': self.show_manual_cb.isChecked(),  
            'show_auto': self.show_auto_cb.isChecked(),  
            'show_ids': self.show_ids_cb.isChecked(),  
            'show_confidence': self.show_confidence_cb.isChecked()  
        }  

class EnhancedMenuPanel(MenuPanel):  
    """複数フレーム機能付きメニューパネル"""  
      
    multi_frame_mode_requested = pyqtSignal(bool, str)  # enabled, label  
      
    def setup_ui(self):  
        super().setup_ui()  
          
        # 親クラスで定義されたannotation_groupを使用  
        if hasattr(self, 'annotation_group'):  
            layout = self.annotation_group.layout()  
              
            self.multi_frame_btn = QPushButton("Multi-Frame Mode")  
            self.multi_frame_btn.setCheckable(True)  
            self.multi_frame_btn.clicked.connect(self._on_multi_frame_clicked)  
            self.multi_frame_btn.setEnabled(False)  
            layout.addWidget(self.multi_frame_btn)  
              
            # ラベル入力フィールド  
            self.multi_frame_label_input = QLineEdit()  
            self.multi_frame_label_input.setPlaceholderText("Object label")  
            self.multi_frame_label_input.setEnabled(False)  
            layout.addWidget(self.multi_frame_label_input)  
              
            # 完了ボタン  
            self.complete_multi_frame_btn = QPushButton("Complete Multi-Frame")  
            self.complete_multi_frame_btn.clicked.connect(self._on_complete_multi_frame)  
            self.complete_multi_frame_btn.setEnabled(False)  
            layout.addWidget(self.complete_multi_frame_btn)  
      
    def _on_multi_frame_clicked(self, checked):  
        if checked:  
            label = self.multi_frame_label_input.text().strip()  
            if not label:  
                QMessageBox.warning(self, "Warning", "Please enter an object label first")  
                self.multi_frame_btn.setChecked(False)  
                return  
              
            # 他のモードを無効化  
            self.annotation_mode_btn.setChecked(False)  
            self.range_selection_btn.setChecked(False)  
            self.result_view_btn.setChecked(False)  
              
            self.multi_frame_label_input.setEnabled(False)  
            self.complete_multi_frame_btn.setEnabled(True)  
        else:  
            self.multi_frame_label_input.setEnabled(True)  
            self.complete_multi_frame_btn.setEnabled(False)  
          
        self.multi_frame_mode_requested.emit(checked, self.multi_frame_label_input.text().strip())  
      
    def _on_complete_multi_frame(self):  
        # 複数フレームアノテーション完了シグナルを発行  
        self.multi_frame_btn.setChecked(False)  
        self._on_multi_frame_clicked(False)

    def update_video_info(self, video_path: str, total_frames: int):  
        """動画情報を更新（Multi-Frame Modeボタンも有効化）"""  
        # 親クラスのメソッドを呼び出し  
        super().update_video_info(video_path, total_frames)  
          
        # Multi-Frame Modeボタンを有効化  
        if hasattr(self, 'multi_frame_btn'):  
            self.multi_frame_btn.setEnabled(True)  
        if hasattr(self, 'multi_frame_label_input'):  
            self.multi_frame_label_input.setEnabled(True)

