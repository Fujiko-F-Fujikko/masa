# BasicTabWidget.py  
from typing import Dict, List, Any, Optional  
from pathlib import Path  
from datetime import datetime  
  
from PyQt6.QtWidgets import (  
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,  
    QPushButton, QGroupBox, QCheckBox, QLineEdit,  
    QMessageBox, QComboBox, QFileDialog,  
    QDoubleSpinBox  
)  
from PyQt6.QtCore import Qt, pyqtSignal  
from PyQt6.QtGui import QFont, QKeyEvent  
  
from ConfigManager import ConfigManager  
from ErrorHandler import ErrorHandler  
from VideoManager import VideoManager  
from VideoPlaybackController import VideoPlaybackController  
from ExportService import ExportService  
from COCOExportWorker import COCOExportWorker  
  
class BasicTabWidget(QWidget):  
    """基本設定タブウィジェット（ファイル操作・再生制御・表示設定）"""  
      
    # シグナル定義  
    load_video_requested = pyqtSignal(str)  
    load_json_requested = pyqtSignal(str)  
    export_requested = pyqtSignal(str)  
    play_requested = pyqtSignal()  
    pause_requested = pyqtSignal()  
    config_changed = pyqtSignal(str, object, str)  
      
    def __init__(self, config_manager: ConfigManager, annotation_repository, command_manager, main_widget, parent=None):  
        super().__init__(parent)  
        self.config_manager = config_manager  
        self.annotation_repository = annotation_repository  
        self.command_manager = command_manager  
        self.main_widget = main_widget  # MASAAnnotationWidgetへの参照  
        self.parent_menu_panel = parent  # MenuPanelへの参照  
          
        self.export_service = ExportService()  
        self.export_worker = None  
          
        self.setup_ui()  
        self._connect_config_signals()  
      
    def setup_ui(self):  
        layout = QVBoxLayout()  
        layout.setContentsMargins(5, 5, 5, 5)  
          
        # ファイル操作グループ  
        file_group = QGroupBox("File Operations")  
        file_layout = QVBoxLayout()  
          
        self.load_video_btn = QPushButton("Load Video (Ctrl+O)")  
        self.load_video_btn.clicked.connect(self._on_load_video_clicked)  
        file_layout.addWidget(self.load_video_btn)  
          
        self.video_info_label = QLabel("No video loaded")  
        self.video_info_label.setWordWrap(True)  
        file_layout.addWidget(self.video_info_label)  
          
        self.load_json_btn = QPushButton("Load JSON (Ctrl+L)")  
        self.load_json_btn.clicked.connect(self._on_load_json_clicked)  
        file_layout.addWidget(self.load_json_btn)  
          
        self.save_masa_json_btn = QPushButton("Save MASA JSON (Ctrl+S)")  
        self.save_masa_json_btn.clicked.connect(self._on_export_masa_clicked)  
        self.save_masa_json_btn.setEnabled(False)  
        file_layout.addWidget(self.save_masa_json_btn)  
          
        self.save_coco_json_btn = QPushButton("Save COCO JSON (Ctrl+Shift+S)")  
        self.save_coco_json_btn.clicked.connect(self._on_export_coco_clicked)  
        self.save_coco_json_btn.setEnabled(False)  
        file_layout.addWidget(self.save_coco_json_btn)  
          
        self.json_info_label = QLabel("No JSON loaded")  
        self.json_info_label.setWordWrap(True)  
        file_layout.addWidget(self.json_info_label)  
          
        # エクスポート進捗表示ラベル  
        self.export_progress_label = QLabel("")  
        file_layout.addWidget(self.export_progress_label)  
          
        file_group.setLayout(file_layout)  
        layout.addWidget(file_group)  
          
        # 再生コントロールグループ  
        playback_group = QGroupBox("Playback Controls")  
        playback_layout = QVBoxLayout()  
          
        self.play_btn = QPushButton("Play (Space)")  
        self.play_btn.setEnabled(False)  
        self.play_btn.clicked.connect(self._on_play_clicked)  
        playback_layout.addWidget(self.play_btn)  
          
        self.frame_label = QLabel("Frame: 0/0")  
        playback_layout.addWidget(self.frame_label)  
          
        playback_group.setLayout(playback_layout)  
        layout.addWidget(playback_group)  
          
        # 表示設定グループ  
        display_group = QGroupBox("Display Settings")  
        display_layout = QVBoxLayout()  
          
        self.show_manual_cb = QCheckBox("Show Manual Annotations")  
        self.show_manual_cb.setChecked(True)  
        self.show_manual_cb.stateChanged.connect(self._on_display_option_changed)  
        display_layout.addWidget(self.show_manual_cb)  
          
        self.show_auto_cb = QCheckBox("Show Auto Annotations")  
        self.show_auto_cb.setChecked(True)  
        self.show_auto_cb.stateChanged.connect(self._on_display_option_changed)  
        display_layout.addWidget(self.show_auto_cb)  
          
        self.show_ids_cb = QCheckBox("Show Track ID")  
        self.show_ids_cb.setChecked(True)  
        self.show_ids_cb.stateChanged.connect(self._on_display_option_changed)  
        display_layout.addWidget(self.show_ids_cb)  
          
        self.show_confidence_cb = QCheckBox("Show Confidence")  
        self.show_confidence_cb.setChecked(True)  
        self.show_confidence_cb.stateChanged.connect(self._on_display_option_changed)  
        display_layout.addWidget(self.show_confidence_cb)  
          
        # スコア閾値設定  
        threshold_layout = QHBoxLayout()  
        threshold_layout.addWidget(QLabel("Score Threshold:"))  
          
        self.score_threshold_spinbox = QDoubleSpinBox()  
        self.score_threshold_spinbox.setRange(0.0, 1.0)  
        self.score_threshold_spinbox.setSingleStep(0.1)  
        self.score_threshold_spinbox.setValue(0.2)  
        self.score_threshold_spinbox.valueChanged.connect(self._on_score_threshold_changed)  
        threshold_layout.addWidget(self.score_threshold_spinbox)  
          
        display_layout.addLayout(threshold_layout)  
          
        # チェックボックスのスタイル設定  
        simple_checkbox_style = """  
        QCheckBox::indicator:checked {  
            background-color: white;  
            border: 2px solid #4CAF50;  
            background-image: url(file:///../AutoAnnotationTool/resources/checkmark_green_thick.svg);  
            background-repeat: no-repeat;  
            background-position: center;  
        }  
        QCheckBox::indicator:unchecked {  
            background-color: white;  
            border: 2px solid #ccc;  
        }  
        """  
        self.show_manual_cb.setStyleSheet(simple_checkbox_style)  
        self.show_auto_cb.setStyleSheet(simple_checkbox_style)  
        self.show_ids_cb.setStyleSheet(simple_checkbox_style)  
        self.show_confidence_cb.setStyleSheet(simple_checkbox_style)  
          
        display_group.setLayout(display_layout)  
        layout.addWidget(display_group)  
          
        layout.addStretch()  
        self.setLayout(layout)  
      
    def _connect_config_signals(self):  
        """ConfigManagerからの設定変更シグナルを接続"""  
        self.config_manager.add_observer(self._on_config_changed)  
      
    def _on_config_changed(self, key: str, value: object, config_type: str):  
        """ConfigManagerからの設定変更を処理"""  
        if config_type == "display":  
            if key == "score_threshold":  
                self.score_threshold_spinbox.setValue(value)  
            elif key == "show_manual_annotations":  
                self.show_manual_cb.setChecked(value)  
            elif key == "show_auto_annotations":  
                self.show_auto_cb.setChecked(value)  
            elif key == "show_ids":  
                self.show_ids_cb.setChecked(value)  
            elif key == "show_confidence":  
                self.show_confidence_cb.setChecked(value)  
      
    # ファイル操作関連メソッド（MASAAnnotationWidgetから移動）  
    @ErrorHandler.handle_with_dialog("Video Load Error")  
    def _on_load_video_clicked(self, _: str = ""):  
        """動画ファイル読み込みボタンのクリックハンドラ"""  
        file_path, _ = QFileDialog.getOpenFileName(  
            self, "Select Video File", "",  
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"  
        )  
        if file_path:  
            self.load_video(file_path)  
      
    @ErrorHandler.handle_with_dialog("JSON Load Error")  
    def _on_load_json_clicked(self, _: str = ""):  
        """JSONファイル読み込みボタンのクリックハンドラ"""  
        file_path, _ = QFileDialog.getOpenFileName(  
            self, "Select JSON Annotation File", "",  
            "JSON Files (*.json);;All Files (*)"  
        )  
        if file_path:  
            self.load_json_annotations(file_path)  
      
    def _on_export_masa_clicked(self):  
        """MASA JSON エクスポートボタンのクリックハンドラ"""  
        self.export_annotations("masa")  
      
    def _on_export_coco_clicked(self):  
        """COCO JSON エクスポートボタンのクリックハンドラ"""  
        self.export_annotations("coco")  
      
    def load_video(self, file_path: str):  
        """動画ファイルを読み込み（内部処理版）"""  
        try:  
            # 既存のVideoManagerがあれば解放  
            if self.main_widget.video_manager:  
                self.main_widget.video_manager.release()  
                self.main_widget.video_manager = None  
              
            self.main_widget.video_manager = VideoManager(file_path)  
            if self.main_widget.video_manager.load_video():  
                self.main_widget.playback_controller = VideoPlaybackController(self.main_widget.video_manager)  
                self.main_widget.playback_controller.frame_updated.connect(self.main_widget.on_playback_frame_changed)  
                self.main_widget.playback_controller.playback_finished.connect(self.main_widget.on_playback_finished)  
                  
                self.main_widget.playback_controller.set_fps(self.main_widget.video_manager.get_fps())  
                  
                self.main_widget.video_preview.set_video_manager(self.main_widget.video_manager)  
                self.main_widget.video_preview.set_annotation_repository(self.main_widget.annotation_repository)  
                self.main_widget.video_control.set_total_frames(self.main_widget.video_manager.get_total_frames())  
                self.main_widget.video_control.set_current_frame(0)  
                  
                self.update_video_info(file_path, self.main_widget.video_manager.get_total_frames())  
                self.play_btn.setEnabled(True)  
                  
                ErrorHandler.show_info_dialog(f"Video loaded: {file_path}", "Success")  
            else:  
                ErrorHandler.show_error_dialog("Failed to load video file", "Error")  
        except Exception as e:  
            ErrorHandler.show_error_dialog(f"Failed to load video: {str(e)}", "Load Error")  
      
    def load_json_annotations(self, file_path: str):  
        """JSONアノテーションファイルを読み込み（内部処理版）"""  
        try:  
            if not self.main_widget.video_manager:  
                ErrorHandler.show_warning_dialog("Please load a video file first", "Warning")  
                return  
              
            loaded_annotations = self.export_service.import_json(file_path)  
            if loaded_annotations:  
                self.main_widget.annotation_repository.clear()  
                for frame_id, frame_ann in loaded_annotations.items():  
                    for obj_ann in frame_ann.objects:  
                        self.main_widget.annotation_repository.add_annotation(obj_ann)  
                  
                self.update_json_info(file_path, self.main_widget.annotation_repository.get_statistics()["total"])  
                self.main_widget.update_annotation_count()  
                self.main_widget.video_preview.set_mode('view')  
                  
                if hasattr(self.main_widget.menu_panel, 'annotation_tab'):  
                    self.main_widget.menu_panel.annotation_tab.edit_mode_btn.setChecked(False)  
                  
                ErrorHandler.show_info_dialog(  
                    f"Successfully loaded {self.main_widget.annotation_repository.get_statistics()['total']} annotations from JSON file",  
                    "JSON Loaded"  
                )  
                  
                # JSON読み込み完了後にオブジェクト一覧を更新  
                current_frame = self.main_widget.video_control.current_frame  
                frame_annotation = self.main_widget.annotation_repository.get_annotations(current_frame)  
                self.main_widget.menu_panel.update_current_frame_objects(current_frame, frame_annotation)  
            else:  
                ErrorHandler.show_error_dialog("Failed to load JSON annotation file", "Error")  
        except Exception as e:  
            ErrorHandler.show_error_dialog(f"Failed to load JSON: {str(e)}", "Load Error")  
      
    def export_annotations(self, format_type: str):  
        """アノテーションをエクスポート（内部処理版）"""  
        try:  
            if not self.main_widget.annotation_repository.frame_annotations:  
                ErrorHandler.show_warning_dialog("No annotations to export", "Warning")  
                return  
              
            if not self.main_widget.video_manager:  
                ErrorHandler.show_warning_dialog("Video not loaded. Cannot export video-related metadata.", "Warning")  
                return  
              
            # タイムスタンプ付きのデフォルトファイル名を生成  
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  
            default_filename = f"annotations_{timestamp}.json"  
              
            file_dialog_title = f"Save {format_type.upper()} Annotations"  
            file_path, _ = QFileDialog.getSaveFileName(  
                self, file_dialog_title, default_filename,  
                "JSON Files (*.json);;All Files (*)"  
            )  
              
            if file_path:  
                if format_type == "masa":  
                    self.export_service.export_masa_json(  
                        self.main_widget.annotation_repository.frame_annotations,  
                        self.main_widget.video_manager.video_path,  
                        file_path  
                    )  
                    ErrorHandler.show_info_dialog(f"MASA annotations exported to {file_path}", "Export Complete")  
                      
                elif format_type == "coco":  
                    # 進捗表示を開始  
                    self.update_export_progress("Exporting COCO JSON...")  
                      
                    # スコア閾値でフィルタリングされたアノテーションを作成  
                    filtered_annotations = self.main_widget._filter_annotations_by_score_threshold()  
                      
                    # ワーカースレッドでエクスポート実行  
                    self.export_worker = COCOExportWorker(  
                        self.export_service,  
                        filtered_annotations,  
                        self.main_widget.video_manager.video_path,  
                        file_path,  
                        self.main_widget.video_manager  
                    )  
                    self.export_worker.progress_updated.connect(self.main_widget.on_export_progress)  
                    self.export_worker.export_completed.connect(self.main_widget.on_export_completed)  
                    self.export_worker.error_occurred.connect(self.main_widget.on_export_error)  
                    self.export_worker.start()  
                else:  
                    ErrorHandler.show_error_dialog(f"Unsupported export format: {format_type}", "Error")  
        except Exception as e:  
            ErrorHandler.show_error_dialog(f"Failed to export: {str(e)}", "Export Error")  
      
    def _on_play_clicked(self):  
        """再生ボタンのクリックハンドラ"""  
        if self.play_btn.text() == "Play (Space)":  
            self.play_requested.emit()  
        else:  
            self.pause_requested.emit()  
      
    def _on_display_option_changed(self):  
        """表示オプション変更時の処理"""  
        display_options = {  
            "show_manual_annotations": self.show_manual_cb.isChecked(),  
            "show_auto_annotations": self.show_auto_cb.isChecked(),  
            "show_ids": self.show_ids_cb.isChecked(),  
            "show_confidence": self.show_confidence_cb.isChecked()  
        }  
          
        for key, value in display_options.items():  
            self.config_manager.update_config(key, value, config_type="display")  
            self.config_changed.emit(key, value, "display")  
      
    def _on_score_threshold_changed(self, value: float):  
        """スコア閾値変更時の処理"""  
        self.config_manager.update_config("score_threshold", value, config_type="display")  
        self.config_changed.emit("score_threshold", value, "display")  
      
    # UI更新メソッド  
    def update_video_info(self, video_path: str, total_frames: int):  
        """動画情報を更新"""  
        filename = Path(video_path).name  
        self.video_info_label.setText(f"{filename}\n{total_frames} frames")  
        self.save_masa_json_btn.setEnabled(True)  
        self.save_coco_json_btn.setEnabled(True)  
      
    def update_json_info(self, json_path: str, annotation_count: int):  
        """JSON情報を更新"""  
        filename = Path(json_path).name  
        self.json_info_label.setText(f"{filename}\n{annotation_count} annotations loaded")  
        self.save_masa_json_btn.setEnabled(True)  
        self.save_coco_json_btn.setEnabled(True)  
      
    def update_export_progress(self, message: str):  
        """エクスポート進捗を更新"""  
        self.export_progress_label.setText(message)  
      
    def update_frame_info(self, current_frame: int, total_frames: int):  
        """フレーム情報を更新"""  
        self.frame_label.setText(f"Frame: {current_frame}/{total_frames - 1}")  
      
    def set_play_button_state(self, is_playing: bool):  
        """再生ボタンの状態を設定"""  
        if is_playing:  
            self.play_btn.setText("Pause (Space)")  
        else:  
            self.play_btn.setText("Play (Space)")  
      
    def get_display_options(self):  
        """現在の表示オプションを取得"""  
        return {  
            "show_manual_annotations": self.show_manual_cb.isChecked(),  
            "show_auto_annotations": self.show_auto_cb.isChecked(),  
            "show_ids": self.show_ids_cb.isChecked(),  
            "show_confidence": self.show_confidence_cb.isChecked(),  
            "score_threshold": self.score_threshold_spinbox.value()  
        }