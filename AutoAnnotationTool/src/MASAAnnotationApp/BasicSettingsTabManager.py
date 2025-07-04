# BasicSettingsTabManager.py
"""
基本設定タブの管理を担当
MenuPanelから基本設定関連のUIと処理を分離
"""
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QPushButton, QLabel, QFileDialog, QProgressBar
)
from PyQt6.QtCore import pyqtSignal

from MASAApplicationService import MASAApplicationService
from ErrorHandler import ErrorHandler

class BasicSettingsTabManager(QWidget):
    """基本設定タブのUI管理とファイル操作"""
    
    # シグナル定義
    load_video_requested = pyqtSignal(str)
    load_json_requested = pyqtSignal(str)
    export_requested = pyqtSignal(str)
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    config_changed = pyqtSignal(str, object, str)
    
    def __init__(self, app_service: MASAApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service
        
        # UI要素
        self.video_info_label: Optional[QLabel] = None
        self.json_info_label: Optional[QLabel] = None
        self.load_video_btn: Optional[QPushButton] = None
        self.load_json_btn: Optional[QPushButton] = None
        self.save_masa_json_btn: Optional[QPushButton] = None
        self.save_coco_json_btn: Optional[QPushButton] = None
        self.play_btn: Optional[QPushButton] = None
        self.pause_btn: Optional[QPushButton] = None
        self.export_progress_bar: Optional[QProgressBar] = None
        self.export_progress_label: Optional[QLabel] = None
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """UIを構築"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # ファイル操作グループ
        self.setup_file_operations(layout)
        
        # 再生コントロールグループ
        self.setup_playback_controls(layout)
        
        # エクスポート進捗グループ
        self.setup_export_progress(layout)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def setup_file_operations(self, parent_layout):
        """ファイル操作UIを構築"""
        file_group = QGroupBox("File Operations")
        file_layout = QVBoxLayout()
        
        # 動画読み込み
        video_section = QVBoxLayout()
        self.load_video_btn = QPushButton("Load Video")
        self.load_video_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.video_info_label = QLabel("No video loaded")
        self.video_info_label.setWordWrap(True)
        self.video_info_label.setStyleSheet("color: #666; font-size: 11px;")
        
        video_section.addWidget(self.load_video_btn)
        video_section.addWidget(self.video_info_label)
        file_layout.addLayout(video_section)
        
        # JSON読み込み
        json_section = QVBoxLayout()
        self.load_json_btn = QPushButton("Load JSON")
        self.load_json_btn.setEnabled(False)
        self.json_info_label = QLabel("No JSON loaded")
        self.json_info_label.setWordWrap(True)
        self.json_info_label.setStyleSheet("color: #666; font-size: 11px;")
        
        json_section.addWidget(self.load_json_btn)
        json_section.addWidget(self.json_info_label)
        file_layout.addLayout(json_section)
        
        # エクスポートボタン
        export_layout = QHBoxLayout()
        self.save_masa_json_btn = QPushButton("Save MASA JSON")
        self.save_masa_json_btn.setEnabled(False)
        self.save_coco_json_btn = QPushButton("Save COCO JSON")
        self.save_coco_json_btn.setEnabled(False)
        
        export_layout.addWidget(self.save_masa_json_btn)
        export_layout.addWidget(self.save_coco_json_btn)
        file_layout.addLayout(export_layout)
        
        file_group.setLayout(file_layout)
        parent_layout.addWidget(file_group)
        
    def setup_playback_controls(self, parent_layout):
        """再生コントロールUIを構築"""
        playback_group = QGroupBox("Playback Controls")
        playback_layout = QHBoxLayout()
        
        self.play_btn = QPushButton("Play")
        self.play_btn.setEnabled(False)
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setEnabled(False)
        
        playback_layout.addWidget(self.play_btn)
        playback_layout.addWidget(self.pause_btn)
        
        playback_group.setLayout(playback_layout)
        parent_layout.addWidget(playback_group)
        
    def setup_export_progress(self, parent_layout):
        """エクスポート進捗UIを構築"""
        progress_group = QGroupBox("Export Progress")
        progress_layout = QVBoxLayout()
        
        self.export_progress_label = QLabel("")
        self.export_progress_label.setStyleSheet("color: #666; font-size: 11px;")
        
        self.export_progress_bar = QProgressBar()
        self.export_progress_bar.setVisible(False)
        
        progress_layout.addWidget(self.export_progress_label)
        progress_layout.addWidget(self.export_progress_bar)
        
        progress_group.setLayout(progress_layout)
        parent_layout.addWidget(progress_group)
        
    def connect_signals(self):
        """シグナル接続を設定"""
        self.load_video_btn.clicked.connect(self._on_load_video_clicked)
        self.load_json_btn.clicked.connect(self._on_load_json_clicked)
        self.save_masa_json_btn.clicked.connect(self._on_save_masa_json_clicked)
        self.save_coco_json_btn.clicked.connect(self._on_save_coco_json_clicked)
        self.play_btn.clicked.connect(self._on_play_clicked)
        self.pause_btn.clicked.connect(self._on_pause_clicked)
        
    # ===== イベントハンドラ =====
    
    def _on_load_video_clicked(self):
        """動画読み込みボタンクリック"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"
        )
        if file_path:
            self.load_video_requested.emit(file_path)
            
    def _on_load_json_clicked(self):
        """JSON読み込みボタンクリック"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select JSON File", "",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self.load_json_requested.emit(file_path)
            
    def _on_save_masa_json_clicked(self):
        """MASA JSON保存ボタンクリック"""
        self.export_requested.emit("masa")
        
    def _on_save_coco_json_clicked(self):
        """COCO JSON保存ボタンクリック"""
        self.export_requested.emit("coco")
        
    def _on_play_clicked(self):
        """再生ボタンクリック"""
        self.play_requested.emit()
        
    def _on_pause_clicked(self):
        """一時停止ボタンクリック"""
        self.pause_requested.emit()
        
    # ===== 状態更新メソッド =====
    
    def update_video_info(self, path: str, total_frames: int):
        """動画情報を更新"""
        if self.video_info_label:
            video_name = path.split('/')[-1]  # ファイル名のみ表示
            self.video_info_label.setText(f"Video: {video_name}\nFrames: {total_frames}")
            
        # 動画読み込み後はJSONボタンと再生ボタンを有効化
        if self.load_json_btn:
            self.load_json_btn.setEnabled(True)
        if self.play_btn:
            self.play_btn.setEnabled(True)
        if self.pause_btn:
            self.pause_btn.setEnabled(True)
            
    def update_json_info(self, path: str, annotation_count: int):
        """JSON情報を更新"""
        if self.json_info_label:
            json_name = path.split('/')[-1]  # ファイル名のみ表示
            self.json_info_label.setText(f"JSON: {json_name}\nAnnotations: {annotation_count}")
            
        # JSON読み込み後はエクスポートボタンを有効化
        if self.save_masa_json_btn:
            self.save_masa_json_btn.setEnabled(True)
        if self.save_coco_json_btn:
            self.save_coco_json_btn.setEnabled(True)
            
    def update_export_progress(self, message: str, progress: int = -1):
        """エクスポート進捗を更新"""
        if self.export_progress_label:
            self.export_progress_label.setText(message)
            
        if self.export_progress_bar:
            if progress >= 0:
                self.export_progress_bar.setVisible(True)
                self.export_progress_bar.setValue(progress)
            else:
                if message == "":
                    self.export_progress_bar.setVisible(False)
                    
    def reset_playback_button(self):
        """再生ボタンをリセット（一時停止後）"""
        # 必要に応じて再生ボタンの状態をリセット
        pass
        
    def get_display_options(self) -> dict:
        """表示オプションを取得（将来の拡張用）"""
        return {}
        
    def set_buttons_enabled(self, enabled: bool):
        """ボタンの有効/無効を設定"""
        if self.load_video_btn:
            self.load_video_btn.setEnabled(enabled)
        if self.load_json_btn and enabled:
            # JSON読み込みは動画読み込み後のみ有効
            video_manager = self.app_service.get_video_manager()
            self.load_json_btn.setEnabled(video_manager is not None)
