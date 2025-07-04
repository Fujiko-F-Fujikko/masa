# AnnotationEditTabManager.py
"""
アノテーション編集タブの管理を担当
MenuPanelからアノテーション編集関連のUIと処理を分離
"""
from typing import Optional, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
    QPushButton, QLabel, QComboBox, QLineEdit, QCheckBox,
    QSpinBox, QProgressBar
)
from PyQt6.QtCore import pyqtSignal

from MASAApplicationService import MASAApplicationService
from DataClass import ObjectAnnotation
from ErrorHandler import ErrorHandler

class AnnotationEditTabManager(QWidget):
    """アノテーション編集タブのUI管理と編集操作"""
    
    # シグナル定義
    edit_mode_requested = pyqtSignal(bool)
    batch_add_mode_requested = pyqtSignal(bool)
    tracking_requested = pyqtSignal(int, str)  # track_id, label
    label_change_requested = pyqtSignal(object, str)  # annotation, new_label
    delete_single_annotation_requested = pyqtSignal(object)  # annotation
    delete_track_requested = pyqtSignal(int)  # track_id
    propagate_label_requested = pyqtSignal(int, str)  # track_id, new_label
    
    def __init__(self, app_service: MASAApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service
        
        # 現在選択中のアノテーション
        self.current_selected_annotation: Optional[ObjectAnnotation] = None
        
        # UI要素
        self.edit_mode_btn: Optional[QCheckBox] = None
        self.batch_add_annotation_btn: Optional[QCheckBox] = None
        self.execute_batch_add_btn: Optional[QPushButton] = None
        
        # アノテーション情報
        self.annotation_count_label: Optional[QLabel] = None
        self.current_annotation_info: Optional[QLabel] = None
        self.label_combo: Optional[QComboBox] = None
        self.track_id_edit: Optional[QLineEdit] = None
        
        # 操作ボタン
        self.delete_single_annotation_btn: Optional[QPushButton] = None
        self.delete_track_btn: Optional[QPushButton] = None
        self.propagate_label_btn: Optional[QPushButton] = None
        self.undo_btn: Optional[QPushButton] = None
        self.redo_btn: Optional[QPushButton] = None
        
        # 追跡関連
        self.tracking_progress_label: Optional[QLabel] = None
        self.tracking_progress_bar: Optional[QProgressBar] = None
        self.track_id_input: Optional[QSpinBox] = None
        self.track_label_combo: Optional[QComboBox] = None
        self.start_tracking_btn: Optional[QPushButton] = None
        
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """UIを構築"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # アノテーション情報グループ
        self.setup_annotation_info(layout)
        
        # 編集コントロールグループ
        self.setup_edit_controls(layout)
        
        # Undo/Redoグループ
        self.setup_undo_redo(layout)
        
        # 自動追跡グループ
        self.setup_tracking_controls(layout)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def setup_annotation_info(self, parent_layout):
        """アノテーション情報UIを構築"""
        info_group = QGroupBox("Annotation Information")
        info_layout = QVBoxLayout()
        
        # アノテーション数表示
        self.annotation_count_label = QLabel("Total: 0, Manual: 0")
        self.annotation_count_label.setStyleSheet("font-weight: bold; color: #2E7D32;")
        info_layout.addWidget(self.annotation_count_label)
        
        # 現在選択中のアノテーション情報
        self.current_annotation_info = QLabel("No annotation selected")
        self.current_annotation_info.setWordWrap(True)
        self.current_annotation_info.setStyleSheet("color: #666; font-size: 11px; padding: 5px; border: 1px solid #ddd; border-radius: 3px;")
        info_layout.addWidget(self.current_annotation_info)
        
        # ラベル変更
        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel("Label:"))
        self.label_combo = QComboBox()
        self.label_combo.setEditable(True)
        self.label_combo.setEnabled(False)
        label_layout.addWidget(self.label_combo)
        info_layout.addLayout(label_layout)
        
        # Track ID表示・編集
        track_layout = QHBoxLayout()
        track_layout.addWidget(QLabel("Track ID:"))
        self.track_id_edit = QLineEdit()
        self.track_id_edit.setEnabled(False)
        self.track_id_edit.setReadOnly(True)
        track_layout.addWidget(self.track_id_edit)
        info_layout.addLayout(track_layout)
        
        info_group.setLayout(info_layout)
        parent_layout.addWidget(info_group)
        
    def setup_edit_controls(self, parent_layout):
        """編集コントロールUIを構築"""
        edit_group = QGroupBox("Annotation Editing")
        edit_layout = QVBoxLayout()
        
        # モード切り替え
        mode_layout = QVBoxLayout()
        self.edit_mode_btn = QCheckBox("Edit Mode")
        self.edit_mode_btn.setStyleSheet("font-weight: bold;")
        mode_layout.addWidget(self.edit_mode_btn)
        
        self.batch_add_annotation_btn = QCheckBox("Batch Add Mode")
        self.batch_add_annotation_btn.setStyleSheet("font-weight: bold; color: #1976D2;")
        mode_layout.addWidget(self.batch_add_annotation_btn)
        
        self.execute_batch_add_btn = QPushButton("Execute Batch Add")
        self.execute_batch_add_btn.setEnabled(False)
        self.execute_batch_add_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover:enabled {
                background-color: #F57C00;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        mode_layout.addWidget(self.execute_batch_add_btn)
        edit_layout.addLayout(mode_layout)
        
        # 削除ボタン
        delete_layout = QVBoxLayout()
        self.delete_single_annotation_btn = QPushButton("Delete Selected")
        self.delete_single_annotation_btn.setEnabled(False)
        self.delete_single_annotation_btn.setStyleSheet("background-color: #F44336; color: white;")
        delete_layout.addWidget(self.delete_single_annotation_btn)
        
        self.delete_track_btn = QPushButton("Delete Track")
        self.delete_track_btn.setEnabled(False)
        self.delete_track_btn.setStyleSheet("background-color: #D32F2F; color: white;")
        delete_layout.addWidget(self.delete_track_btn)
        
        self.propagate_label_btn = QPushButton("Propagate Label")
        self.propagate_label_btn.setEnabled(False)
        self.propagate_label_btn.setStyleSheet("background-color: #1976D2; color: white;")
        delete_layout.addWidget(self.propagate_label_btn)
        edit_layout.addLayout(delete_layout)
        
        edit_group.setLayout(edit_layout)
        parent_layout.addWidget(edit_group)
        
    def setup_undo_redo(self, parent_layout):
        """Undo/RedoUIを構築"""
        undo_group = QGroupBox("Undo/Redo")
        undo_layout = QHBoxLayout()
        
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.setEnabled(False)
        self.undo_btn.setStyleSheet("background-color: #607D8B; color: white;")
        
        self.redo_btn = QPushButton("Redo")
        self.redo_btn.setEnabled(False)
        self.redo_btn.setStyleSheet("background-color: #607D8B; color: white;")
        
        undo_layout.addWidget(self.undo_btn)
        undo_layout.addWidget(self.redo_btn)
        
        undo_group.setLayout(undo_layout)
        parent_layout.addWidget(undo_group)
        
    def setup_tracking_controls(self, parent_layout):
        """自動追跡UIを構築"""
        tracking_group = QGroupBox("Auto Tracking")
        tracking_layout = QVBoxLayout()
        
        # Track ID・ラベル設定
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Track ID:"))
        self.track_id_input = QSpinBox()
        self.track_id_input.setMinimum(1)
        self.track_id_input.setMaximum(99999)
        self.track_id_input.setValue(1)
        input_layout.addWidget(self.track_id_input)
        
        input_layout.addWidget(QLabel("Label:"))
        self.track_label_combo = QComboBox()
        self.track_label_combo.setEditable(True)
        input_layout.addWidget(self.track_label_combo)
        tracking_layout.addLayout(input_layout)
        
        # 追跡開始ボタン
        self.start_tracking_btn = QPushButton("Start Tracking")
        self.start_tracking_btn.setEnabled(False)
        self.start_tracking_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover:enabled {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #CCCCCC;
            }
        """)
        tracking_layout.addWidget(self.start_tracking_btn)
        
        # 追跡進捗
        self.tracking_progress_label = QLabel("")
        self.tracking_progress_label.setStyleSheet("color: #666; font-size: 11px;")
        tracking_layout.addWidget(self.tracking_progress_label)
        
        self.tracking_progress_bar = QProgressBar()
        self.tracking_progress_bar.setVisible(False)
        tracking_layout.addWidget(self.tracking_progress_bar)
        
        tracking_group.setLayout(tracking_layout)
        parent_layout.addWidget(tracking_group)
        
    def connect_signals(self):
        """シグナル接続を設定"""
        # モード切り替え
        self.edit_mode_btn.toggled.connect(self._on_edit_mode_toggled)
        self.batch_add_annotation_btn.toggled.connect(self._on_batch_add_mode_toggled)
        self.execute_batch_add_btn.clicked.connect(self._on_execute_batch_add_clicked)
        
        # ラベル変更
        self.label_combo.currentTextChanged.connect(self._on_label_changed)
        
        # 削除操作
        self.delete_single_annotation_btn.clicked.connect(self._on_delete_single_clicked)
        self.delete_track_btn.clicked.connect(self._on_delete_track_clicked)
        self.propagate_label_btn.clicked.connect(self._on_propagate_label_clicked)
        
        # Undo/Redo
        self.undo_btn.clicked.connect(self._on_undo_clicked)
        self.redo_btn.clicked.connect(self._on_redo_clicked)
        
        # 追跡
        self.start_tracking_btn.clicked.connect(self._on_start_tracking_clicked)
        
    # ===== イベントハンドラ =====
    
    def _on_edit_mode_toggled(self, checked: bool):
        """編集モード切り替え"""
        if checked and self.batch_add_annotation_btn.isChecked():
            self.batch_add_annotation_btn.setChecked(False)
        self.edit_mode_requested.emit(checked)
        
    def _on_batch_add_mode_toggled(self, checked: bool):
        """一括追加モード切り替え"""
        if checked and self.edit_mode_btn.isChecked():
            self.edit_mode_btn.setChecked(False)
        self.batch_add_mode_requested.emit(checked)
        self.execute_batch_add_btn.setEnabled(checked)
        
    def _on_execute_batch_add_clicked(self):
        """一括追加実行"""
        # バッチ追加の実行準備
        track_id = self.track_id_input.value()
        label = self.track_label_combo.currentText().strip()
        if not label:
            ErrorHandler.show_warning_dialog("Please enter a label for tracking.", "Input Error")
            return
        self.tracking_requested.emit(track_id, label)
        
    def _on_label_changed(self, new_label: str):
        """ラベル変更"""
        if self.current_selected_annotation and new_label.strip():
            if new_label.strip() != self.current_selected_annotation.label:
                self.label_change_requested.emit(self.current_selected_annotation, new_label.strip())
                
    def _on_delete_single_clicked(self):
        """単一アノテーション削除"""
        if self.current_selected_annotation:
            self.delete_single_annotation_requested.emit(self.current_selected_annotation)
            
    def _on_delete_track_clicked(self):
        """トラック一括削除"""
        if self.current_selected_annotation:
            self.delete_track_requested.emit(self.current_selected_annotation.object_id)
            
    def _on_propagate_label_clicked(self):
        """ラベル一括変更"""
        if self.current_selected_annotation:
            new_label = self.label_combo.currentText().strip()
            if new_label:
                self.propagate_label_requested.emit(self.current_selected_annotation.object_id, new_label)
                
    def _on_undo_clicked(self):
        """Undo実行"""
        if self.app_service.undo():
            print("Undo executed")
        else:
            ErrorHandler.show_info_dialog("取り消す操作がありません。", "Undo")
            
    def _on_redo_clicked(self):
        """Redo実行"""
        if self.app_service.redo():
            print("Redo executed")
        else:
            ErrorHandler.show_info_dialog("やり直す操作がありません。", "Redo")
            
    def _on_start_tracking_clicked(self):
        """自動追跡開始"""
        track_id = self.track_id_input.value()
        label = self.track_label_combo.currentText().strip()
        if not label:
            ErrorHandler.show_warning_dialog("Please enter a label for tracking.", "Input Error")
            return
        self.tracking_requested.emit(track_id, label)
        
    # ===== 状態更新メソッド =====
    
    def update_annotation_count(self, total: int, manual: int):
        """アノテーション数を更新"""
        if self.annotation_count_label:
            self.annotation_count_label.setText(f"Total: {total}, Manual: {manual}")
            
    def update_selected_annotation_info(self, annotation: Optional[ObjectAnnotation]):
        """選択アノテーション情報を更新"""
        self.current_selected_annotation = annotation
        
        if annotation:
            # アノテーション情報表示
            info_text = (f"Object ID: {annotation.object_id}\n"
                        f"Frame: {annotation.frame_id}\n"
                        f"Label: {annotation.label}\n"
                        f"Manual: {annotation.is_manual}\n"
                        f"Confidence: {annotation.bbox.confidence:.3f}")
            if self.current_annotation_info:
                self.current_annotation_info.setText(info_text)
                
            # ラベルコンボボックス設定
            if self.label_combo:
                self.label_combo.setCurrentText(annotation.label)
                self.label_combo.setEnabled(True)
                
            # Track ID表示
            if self.track_id_edit:
                self.track_id_edit.setText(str(annotation.object_id))
                
            # ボタン有効化
            self._enable_annotation_buttons(True)
        else:
            # 選択なしの場合
            if self.current_annotation_info:
                self.current_annotation_info.setText("No annotation selected")
            if self.label_combo:
                self.label_combo.setEnabled(False)
            if self.track_id_edit:
                self.track_id_edit.setText("")
                
            # ボタン無効化
            self._enable_annotation_buttons(False)
            
    def _enable_annotation_buttons(self, enabled: bool):
        """アノテーション操作ボタンの有効/無効切り替え"""
        if self.delete_single_annotation_btn:
            self.delete_single_annotation_btn.setEnabled(enabled)
        if self.delete_track_btn:
            self.delete_track_btn.setEnabled(enabled)
        if self.propagate_label_btn:
            self.propagate_label_btn.setEnabled(enabled)
            
    def initialize_label_combo(self, labels: List[str]):
        """ラベルコンボボックスを初期化"""
        if self.label_combo:
            current_text = self.label_combo.currentText()
            self.label_combo.clear()
            self.label_combo.addItems(labels)
            if current_text in labels:
                self.label_combo.setCurrentText(current_text)
                
        if self.track_label_combo:
            current_text = self.track_label_combo.currentText()
            self.track_label_combo.clear()
            self.track_label_combo.addItems(labels)
            if current_text in labels:
                self.track_label_combo.setCurrentText(current_text)
                
    def update_undo_redo_buttons(self, command_manager):
        """Undo/Redoボタンの状態を更新"""
        if self.undo_btn:
            self.undo_btn.setEnabled(command_manager.can_undo())
            if command_manager.can_undo():
                self.undo_btn.setToolTip(f"Undo: {command_manager.get_undo_description()}")
            else:
                self.undo_btn.setToolTip("No operation to undo")
                
        if self.redo_btn:
            self.redo_btn.setEnabled(command_manager.can_redo())
            if command_manager.can_redo():
                self.redo_btn.setToolTip(f"Redo: {command_manager.get_redo_description()}")
            else:
                self.redo_btn.setToolTip("No operation to redo")
                
    def update_tracking_progress(self, message: str, progress: int = -1):
        """追跡進捗を更新"""
        if self.tracking_progress_label:
            self.tracking_progress_label.setText(message)
            
        if self.tracking_progress_bar:
            if progress >= 0:
                self.tracking_progress_bar.setVisible(True)
                self.tracking_progress_bar.setValue(progress)
            else:
                if message == "":
                    self.tracking_progress_bar.setVisible(False)
                    
    def set_tracking_enabled(self, enabled: bool):
        """追跡機能の有効/無効を設定"""
        if self.start_tracking_btn:
            self.start_tracking_btn.setEnabled(enabled)
            
    def update_edit_controls_state(self, enabled: bool):
        """編集コントロールの状態を更新"""
        if self.edit_mode_btn:
            self.edit_mode_btn.setEnabled(enabled)
        if self.batch_add_annotation_btn:
            self.batch_add_annotation_btn.setEnabled(enabled)
