# MainUIController.py
"""
UIレイアウト管理を担当するコントローラ
MASAAnnotationWidgetからUIレイアウト処理を分離
"""
from typing import Optional
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PyQt6.QtCore import Qt

from MASAApplicationService import MASAApplicationService
from MenuPanel import MenuPanel
from VideoPreviewWidget import VideoPreviewWidget
from VideoControlPanel import VideoControlPanel

class MainUIController:
    """UIレイアウトの管理とコンポーネントの配置を担当"""
    
    def __init__(self, parent: QWidget, app_service: MASAApplicationService):
        """UIコントローラの初期化"""
        self.parent = parent
        self.app_service = app_service
        
        # UIコンポーネント
        self.splitter: Optional[QSplitter] = None
        self.menu_panel: Optional[MenuPanel] = None
        self.video_preview: Optional[VideoPreviewWidget] = None
        self.video_control: Optional[VideoControlPanel] = None
        
    def setup_main_layout(self):
        """メインレイアウトを構築"""
        # QSplitterを使用してMenuPanelの幅を可変にする
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.setup_splitter()
        main_layout.addWidget(self.splitter)
        
        self.parent.setLayout(main_layout)
        
    def setup_splitter(self):  
        """水平スプリッターを設定"""  
        self.splitter = QSplitter(Qt.Orientation.Horizontal)  
        
        # MenuPanelを作成・追加（修正版 - MASAApplicationServiceを渡す）  
        self.menu_panel = MenuPanel(self.app_service)  
        self.splitter.addWidget(self.menu_panel)  
        
        # 右側レイアウト（動画プレビューとコントロール）を作成  
        right_widget = self._create_right_side_widget()  
        self.splitter.addWidget(right_widget)  
        
        # 初期幅の比率を設定（MenuPanel:VideoArea = 1:3）  
        self.splitter.setSizes([300, 1100])  
        
        # スプリッターのスタイルを設定  
        self.splitter.setStyleSheet("""  
            QSplitter::handle {  
                background-color: #ccc;  
                width: 3px;  
            }  
            QSplitter::handle:hover {  
                background-color: #4CAF50;  
            }  
        """)
        
    def _create_right_side_widget(self) -> QWidget:
        """右側のウィジェット（動画プレビュー + コントロール）を作成"""
        from PyQt6.QtWidgets import QVBoxLayout
        
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 動画プレビューウィジェット
        self.video_preview = VideoPreviewWidget(self.parent)
        right_layout.addWidget(self.video_preview)
        
        # 動画コントロールパネル
        self.video_control = VideoControlPanel()
        right_layout.addWidget(self.video_control)
        
        right_widget.setLayout(right_layout)
        return right_widget
        
    def connect_components(self):
        """コンポーネント間のシグナル/スロット接続を設定"""
        if not self.menu_panel or not self.video_preview or not self.video_control:
            return
            
        # MenuPanelからのシグナル接続
        self.menu_panel.load_video_requested.connect(self._on_load_video_requested)
        self.menu_panel.load_json_requested.connect(self._on_load_json_requested)
        self.menu_panel.export_requested.connect(self._on_export_requested)
        self.menu_panel.edit_mode_requested.connect(self._on_edit_mode_requested)
        self.menu_panel.batch_add_mode_requested.connect(self._on_batch_add_mode_requested)
        self.menu_panel.tracking_requested.connect(self._on_tracking_requested)
        self.menu_panel.label_change_requested.connect(self._on_label_change_requested)
        self.menu_panel.delete_single_annotation_requested.connect(self._on_delete_annotation_requested)
        self.menu_panel.delete_track_requested.connect(self._on_delete_track_requested)
        self.menu_panel.propagate_label_requested.connect(self._on_propagate_label_requested)
        self.menu_panel.play_requested.connect(self._on_play_requested)
        self.menu_panel.pause_requested.connect(self._on_pause_requested)
        self.menu_panel.config_changed.connect(self._on_config_changed)
        
        # VideoPreviewWidgetからのシグナル接続
        self.video_preview.bbox_created.connect(self._on_bbox_created)
        self.video_preview.frame_changed.connect(self._on_frame_changed)
        self.video_preview.annotation_selected.connect(self._on_annotation_selected)
        self.video_preview.annotation_updated.connect(self._on_annotation_updated)
        
        # VideoControlPanelからのシグナル接続
        self.video_control.frame_changed.connect(self.video_preview.set_frame)
        self.video_control.range_changed.connect(self._on_range_selection_changed)
        self.video_control.range_frame_preview.connect(self.video_preview.set_frame)
        
        # BoundingBoxEditorからのシグナル接続
        if hasattr(self.video_preview, 'bbox_editor'):
            self.video_preview.bbox_editor.bbox_position_updated.connect(self._on_bbox_position_updated)
        
        # オブジェクト一覧ウィジェットからのシグナル接続
        object_list_tab = self.menu_panel.get_object_list_tab()
        if object_list_tab:
            object_list_tab.object_selected.connect(self._on_annotation_selected)
            object_list_tab.object_double_clicked.connect(self._on_object_focus_requested)
    
    def refresh_display(self):  
        """表示を更新"""  
        if self.video_preview:  
            self.video_preview.update_frame_display()  
            
        # アノテーション数の更新（修正版 - MASAApplicationService経由）  
        if self.menu_panel:  
            stats = self.app_service.annotation_repository.get_statistics()  
            self.menu_panel.update_annotation_count(stats["total"], stats["manual"])  
            self.menu_panel.initialize_label_combo(self.app_service.annotation_repository.get_all_labels())  
            
            # Undo/Redoボタンの状態更新  
            if hasattr(self.menu_panel, 'update_undo_redo_buttons'):  
                self.menu_panel.update_undo_redo_buttons(self.app_service.command_manager)  
                
        # 現在フレームのオブジェクト一覧更新  
        if self.video_control and self.menu_panel:  
            current_frame = self.video_control.current_frame  
            frame_annotation = self.app_service.annotation_repository.get_annotations(current_frame)  
            self.menu_panel.update_current_frame_objects(current_frame, frame_annotation)    

    # ===== シグナルハンドラ（アプリケーションサービスへの委譲） =====
    
    def _on_load_video_requested(self, file_path: str):
        """動画読み込み要求"""
        success = self.app_service.load_video(file_path)
        if success:
            self._setup_video_components()
            self._update_video_info()
            self.refresh_display()
    
    def _on_load_json_requested(self, file_path: str):
        """JSON読み込み要求"""
        success = self.app_service.load_json(file_path)
        if success:
            self._update_json_info(file_path)
            self.refresh_display()
            # 表示モードに切り替え
            if self.video_preview:
                self.video_preview.set_mode('view')
            if self.menu_panel:
                self.menu_panel.edit_mode_btn.setChecked(False)
    
    def _on_export_requested(self, format: str):
        """エクスポート要求"""
        from PyQt6.QtWidgets import QFileDialog
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"annotations_{timestamp}.{format}"
        
        file_dialog_title = f"Save {format.upper()} Annotations"
        file_path, _ = QFileDialog.getSaveFileName(
            self.parent, file_dialog_title, default_filename,
            "JSON Files (*.json);;All Files (*)"
        )
        
        if file_path:
            if format == "masa":
                success = self.app_service.export_masa_json(file_path)
            elif format == "coco":
                # 進捗表示付きエクスポート
                if self.menu_panel:
                    self.menu_panel.update_export_progress("Exporting COCO JSON...")
                success = self.app_service.export_coco_json(file_path, self._on_export_progress)
            else:
                success = False
                
            if success and self.menu_panel:
                self.menu_panel.update_export_progress("Export completed!")
    
    def _on_export_progress(self, current: int, total: int):
        """エクスポート進捗更新"""
        if self.menu_panel:
            progress_percent = (current / total) * 100
            progress_text = f"Exporting... {current}/{total} ({progress_percent:.1f}%)"
            self.menu_panel.update_export_progress(progress_text)
    
    def _on_edit_mode_requested(self, enabled: bool):
        """編集モード切り替え要求"""
        if self.video_preview:
            if enabled:
                self.video_preview.set_mode('edit')
                if self.video_control:
                    self.video_control.range_slider.setVisible(False)
            else:
                self.video_preview.set_mode('view')
                if self.video_control:
                    self.video_control.range_slider.setVisible(False)
            
            self.video_preview.bbox_editor.set_editing_mode(enabled)
            self.refresh_display()
    
    def _on_batch_add_mode_requested(self, enabled: bool):
        """一括追加モード切り替え要求"""
        if self.video_preview:
            if enabled:
                self.video_preview.set_mode('batch_add')
                if self.video_control:
                    self.video_control.range_slider.setVisible(True)
                self.video_preview.clear_temp_batch_annotations()
            else:
                self.video_preview.set_mode('view')
            
            self.video_preview.bbox_editor.set_editing_mode(enabled)
            self.refresh_display()
    
    def _on_tracking_requested(self, assigned_track_id: int, assigned_label: str):
        """追跡要求"""
        if not self.video_control:
            return
            
        start_frame, end_frame = self.video_control.get_selected_range()
        
        # 一時的なバッチアノテーションを取得
        temp_annotations = []
        if hasattr(self.parent, 'temp_bboxes_for_batch_add'):
            temp_annotations = self.parent.temp_bboxes_for_batch_add
        
        success = self.app_service.start_tracking(
            assigned_track_id, assigned_label, start_frame, end_frame, temp_annotations
        )
        
        if success and self.menu_panel:
            self.menu_panel.update_tracking_progress("Tracking started...")
    
    def _on_label_change_requested(self, annotation, new_label: str):
        """ラベル変更要求"""
        success = self.app_service.update_label(annotation, new_label)
        if success:
            self.refresh_display()
    
    def _on_delete_annotation_requested(self, annotation):
        """アノテーション削除要求"""
        success = self.app_service.delete_annotation(annotation)
        if success:
            self.refresh_display()
    
    def _on_delete_track_requested(self, track_id: int):
        """トラック削除要求"""
        deleted_count = self.app_service.delete_track(track_id)
        if deleted_count > 0:
            self.refresh_display()
    
    def _on_propagate_label_requested(self, track_id: int, new_label: str):
        """ラベル一括変更要求"""
        updated_count = self.app_service.propagate_label(track_id, new_label)
        if updated_count > 0:
            self.refresh_display()
    
    def _on_play_requested(self):
        """再生要求"""
        # 再生処理は親ウィジェットに委譲
        if hasattr(self.parent, 'start_playback'):
            self.parent.start_playback()
    
    def _on_pause_requested(self):
        """一時停止要求"""
        # 一時停止処理は親ウィジェットに委譲
        if hasattr(self.parent, 'pause_playback'):
            self.parent.pause_playback()
    
    def _on_config_changed(self, key: str, value, config_type: str):
        """設定変更要求"""
        self.app_service.update_display_setting(key, value)
        if config_type == "display":
            display_config = self.app_service.get_display_config()
            if self.video_preview:
                self.video_preview.set_display_options(
                    display_config.show_manual_annotations,
                    display_config.show_auto_annotations,
                    display_config.show_ids,
                    display_config.show_confidence,
                    display_config.score_threshold
                )
            # オブジェクト一覧のスコア閾値も更新
            if self.menu_panel:
                self.menu_panel.set_object_list_score_threshold(display_config.score_threshold)
    
    def _on_bbox_created(self, x1: int, y1: int, x2: int, y2: int):
        """バウンディングボックス作成"""
        # ラベル入力処理は親ウィジェットに委譲
        if hasattr(self.parent, 'on_bbox_created'):
            self.parent.on_bbox_created(x1, y1, x2, y2)
    
    def _on_frame_changed(self, frame_id: int):  
        """フレーム変更"""  
        self.app_service.set_current_frame(frame_id)  
        if self.video_control:  
            self.video_control.set_current_frame(frame_id)  
        
        # 修正版：MenuPanelの情報同期マネージャー経由でフレーム表示を更新  
        if self.menu_panel and self.menu_panel.info_sync_manager:  
            video_manager = self.app_service.video_manager  
            total_frames = video_manager.get_total_frames() if video_manager else 0  
            self.menu_panel.info_sync_manager.update_frame_display(frame_id, total_frames)  
        
        # オブジェクト一覧を更新  
        frame_annotation = self.app_service.annotation_repository.get_annotations(frame_id)  
        if self.menu_panel:  
            self.menu_panel.update_current_frame_objects(frame_id, frame_annotation)
    
    def _on_annotation_selected(self, annotation):
        """アノテーション選択"""
        # 選択処理は親ウィジェットに委譲
        if hasattr(self.parent, 'on_annotation_selected'):
            self.parent.on_annotation_selected(annotation)
    
    def _on_annotation_updated(self, annotation):
        """アノテーション更新"""
        # 更新処理は親ウィジェットに委譲
        if hasattr(self.parent, 'on_annotation_updated'):
            self.parent.on_annotation_updated(annotation)
    
    def _on_range_selection_changed(self, start_frame: int, end_frame: int):
        """範囲選択変更"""
        if self.menu_panel:
            self.menu_panel.update_range_info(start_frame, end_frame)
    
    def _on_bbox_position_updated(self, annotation, old_bbox, new_bbox):
        """バウンディングボックス位置更新"""
        success = self.app_service.update_bbox_position(annotation, old_bbox, new_bbox)
        if success:
            self.refresh_display()
    
    def _on_object_focus_requested(self, annotation):
        """オブジェクトフォーカス要求"""
        if self.video_preview and hasattr(self.video_preview, 'focus_on_annotation'):
            self.video_preview.focus_on_annotation(annotation)
        self._on_annotation_selected(annotation)
    
    # ===== ヘルパーメソッド =====
    
    def _setup_video_components(self):
        """動画読み込み後のコンポーネント設定"""
        video_manager = self.app_service.get_video_manager()
        if not video_manager:
            return
            
        if self.video_preview:
            self.video_preview.set_video_manager(video_manager)
            self.video_preview.set_annotation_repository(self.app_service.annotation_repository)
            
        if self.video_control:
            self.video_control.set_total_frames(video_manager.get_total_frames())
            self.video_control.set_current_frame(0)
    
    def _update_video_info(self):
        """動画情報の更新"""
        video_info = self.app_service.get_video_info()
        if self.menu_panel and video_info:
            self.menu_panel.update_video_info(video_info["path"], video_info["total_frames"])
    
    def _update_json_info(self, json_path: str):
        """JSON情報の更新"""
        stats = self.app_service.get_statistics()
        if self.menu_panel:
            self.menu_panel.update_json_info(json_path, stats["total"])
    
    # ===== アクセサメソッド =====
    
    def get_menu_panel(self) -> Optional[MenuPanel]:
        """MenuPanelを取得"""
        return self.menu_panel
    
    def get_video_preview(self) -> Optional[VideoPreviewWidget]:
        """VideoPreviewWidgetを取得"""
        return self.video_preview
    
    def get_video_control(self) -> Optional[VideoControlPanel]:
        """VideoControlPanelを取得"""
        return self.video_control
    
    def get_splitter(self) -> Optional[QSplitter]:
        """Splitterを取得"""
        return self.splitter
