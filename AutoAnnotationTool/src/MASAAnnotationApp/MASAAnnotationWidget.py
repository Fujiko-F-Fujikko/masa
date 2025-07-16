# MASAAnnotationWidget.py
from typing import Dict, List, Optional, Tuple    

from PyQt6.QtWidgets import (    
    QWidget, QHBoxLayout, QVBoxLayout, QDialog,    
    QMessageBox, QFileDialog, QPushButton, QApplication, QSplitter   
)
from PyQt6.QtGui import QKeyEvent  
from PyQt6.QtCore import Qt, QObject, QEvent    
    
from DataClass import BoundingBox, ObjectAnnotation    
from MenuPanel import MenuPanel    
from VideoControlPanel import VideoControlPanel    
from VideoPreviewWidget import VideoPreviewWidget    
from VideoPlaybackController import VideoPlaybackController    
from VideoManager import VideoManager    
from AnnotationRepository import AnnotationRepository    
from ExportService import ExportService    
from ObjectTracker import ObjectTracker    
from TrackingWorker import TrackingWorker    
from AnnotationInputDialog import AnnotationInputDialog    
from ConfigManager import ConfigManager    
from ErrorHandler import ErrorHandler    
from COCOExportWorker import COCOExportWorker  
from TrackingResultConfirmDialog import TrackingResultConfirmDialog  
from CommandPattern import CommandManager, AddAnnotationCommand, DeleteAnnotationCommand, \
                            DeleteTrackCommand, UpdateLabelCommand, UpdateLabelByTrackCommand, \
                            UpdateBoundingBoxCommand, AlignTrackIdsByLabelCommand
  
# QtのデフォルトではSpaceキーでボタンクリックだが、Enterキーに変更する  
class ButtonKeyEventFilter(QObject):    
    def eventFilter(self, obj, event):    
        try:
            if isinstance(obj, QPushButton) and event.type() == QEvent.Type.KeyPress:    
                if event.key() == Qt.Key.Key_Space:    
                    # Spaceキーを無効化    
                    return True    
                elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:    
                    # Enterキーでクリック    
                    obj.click()    
                    return True    
        except RecursionError:
            # 再帰エラーを防ぐ
            return False
        return QObject.eventFilter(self, obj, event)
  
class MASAAnnotationWidget(QWidget):    
    """統合されたMASAアノテーションメインウィジェット（改善版）"""    
        
    def __init__(self, parent=None):    
        super().__init__(parent)    
  
        # キーボードフォーカスを有効にする    
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)    
        self.setFocus()  
        # イベントフィルターを作成してアプリケーションに適用    
        self.button_filter = ButtonKeyEventFilter()    
        QApplication.instance().installEventFilter(self.button_filter)  
  
        self.config_manager = ConfigManager()    
        self.video_manager: Optional[VideoManager] = None    
        self.annotation_repository = AnnotationRepository()    
        self.export_service = ExportService()    
        self.object_tracker = ObjectTracker(self.config_manager.get_full_config(config_type="masa")) # ObjectTrackerにはMASAモデル関連のConfigのみを渡す  
        self.playback_controller: Optional[VideoPlaybackController] = None    
        self.tracking_worker: Optional[TrackingWorker] = None    
        self.temp_bboxes_for_tracking: List[Tuple[int, BoundingBox]] = []    
          
        # CommandManagerを追加  
        self.command_manager = CommandManager()  
            
        self.setup_ui()    
        self._connect_signals()
          
    def setup_ui(self):  
        """UIの初期設定"""  
        self.setWindowTitle("MASA Video Annotation Tool")  
        self.setGeometry(100, 100, 1400, 900)  
          
        # QSplitterを使用してMenuPanelの幅を可変にする
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 水平スプリッターを作成
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # MenuPanelを追加
        self.menu_panel = MenuPanel(self.config_manager)  
        splitter.addWidget(self.menu_panel)
          
        # 右側レイアウトを作成
        right_layout = QVBoxLayout()  
        right_layout.setContentsMargins(0, 0, 0, 0)
          
        self.video_preview = VideoPreviewWidget(self)  
        right_layout.addWidget(self.video_preview)  
          
        self.video_control = VideoControlPanel()  
        right_layout.addWidget(self.video_control)  
          
        right_widget = QWidget()  
        right_widget.setLayout(right_layout)  
        splitter.addWidget(right_widget)
          
        # 初期幅の比率を設定（MenuPanel:VideoArea = 1:3）
        splitter.setSizes([300, 1100])
        
        # スプリッターのスタイルを設定
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #ccc;
                width: 3px;
            }
            QSplitter::handle:hover {
                background-color: #4CAF50;
            }
        """)
        
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
        
        # MenuPanelにAnnotationRepositoryへの参照を設定
        self.menu_panel.annotation_repository = self.annotation_repository
          
    def _connect_signals(self):  
        """シグナルとスロットを接続"""  
        # MenuPanelからのシグナル  
        self.menu_panel.load_video_requested.connect(self.load_video)  
        self.menu_panel.load_json_requested.connect(self.load_json_annotations)  
        self.menu_panel.export_requested.connect(self.export_annotations)  
        self.menu_panel.edit_mode_requested.connect(self.set_edit_mode)  
        self.menu_panel.tracking_mode_requested.connect(self.set_tracking_mode)  
        self.menu_panel.tracking_requested.connect(self.start_tracking)  
        self.menu_panel.label_change_requested.connect(self.on_label_change_requested)  
        self.menu_panel.delete_single_annotation_requested.connect(self.on_delete_annotation_requested)  
        self.menu_panel.delete_track_requested.connect(self.on_delete_track_requested)  
        self.menu_panel.propagate_label_requested.connect(self.on_propagate_label_requested)  
        self.menu_panel.play_requested.connect(self.start_playback)  
        self.menu_panel.pause_requested.connect(self.pause_playback)  
        self.menu_panel.config_changed.connect(self.on_config_changed)  
        self.menu_panel.align_track_ids_requested.connect(self.on_align_track_ids_requested)
        self.menu_panel.copy_mode_requested.connect(self.set_copy_mode)  
        self.menu_panel.copy_annotations_requested.connect(self.start_copy_annotations)

        # VideoPreviewWidgetからのシグナル  
        self.video_preview.bbox_created.connect(self.on_bbox_created)  
        self.video_preview.frame_changed.connect(self.on_frame_changed)  
        self.video_preview.annotation_selected.connect(self.on_annotation_selected)  
        self.video_preview.annotation_updated.connect(self.on_annotation_updated)  
          
        # VideoControlPanelからのシグナル  
        self.video_control.frame_changed.connect(self.video_preview.set_frame)  
        self.video_control.range_changed.connect(self.on_range_selection_changed)  
        self.video_control.range_frame_preview.connect(self.video_preview.set_frame)

        # BoundingBoxEditorからのシグナル
        self.video_preview.bbox_editor.bbox_position_updated.connect(self.on_bbox_position_updated)
        
        # オブジェクト一覧ウィジェットからのシグナル
        object_list_widget = self.menu_panel.get_object_list_widget()
        if object_list_widget:
            object_list_widget.object_selected.connect(self.on_annotation_selected)
            object_list_widget.object_double_clicked.connect(self.on_object_focus_requested)

    @ErrorHandler.handle_with_dialog("Video Load Error")  
    def load_video(self, file_path: str):  
        """動画ファイルを読み込み"""  
        # 既存のVideoManagerがあれば解放  
        if self.video_manager:  
            self.video_manager.release() 
            self.video_manager = None  

        self.video_manager = VideoManager(file_path)  
        if self.video_manager.load_video():  
            self.playback_controller = VideoPlaybackController(self.video_manager)  
            self.playback_controller.frame_updated.connect(self.on_playback_frame_changed)  
            self.playback_controller.playback_finished.connect(self.on_playback_finished)  
              
            self.playback_controller.set_fps(self.video_manager.get_fps())  
              
            self.video_preview.set_video_manager(self.video_manager)  
            self.video_preview.set_annotation_repository(self.annotation_repository)  
            self.video_control.set_total_frames(self.video_manager.get_total_frames())  
            self.video_control.set_current_frame(0)  
            self.menu_panel.update_video_info(file_path, self.video_manager.get_total_frames())  
              
            ErrorHandler.show_info_dialog(f"Video loaded: {file_path}", "Success")  
        else:  
            ErrorHandler.show_error_dialog("Failed to load video file", "Error")  
              
    @ErrorHandler.handle_with_dialog("JSON Load Error")  
    def load_json_annotations(self, file_path: str):  
        """JSONアノテーションファイルを読み込み"""  
        if not self.video_manager:  
            ErrorHandler.show_warning_dialog("Please load a video file first", "Warning")  
            return  
          
        loaded_annotations = self.export_service.import_json(file_path)  
        if loaded_annotations:  
            self.annotation_repository.clear() # 既存のアノテーションをクリア  
            for frame_id, frame_ann in loaded_annotations.items():  
                for obj_ann in frame_ann.objects:  
                    self.annotation_repository.add_annotation(obj_ann)  
              
            self.menu_panel.update_json_info(file_path, self.annotation_repository.get_statistics()["total"])  
            self.update_annotation_count()  
            self.video_preview.set_mode('view') # JSON読み込み後は表示モードに  
            self.menu_panel.edit_mode_btn.setChecked(False) # 編集モードをオフに  
              
            ErrorHandler.show_info_dialog(  
                f"Successfully loaded {self.annotation_repository.get_statistics()['total']} annotations from JSON file",  
                "JSON Loaded"  
            )
            
            # JSON読み込み完了後にオブジェクト一覧を更新
            current_frame = self.video_control.current_frame
            frame_annotation = self.annotation_repository.get_annotations(current_frame)
            self.menu_panel.update_current_frame_objects(current_frame, frame_annotation)
        else:  
            ErrorHandler.show_error_dialog("Failed to load JSON annotation file", "Error")
              
    @ErrorHandler.handle_with_dialog("Export Error")  
    def export_annotations(self, format: str):  
        """アノテーションをエクスポート"""  
        if not self.annotation_repository.frame_annotations:  
            ErrorHandler.show_warning_dialog("No annotations to export", "Warning")  
            return  
          
        if not self.video_manager:  
            ErrorHandler.show_warning_dialog("Video not loaded. Cannot export video-related metadata.", "Warning")  
            return  

        # タイムスタンプ付きのデフォルトファイル名を生成  
        from datetime import datetime  
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  
        default_filename = f"annotations_{timestamp}.{format}" 

        file_dialog_title = f"Save {format.upper()} Annotations"  
        file_path, _ = QFileDialog.getSaveFileName(  
            self, file_dialog_title, default_filename,  
            "JSON Files (*.json);;All Files (*)"  
        )  
          
        if file_path:  
            if format == "masa":  
                self.export_service.export_masa_json(  
                    self.annotation_repository.frame_annotations,  
                    self.video_manager.video_path,  
                    file_path  
                )  
            elif format == "coco":  
                # 進捗表示を開始  
                self.menu_panel.update_export_progress("Exporting COCO JSON...")  
                  
                # スコア閾値でフィルタリングされたアノテーションを作成  
                filtered_annotations = self._filter_annotations_by_score_threshold() 
                # ワーカースレッドでエクスポート実行  
                self.export_worker = COCOExportWorker(  
                    self.export_service,  
                    filtered_annotations,  # スコア閾値でフィルタリング済み  
                    self.video_manager.video_path,  
                    file_path,  
                    self.video_manager  
                )  
                self.export_worker.progress_updated.connect(self.on_export_progress)  
                self.export_worker.export_completed.connect(self.on_export_completed)  
                self.export_worker.error_occurred.connect(self.on_export_error)  
                self.export_worker.start()  
            else:  
                ErrorHandler.show_error_dialog(f"Unsupported export format: {format}", "Error")  
                return

            ErrorHandler.show_info_dialog(f"Annotations exported to {file_path}", "Export Complete")  

    def _filter_annotations_by_score_threshold(self):  
        """現在の表示設定のスコア閾値でアノテーションをフィルタリング"""  
        filtered_frame_annotations = {}  
        score_threshold = self.video_preview.score_threshold  
          
        for frame_id, frame_annotation in self.annotation_repository.frame_annotations.items():  
            if frame_annotation and frame_annotation.objects:  
                filtered_objects = []  
                for annotation in frame_annotation.objects:  
                    # スコア閾値チェック  
                    if annotation.bbox.confidence >= score_threshold:  
                        filtered_objects.append(annotation)  
                  
                if filtered_objects:  
                    # 新しいFrameAnnotationオブジェクトを作成  
                    from DataClass import FrameAnnotation  
                    filtered_frame_annotation = FrameAnnotation(  
                        frame_id=frame_annotation.frame_id,  
                        frame_path=frame_annotation.frame_path,  
                        objects=filtered_objects  
                    )  
                    filtered_frame_annotations[frame_id] = filtered_frame_annotation  
          
        return filtered_frame_annotations

    def on_export_progress(self, current: int, total: int):  
        """エクスポート進捗更新"""  
        progress_percent = (current / total) * 100  
        progress_text = f"Exporting... {current}/{total} ({progress_percent:.1f}%)"  
        self.menu_panel.update_export_progress(progress_text)  
      
    def on_export_completed(self):  
        """エクスポート完了時の処理"""  
        self.menu_panel.update_export_progress("Export completed!")  
      
    def on_export_error(self, error_message: str):  
        """エクスポートエラー時の処理"""  
        self.menu_panel.update_export_progress("")  
        ErrorHandler.show_error_dialog(f"Export failed: {error_message}", "Export Error")

    @ErrorHandler.handle_with_dialog("Tracking Error")  
    def start_tracking(self,  assigned_track_id: int, assigned_label: str):  
        """自動追跡を開始"""  
        if not self.object_tracker:  
            ErrorHandler.show_warning_dialog("MASA models are still loading. Please wait.", "Warning")  
            return  
        
        # ObjectTrackerの実際の初期化（まだされていない場合）  
        if not self.object_tracker.initialized:  
            try:  
                self.object_tracker.initialize()  
            except Exception as e:  
                ErrorHandler.show_error_dialog(f"Failed to initialize MASA models: {str(e)}", "Initialization Error")  
                return  

        if not self.video_manager:  
            ErrorHandler.show_warning_dialog("Please load a video file first", "Warning")  
            return  
          
        start_frame, end_frame = self.video_control.get_selected_range()  
          
        # temp_bboxes_for_tracking に含まれるアノテーションのラベルを assigned_label で上書き  
        initial_annotations_for_worker = []  
        for frame_id, ann_obj in self.temp_bboxes_for_tracking:  
            ann_obj.label = assigned_label # ラベルを上書き  
            initial_annotations_for_worker.append((frame_id, ann_obj.bbox)) # (frame_id, BoundingBox) のタプルを追加  

        new_track_id = assigned_track_id  
        label_for_tracking = assigned_label  
        
        frame_count = end_frame - start_frame + 1  
        reply = QMessageBox.question(  
            self, "Confirm Tracking",  
            f"Start automatic tracking from frame {start_frame} to {end_frame}?\n"  
            f"Total frames to process: {frame_count}\n"  
            f"This may take several minutes.",  
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
        )  
          
        if reply == QMessageBox.StandardButton.Yes:  
            self.menu_panel.update_tracking_progress("Tracking in progress...")  
        
            # 動画の幅と高さを取得  
            video_width = self.video_manager.get_video_width()  
            video_height = self.video_manager.get_video_height()  
        
            self.tracking_worker = TrackingWorker(  
                self.video_manager,  
                self.annotation_repository,  
                self.object_tracker,  
                start_frame,  
                end_frame,  
                initial_annotations_for_worker,  
                new_track_id,  
                label_for_tracking,
                video_width, video_height
            )  
            self.tracking_worker.tracking_completed.connect(self.on_tracking_completed)  
            self.tracking_worker.progress_updated.connect(self.on_tracking_progress)  
            self.tracking_worker.error_occurred.connect(self.on_tracking_error)  
            self.tracking_worker.start()  
              
            # バッチ追加モードの場合はUIをリセット  
            if self.video_preview.mode_manager.current_mode_name == 'tracking':  
                # tmpアノテーションをクリア
                self.temp_bboxes_for_tracking.clear()  
                self.video_preview.clear_temp_tracking_annotations()
                # 編集モードに切り替え
                self.video_preview.set_mode('edit') 
                self.menu_panel.tracking_annotation_btn.setChecked(False)  
                self.menu_panel.execute_add_btn.setEnabled(False)  
                self.menu_panel.edit_mode_btn.setChecked(True)
                self.menu_panel.edit_mode_btn.setEnabled(True)
                self.video_preview.update_frame_display()

    def on_tracking_progress(self, current_frame: int, total_frames: int):  
        """追跡進捗更新"""  
        progress_percent = (current_frame / total_frames) * 100  
        progress_text = f"Tracking... {current_frame}/{total_frames} ({progress_percent:.1f}%)"  
        self.menu_panel.update_tracking_progress(progress_text)  
          
    def on_tracking_completed(self, results: Dict[int, List[ObjectAnnotation]]):  
        """追跡完了時の処理（確認ダイアログ付き）"""  
        self.menu_panel.update_tracking_progress("Tracking completed. Waiting for confirmation...")  
          
        # 確認ダイアログを表示  
        dialog = TrackingResultConfirmDialog(results, self.video_manager, self)  
          
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.approved:  
            # ユーザーが承認した場合のみ追加  
            added_count = 0  
            # dialog.tracking_results にはユーザーが削除した後のアノテーションが含まれる  
            final_results_to_add = dialog.tracking_results   
  
            for frame_id, annotations in final_results_to_add.items():  
                for annotation in annotations:  
                    if self.annotation_repository.add_annotation(annotation):  
                        added_count += 1  
              
            self.update_annotation_count()  
            self.video_preview.update_frame_display()  
              
            ErrorHandler.show_info_dialog(
                f"Tracking completed. {added_count} annotations were added.",
                "Tracking Complete"
            )
            self.menu_panel.update_tracking_progress("Tracking completed and annotations added!")  
        else:  
            # ユーザーが破棄を選択した場合  
            ErrorHandler.show_info_dialog(
                "Tracking results were discarded.",
                "Tracking Cancelled"
            )
            self.menu_panel.update_tracking_progress("Tracking results discarded.")
          
    def on_tracking_error(self, message: str):  
        """追跡エラー時の処理"""  
        self.menu_panel.update_tracking_progress("Tracking failed.")  
        ErrorHandler.show_error_dialog(f"Tracking encountered an error: {message}", "Tracking Error")  
          
    def on_bbox_created(self, x1: int, y1: int, x2: int, y2: int):  
        """バウンディングボックス作成時の処理（コマンドパターン対応）"""  
        bbox = BoundingBox(x1, y1, x2, y2)  
        current_frame = self.video_control.current_frame  
          
        # 現在のモードがEditModeの場合のみラベル入力ダイアログを表示  
        if self.video_preview.mode_manager.current_mode_name == 'edit':  
            dialog = AnnotationInputDialog(bbox, self, existing_labels=self.annotation_repository.get_all_labels())  
            if dialog.exec() == QDialog.DialogCode.Accepted:  
                label = dialog.get_label()  
                if label:  
                    annotation = ObjectAnnotation(  
                        object_id=-1,  # 新規IDを意味  
                        frame_id=current_frame,  
                        bbox=bbox,  
                        label=label,  
                        is_manual=True,  
                        track_confidence=1.0,  
                        is_manual_added= True  # 手動追加されたアノテーションとしてマーク
                    )  
                      
                    # コマンドパターンを使用してアノテーション追加  
                    command = AddAnnotationCommand(self.annotation_repository, annotation)  
                    self.command_manager.execute_command(command)  
                      
                    self.update_annotation_count()  
                    ErrorHandler.show_info_dialog(f"Added annotation: {label} at frame {current_frame}", "Annotation Added")  
                      
                    self.video_preview.bbox_editor.selected_annotation = annotation  
                    self.video_preview.bbox_editor.selection_changed.emit(annotation)  
                    self.video_preview.update_frame_display()
                    
                    # オブジェクト一覧を更新
                    frame_annotation = self.annotation_repository.get_annotations(current_frame)
                    self.menu_panel.update_current_frame_objects(current_frame, frame_annotation)
                else:  
                    ErrorHandler.show_warning_dialog("Label cannot be empty.", "Input Error")
        elif self.video_preview.mode_manager.current_mode_name == 'tracking':  
            # TrackingModeの場合、ラベル入力ダイアログは表示しない(正常動作)  
            pass  
        else:  
            # その他のモードの場合（予期しないケース）  
            ErrorHandler.show_warning_dialog("bbox_created was called in an unknown mode.", "Warning")
    def on_frame_changed(self, frame_id: int):  
        """フレーム変更時の処理"""  
        self.video_control.set_current_frame(frame_id)  
        self.menu_panel.update_frame_display(frame_id, self.video_manager.get_total_frames())
        
        # オブジェクト一覧を更新
        frame_annotation = self.annotation_repository.get_annotations(frame_id)
        self.menu_panel.update_current_frame_objects(frame_id, frame_annotation)

    def set_edit_mode(self, enabled: bool):  
        """編集モードの設定とUIの更新"""  
        if enabled:  
            # TrackingModeがONの場合はOFFにする  
            if self.menu_panel.tracking_annotation_btn.isChecked():  
                self.menu_panel.tracking_annotation_btn.setChecked(False)  
                self.set_tracking_mode(False)  
              
            self.video_preview.set_mode('edit')  
            self.video_control.range_slider.setVisible(False)  
            self.video_preview.clear_temp_tracking_annotations()  
            ErrorHandler.show_info_dialog("Edit mode enabled.", "Mode Change")
        else:  
            self.video_preview.set_mode('view')  
            self.video_control.range_slider.setVisible(False)  
            ErrorHandler.show_info_dialog("Edit mode disabled.", "Mode Change")
        self.video_preview.bbox_editor.set_editing_mode(enabled)  
        self.video_preview.update_frame_display()  
      
    def set_tracking_mode(self, enabled: bool):  
        """一括追加モードの設定とUIの更新"""  
        if enabled:  
            # EditModeがONの場合はOFFにする  
            if self.menu_panel.edit_mode_btn.isChecked():  
                self.menu_panel.edit_mode_btn.setChecked(False)  
                self.set_edit_mode(False)  
              
            self.video_preview.set_mode('tracking')  
            self.video_control.range_slider.setVisible(True)
            self.video_preview.clear_temp_tracking_annotations()  
            ErrorHandler.show_info_dialog(
                "Tracking mode enabled.\n"
                "1. Draw bounding boxes on the video preview.\n"
                "2. Specify the frame range to add.\n"
                "3. Press the Run button.",
                "Mode Change"
            )
            self.temp_bboxes_for_tracking.clear()  
            # 再生中の場合は停止  
            if self.playback_controller and self.playback_controller.is_playing:  
                self.playback_controller.pause()  
        else:  
            self.video_preview.set_mode('view')  
            ErrorHandler.show_info_dialog("Tracking Mode disabled.", "Mode Change")
            # モード終了時に再生を停止し、タイマーを確実に停止  
            if self.playback_controller:  
                self.playback_controller.pause() 
        self.video_preview.bbox_editor.set_editing_mode(enabled)  
        self.video_preview.update_frame_display()

  
    def on_delete_annotation_requested(self, annotation: ObjectAnnotation):  
        """単一アノテーション削除要求時の処理（コマンドパターン対応）"""  
        # コマンドパターンを使用してアノテーション削除  
        command = DeleteAnnotationCommand(self.annotation_repository, annotation)  
        if self.command_manager.execute_command(command):  
            self.video_preview.bbox_editor.selected_annotation = None  
            self.video_preview.bbox_editor.selection_changed.emit(None)  
            ErrorHandler.show_info_dialog("Annotation deleted.", "Delete Complete")
            self.update_annotation_count()  
            self.video_preview.update_frame_display()
            
            # オブジェクト一覧を更新
            current_frame = self.video_control.current_frame
            frame_annotation = self.annotation_repository.get_annotations(current_frame)
            self.menu_panel.update_current_frame_objects(current_frame, frame_annotation)
        else:  
            ErrorHandler.show_warning_dialog("Failed to delete annotation.", "Error")
  
    def on_delete_track_requested(self, track_id: int):  
        """Track IDによる一括削除要求時の処理（コマンドパターン対応）"""  
        # コマンドパターンを使用してトラック削除  
        command = DeleteTrackCommand(self.annotation_repository, track_id)  
        deleted_count = self.command_manager.execute_command(command)  
          
        if deleted_count > 0:  
            self.video_preview.bbox_editor.selected_annotation = None  
            self.video_preview.bbox_editor.selection_changed.emit(None)  
            ErrorHandler.show_info_dialog(
                f"Deleted {deleted_count} annotations for Track ID '{track_id}'.",
                "Delete Complete"
            )
            self.update_annotation_count()  
            self.video_preview.update_frame_display()
            
            # オブジェクト一覧を更新
            current_frame = self.video_control.current_frame
            frame_annotation = self.annotation_repository.get_annotations(current_frame)
            self.menu_panel.update_current_frame_objects(current_frame, frame_annotation)
        else:  
            ErrorHandler.show_warning_dialog(
                f"No annotations found for Track ID '{track_id}'.",
                "Error"
            )
  
    def on_label_change_requested(self, annotation: ObjectAnnotation, new_label: str):  
        """アノテーションのラベル変更要求時の処理（コマンドパターン対応）"""  
        try:  
            old_label = annotation.label  
            # コマンドパターンを使用してラベル更新  
            command = UpdateLabelCommand(self.annotation_repository, annotation, old_label, new_label)  
            if self.command_manager.execute_command(command):  
                self.video_preview.update_frame_display()  
                self.update_annotation_count()
                
                # オブジェクト一覧を更新
                current_frame = self.video_control.current_frame
                frame_annotation = self.annotation_repository.get_annotations(current_frame)
                self.menu_panel.update_current_frame_objects(current_frame, frame_annotation)
            else:  
                ErrorHandler.show_warning_dialog("Failed to update annotation.", "Error")
        except Exception as e:  
            ErrorHandler.show_error_dialog(f"Error occurred while changing label: {e}", "Error")
  
    def on_propagate_label_requested(self, track_id: int, new_label: str):  
        """トラック単位でのラベル変更要求時の処理（コマンドパターン対応）"""  
        try:  
            # 現在のラベルを取得（最初のアノテーションから）  
            annotations = self.annotation_repository.get_annotations_by_track_id(track_id)  
            if not annotations:  
                ErrorHandler.show_warning_dialog(
                    f"No annotations found for Track ID '{track_id}'.",
                    "Error"
                )
                return  
              
            old_label = annotations[0].label  
            # コマンドパターンを使用してトラック単位でラベル更新  
            command = UpdateLabelByTrackCommand(self.annotation_repository, track_id, old_label, new_label)  
            updated_count = self.command_manager.execute_command(command)  
              
            if updated_count > 0:  
                self.video_preview.update_frame_display()  
                self.update_annotation_count()
                
                # オブジェクト一覧を更新
                current_frame = self.video_control.current_frame
                frame_annotation = self.annotation_repository.get_annotations(current_frame)
                self.menu_panel.update_current_frame_objects(current_frame, frame_annotation)
                
                ErrorHandler.show_info_dialog(
                    f"Changed label of {updated_count} annotations for Track ID '{track_id}' to '{new_label}'.",
                    "Label Change Complete"
                )
            else:  
                ErrorHandler.show_warning_dialog("Failed to update label.", "Error")
        except Exception as e:  
            ErrorHandler.show_error_dialog(f"Error occurred while changing label: {e}", "Error")
  
    def on_align_track_ids_requested(self, label: str, target_track_id: int):  
        """Track ID統一要求時の処理（コマンドパターン対応）"""  
        try:  
            # コマンドパターンを使用してTrack ID統一  
            command = AlignTrackIdsByLabelCommand(self.annotation_repository, label, target_track_id)  
            updated_count = self.command_manager.execute_command(command)  
            
            if updated_count > 0:  
                self.video_preview.update_frame_display()  
                self.update_annotation_count()  
                
                # オブジェクト一覧を更新  
                current_frame = self.video_control.current_frame  
                frame_annotation = self.annotation_repository.get_annotations(current_frame)  
                self.menu_panel.update_current_frame_objects(current_frame, frame_annotation)  
                
                ErrorHandler.show_info_dialog(  
                    f"Aligned {updated_count} annotations with label '{label}' to Track ID '{target_track_id}'.",  
                    "Track ID Alignment Complete"  
                )  
            else:  
                ErrorHandler.show_warning_dialog("No annotations were updated.", "Info")  
        except Exception as e: 
            ErrorHandler.show_error_dialog(f"Error occurred while merging track id: {e}", "Error") 

    def start_playback(self):  
        """動画再生を開始"""  
        if self.playback_controller:  
            self.playback_controller.play(self.video_control.current_frame)

    def pause_playback(self):  
        """動画再生を一時停止"""  
        if self.playback_controller:  
            self.playback_controller.pause()  
            self.menu_panel.reset_playback_button()

    def on_config_changed(self, key: str, value: object, config_type: str): # config_type引数を追加  
        """設定変更時の処理"""  
        if config_type == "display":  
            display_options = self.config_manager.get_full_config(config_type="display")  
            self.video_preview.set_display_options(  
                display_options.show_manual_annotations,  
                display_options.show_auto_annotations,  
                display_options.show_ids,  
                display_options.show_confidence,  
                display_options.score_threshold  
            )
            # オブジェクト一覧のスコア閾値も更新
            self.menu_panel.set_object_list_score_threshold(display_options.score_threshold)
        # 他のconfig_typeの変更もここに追加

    def on_annotation_selected(self, annotation: Optional[ObjectAnnotation]):  
        """アノテーション選択時の処理（中央集権的制御）"""  
        # ガード条件: 必要なオブジェクトが初期化されているかチェック
        if not self.video_manager or not self.annotation_repository:
            return
            
        if not hasattr(self.video_preview, 'update_frame_display'):
            return
            
        # 循環呼び出し防止
        if hasattr(self, '_updating_selection') and self._updating_selection:
            return
            
        self._updating_selection = True
        try:
            # MenuPanelの情報を更新  
            self.menu_panel.update_selected_annotation_info(annotation)  
            
            # オブジェクト一覧の選択状態も更新（双方向同期）
            self.menu_panel.update_object_list_selection(annotation)
            
            # VideoPreviewWidgetの選択状態を更新
            if hasattr(self.video_preview, 'bbox_editor') and self.video_preview.bbox_editor:
                self.video_preview.bbox_editor.selected_annotation = annotation
                self.video_preview.bbox_editor.selection_changed.emit(annotation)
            
            # VideoPreviewWidgetの表示も確実に更新  
            self.video_preview.update_frame_display()
            
            # Undo/Redoボタンの状態も更新  
            if hasattr(self.menu_panel, 'update_undo_redo_buttons'):  
                self.menu_panel.update_undo_redo_buttons(self.command_manager)
        finally:
            self._updating_selection = False

    def on_annotation_updated(self, annotation: ObjectAnnotation):  
        """アノテーション更新時の処理（位置変更以外）"""  
        # 一時的なバッチアノテーションの場合は、アノテーションリポジトリ更新をスキップ  
        if hasattr(annotation, 'is_manual_added') and annotation.is_manual_added:  
            self.update_annotation_count()  
            return  
        
        # 位置変更は別途bbox_position_updatedで処理されるため、ここでは他の更新のみ  
        if self.annotation_repository.update_annotation(annotation):  
            self.update_annotation_count()  
        else:  
            ErrorHandler.show_warning_dialog("アノテーションの更新に失敗しました。", "Error")

    def on_range_selection_changed(self, start_frame: int, end_frame: int):  
        """範囲選択変更時の処理"""  
        self.menu_panel.update_range_info(start_frame, end_frame)

    def on_playback_frame_changed(self, frame_id: int):  
        """再生中のフレーム更新時の処理"""  
        self.video_control.set_current_frame(frame_id)  
        self.video_preview.set_frame(frame_id)  
        self.menu_panel.update_frame_display(frame_id, self.video_manager.get_total_frames())

    def on_playback_finished(self):  
        """再生完了時の処理"""  
        self.menu_panel.reset_playback_button()  
        ErrorHandler.show_info_dialog("Video playback completed.", "Playback Complete")

    def on_model_initialization_completed(self, object_tracker):  
        """モデル初期化完了時の処理"""  
        self.object_tracker = object_tracker  
        self.menu_panel.set_tracking_enabled(True)  # トラッキング機能を有効化  
        print("MASA models loaded successfully")
    
    def on_model_initialization_failed(self, error_message):  
        """モデル初期化失敗時の処理"""  
        ErrorHandler.show_error_dialog(f"Failed to initialize MASA models: {error_message}", "Initialization Error")  
        self.menu_panel.set_tracking_enabled(False)  # トラッキング機能を無効化

    def update_annotation_count(self):  
        """アノテーション数を更新し、UIに反映（Undo/Redoボタン状態も更新）"""  
        stats = self.annotation_repository.get_statistics()  
        self.menu_panel.update_annotation_count(stats["total"], stats["manual"])  
        self.menu_panel.initialize_label_combo(self.annotation_repository.get_all_labels())  
          
        # Undo/Redoボタンの状態を更新  
        if hasattr(self.menu_panel, 'update_undo_redo_buttons'):  
            self.menu_panel.update_undo_redo_buttons(self.command_manager)

    def on_bbox_position_updated(self, annotation: ObjectAnnotation, old_bbox: BoundingBox, new_bbox: BoundingBox):  
        """バウンディングボックス位置更新時の処理（コマンドパターン対応）"""  
        # 位置に変更があった場合のみコマンドを実行  
        if (old_bbox.x1 != new_bbox.x1 or old_bbox.y1 != new_bbox.y1 or   
            old_bbox.x2 != new_bbox.x2 or old_bbox.y2 != new_bbox.y2):  
            
            command = UpdateBoundingBoxCommand(self.annotation_repository, annotation, old_bbox, new_bbox)  
            self.command_manager.execute_command(command)  
            
            self.update_annotation_count()  
            self.video_preview.update_frame_display()
            
            # オブジェクト一覧を更新
            current_frame = self.video_control.current_frame
            frame_annotation = self.annotation_repository.get_annotations(current_frame)
            self.menu_panel.update_current_frame_objects(current_frame, frame_annotation)
            
    def on_object_focus_requested(self, annotation: Optional[ObjectAnnotation]):
        """オブジェクトフォーカス要求時の処理"""
        if annotation and hasattr(self.video_preview, 'focus_on_annotation'):
            # ビデオプレビューでオブジェクトにフォーカス
            self.video_preview.focus_on_annotation(annotation)
            # アノテーションを選択状態にする
            self.on_annotation_selected(annotation)

    def set_copy_mode(self, enabled: bool):  
        """コピーモードの設定とUIの更新"""  
        if enabled:  
            # 他のモードがONの場合はOFFにする  
            if self.menu_panel.edit_mode_btn.isChecked():  
                self.menu_panel.edit_mode_btn.setChecked(False)  
                self.set_edit_mode(False)  
            if self.menu_panel.tracking_annotation_btn.isChecked():  
                self.menu_panel.tracking_annotation_btn.setChecked(False)  
                self.set_tracking_mode(False)  
            
            # コピーモードでは既存アノテーションを選択可能にする  
            self.video_preview.set_mode('edit')  # editモードベースで既存アノテーション選択を有効化  
            self.video_control.range_slider.setVisible(True)  # フレーム範囲選択を表示  
            self.video_preview.bbox_editor.set_editing_mode(True)  
            
            ErrorHandler.show_info_dialog(  
                "Copy mode enabled.\n"  
                "1. Select an annotation to copy.\n"  
                "2. Specify the frame range.\n"  
                "3. Press the Run button.",  
                "Mode Change"  
            )  
        else:  
            self.video_preview.set_mode('view')  
            self.video_control.range_slider.setVisible(False)  
            self.video_preview.bbox_editor.set_editing_mode(False)  
            ErrorHandler.show_info_dialog("Copy mode disabled.", "Mode Change")  
        
        self.video_preview.update_frame_display()

    def start_copy_annotations(self, assigned_track_id: int, assigned_label: str):  
        """選択されたアノテーションのコピーを開始"""  
        if not self.video_manager:  
            ErrorHandler.show_warning_dialog("Please load a video file first", "Warning")  
            return  
        
        # 選択されたアノテーションを取得  
        selected_annotation = self.menu_panel.current_selected_annotation  
        if not selected_annotation:  
            ErrorHandler.show_warning_dialog("Please select an annotation to copy", "Warning")  
            return  
        
        start_frame, end_frame = self.video_control.get_selected_range()  
        if start_frame == -1 or end_frame == -1:  
            ErrorHandler.show_warning_dialog("No frame range selected.", "Warning")  
            return  
        
        # 選択されたアノテーションを指定フレーム範囲にコピー  
        copied_count = 0  
        for frame_id in range(start_frame, end_frame + 1):  
            # 新しいアノテーションを作成  
            new_annotation = ObjectAnnotation(  
                object_id=selected_annotation.object_id,  # コピー元と同じTrack IDを使用  
                frame_id=frame_id,  
                bbox=BoundingBox(  
                    selected_annotation.bbox.x1,  
                    selected_annotation.bbox.y1,  
                    selected_annotation.bbox.x2,  
                    selected_annotation.bbox.y2,  
                    confidence=1.0  
                ),  
                label=assigned_label,  
                is_manual=True,  
                track_confidence=1.0,  
                is_manual_added=True  # 手動追加されたアノテーションとしてマーク  
            )  
            
            # コマンドパターンでアノテーション追加  
            command = AddAnnotationCommand(self.annotation_repository, new_annotation)  
            if self.command_manager.execute_command(command):  
                copied_count += 1  
        
        self.update_annotation_count()  
        self.video_preview.update_frame_display()  
        
        ErrorHandler.show_info_dialog(  
            f"Copied annotation to {copied_count} frames.",  
            "Copy Complete"  
        )  

        # 現在の選択を解除して次のアノテーション選択を促す  
        self.video_preview.bbox_editor.selected_annotation = None  
        self.video_preview.bbox_editor.selection_changed.emit(None)  
        self.menu_panel.update_selected_annotation_info(None)

    def keyPressEvent(self, event: QKeyEvent):  
        """キーボードショートカットの処理（拡張版）"""  
        # フォーカスされたウィジェットを取得  
        focused_widget = self.focusWidget()  
        
        # テキスト入力中（QLineEdit、QComboBox編集中）はショートカットを無効化  
        from PyQt6.QtWidgets import QLineEdit, QComboBox  
        if isinstance(focused_widget, (QLineEdit, QComboBox)):  
            # ただし、Ctrl系のショートカットは有効にする  
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:  
                pass  # Ctrl系は下で処理  
            else:  
                super().keyPressEvent(event)  
                return  
          
        if isinstance(focused_widget, QPushButton):  
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:  
                # Enterキーでボタンをクリック  
                focused_widget.click()  
                event.accept()  
                return  
            elif event.key() == Qt.Key.Key_Space:  
                # Spaceキーの場合は何もしない（デフォルト動作を無効化）  
                event.accept()  
                return  
        
        # Ctrlキー組み合わせの処理  
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:  
            if event.key() == Qt.Key.Key_O:  
                # Ctrl+O: 動画を読み込み  
                self.menu_panel._on_load_video_clicked("")  
                event.accept()  
                return  
            elif event.key() == Qt.Key.Key_L:  
                # Ctrl+L: JSONを読み込み  
                self.menu_panel._on_load_json_clicked("")  
                event.accept()  
                return  
            elif event.key() == Qt.Key.Key_S:  
                # Ctrl+S: MASA JSONを保存  
                if self.menu_panel.save_masa_json_btn.isEnabled():  
                    self.export_annotations("masa")  
                event.accept()  
                return
            elif event.key() == Qt.Key.Key_Z:  
                # Ctrl+Z: Undo  
                if self.command_manager.undo():  
                    self.update_annotation_count()  
                    self.video_preview.update_frame_display()  
                    # 選択状態をクリア  
                    self.video_preview.bbox_editor.selected_annotation = None  
                    self.video_preview.bbox_editor.selection_changed.emit(None)  
                    print("--- Undo ---")
                else:  
                    ErrorHandler.show_info_dialog("There are no actions to undo.", "Undo")  
                event.accept()  
                return  
            elif event.key() == Qt.Key.Key_Y:  
                # Ctrl+Y: Redo  
                if self.command_manager.redo():  
                    self.update_annotation_count()  
                    self.video_preview.update_frame_display()  
                    # 選択状態をクリア  
                    self.video_preview.bbox_editor.selected_annotation = None  
                    self.video_preview.bbox_editor.selection_changed.emit(None)  
                    print("--- Redo ---")
                else:  
                    ErrorHandler.show_info_dialog("There are no actions to redo.", "Redo")  
                event.accept()  
                return  
        
        # Ctrl+Shift組み合わせの処理  
        if event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):  
            if event.key() == Qt.Key.Key_S:  
                # Ctrl+Shift+S: COCO JSONを保存  
                if self.menu_panel.save_coco_json_btn.isEnabled():  
                    self.export_annotations("coco")  
                event.accept()  
                return
        
        # 単独キーのショートカット処理  
        if event.key() == Qt.Key.Key_Space:  
            # 動画再生・一時停止の処理  
            if self.playback_controller and self.playback_controller.is_playing:  
                self.pause_playback()  
            else:  
                self.start_playback()  
            event.accept()  
        elif event.key() == Qt.Key.Key_Left:  
            self.video_control.prev_frame()  
            event.accept()  
        elif event.key() == Qt.Key.Key_Right:  
            self.video_control.next_frame()  
            event.accept()  
        elif event.key() == Qt.Key.Key_E:  
            # Eキー: 編集モード切り替え  
            if self.menu_panel.edit_mode_btn.isEnabled():  
                current_state = self.menu_panel.edit_mode_btn.isChecked()  
                self.menu_panel.edit_mode_btn.setChecked(not current_state)  
                self.menu_panel._on_edit_mode_clicked(not current_state)  
            event.accept()  
        elif event.key() == Qt.Key.Key_T:  
            # Tキー: トラッキングモード切り替え  
            if self.menu_panel.tracking_annotation_btn.isEnabled():  
                current_state = self.menu_panel.tracking_annotation_btn.isChecked()  
                self.menu_panel.tracking_annotation_btn.setChecked(not current_state)  
                self.menu_panel._on_tracking_annotation_clicked(not current_state)  
            event.accept()  
        elif event.key() == Qt.Key.Key_C:  
            # Cキー: コピーモード切り替え  
            if self.menu_panel.copy_annotation_btn.isEnabled():  
                current_state = self.menu_panel.copy_annotation_btn.isChecked()  
                self.menu_panel.copy_annotation_btn.setChecked(not current_state)  
                self.menu_panel._on_copy_annotation_clicked(not current_state)  
            event.accept()  
        elif event.key() == Qt.Key.Key_X:  
            # Xキー: 選択アノテーションを削除  
            if (self.menu_panel.current_selected_annotation and   
                self.menu_panel.delete_single_annotation_btn.isEnabled()):  
                self.menu_panel._on_delete_single_annotation_clicked()  
            event.accept()  
        elif event.key() == Qt.Key.Key_D:  
            # Dキー: トラック一括削除  
            if (self.menu_panel.current_selected_annotation and   
                self.menu_panel.delete_track_btn.isEnabled()):  
                self.menu_panel._on_delete_track_clicked()  
            event.accept()  
        elif event.key() == Qt.Key.Key_P:  
            # Pキー: 一括ラベル変更  
            if (self.menu_panel.current_selected_annotation and   
                self.menu_panel.propagate_label_btn.isEnabled()):  
                self.menu_panel._on_propagate_label_clicked()  
            event.accept()  
        elif event.key() == Qt.Key.Key_R:  
            # Rキー: 実行ボタン  
            if self.menu_panel.execute_add_btn.isEnabled():  
                self.menu_panel._on_complete_tracking_clicked()  
            event.accept()  
        elif event.key() == Qt.Key.Key_G:  
            # Gキー: フレームジャンプ実行  
            self.video_control.jump_to_frame()  
            event.accept()  
        elif event.key() == Qt.Key.Key_F:  
            # Fキー: フレーム入力フィールドにフォーカス移動  
            self.video_control.frame_input.setFocus()  
            self.video_control.frame_input.selectAll()  
            event.accept()  
        elif event.key() == Qt.Key.Key_A:  
            # Aキー: Track ID統一  
            if (self.menu_panel.current_selected_annotation and     
                self.menu_panel.align_track_ids_btn.isEnabled()):  
                self.menu_panel._on_align_track_ids_clicked()  
            event.accept()
        else:  
            super().keyPressEvent(event)
