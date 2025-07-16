# 改善されたMenuPanel.py  
from typing import Dict, List, Any, Optional
from pathlib import Path  

from PyQt6.QtWidgets import (  
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,  
    QPushButton, QGroupBox, QCheckBox, QLineEdit,  
    QMessageBox, QTabWidget, QComboBox, QFileDialog,  
    QDoubleSpinBox, QDialog, QTextEdit
)  
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
  
from AnnotationInputDialog import AnnotationInputDialog  
from DataClass import BoundingBox, ObjectAnnotation  
from ConfigManager import ConfigManager  
from ErrorHandler import ErrorHandler
from CurrentFrameObjectListWidget import CurrentFrameObjectListWidget
  
class MenuPanel(QWidget):  
    """タブベースの左側メニューパネル（改善版）"""  
      
    # シグナル定義  
    load_video_requested = pyqtSignal(str)  
    load_json_requested = pyqtSignal(str)  
    export_requested = pyqtSignal(str)  # format  
      
    edit_mode_requested = pyqtSignal(bool)  
    tracking_mode_requested = pyqtSignal(bool)  
      
    tracking_requested = pyqtSignal(int, str) # assigned_track_id, assigned_label  
      
    label_change_requested = pyqtSignal(object, str)  # annotation, new_label  
    delete_single_annotation_requested = pyqtSignal(object) # ObjectAnnotation  
    delete_track_requested = pyqtSignal(int) # track_id  
    propagate_label_requested = pyqtSignal(int, str) # track_id, new_label  
    align_track_ids_requested = pyqtSignal(str, int)  # label, target_track_id
    copy_mode_requested = pyqtSignal(bool)  # コピーモードの切り替え  
    copy_annotations_requested = pyqtSignal(int, str)  # assigned_track_id, assigned_label      

    copy_annotation_requested = pyqtSignal()  
    paste_annotation_requested = pyqtSignal()

    play_requested = pyqtSignal()  
    pause_requested = pyqtSignal()  
      
    config_changed = pyqtSignal(str, object, str) # key, value  
      
    def __init__(self, config_manager: ConfigManager, parent=None):  
        super().__init__(parent)  
        self.config_manager = config_manager  
        self.current_selected_annotation: Optional[ObjectAnnotation] = None  
        self.current_selected_annotation_label: Optional[str] = None  
        self.annotation_repository = None  # AnnotationRepositoryへの直接参照を追加
          
        # 固定幅を削除し、最小幅のみ設定
        self.setMinimumWidth(250)  
        self.setStyleSheet("background-color: #f0f0f0; border-right: 1px solid #ccc;")  
        self.setup_ui()  
          
        self._connect_config_signals()
          
    def setup_ui(self):  
        layout = QVBoxLayout()  
        layout.setSpacing(10)  
        layout.setContentsMargins(10, 10, 10, 10)  
          
        title_label = QLabel("MASA Annotation Tool")  
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))  
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        layout.addWidget(title_label)  
          
        self.tab_widget = QTabWidget()  
        # タブのスタイルを設定  
        tab_style = """  
            QTabWidget::pane {  
                border: 2px solid #ccc;  
                background-color: white;  
            }  
            QTabBar::tab {  
                background-color: #e0e0e0;  
                border: 1px solid #ccc;  
                padding: 8px 16px;  
                margin-right: 2px;  
                font-weight: bold;  
            }  
            QTabBar::tab:selected {  
                background-color: #4CAF50;  
                color: white;  
                border-bottom: 2px solid #4CAF50;  
            }  
            QTabBar::tab:hover {  
                background-color: #f0f0f0;  
            }  
        """  
        self.tab_widget.setStyleSheet(tab_style)  
        layout.addWidget(self.tab_widget)  

        self.setup_basic_tab()  
        self.setup_annotation_tab()
        self.setup_object_list_tab()
        self.setup_license_tab()
          
        self.setLayout(layout)
          
    def _connect_config_signals(self):  
        """ConfigManagerからの設定変更シグナルを接続"""  
        self.config_manager.add_observer(self._on_config_changed)  
          
    def _on_config_changed(self, key: str, value: object, config_type: str): # config_type引数を追加  
        """ConfigManagerからの設定変更を処理"""  
        if config_type == "display" and key == "score_threshold":  
            self.score_threshold_spinbox.setValue(value)  
        # 他の設定項目もここに追加
          
    def setup_basic_tab(self):  
        basic_tab = QWidget()  
        layout = QVBoxLayout()  
          
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
        self.save_masa_json_btn.clicked.connect(lambda: self.export_requested.emit("masa"))  
        self.save_masa_json_btn.setEnabled(False)  
        file_layout.addWidget(self.save_masa_json_btn)  
      
        self.save_coco_json_btn = QPushButton("Save COCO JSON (Ctrl+Shift+S)")
        self.save_coco_json_btn.clicked.connect(lambda: self.export_requested.emit("coco"))  
        self.save_coco_json_btn.setEnabled(False)  
        file_layout.addWidget(self.save_coco_json_btn)
          
        self.json_info_label = QLabel("No JSON loaded")
        self.json_info_label.setWordWrap(True)  
        file_layout.addWidget(self.json_info_label)  
          
        # エクスポート進捗表示ラベルを追加  
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
          
        score_threshold_layout = QHBoxLayout()  
        score_threshold_layout.addWidget(QLabel("Confidence Threshold:"))
          
        self.score_threshold_spinbox = QDoubleSpinBox()  
        self.score_threshold_spinbox.setRange(0.0, 1.0)  
        self.score_threshold_spinbox.setSingleStep(0.1)  
        self.score_threshold_spinbox.setDecimals(2)  
        self.score_threshold_spinbox.setValue(self.config_manager.get_config("score_threshold"))  
        self.score_threshold_spinbox.valueChanged.connect(self._on_display_option_changed)
        score_threshold_layout.addWidget(self.score_threshold_spinbox)  
          
        display_layout.addLayout(score_threshold_layout)  
        display_group.setLayout(display_layout)  
        layout.addWidget(display_group)  
          
        layout.addStretch()  
        basic_tab.setLayout(layout)  
        self.tab_widget.addTab(basic_tab, "⚙️ Basic Settings")
    
    def setup_annotation_tab(self):  
        annotation_tab = QWidget()  
        layout = QVBoxLayout()  
          
        # アノテーション情報グループ  
        info_group = QGroupBox("Annotation Info")
        info_layout = QVBoxLayout()  
        self.annotation_count_label = QLabel("Annotation Count: 0")
        info_layout.addWidget(self.annotation_count_label)  
        info_group.setLayout(info_layout)  
        layout.addWidget(info_group)  
          
        # アノテーション編集グループ  
        edit_group = QGroupBox("Edit Annotation")
        edit_layout = QVBoxLayout()  
          
        # EditModeボタン用
        edit_button_style = """  
            QPushButton {  
                background-color: #f0f0f0;  
                border: 2px solid #ccc;  
                padding: 5px;  
            }  
            QPushButton:checked {  
                background-color: #FFD700;  
                border: 2px solid #FFA500;  
                font-weight: bold;  
            }  
        """  
          
        self.edit_mode_btn = QPushButton("Edit Mode (E)")
        self.edit_mode_btn.setCheckable(True)  
        self.edit_mode_btn.setStyleSheet(edit_button_style)  
        self.edit_mode_btn.clicked.connect(self._on_edit_mode_clicked)  
        self.edit_mode_btn.setEnabled(False)  
        edit_layout.addWidget(self.edit_mode_btn)  
          
        self.label_combo = QComboBox()  
        self.label_combo.setEditable(True)  
        self.label_combo.setEnabled(False)
        self.label_combo.currentIndexChanged.connect(self._on_label_changed)  
        edit_layout.addWidget(QLabel("Label:"))
        edit_layout.addWidget(self.label_combo)  
          
        self.track_id_edit = QLineEdit()  
        self.track_id_edit.setEnabled(False)  
        self.track_id_edit.setReadOnly(True)  
        edit_layout.addWidget(QLabel("Track ID:"))
        edit_layout.addWidget(self.track_id_edit)  
          
        self.delete_single_annotation_btn = QPushButton("Delete Selected Annotation (X)")
        self.delete_single_annotation_btn.setEnabled(False)  
        self.delete_single_annotation_btn.clicked.connect(self._on_delete_single_annotation_clicked)  
        edit_layout.addWidget(self.delete_single_annotation_btn)  
          
        self.delete_track_btn = QPushButton("Delete All (D)")
        self.delete_track_btn.setEnabled(False)  
        self.delete_track_btn.clicked.connect(self._on_delete_track_clicked)  
        edit_layout.addWidget(self.delete_track_btn)  
          
        self.propagate_label_btn = QPushButton("Change Label for All (P)")
        self.propagate_label_btn.setEnabled(False)  
        self.propagate_label_btn.clicked.connect(self._on_propagate_label_clicked)  
        edit_layout.addWidget(self.propagate_label_btn)

        self.align_track_ids_btn = QPushButton("Align Track IDs for All(A)")  
        self.align_track_ids_btn.setEnabled(False)  
        self.align_track_ids_btn.clicked.connect(self._on_align_track_ids_clicked)  
        edit_layout.addWidget(self.align_track_ids_btn)

        self.copy_annotation_btn = QPushButton("Copy Annotation (Ctrl+C)")  
        self.copy_annotation_btn.setEnabled(False)  
        self.copy_annotation_btn.clicked.connect(self._on_copy_annotation_clicked)  
        edit_layout.addWidget(self.copy_annotation_btn)  
        
        self.paste_annotation_btn = QPushButton("Paste Annotation (Ctrl+V)")  
        self.paste_annotation_btn.setEnabled(False)  
        self.paste_annotation_btn.clicked.connect(self._on_paste_annotation_clicked)  
        edit_layout.addWidget(self.paste_annotation_btn)

        edit_group.setLayout(edit_layout)  
        layout.addWidget(edit_group)  
          

        # Undo/Redoグループ
        undo_redo_group = QGroupBox("Undo/Redo")
        undo_redo_layout = QHBoxLayout()  
        
        self.undo_btn = QPushButton("Undo (Ctrl+Z)")
        self.undo_btn.setEnabled(False)  
        self.undo_btn.clicked.connect(self._on_undo_clicked)  
        undo_redo_layout.addWidget(self.undo_btn)  
        
        self.redo_btn = QPushButton("Redo (Ctrl+Y)")
        self.redo_btn.setEnabled(False)  
        self.redo_btn.clicked.connect(self._on_redo_clicked)  
        undo_redo_layout.addWidget(self.redo_btn)  
        
        undo_redo_group.setLayout(undo_redo_layout)  
        layout.addWidget(undo_redo_group)  


        # 一括追加グループ  
        tracking_group = QGroupBox("Batch Add Annotations")
        tracking_layout = QVBoxLayout()  
        
        # TrackingAddModeボタン用
        tracking_button_style = """  
            QPushButton {  
                background-color: #f0f0f0;  
                border: 2px solid #ccc;  
                padding: 5px;  
            }  
            QPushButton:checked {  
                background-color: #87CEEB;
                border: 2px solid #4682B4;
                font-weight: bold;  
            }  
        """  
        self.tracking_annotation_btn = QPushButton("Add Annotations by Tracking(T)")
        self.tracking_annotation_btn.setCheckable(True)  
        self.tracking_annotation_btn.setEnabled(True)  
        self.tracking_annotation_btn.setStyleSheet(tracking_button_style)
        self.tracking_annotation_btn.clicked.connect(self._on_tracking_annotation_clicked)  
        tracking_layout.addWidget(self.tracking_annotation_btn)  

        # コピーモード用のボタンを追加  
        self.copy_annotations_btn = QPushButton("Add Annotations by Copy(C)")  
        self.copy_annotations_btn.setCheckable(True)  
        self.copy_annotations_btn.setEnabled(True)  
        self.copy_annotations_btn.setStyleSheet(tracking_button_style)  
        self.copy_annotations_btn.clicked.connect(self._on_copy_annotations_clicked)  
        tracking_layout.addWidget(self.copy_annotations_btn)

        self.tracking_status_label = QLabel("Loading MASA models...")  
        tracking_layout.addWidget(self.tracking_status_label)  
        
        self.tracking_progress_label = QLabel("")  
        tracking_layout.addWidget(self.tracking_progress_label)

        self.execute_add_btn = QPushButton("Run (R)")
        self.execute_add_btn.setEnabled(False)  
        self.execute_add_btn.clicked.connect(self._on_complete_tracking_clicked)  
        tracking_layout.addWidget(self.execute_add_btn)
          
        self.range_info_label = QLabel("Range: Not Selected")
        tracking_layout.addWidget(self.range_info_label)  
          
        self.tracking_progress_label = QLabel("")  
        tracking_layout.addWidget(self.tracking_progress_label)  

        tracking_group.setLayout(tracking_layout)  
        layout.addWidget(tracking_group)  
          
        layout.addStretch()  
        annotation_tab.setLayout(layout)  
        self.tab_widget.addTab(annotation_tab, "📝 Annotation")
    
    def setup_object_list_tab(self):
        """オブジェクト一覧タブのセットアップ"""
        object_list_tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # CurrentFrameObjectListWidgetを追加
        self.object_list_widget = CurrentFrameObjectListWidget(self)
        layout.addWidget(self.object_list_widget)
        
        object_list_tab.setLayout(layout)
        self.tab_widget.addTab(object_list_tab, "📋 Object List")
    
    def setup_license_tab(self):  
        """ライセンス表示タブのセットアップ"""  
        license_tab = QWidget()  
        layout = QVBoxLayout()  
        
        # ライブラリ選択用のコンボボックス  
        library_layout = QHBoxLayout()  
        library_layout.addWidget(QLabel("Library:"))  
        
        self.license_combo = QComboBox()  
        self.license_combo.addItems([  
            "masa", "mmcv", "mmdet", "numpy",   
            "opencv-python", "PyQt6", "torch"  
        ])  
        self.license_combo.currentTextChanged.connect(self._on_license_selection_changed)  
        library_layout.addWidget(self.license_combo)  
        library_layout.addStretch()  
        
        layout.addLayout(library_layout)  
        
        # ライセンス内容表示用のテキストエリア  
        self.license_text = QTextEdit()  
        self.license_text.setReadOnly(True)  
        self.license_text.setFont(QFont("Courier", 9))  # 等幅フォント  
        self.license_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)  # 追加  
        self.license_text.setAcceptRichText(False)  # プレーンテキストのみ受け入れ
        layout.addWidget(self.license_text)  
        
        license_tab.setLayout(layout)  
        self.tab_widget.addTab(license_tab, "📄 License")
        
        # 初期表示（最初のライブラリのライセンスを表示）  
        if self.license_combo.count() > 0:  
            self._load_license_content(self.license_combo.itemText(0))

    @ErrorHandler.handle_with_dialog("File Load Error")
    def _on_load_video_clicked(self, _: str):  
        """動画ファイル読み込みボタンのクリックハンドラ"""  
        file_path, _ = QFileDialog.getOpenFileName(  
            self, "Select Video File", "",  
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"  
        )  
        if file_path:  
            self.load_video_requested.emit(file_path)  
              
    @ErrorHandler.handle_with_dialog("File Load Error")  
    def _on_load_json_clicked(self, _: str):  
        """JSONファイル読み込みボタンのクリックハンドラ"""  
        file_path, _ = QFileDialog.getOpenFileName(  
            self, "Select JSON Annotation File", "",  
            "JSON Files (*.json);;All Files (*)"  
        )  
        if file_path:  
            self.load_json_requested.emit(file_path)  
              
    def update_json_info(self, json_path: str, annotation_count: int):  
        """JSON情報を更新"""  
        filename = Path(json_path).name  
        self.json_info_label.setText(f"{filename}\n{annotation_count} annotations loaded")  
        self.save_masa_json_btn.setEnabled(True)  
        self.save_coco_json_btn.setEnabled(True)  

    def update_export_progress(self, message: str):  
        """エクスポート進捗を更新"""  
        self.export_progress_label.setText(message)

    def _on_edit_mode_clicked(self, checked: bool):  
        """編集モードボタンクリック時の処理"""  
        if checked:  
            # TrackingAddModeがONの場合はOFFにして無効化  
            if self.tracking_annotation_btn.isChecked():  
                self.tracking_annotation_btn.setChecked(False)  
            if self.copy_annotations_btn.isChecked():  
                self.copy_annotations_btn.setChecked(False)  
            self.tracking_annotation_btn.setEnabled(False)
            self.copy_annotations_btn.setEnabled(False)   
        else:  
            # EditModeがOFFになった時はTrackingAddModeボタンを有効化  
            self.tracking_annotation_btn.setEnabled(True)  
            self.copy_annotations_btn.setEnabled(True) 
          
        self.edit_mode_requested.emit(checked)  
        self._update_edit_controls_state(checked)  

    def _update_edit_controls_state(self, enabled: bool):  
        """編集関連コントロールの有効/無効を切り替える"""  
        self.label_combo.setEnabled(enabled)  
        self.track_id_edit.setEnabled(enabled)  
        self.delete_single_annotation_btn.setEnabled(enabled and self.current_selected_annotation is not None)  
        self.delete_track_btn.setEnabled(enabled and self.current_selected_annotation is not None)  
        self.propagate_label_btn.setEnabled(enabled and self.current_selected_annotation is not None)  
        self.align_track_ids_btn.setEnabled(enabled and self.current_selected_annotation is not None)
        self.copy_annotation_btn.setEnabled(enabled and self.current_selected_annotation is not None)  
        self.paste_annotation_btn.setEnabled(enabled and self.parent().parent().clipboard_annotation is not None)

    def update_video_info(self, video_path: str, total_frames: int):  
        """動画情報を更新"""  
        filename = Path(video_path).name  
        self.video_info_label.setText(f"{filename}\n{total_frames} frames")  
        self.frame_label.setText(f"フレーム: 0/{total_frames - 1}")  
        self.edit_mode_btn.setEnabled(True)  
        self.play_btn.setEnabled(True)  
          
    def update_annotation_count(self, count: int, manual_count: int = None):  
        """アノテーション数を更新"""  
        if manual_count is not None:  
            loaded_count = count - manual_count  
            self.annotation_count_label.setText(  
                f"All Annotation count: {count}\n"  
                f"(auto: {loaded_count}, manual: {manual_count})"  
            )  
        else:  
            self.annotation_count_label.setText(f"Annotation count: {count}")  
              
    def update_range_info(self, start_frame: int, end_frame: int):  
        """範囲情報を更新"""  
        self.range_info_label.setText(f"Range: {start_frame} - {end_frame}")  
          
    def update_tracking_progress(self, progress_text: str):  
        """追跡進捗を更新"""  
        self.tracking_progress_label.setText(progress_text)  
          
    def _on_display_option_changed(self):  
        """表示オプション変更時の処理"""  
        self.config_manager.update_config("show_manual_annotations", self.show_manual_cb.isChecked(), config_type="display")  
        self.config_manager.update_config("show_auto_annotations", self.show_auto_cb.isChecked(), config_type="display")  
        self.config_manager.update_config("show_ids", self.show_ids_cb.isChecked(), config_type="display")  
        self.config_manager.update_config("show_confidence", self.show_confidence_cb.isChecked(), config_type="display")  
        # score_thresholdはspinboxのvalueChangedシグナルで直接更新される  
        self.config_manager.update_config("score_threshold", self.score_threshold_spinbox.value(), config_type="display") # score_thresholdもdisplay configに移動  
        self.config_changed.emit("display_options", self.get_display_options(), "display") # このシグナルはMASAAnnotationWidgetに通知するため、そのまま  
          
    def get_display_options(self) -> Dict[str, Any]:  
        """表示オプションを取得"""  
        # ConfigManagerから直接取得するように変更  
        display_config = self.config_manager.get_full_config(config_type="display")  
        return {  
            'show_manual': display_config.show_manual_annotations,  
            'show_auto': display_config.show_auto_annotations,  
            'show_ids': display_config.show_ids,  
            'show_confidence': display_config.show_confidence,  
            'score_threshold': display_config.score_threshold  
        }  
          
    def _on_play_clicked(self):  
        """再生/一時停止ボタンクリック処理"""  
        if self.play_btn.text() == "Play (Space)":  
            self.play_requested.emit()  
            self.play_btn.setText("Stop (Space)")  
        else:  
            self.pause_requested.emit()  
            self.play_btn.setText("Play (Space)")  
              
    def reset_playback_button(self):  
        """再生ボタンを初期状態にリセット"""  
        self.play_btn.setText("Play (Space)")  
          
    def update_frame_display(self, current_frame: int, total_frames: int):  
        """フレーム表示を更新"""  
        self.frame_label.setText(f"Frame: {current_frame}/{total_frames - 1}")  
          
    def _on_label_changed(self):  
        """ラベル変更時の処理"""  
        if self.current_selected_annotation:  
            new_label = self.label_combo.currentText()  
            if new_label != self.current_selected_annotation_label:  
                self.label_change_requested.emit(self.current_selected_annotation, new_label)  
                self.current_selected_annotation_label = new_label  
                ErrorHandler.show_info_dialog(  
                    f"Changed label of annotation ID {self.current_selected_annotation.object_id} to '{new_label}'",  
                    "Change Label Success"  
                )  
                  
    def update_selected_annotation_info(self, annotation: Optional[ObjectAnnotation]):  
        """選択されたアノテーション情報をUIに反映"""  
        self.current_selected_annotation = annotation  
        self.label_combo.blockSignals(True) # シグナルを一時的にブロック  
          
        try:  
            if annotation is None:  
                self.current_selected_annotation_label = None  
                self.label_combo.setCurrentText("")  
                self.track_id_edit.setText("")  
            else:  
                self.current_selected_annotation_label = annotation.label  
                  
                # 既存のラベルをコンボボックスに追加（重複チェック）  
                current_labels = [self.label_combo.itemText(i) for i in range(self.label_combo.count())]  
                if annotation.label not in current_labels:  
                    self.label_combo.addItem(annotation.label)  
                  
                # 現在のラベルを選択  
                index = self.label_combo.findText(annotation.label)  
                if index >= 0:  
                    self.label_combo.setCurrentIndex(index)  
                else:  
                    self.label_combo.addItem(annotation.label)  
                    self.label_combo.setCurrentText(annotation.label)  
                  
                self.track_id_edit.setText(str(annotation.object_id))  
        finally:  
            self.label_combo.blockSignals(False)  
              
        # 選択状態に応じてボタンの有効/無効を更新  
        self._update_edit_controls_state(self.edit_mode_btn.isChecked())  
          
    def initialize_label_combo(self, labels: List[str]):  
        """ラベルコンボボックスを初期化"""  
        # 現在選択されているラベルを一時的に保持  
        current_selected_label = self.label_combo.currentText()  
          
        self.label_combo.blockSignals(True) # シグナルを一時的にブロック  
        self.label_combo.clear() # 既存のアイテムをクリア  
          
        # 新しいラベルを追加  
        for label in sorted(list(set(labels))): # 重複を排除しソート  
            self.label_combo.addItem(label)  
          
        # 以前選択されていたラベルを再設定  
        if current_selected_label and self.label_combo.findText(current_selected_label) >= 0:  
            self.label_combo.setCurrentText(current_selected_label)  
        elif self.current_selected_annotation: # 現在選択中のアノテーションのラベルを優先  
            index = self.label_combo.findText(self.current_selected_annotation.label)  
            if index >= 0:  
                self.label_combo.setCurrentIndex(index)  
            else:  
                # もし現在のラベルがリストにない場合は追加して選択  
                self.label_combo.addItem(self.current_selected_annotation.label)  
                self.label_combo.setCurrentText(self.current_selected_annotation.label)  
        elif self.label_combo.count() > 0:  
            self.label_combo.setCurrentIndex(0) # リストが空でなければ最初の要素を選択  
              
        self.label_combo.blockSignals(False) # シグナルブロックを解除
          
    def _on_delete_single_annotation_clicked(self):  
        """選択アノテーション削除ボタンクリック時の処理"""  
        if self.current_selected_annotation:  
            reply = QMessageBox.question(  
                self, "Confirm Delete Annotation",  
                f"Do you want to delete the annotation for SELECTED frame {self.current_selected_annotation.frame_id} (ID: {self.current_selected_annotation.object_id}, label: '{self.current_selected_annotation.label}')?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
            )  
            if reply == QMessageBox.StandardButton.Yes:  
                self.delete_single_annotation_requested.emit(self.current_selected_annotation)  
                self.current_selected_annotation = None  
                self.update_selected_annotation_info(None)  
                  
    def _on_delete_track_clicked(self):  
        """一括削除ボタンクリック時の処理"""  
        if self.current_selected_annotation:  
            track_id_to_delete = self.current_selected_annotation.object_id  
            reply = QMessageBox.question(
                self, "Confirm ALL Track Deletion",
                f"Do you want to delete ALL annotations with Track ID '{track_id_to_delete}'?\n"
                "This action cannot be undone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:  
                self.delete_track_requested.emit(track_id_to_delete)  
                self.current_selected_annotation = None  
                self.update_selected_annotation_info(None)  
                  
    def _on_propagate_label_clicked(self):  
        """一括ラベル変更ボタンクリック時の処理"""  
        if self.current_selected_annotation:  
            track_id_to_change = self.current_selected_annotation.object_id  
            current_label = self.current_selected_annotation.label  # 現在のラベルを取得
              
            dialog = AnnotationInputDialog(
                BoundingBox(0, 0, 1, 1), 
                self, 
                existing_labels=self.get_all_labels_from_manager(),
                default_label=current_label  # 現在のラベルをデフォルトとして設定
            )  
            dialog.setWindowTitle(f"Change Label forALLL with Track ID {track_id_to_change}")
              
            if dialog.exec() == QDialog.DialogCode.Accepted:  
                new_label = dialog.get_label()  
                if new_label:  
                    reply = QMessageBox.question(
                        self, "Confirm ALL Track Label Change",
                        f"Do you want to change the label of ALL annotations with Track ID '{track_id_to_change}' to '{new_label}'?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    if reply == QMessageBox.StandardButton.Yes:  
                        self.propagate_label_requested.emit(track_id_to_change, new_label)  
                else:  
                    ErrorHandler.show_warning_dialog("Please enter a new label name.", "Input Error")
                      
    def _on_align_track_ids_clicked(self):  
        """Track ID統一ボタンクリック時の処理"""  
        if self.current_selected_annotation:  
            target_label = self.current_selected_annotation.label  
            target_track_id = self.current_selected_annotation.object_id  
            
            reply = QMessageBox.question(  
                self, "Confirm Track ID Alignment",  
                f"Do you want to align ALL annotations with label '{target_label}' to Track ID '{target_track_id}'?\n"  
                "This will change the Track ID of all annotations with the same label.",  
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
            )  
            if reply == QMessageBox.StandardButton.Yes:  
                self.align_track_ids_requested.emit(target_label, target_track_id)

    def get_all_labels_from_manager(self) -> List[str]:  
        """AnnotationRepositoryの全ラベルを取得するヘルパーメソッド"""  
        if self.annotation_repository:  
            return self.annotation_repository.get_all_labels()  
        return []
      
    def _on_tracking_annotation_clicked(self, checked: bool):  
        """新規アノテーション一括追加ボタンクリック時の処理"""  
        if checked:  
            # EditModeとCopyModeがONの場合はOFFにして無効化  
            if self.edit_mode_btn.isChecked():  
                self.edit_mode_btn.setChecked(False)  
            if self.copy_annotations_btn.isChecked():
                self.copy_annotations_btn.setChecked(False)  
            
            self.edit_mode_btn.setEnabled(False)  
            self.copy_annotation_btn.setEnabled(False)
        else:  
            # TrackingAddModeがOFFになった時は他のボタンを有効化  
            self.edit_mode_btn.setEnabled(True)  
            self.copy_annotations_btn.setEnabled(True) 
        
        self.tracking_mode_requested.emit(checked)  
        self.execute_add_btn.setEnabled(checked)

    def _on_complete_tracking_clicked(self):  
        """一括追加完了ボタンクリック時の処理"""  
        # コピーモードの場合  
        if self.copy_annotations_btn.isChecked():  
            return self._handle_copy_mode_execution() 

        # temp_bboxes_for_tracking が空でないことを確認  
        if not self.parent().parent().temp_bboxes_for_tracking:  
            ErrorHandler.show_warning_dialog("There are no annotations to add.", "Warning")
            return  
  
        # 共通ラベル入力ダイアログを表示  
        # 既存のラベルリストを取得  
        # MASAAnnotationWidgetのannotation_repositoryからラベルを取得  
        existing_labels = self.parent().parent().annotation_repository.get_all_labels()   
        dialog = AnnotationInputDialog(None, self, existing_labels=existing_labels) # bboxは不要なのでNone  
        dialog.setWindowTitle("Select Common Label for Tracking Added Annotations")
  
        if dialog.exec() == QDialog.DialogCode.Accepted:  
            assigned_label = dialog.get_label()  
            if not assigned_label:  
                ErrorHandler.show_warning_dialog("No label selected.", "Warning")
                return  
  
            # 追跡範囲の取得  
            start_frame, end_frame = self.parent().parent().video_control.get_selected_range()  
            if start_frame == -1 or end_frame == -1:  
                ErrorHandler.show_warning_dialog("No tracking range selected.", "Warning")
                return  
  
            # AnnotationRepositoryから現在のTrack IDの最大値を取得  
            # MASAAnnotationWidgetのannotation_repositoryにアクセス  
            current_max_track_id = self.parent().parent().annotation_repository.next_object_id  
            # MASAAnnotationWidgetに追跡開始を要求  
            # assigned_track_id は バッチ追加で追加されるアノテーションのTrack IDの始まりののインデックスになる。
            self.tracking_requested.emit(current_max_track_id, assigned_label)  
              
        else:  
            ErrorHandler.show_info_dialog("Label selection was cancelled.", "Info")

    def set_tracking_enabled(self, enabled: bool):  
        """トラッキング機能の有効/無効を設定"""  
        self.execute_add_btn.setEnabled(enabled)  
        if not enabled:  
            self.tracking_status_label.setText("Loading MASA models...")  
        else:  
            self.tracking_status_label.setText("Ready for tracking")

    def _on_undo_clicked(self):    
        """Undoボタンクリック時の処理"""    
        # QSplitterの親がMASAAnnotationWidget  
        main_widget = self.parent().parent()  
        if hasattr(main_widget, 'command_manager'):    
            if main_widget.command_manager.undo():    
                main_widget.update_annotation_count()    
                main_widget.video_preview.update_frame_display()    
                main_widget.video_preview.bbox_editor.selected_annotation = None    
                main_widget.video_preview.bbox_editor.selection_changed.emit(None)    
                print("--- Undo ---")  
            else:    
                ErrorHandler.show_info_dialog("There are no actions to undo.", "Undo")
    
    def _on_redo_clicked(self):    
        """Redoボタンクリック時の処理"""    
        # QSplitterの親がMASAAnnotationWidget  
        main_widget = self.parent().parent()  
        if hasattr(main_widget, 'command_manager'):    
            if main_widget.command_manager.redo():    
                main_widget.update_annotation_count()    
                main_widget.video_preview.update_frame_display()    
                main_widget.video_preview.bbox_editor.selected_annotation = None    
                main_widget.video_preview.bbox_editor.selection_changed.emit(None)    
                print("--- Redo ---")  
            else:    
                ErrorHandler.show_info_dialog("There are no actions to redo.", "Redo")
    
    def update_undo_redo_buttons(self, command_manager):  
        """Undo/Redoボタンの状態を更新"""  
        if hasattr(self, 'undo_btn') and hasattr(self, 'redo_btn'):  
            self.undo_btn.setEnabled(command_manager.can_undo())  
            self.redo_btn.setEnabled(command_manager.can_redo())  
            
            # ツールチップに次の操作の説明を表示  
            if command_manager.can_undo():  
                self.undo_btn.setToolTip(f"Undo: {command_manager.get_undo_description()}")  
            else:  
                self.undo_btn.setToolTip("Undo (Ctrl+Z)")  
                
            if command_manager.can_redo():  
                self.redo_btn.setToolTip(f"Redo: {command_manager.get_redo_description()}")  
            else:  
                self.redo_btn.setToolTip("Redo (Ctrl+Y)")

    def update_current_frame_objects(self, frame_id: int, frame_annotation=None):
        """現在フレームのオブジェクト一覧を更新"""
        if hasattr(self, 'object_list_widget'):
            self.object_list_widget.update_frame_data(frame_id, frame_annotation)
            
    def set_object_list_score_threshold(self, threshold: float):
        """オブジェクト一覧のスコア閾値を設定"""
        if hasattr(self, 'object_list_widget'):
            self.object_list_widget.set_score_threshold(threshold)
            
    def update_object_list_selection(self, annotation):
        """オブジェクト一覧の選択状態を更新"""
        if hasattr(self, 'object_list_widget') and self.object_list_widget:
            # 循環防止: _updating_selectionフラグで制御
            if hasattr(self.object_list_widget, '_updating_selection'):
                self.object_list_widget._updating_selection = True
            try:
                self.object_list_widget.select_annotation(annotation)
            finally:
                if hasattr(self.object_list_widget, '_updating_selection'):
                    self.object_list_widget._updating_selection = False
            
    def get_object_list_widget(self):
        """オブジェクト一覧ウィジェットを取得"""
        return getattr(self, 'object_list_widget', None)

    def _on_license_selection_changed(self, library_name: str):  
        """ライブラリ選択変更時の処理"""  
        self._load_license_content(library_name)  
    
    def _load_license_content(self, library_name: str):  
        """指定されたライブラリのライセンス内容を読み込み（複数ファイル対応）"""  
        try:  
            # ライセンスディレクトリのパスを構築  
            license_dir = Path(__file__).parent.parent.parent / "licenses" / library_name  

            if not license_dir.exists():
                self.license_text.setPlainText(
                    f"License directory for {library_name} not found.\n"
                    f"Path: {license_dir}"
                )
                return
            
            # ディレクトリ内のすべてのファイルを取得してソート  
            license_files = sorted(license_dir.glob("*"))  
            
            if not license_files:
                self.license_text.setPlainText(
                    f"No license files found for {library_name}."
                )
                return
            
            # 複数ファイルの内容を連結  
            combined_content = []  
            for file_path in license_files:  
                if file_path.is_file():  # ファイルのみを対象  
                    try:  
                        with open(file_path, 'r', encoding='utf-8') as f:  
                            file_content = f.read().strip()  
                        
                        # ファイル名をヘッダーとして追加  
                        combined_content.append(f"=== {file_path.name} ===")  
                        combined_content.append(file_content)  
                        combined_content.append("")  # 空行で区切り  
                        
                    except UnicodeDecodeError:  
                        # UTF-8で読めない場合は別のエンコーディングを試す  
                        try:  
                            with open(file_path, 'r', encoding='latin-1') as f:  
                                file_content = f.read().strip()  
                            combined_content.append(f"=== {file_path.name} ===")  
                            combined_content.append(file_content)  
                            combined_content.append("")  
                        except Exception as e:  
                            combined_content.append(f"=== {file_path.name} (load error) ===")  
                            combined_content.append(f"Error: {str(e)}")  
                            combined_content.append("")  
            
            # 連結した内容を表示  
            final_content = '\n\n'.join(combined_content)  
            
            # QTextEditに設定  
            self.license_text.clear()  # 既存の内容をクリア  
            self.license_text.setPlainText(final_content)  
            
        except Exception as e:  
            error_message = f"An error occurred while loading the license for {library_name}:\n{str(e)}"
            print(f"Error: {error_message}")  
            self.license_text.setPlainText(error_message)

    def _on_copy_annotations_clicked(self, checked: bool):  
        """コピーモードボタンクリック時の処理"""  
        if checked:  
            # 他のモードがONの場合はOFFにする  
            if self.edit_mode_btn.isChecked():  
                self.edit_mode_btn.setChecked(False)  
            if self.tracking_annotation_btn.isChecked():  
                self.tracking_annotation_btn.setChecked(False)  
            
            self.edit_mode_btn.setEnabled(False)  
            self.tracking_annotation_btn.setEnabled(False)  
        else:  
            # コピーモードがOFFになった時は他のボタンを有効化  
            self.edit_mode_btn.setEnabled(True)  
            self.tracking_annotation_btn.setEnabled(True)  
        
        self.copy_mode_requested.emit(checked)  
        # 実行ボタンの有効/無効を切り替え（既存のexecute_add_btnを流用）  
        self.execute_add_btn.setEnabled(checked)

    def _handle_copy_mode_execution(self):  
        """コピーモード実行時の処理"""  
        # 選択されたアノテーションがあるかチェック  
        if not self.current_selected_annotation:  
            ErrorHandler.show_warning_dialog("Please select an annotation to copy.", "Warning")  
            return  
        
        # フレーム範囲の取得  
        start_frame, end_frame = self.parent().parent().video_control.get_selected_range()  
        if start_frame == -1 or end_frame == -1:  
            ErrorHandler.show_warning_dialog("No frame range selected.", "Warning")  
            return  
        
        # 新しいTrack IDを取得  
        current_max_track_id = self.parent().parent().annotation_repository.next_object_id  
        
        # コピー処理を要求  
        self.copy_annotations_requested.emit(current_max_track_id, self.current_selected_annotation.label)  
        
    def _on_copy_annotation_clicked(self):  
        """コピーボタンクリック時の処理"""  
        self.copy_annotation_requested.emit()  
    
    def _on_paste_annotation_clicked(self):  
        """ペーストボタンクリック時の処理"""  
        self.paste_annotation_requested.emit()