# AnnotationInfoSyncManager.py
"""
アノテーション情報の同期管理を担当
MenuPanelから情報同期処理を分離
"""
from typing import Optional, List
from PyQt6.QtWidgets import QWidget, QLabel, QComboBox, QLineEdit
from PyQt6.QtCore import QObject, pyqtSignal

from MASAApplicationService import MASAApplicationService
from DataClass import ObjectAnnotation

class AnnotationInfoSyncManager(QObject):
    """アノテーション情報の同期管理"""
    
    # シグナル定義
    frame_display_updated = pyqtSignal(int, int)  # current_frame, total_frames
    range_info_updated = pyqtSignal(int, int)  # start_frame, end_frame
    
    def __init__(self, app_service: MASAApplicationService, parent=None):
        super().__init__(parent)
        self.app_service = app_service
        
        # 現在選択中のアノテーション
        self.current_selected_annotation: Optional[ObjectAnnotation] = None
        
        # 管理対象のUI要素（外部から設定される）
        self.annotation_edit_tab = None
        self.object_list_tab = None
        self.basic_settings_tab = None
        
    def set_managed_tabs(self, annotation_edit_tab, object_list_tab, basic_settings_tab):
        """管理対象のタブを設定"""
        self.annotation_edit_tab = annotation_edit_tab
        self.object_list_tab = object_list_tab
        self.basic_settings_tab = basic_settings_tab
        
    def update_selected_annotation_info(self, annotation: Optional[ObjectAnnotation]):
        """選択されたアノテーション情報を同期更新"""
        self.current_selected_annotation = annotation
        
        # AnnotationEditTabに情報を同期
        if self.annotation_edit_tab:
            self.annotation_edit_tab.update_selected_annotation_info(annotation)
            
        # ObjectListTabの選択状態を同期
        if self.object_list_tab:
            self.object_list_tab.update_object_list_selection(annotation)
            
    def update_annotation_count(self, total: int, manual: int):
        """アノテーション数を同期更新"""
        # AnnotationEditTabのカウント表示を更新
        if self.annotation_edit_tab:
            self.annotation_edit_tab.update_annotation_count(total, manual)
            
    def initialize_label_combo(self, labels: List[str]):
        """ラベルコンボボックスを初期化"""
        # AnnotationEditTabのラベルコンボを更新
        if self.annotation_edit_tab:
            self.annotation_edit_tab.initialize_label_combo(labels)
            
    def sync_object_list_selection(self, annotation: Optional[ObjectAnnotation]):
        """オブジェクト一覧の選択状態を同期"""
        # ObjectListTabの選択を更新
        if self.object_list_tab:
            self.object_list_tab.update_object_list_selection(annotation)
            
    def update_current_frame_objects(self, frame_id: int, frame_annotation):
        """現在フレームのオブジェクト一覧を更新"""
        # ObjectListTabのデータを更新
        if self.object_list_tab:
            self.object_list_tab.update_frame_data(frame_id, frame_annotation)
            
    def update_undo_redo_buttons(self, command_manager):
        """Undo/Redoボタンの状態を更新"""
        # AnnotationEditTabのUndo/Redoボタンを更新
        if self.annotation_edit_tab:
            self.annotation_edit_tab.update_undo_redo_buttons(command_manager)
            
    def update_frame_display(self, frame_id: int, total_frames: int):
        """フレーム表示を更新"""
        # ObjectListTabのフレーム情報を更新
        if self.object_list_tab and hasattr(self.object_list_tab, 'frame_info_label'):
            if self.object_list_tab.frame_info_label:
                self.object_list_tab.frame_info_label.setText(f"Frame: {frame_id} / {total_frames}")
                
        # シグナルを発信
        self.frame_display_updated.emit(frame_id, total_frames)
        
    def update_range_info(self, start_frame: int, end_frame: int):
        """範囲選択情報を更新"""
        # シグナルを発信
        self.range_info_updated.emit(start_frame, end_frame)
        
    def update_video_info(self, path: str, total_frames: int):
        """動画情報を更新"""
        # BasicSettingsTabの動画情報を更新
        if self.basic_settings_tab:
            self.basic_settings_tab.update_video_info(path, total_frames)
            
    def update_json_info(self, path: str, annotation_count: int):
        """JSON情報を更新"""
        # BasicSettingsTabのJSON情報を更新
        if self.basic_settings_tab:
            self.basic_settings_tab.update_json_info(path, annotation_count)
            
    def update_export_progress(self, message: str, progress: int = -1):
        """エクスポート進捗を更新"""
        # BasicSettingsTabの進捗表示を更新
        if self.basic_settings_tab:
            self.basic_settings_tab.update_export_progress(message, progress)
            
    def update_tracking_progress(self, message: str, progress: int = -1):
        """追跡進捗を更新"""
        # AnnotationEditTabの追跡進捗を更新
        if self.annotation_edit_tab:
            self.annotation_edit_tab.update_tracking_progress(message, progress)
            
    def set_tracking_enabled(self, enabled: bool):
        """追跡機能の有効/無効を設定"""
        # AnnotationEditTabの追跡機能状態を更新
        if self.annotation_edit_tab:
            self.annotation_edit_tab.set_tracking_enabled(enabled)
            
    def set_object_list_score_threshold(self, threshold: float):
        """オブジェクト一覧のスコア閾値を設定"""
        # ObjectListTabのスコア閾値を更新
        if self.object_list_tab:
            self.object_list_tab.set_score_threshold(threshold)
            
    def reset_playback_button(self):
        """再生ボタンをリセット"""
        # BasicSettingsTabの再生ボタンをリセット
        if self.basic_settings_tab:
            self.basic_settings_tab.reset_playback_button()
            
    def sync_ui_elements(self):
        """UI要素の状態を同期"""
        # 現在のアプリケーション状態に基づいてUI要素を同期
        
        # アノテーション数の同期
        stats = self.app_service.get_statistics()
        self.update_annotation_count(stats["total"], stats["manual"])
        
        # ラベル一覧の同期
        labels = self.app_service.get_all_labels()
        self.initialize_label_combo(labels)
        
        # 表示設定の同期
        display_config = self.app_service.get_display_config()
        if self.object_list_tab and display_config:
            self.object_list_tab.set_display_options(
                display_config.show_manual_annotations,
                display_config.show_auto_annotations
            )
            self.object_list_tab.set_score_threshold(display_config.score_threshold)
            
        # Undo/Redoボタンの同期
        self.update_undo_redo_buttons(self.app_service.command_manager)
        
        # 現在フレームのオブジェクト一覧を同期
        current_frame = self.app_service.get_current_frame()
        frame_annotation = self.app_service.get_annotations(current_frame)
        self.update_current_frame_objects(current_frame, frame_annotation)
        
    def get_current_selected_annotation(self) -> Optional[ObjectAnnotation]:
        """現在選択中のアノテーションを取得"""
        return self.current_selected_annotation
        
    def clear_selection(self):
        """選択状態をクリア"""
        self.update_selected_annotation_info(None)
        
    def refresh_all_displays(self):
        """すべての表示を更新"""
        self.sync_ui_elements()
        
        # 各タブの表示を強制更新
        if self.object_list_tab:
            current_frame = self.app_service.get_current_frame()
            frame_annotation = self.app_service.get_annotations(current_frame)
            self.object_list_tab.update_frame_data(current_frame, frame_annotation)
            
    def handle_config_change(self, key: str, value, config_type: str):
        """設定変更の処理"""
        if config_type == "display":
            if key == "score_threshold":
                self.set_object_list_score_threshold(value)
            elif key in ["show_manual_annotations", "show_auto_annotations"]:
                # 表示オプションの更新
                display_config = self.app_service.get_display_config()
                if self.object_list_tab and display_config:
                    self.object_list_tab.set_display_options(
                        display_config.show_manual_annotations,
                        display_config.show_auto_annotations
                    )
                    
    def validate_ui_consistency(self) -> bool:
        """UI状態の一貫性をチェック"""
        # 選択されたアノテーションが各タブで一致しているかチェック
        edit_tab_annotation = None
        if self.annotation_edit_tab:
            edit_tab_annotation = self.annotation_edit_tab.current_selected_annotation
            
        object_list_annotation = None
        if self.object_list_tab:
            object_list_annotation = self.object_list_tab.get_selected_annotation()
            
        # 一致しているかチェック
        if edit_tab_annotation != object_list_annotation:
            # 不一致の場合は同期修復
            consistent_annotation = self.current_selected_annotation or edit_tab_annotation or object_list_annotation
            self.update_selected_annotation_info(consistent_annotation)
            return False
            
        return True
        
    def force_sync_selection(self, source: str, annotation: Optional[ObjectAnnotation]):
        """強制的に選択状態を同期（循環参照防止）"""
        self.current_selected_annotation = annotation
        
        # ソース以外のタブを更新
        if source != "annotation_edit" and self.annotation_edit_tab:
            self.annotation_edit_tab.update_selected_annotation_info(annotation)
            
        if source != "object_list" and self.object_list_tab:
            self.object_list_tab.update_object_list_selection(annotation)
