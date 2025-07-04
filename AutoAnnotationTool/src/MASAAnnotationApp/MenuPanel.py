# MenuPanel.py
"""
リファクタリングされたMenuPanel - タブ管理のみに責任を限定
各タブの実装は専用のTabManagerに委譲
"""
from typing import Optional
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QLabel
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont

from MASAApplicationService import MASAApplicationService
from BasicSettingsTabManager import BasicSettingsTabManager
from AnnotationEditTabManager import AnnotationEditTabManager
from ObjectListTabManager import ObjectListTabManager
from AnnotationInfoSyncManager import AnnotationInfoSyncManager
from DataClass import ObjectAnnotation, FrameAnnotation

class MenuPanel(QWidget):
    """新しいアーキテクチャによるMenuPanel - タブ統合のみを担当"""
    
    # 各TabManagerからのシグナルを統合して転送
    load_video_requested = pyqtSignal(str)
    load_json_requested = pyqtSignal(str)
    export_requested = pyqtSignal(str)
    
    edit_mode_requested = pyqtSignal(bool)
    batch_add_mode_requested = pyqtSignal(bool)
    tracking_requested = pyqtSignal(int, str)
    
    label_change_requested = pyqtSignal(object, str)
    delete_single_annotation_requested = pyqtSignal(object)
    delete_track_requested = pyqtSignal(int)
    propagate_label_requested = pyqtSignal(int, str)
    
    play_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    
    config_changed = pyqtSignal(str, object, str)
    
    def __init__(self, app_service: MASAApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service
        
        # タブマネージャーの初期化
        self.basic_settings_tab: Optional[BasicSettingsTabManager] = None
        self.annotation_edit_tab: Optional[AnnotationEditTabManager] = None
        self.object_list_tab: Optional[ObjectListTabManager] = None
        self.info_sync_manager: Optional[AnnotationInfoSyncManager] = None
        
        # UI要素
        self.tab_widget: Optional[QTabWidget] = None
        
        # 固定幅を削除し、最小幅のみ設定
        self.setMinimumWidth(250)
        self.setStyleSheet("background-color: #f0f0f0; border-right: 1px solid #ccc;")
        
        self.setup_ui()
        self.connect_tab_signals()
        
    def setup_ui(self):
        """UIを構築"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # タイトル
        title_label = QLabel("MASA Annotation Tool")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # タブウィジェット設定
        self.setup_tab_widget(layout)
        
        self.setLayout(layout)
        
    def setup_tab_widget(self, parent_layout):
        """タブウィジェットを設定"""
        self.tab_widget = QTabWidget()
        
        # タブスタイル設定
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
        
        # 各タブマネージャーを作成・追加
        self.basic_settings_tab = BasicSettingsTabManager(self.app_service, self)
        self.tab_widget.addTab(self.basic_settings_tab, "⚙️ 基本設定")
        
        self.annotation_edit_tab = AnnotationEditTabManager(self.app_service, self)
        self.tab_widget.addTab(self.annotation_edit_tab, "📝 アノテーション")
        
        self.object_list_tab = ObjectListTabManager(self.app_service, self)
        self.tab_widget.addTab(self.object_list_tab, "📋 オブジェクト一覧")
        
        # 情報同期マネージャーを初期化
        self.info_sync_manager = AnnotationInfoSyncManager(self.app_service, self)
        self.info_sync_manager.set_managed_tabs(
            self.annotation_edit_tab,
            self.object_list_tab,
            self.basic_settings_tab
        )
        
        parent_layout.addWidget(self.tab_widget)
        
    def connect_tab_signals(self):
        """各タブのシグナルを接続"""
        if not all([self.basic_settings_tab, self.annotation_edit_tab, self.object_list_tab]):
            return
            
        # BasicSettingsTabのシグナル
        self.basic_settings_tab.load_video_requested.connect(self.load_video_requested.emit)
        self.basic_settings_tab.load_json_requested.connect(self.load_json_requested.emit)
        self.basic_settings_tab.export_requested.connect(self.export_requested.emit)
        self.basic_settings_tab.play_requested.connect(self.play_requested.emit)
        self.basic_settings_tab.pause_requested.connect(self.pause_requested.emit)
        
        # AnnotationEditTabのシグナル
        self.annotation_edit_tab.edit_mode_requested.connect(self.edit_mode_requested.emit)
        self.annotation_edit_tab.batch_add_mode_requested.connect(self.batch_add_mode_requested.emit)
        self.annotation_edit_tab.tracking_requested.connect(self.tracking_requested.emit)
        self.annotation_edit_tab.label_change_requested.connect(self.label_change_requested.emit)
        self.annotation_edit_tab.delete_single_annotation_requested.connect(self.delete_single_annotation_requested.emit)
        self.annotation_edit_tab.delete_track_requested.connect(self.delete_track_requested.emit)
        self.annotation_edit_tab.propagate_label_requested.connect(self.propagate_label_requested.emit)
        
        # ObjectListTabのシグナル
        self.object_list_tab.config_changed.connect(self.config_changed.emit)
        
    # ===== 公開メソッド（外部からの呼び出し用） =====
    
    def update_video_info(self, path: str, total_frames: int):
        """動画情報を更新"""
        if self.info_sync_manager:
            self.info_sync_manager.update_video_info(path, total_frames)
            
    def update_json_info(self, path: str, annotation_count: int):
        """JSON情報を更新"""
        if self.info_sync_manager:
            self.info_sync_manager.update_json_info(path, annotation_count)
            
    def update_annotation_count(self, total: int, manual: int):
        """アノテーション数を更新"""
        if self.info_sync_manager:
            self.info_sync_manager.update_annotation_count(total, manual)
            
    def update_selected_annotation_info(self, annotation: Optional[ObjectAnnotation]):
        """選択アノテーション情報を更新"""
        if self.info_sync_manager:
            self.info_sync_manager.update_selected_annotation_info(annotation)
            
    def initialize_label_combo(self, labels):
        """ラベルコンボボックスを初期化"""
        if self.info_sync_manager:
            self.info_sync_manager.initialize_label_combo(labels)
            
    def update_undo_redo_buttons(self, command_manager):
        """Undo/Redoボタンの状態を更新"""
        if self.info_sync_manager:
            self.info_sync_manager.update_undo_redo_buttons(command_manager)
            
    def update_frame_display(self, frame_id: int, total_frames: int):
        """フレーム表示を更新"""
        if self.info_sync_manager:
            self.info_sync_manager.update_frame_display(frame_id, total_frames)
            
    def update_current_frame_objects(self, frame_id: int, frame_annotation: Optional[FrameAnnotation]):
        """現在フレームのオブジェクト一覧を更新"""
        if self.info_sync_manager:
            self.info_sync_manager.update_current_frame_objects(frame_id, frame_annotation)
            
    def update_range_info(self, start_frame: int, end_frame: int):
        """範囲選択情報を更新"""
        if self.info_sync_manager:
            self.info_sync_manager.update_range_info(start_frame, end_frame)
            
    def update_export_progress(self, message: str, progress: int = -1):
        """エクスポート進捗を更新"""
        if self.info_sync_manager:
            self.info_sync_manager.update_export_progress(message, progress)
            
    def update_tracking_progress(self, message: str, progress: int = -1):
        """追跡進捗を更新"""
        if self.info_sync_manager:
            self.info_sync_manager.update_tracking_progress(message, progress)
            
    def set_tracking_enabled(self, enabled: bool):
        """追跡機能の有効/無効を設定"""
        if self.info_sync_manager:
            self.info_sync_manager.set_tracking_enabled(enabled)
            
    def set_object_list_score_threshold(self, threshold: float):
        """オブジェクト一覧のスコア閾値を設定"""
        if self.info_sync_manager:
            self.info_sync_manager.set_object_list_score_threshold(threshold)
            
    def reset_playback_button(self):
        """再生ボタンをリセット"""
        if self.info_sync_manager:
            self.info_sync_manager.reset_playback_button()
            
    def update_object_list_selection(self, annotation: Optional[ObjectAnnotation]):
        """オブジェクト一覧の選択状態を更新"""
        if self.info_sync_manager:
            self.info_sync_manager.sync_object_list_selection(annotation)
            
    # ===== アクセサメソッド =====
    
    def get_basic_settings_tab(self) -> Optional[BasicSettingsTabManager]:
        """BasicSettingsTabManagerを取得"""
        return self.basic_settings_tab
        
    def get_annotation_edit_tab(self) -> Optional[AnnotationEditTabManager]:
        """AnnotationEditTabManagerを取得"""
        return self.annotation_edit_tab
        
    def get_object_list_tab(self) -> Optional[ObjectListTabManager]:
        """ObjectListTabManagerを取得"""
        return self.object_list_tab
        
    def get_object_list_widget(self):
        """互換性のため - ObjectListTabManagerを返す"""
        return self.object_list_tab
        
    # ===== 後方互換性メソッド（既存コードとの互換性のため） =====
    
    @property
    def current_selected_annotation(self) -> Optional[ObjectAnnotation]:
        """現在選択中のアノテーション（互換性のため）"""
        if self.info_sync_manager:
            return self.info_sync_manager.get_current_selected_annotation()
        return None
        
    @property
    def edit_mode_btn(self):
        """編集モードボタン（互換性のため）"""
        if self.annotation_edit_tab:
            return self.annotation_edit_tab.edit_mode_btn
        return None
        
    @property
    def batch_add_annotation_btn(self):
        """一括追加ボタン（互換性のため）"""
        if self.annotation_edit_tab:
            return self.annotation_edit_tab.batch_add_annotation_btn
        return None
        
    @property
    def execute_batch_add_btn(self):
        """実行ボタン（互換性のため）"""
        if self.annotation_edit_tab:
            return self.annotation_edit_tab.execute_batch_add_btn
        return None
        
    @property
    def delete_single_annotation_btn(self):
        """削除ボタン（互換性のため）"""
        if self.annotation_edit_tab:
            return self.annotation_edit_tab.delete_single_annotation_btn
        return None
        
    @property
    def delete_track_btn(self):
        """トラック削除ボタン（互換性のため）"""
        if self.annotation_edit_tab:
            return self.annotation_edit_tab.delete_track_btn
        return None
        
    @property
    def propagate_label_btn(self):
        """ラベル一括変更ボタン（互換性のため）"""
        if self.annotation_edit_tab:
            return self.annotation_edit_tab.propagate_label_btn
        return None
        
    @property
    def save_masa_json_btn(self):
        """MASA JSON保存ボタン（互換性のため）"""
        if self.basic_settings_tab:
            return self.basic_settings_tab.save_masa_json_btn
        return None
        
    @property
    def save_coco_json_btn(self):
        """COCO JSON保存ボタン（互換性のため）"""
        if self.basic_settings_tab:
            return self.basic_settings_tab.save_coco_json_btn
        return None
        
    # ===== 互換性メソッド（既存のイベントハンドラ呼び出しのため） =====
    
    def _on_load_video_clicked(self, text: str = ""):
        """互換性のため - BasicSettingsTabに委譲"""
        if self.basic_settings_tab:
            self.basic_settings_tab._on_load_video_clicked()
            
    def _on_load_json_clicked(self, text: str = ""):
        """互換性のため - BasicSettingsTabに委譲"""
        if self.basic_settings_tab:
            self.basic_settings_tab._on_load_json_clicked()
            
    def _on_edit_mode_clicked(self, checked: bool):
        """互換性のため - AnnotationEditTabに委譲"""
        if self.annotation_edit_tab:
            self.annotation_edit_tab._on_edit_mode_toggled(checked)
            
    def _on_batch_add_annotation_clicked(self, checked: bool):
        """互換性のため - AnnotationEditTabに委譲"""
        if self.annotation_edit_tab:
            self.annotation_edit_tab._on_batch_add_mode_toggled(checked)
            
    def _on_complete_batch_add_clicked(self):
        """互換性のため - AnnotationEditTabに委譲"""
        if self.annotation_edit_tab:
            self.annotation_edit_tab._on_execute_batch_add_clicked()
            
    def _on_delete_single_annotation_clicked(self):
        """互換性のため - AnnotationEditTabに委譲"""
        if self.annotation_edit_tab:
            self.annotation_edit_tab._on_delete_single_clicked()
            
    def _on_delete_track_clicked(self):
        """互換性のため - AnnotationEditTabに委譲"""
        if self.annotation_edit_tab:
            self.annotation_edit_tab._on_delete_track_clicked()
            
    def _on_propagate_label_clicked(self):
        """互換性のため - AnnotationEditTabに委譲"""
        if self.annotation_edit_tab:
            self.annotation_edit_tab._on_propagate_label_clicked()
