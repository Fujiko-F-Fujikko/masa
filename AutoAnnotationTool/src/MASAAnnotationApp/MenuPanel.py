# 改善されたMenuPanel.py  
from typing import Dict, List, Any, Optional
from pathlib import Path  

from PyQt6.QtWidgets import (  
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,  
    QPushButton, QGroupBox, QCheckBox, QLineEdit,  
    QMessageBox, QTabWidget, QComboBox, QFileDialog,  
    QDoubleSpinBox, QDialog,
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
    batch_add_mode_requested = pyqtSignal(bool)  
      
    tracking_requested = pyqtSignal(int, str) # assigned_track_id, assigned_label  
      
    label_change_requested = pyqtSignal(object, str)  # annotation, new_label  
    delete_single_annotation_requested = pyqtSignal(object) # ObjectAnnotation  
    delete_track_requested = pyqtSignal(int) # object_id (Track ID)  
    propagate_label_requested = pyqtSignal(int, str) # object_id (Track ID), new_label  
      
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
        file_group = QGroupBox("ファイル操作")  
        file_layout = QVBoxLayout()  
          
        self.load_video_btn = QPushButton("動画を読み込み (Ctrl+O)")  
        self.load_video_btn.clicked.connect(self._on_load_video_clicked)  
        file_layout.addWidget(self.load_video_btn)  
        self.video_info_label = QLabel("動画が読み込まれていません")  
        self.video_info_label.setWordWrap(True)  
        file_layout.addWidget(self.video_info_label)  
          
        self.load_json_btn = QPushButton("JSONを読み込み (Ctrl+L)")  
        self.load_json_btn.clicked.connect(self._on_load_json_clicked)  
        file_layout.addWidget(self.load_json_btn)  
          
        self.save_masa_json_btn = QPushButton("MASA JSONを保存 (Ctrl+S)")  
        self.save_masa_json_btn.clicked.connect(lambda: self.export_requested.emit("masa"))  
        self.save_masa_json_btn.setEnabled(False)  
        file_layout.addWidget(self.save_masa_json_btn)  
      
        self.save_coco_json_btn = QPushButton("COCO JSONを保存 (Ctrl+Shift+S)")  
        self.save_coco_json_btn.clicked.connect(lambda: self.export_requested.emit("coco"))  
        self.save_coco_json_btn.setEnabled(False)  
        file_layout.addWidget(self.save_coco_json_btn)
          
        self.json_info_label = QLabel("JSONが読み込まれていません")  
        self.json_info_label.setWordWrap(True)  
        file_layout.addWidget(self.json_info_label)  
          
        # エクスポート進捗表示ラベルを追加  
        self.export_progress_label = QLabel("")  
        file_layout.addWidget(self.export_progress_label)  

        file_group.setLayout(file_layout)  
        layout.addWidget(file_group)  
          
        # 再生コントロールグループ  
        playback_group = QGroupBox("再生コントロール")  
        playback_layout = QVBoxLayout()  
          
        self.play_btn = QPushButton("再生(Space)")  
        self.play_btn.setEnabled(False)  
        self.play_btn.clicked.connect(self._on_play_clicked)  
        playback_layout.addWidget(self.play_btn)  
          
        self.frame_label = QLabel("フレーム: 0/0")  
        playback_layout.addWidget(self.frame_label)  
        playback_group.setLayout(playback_layout)  
        layout.addWidget(playback_group)  
          
        # 表示設定グループ  
        display_group = QGroupBox("表示設定")  
        display_layout = QVBoxLayout()  
          
        self.show_manual_cb = QCheckBox("手動アノテーション結果表示")  
        self.show_manual_cb.setChecked(True)  
        self.show_manual_cb.stateChanged.connect(self._on_display_option_changed)  
        display_layout.addWidget(self.show_manual_cb)  
          
        self.show_auto_cb = QCheckBox("自動アノテーション結果表示")  
        self.show_auto_cb.setChecked(True)  
        self.show_auto_cb.stateChanged.connect(self._on_display_option_changed)  
        display_layout.addWidget(self.show_auto_cb)  
          
        self.show_ids_cb = QCheckBox("Track ID表示")  
        self.show_ids_cb.setChecked(True)  
        self.show_ids_cb.stateChanged.connect(self._on_display_option_changed)  
        display_layout.addWidget(self.show_ids_cb)  
          
        self.show_confidence_cb = QCheckBox("スコア表示")  
        self.show_confidence_cb.setChecked(True)  
        self.show_confidence_cb.stateChanged.connect(self._on_display_option_changed)  
        display_layout.addWidget(self.show_confidence_cb)  
          
        simple_checkbox_style = """  
        QCheckBox::indicator:checked {  
            background-color: #4CAF50;  
            border: 1px solid #4CAF50;  
        }  
        QCheckBox::indicator:unchecked {  
            background-color: white;  
            border: 1px solid #ccc;  
        }  
        """  
        self.show_manual_cb.setStyleSheet(simple_checkbox_style)  
        self.show_auto_cb.setStyleSheet(simple_checkbox_style)  
        self.show_ids_cb.setStyleSheet(simple_checkbox_style)  
        self.show_confidence_cb.setStyleSheet(simple_checkbox_style)  
          
        score_threshold_layout = QHBoxLayout()  
        score_threshold_layout.addWidget(QLabel("スコア閾値:"))  
          
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
        self.tab_widget.addTab(basic_tab, "⚙️ 基本設定")  
    
    def setup_annotation_tab(self):  
        annotation_tab = QWidget()  
        layout = QVBoxLayout()  
          
        # アノテーション情報グループ  
        info_group = QGroupBox("アノテーション情報")  
        info_layout = QVBoxLayout()  
        self.annotation_count_label = QLabel("アノテーション数: 0")  
        info_layout.addWidget(self.annotation_count_label)  
        info_group.setLayout(info_layout)  
        layout.addWidget(info_group)  
          
        # アノテーション編集グループ  
        edit_group = QGroupBox("アノテーション編集")  
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
          
        self.edit_mode_btn = QPushButton("編集モード (E)")  
        self.edit_mode_btn.setCheckable(True)  
        self.edit_mode_btn.setStyleSheet(edit_button_style)  
        self.edit_mode_btn.clicked.connect(self._on_edit_mode_clicked)  
        self.edit_mode_btn.setEnabled(False)  
        edit_layout.addWidget(self.edit_mode_btn)  
          
        self.label_combo = QComboBox()  
        self.label_combo.setEditable(True)  
        self.label_combo.setEnabled(False)
        self.label_combo.currentIndexChanged.connect(self._on_label_changed)  
        edit_layout.addWidget(QLabel("ラベル:"))  
        edit_layout.addWidget(self.label_combo)  
          
        self.track_id_edit = QLineEdit()  
        self.track_id_edit.setEnabled(False)  
        self.track_id_edit.setReadOnly(True)  
        edit_layout.addWidget(QLabel("Track ID:"))  
        edit_layout.addWidget(self.track_id_edit)  
          
        self.delete_single_annotation_btn = QPushButton("選択アノテーションを削除 (X)")  
        self.delete_single_annotation_btn.setEnabled(False)  
        self.delete_single_annotation_btn.clicked.connect(self._on_delete_single_annotation_clicked)  
        edit_layout.addWidget(self.delete_single_annotation_btn)  
          
        self.delete_track_btn = QPushButton("一括削除 (D)")  
        self.delete_track_btn.setEnabled(False)  
        self.delete_track_btn.clicked.connect(self._on_delete_track_clicked)  
        edit_layout.addWidget(self.delete_track_btn)  
          
        self.propagate_label_btn = QPushButton("一括ラベル変更 (P)")  
        self.propagate_label_btn.setEnabled(False)  
        self.propagate_label_btn.clicked.connect(self._on_propagate_label_clicked)  
        edit_layout.addWidget(self.propagate_label_btn)

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


        # 自動追跡グループ  
        tracking_group = QGroupBox("自動追跡")  
        tracking_layout = QVBoxLayout()  
        
        # BatchAddModeボタン用
        batch_add_button_style = """  
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
        self.batch_add_annotation_btn = QPushButton("新規アノテーション一括追加 (B)")  
        self.batch_add_annotation_btn.setCheckable(True)  
        self.batch_add_annotation_btn.setEnabled(True)  
        self.batch_add_annotation_btn.setStyleSheet(batch_add_button_style)
        self.batch_add_annotation_btn.clicked.connect(self._on_batch_add_annotation_clicked)  
        tracking_layout.addWidget(self.batch_add_annotation_btn)  
          
        self.tracking_status_label = QLabel("Loading MASA models...")  
        tracking_layout.addWidget(self.tracking_status_label)  
        
        self.tracking_progress_label = QLabel("")  
        tracking_layout.addWidget(self.tracking_progress_label)

        self.execute_batch_add_btn = QPushButton("実行 (R)")  
        self.execute_batch_add_btn.setEnabled(False)  
        self.execute_batch_add_btn.clicked.connect(self._on_complete_batch_add_clicked)  
        tracking_layout.addWidget(self.execute_batch_add_btn)
          
        self.range_info_label = QLabel("範囲: 未選択")  
        tracking_layout.addWidget(self.range_info_label)  
          
        self.tracking_progress_label = QLabel("")  
        tracking_layout.addWidget(self.tracking_progress_label)  

        tracking_group.setLayout(tracking_layout)  
        layout.addWidget(tracking_group)  
          
        layout.addStretch()  
        annotation_tab.setLayout(layout)  
        self.tab_widget.addTab(annotation_tab, "📝 アノテーション")  
    
    def setup_object_list_tab(self):
        """オブジェクト一覧タブのセットアップ"""
        object_list_tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # CurrentFrameObjectListWidgetを追加
        self.object_list_widget = CurrentFrameObjectListWidget(self)
        layout.addWidget(self.object_list_widget)
        
        object_list_tab.setLayout(layout)
        self.tab_widget.addTab(object_list_tab, "📋 オブジェクト一覧")
    
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
            # BatchAddModeがONの場合はOFFにして無効化  
            if self.batch_add_annotation_btn.isChecked():  
                self.batch_add_annotation_btn.setChecked(False)  
            self.batch_add_annotation_btn.setEnabled(False)  
        else:  
            # EditModeがOFFになった時はBatchAddModeボタンを有効化  
            self.batch_add_annotation_btn.setEnabled(True)  
          
        self.edit_mode_requested.emit(checked)  
        self._update_edit_controls_state(checked)  

    def _update_edit_controls_state(self, enabled: bool):  
        """編集関連コントロールの有効/無効を切り替える"""  
        self.label_combo.setEnabled(enabled)  
        self.track_id_edit.setEnabled(enabled)  
        self.delete_single_annotation_btn.setEnabled(enabled and self.current_selected_annotation is not None)  
        self.delete_track_btn.setEnabled(enabled and self.current_selected_annotation is not None)  
        self.propagate_label_btn.setEnabled(enabled and self.current_selected_annotation is not None)  

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
                f"総アノテーション数: {count}\n"  
                f"(読み込み: {loaded_count}, 手動: {manual_count})"  
            )  
        else:  
            self.annotation_count_label.setText(f"アノテーション数: {count}")  
              
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
        if self.play_btn.text() == "再生":  
            self.play_requested.emit()  
            self.play_btn.setText("一時停止(Space)")  
        else:  
            self.pause_requested.emit()  
            self.play_btn.setText("再生(Space)")  
              
    def reset_playback_button(self):  
        """再生ボタンを初期状態にリセット"""  
        self.play_btn.setText("再生(Space)")  
          
    def update_frame_display(self, current_frame: int, total_frames: int):  
        """フレーム表示を更新"""  
        self.frame_label.setText(f"フレーム: {current_frame}/{total_frames - 1}")  
          
    def _on_label_changed(self):  
        """ラベル変更時の処理"""  
        if self.current_selected_annotation:  
            new_label = self.label_combo.currentText()  
            if new_label != self.current_selected_annotation_label:  
                self.label_change_requested.emit(self.current_selected_annotation, new_label)  
                self.current_selected_annotation_label = new_label  
                ErrorHandler.show_info_dialog(  
                    f"アノテーションID {self.current_selected_annotation.object_id} のラベルを '{new_label}' に変更しました。",  
                    "ラベル変更"  
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
                self, "アノテーション削除確認",  
                f"フレーム {self.current_selected_annotation.frame_id} のアノテーション (ID: {self.current_selected_annotation.object_id}, ラベル: '{self.current_selected_annotation.label}') を削除しますか？",  
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
                self, "Track一括削除確認",  
                f"Track ID '{track_id_to_delete}' を持つすべてのアノテーションを削除しますか？\n"  
                "この操作は元に戻せません。",  
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
            dialog.setWindowTitle(f"Track ID {track_id_to_change} のラベルを一括変更")  
              
            if dialog.exec() == QDialog.DialogCode.Accepted:  
                new_label = dialog.get_label()  
                if new_label:  
                    reply = QMessageBox.question(  
                        self, "Track一括ラベル変更確認",  
                        f"Track ID '{track_id_to_change}' を持つすべてのアノテーションのラベルを '{new_label}' に変更しますか？",  
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
                    )  
                    if reply == QMessageBox.StandardButton.Yes:  
                        self.propagate_label_requested.emit(track_id_to_change, new_label)  
                else:  
                    ErrorHandler.show_warning_dialog("新しいラベル名を入力してください。", "入力エラー")
                      
    def get_all_labels_from_manager(self) -> List[str]:  
        """AnnotationRepositoryの全ラベルを取得するヘルパーメソッド"""  
        if self.annotation_repository:  
            return self.annotation_repository.get_all_labels()  
        return []
      
    def _on_batch_add_annotation_clicked(self, checked: bool):  
        """新規アノテーション一括追加ボタンクリック時の処理"""  
        if checked:  
            # EditModeがONの場合はOFFにして無効化  
            if self.edit_mode_btn.isChecked():  
                self.edit_mode_btn.setChecked(False)  
            self.edit_mode_btn.setEnabled(False)  
        else:  
            # BatchAddModeがOFFになった時はEditModeボタンを有効化  
            self.edit_mode_btn.setEnabled(True)  
          
        self.batch_add_mode_requested.emit(checked)  
        self.execute_batch_add_btn.setEnabled(checked)

    def _on_complete_batch_add_clicked(self):  
        """一括追加完了ボタンクリック時の処理"""  
        # temp_bboxes_for_batch_add が空でないことを確認  
        if not self.parent().parent().temp_bboxes_for_batch_add:  
            ErrorHandler.show_warning_dialog("追加するアノテーションがありません。", "警告")  
            return  
  
        # 共通ラベル入力ダイアログを表示  
        # 既存のラベルリストを取得  
        # MASAAnnotationWidgetのannotation_repositoryからラベルを取得  
        existing_labels = self.parent().parent().annotation_repository.get_all_labels()   
        dialog = AnnotationInputDialog(None, self, existing_labels=existing_labels) # bboxは不要なのでNone  
        dialog.setWindowTitle("一括追加アノテーションの共通ラベルを選択")  
  
        if dialog.exec() == QDialog.DialogCode.Accepted:  
            assigned_label = dialog.get_label()  
            if not assigned_label:  
                ErrorHandler.show_warning_dialog("ラベルが選択されていません。", "Warning")  
                return  
  
            # 追跡範囲の取得  
            start_frame, end_frame = self.parent().parent().video_control.get_selected_range()  
            if start_frame == -1 or end_frame == -1:  
                ErrorHandler.show_warning_dialog("追跡範囲が選択されていません。", "Warning")  
                return  
  
            # AnnotationRepositoryから現在のTrack IDの最大値を取得  
            # MASAAnnotationWidgetのannotation_repositoryにアクセス  
            current_max_track_id = self.parent().parent().annotation_repository.next_object_id  
            # MASAAnnotationWidgetに追跡開始を要求  
            # assigned_track_id は バッチ追加で追加されるアノテーションのTrack IDの始まりののインデックスになる。
            self.tracking_requested.emit(current_max_track_id, assigned_label)  
              
            # UIをリセット  
            self.batch_add_annotation_btn.setChecked(False)  
            self.execute_batch_add_btn.setEnabled(False)  
        else:  
            ErrorHandler.show_info_dialog("ラベル選択がキャンセルされました。", "Info")  

    def set_tracking_enabled(self, enabled: bool):  
        """トラッキング機能の有効/無効を設定"""  
        self.execute_batch_add_btn.setEnabled(enabled)  
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
                from ErrorHandler import ErrorHandler  
                ErrorHandler.show_info_dialog("取り消す操作がありません。", "Undo")    
    
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
                from ErrorHandler import ErrorHandler  
                ErrorHandler.show_info_dialog("やり直す操作がありません。", "Redo")
    
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
