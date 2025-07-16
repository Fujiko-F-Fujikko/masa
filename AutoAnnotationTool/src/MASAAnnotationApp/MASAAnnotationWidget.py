# MASAAnnotationWidget.py  
from typing import List, Optional, Tuple      
  
from PyQt6.QtWidgets import (      
    QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QApplication, QSplitter     
)  
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
from ConfigManager import ConfigManager      
from ErrorHandler import ErrorHandler      
from CommandPattern import CommandManager, DeleteAnnotationCommand, DeleteTrackCommand, \
                            UpdateLabelCommand, UpdateLabelByTrackCommand, AlignTrackIdsByLabelCommand  
  
class ButtonKeyEventFilter(QObject):      
    def eventFilter(self, obj, event):      
        try:  
            if isinstance(obj, QPushButton) and event.type() == QEvent.Type.KeyPress:      
                if event.key() == Qt.Key.Key_Space:      
                    return True      
                elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:      
                    obj.click()      
                    return True      
        except RecursionError:  
            return False  
        return QObject.eventFilter(self, obj, event)  
  
class MASAAnnotationWidget(QWidget):      
    """統合されたMASAアノテーションメインウィジェット（軽量化版）"""      
          
    def __init__(self, parent=None):      
        super().__init__(parent)      
    
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)      
        self.setFocus()    
        self.button_filter = ButtonKeyEventFilter()      
        QApplication.instance().installEventFilter(self.button_filter)    
    
        self.config_manager = ConfigManager()      
        self.video_manager: Optional[VideoManager] = None      
        self.annotation_repository = AnnotationRepository()      
        self.export_service = ExportService()      
        self.object_tracker = ObjectTracker(self.config_manager.get_full_config(config_type="masa"))  
        self.playback_controller: Optional[VideoPlaybackController] = None      
        self.tracking_worker: Optional[TrackingWorker] = None      
        self.temp_bboxes_for_tracking: List[Tuple[int, BoundingBox]] = []      
          
        self.command_manager = CommandManager()    
              
        self.setup_ui()      
        self._connect_signals()  
            
    def setup_ui(self):    
        """UIの初期設定"""    
        self.setWindowTitle("MASA Video Annotation Tool")    
        self.setGeometry(100, 100, 1400, 900)    
            
        main_layout = QHBoxLayout()  
        main_layout.setContentsMargins(0, 0, 0, 0)  
          
        splitter = QSplitter(Qt.Orientation.Horizontal)  
          
        # MenuPanelに必要な参照を渡す（分割後の新しいコンストラクタ）  
        self.menu_panel = MenuPanel(  
            self.config_manager,   
            self.annotation_repository,  
            self.command_manager,  
            self  
        )    
        splitter.addWidget(self.menu_panel)  
            
        right_layout = QVBoxLayout()    
        right_layout.setContentsMargins(0, 0, 0, 0)  
            
        self.video_preview = VideoPreviewWidget(self)    
        right_layout.addWidget(self.video_preview)    
            
        # VideoControlPanelに必要な参照を渡す  
        self.video_control = VideoControlPanel(self)    
        right_layout.addWidget(self.video_control)    
            
        right_widget = QWidget()    
        right_widget.setLayout(right_layout)    
        splitter.addWidget(right_widget)  
            
        splitter.setSizes([300, 1100])  
          
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
          
    def _connect_signals(self):    
        """シグナルとスロットを接続（軽量化版）"""    
        # 主要なコンポーネント間調整のみ残す  
        self.menu_panel.edit_mode_requested.connect(self.set_edit_mode)    
          
        # VideoControlPanelからのシグナル（直接接続のみ）  
        self.video_control.frame_changed.connect(self.video_preview.set_frame)    
        self.video_control.range_frame_preview.connect(self.video_preview.set_frame)  
  
        # 再生制御関連  
        self.menu_panel.play_requested.connect(self.start_playback)    
        self.menu_panel.pause_requested.connect(self.pause_playback)    
          
        # アノテーション操作関連（削除・ラベル変更・Track ID統一）  
        self.menu_panel.label_change_requested.connect(self.on_label_change_requested)    
        self.menu_panel.delete_single_annotation_requested.connect(self.on_delete_annotation_requested)    
        self.menu_panel.delete_track_requested.connect(self.on_delete_track_requested)    
        self.menu_panel.propagate_label_requested.connect(self.on_propagate_label_requested)    
        self.menu_panel.align_track_ids_requested.connect(self.on_align_track_ids_requested)  
  
    # 残存する主要メソッド（コンポーネント間調整役）  
    def set_edit_mode(self, enabled: bool):    
        """編集モードの設定とUIの更新"""    
        if enabled:    
            if self.menu_panel.tracking_annotation_btn.isChecked():    
                self.menu_panel.tracking_annotation_btn.setChecked(False)    
                
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
  
    def start_playback(self):    
        """動画再生を開始"""    
        if self.playback_controller:    
            self.playback_controller.play()    
            self.menu_panel.basic_tab.set_play_button_state(True)  
  
    def pause_playback(self):    
        """動画再生を一時停止"""    
        if self.playback_controller:    
            self.playback_controller.pause()    
            self.menu_panel.basic_tab.set_play_button_state(False)  
  
    # アノテーション操作メソッド（コマンドパターン使用）  
    def on_delete_annotation_requested(self, annotation: ObjectAnnotation):    
        """単一アノテーション削除要求時の処理"""    
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
        """Track IDによる一括削除要求時の処理"""    
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
        """アノテーションのラベル変更要求時の処理"""    
        try:    
            old_label = annotation.label    
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
        """トラック単位でのラベル変更要求時の処理"""    
        try:    
            annotations = self.annotation_repository.get_annotations_by_track_id(track_id)    
            if not annotations:    
                ErrorHandler.show_warning_dialog(  
                    f"No annotations found for Track ID '{track_id}'.",  
                    "Error"  
                )  
                return    
                
            old_label = annotations[0].label    
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
  
    def on_align_track_ids_requested(self, target_label: str, target_track_id: int):    
        """ラベル単位でのTrack ID統一要求時の処理"""    
        try:    
            command = AlignTrackIdsByLabelCommand(self.annotation_repository, target_label, target_track_id)    
            updated_count = self.command_manager.execute_command(command)    
                
            if updated_count > 0:    
                self.video_preview.update_frame_display()    
                self.update_annotation_count()  
                  
                # オブジェクト一覧を更新  
                current_frame = self.video_control.current_frame  
                frame_annotation = self.annotation_repository.get_annotations(current_frame)  
                self.menu_panel.update_current_frame_objects(current_frame, frame_annotation)  
                  
                ErrorHandler.show_info_dialog(  
                    f"Aligned {updated_count} annotations with label '{target_label}' to Track ID '{target_track_id}'.",  
                    "Track ID Alignment Complete"  
                )  
            else:    
                ErrorHandler.show_warning_dialog("No annotations found to align.", "Error")  
        except Exception as e:
            ErrorHandler.show_error_dialog(f"Error occurred while aligning track IDs: {e}", "Error")  
  
    def update_annotation_count(self):    
        """アノテーション数を更新し、UIに反映"""    
        stats = self.annotation_repository.get_statistics()    
        self.menu_panel.update_annotation_count(stats["total"], stats["manual"])    
        self.menu_panel.initialize_label_combo(self.annotation_repository.get_all_labels())    
            
        # Undo/Redoボタンの状態を更新    
        if hasattr(self.menu_panel, 'update_undo_redo_buttons'):    
            self.menu_panel.update_undo_redo_buttons(self.command_manager)  
  
    # トラッキング関連のコールバック（動的に接続される）  
    def on_tracking_completed(self, results):  
        """トラッキング完了時の処理"""  
        if results:  
            self.update_annotation_count()  
            self.video_preview.update_frame_display()  
              
            # 現在フレームのオブジェクト一覧を更新  
            current_frame = self.video_control.current_frame  
            frame_annotation = self.annotation_repository.get_annotations(current_frame)  
            self.menu_panel.update_current_frame_objects(current_frame, frame_annotation)  
              
            ErrorHandler.show_info_dialog("Tracking completed successfully.", "Tracking Complete")  
        else:  
            ErrorHandler.show_warning_dialog("Tracking failed or was cancelled.", "Tracking Failed")  
          
        # トラッキングワーカーをクリーンアップ  
        self.tracking_worker = None  
  
    def on_tracking_progress(self, current: int, total: int):  
        """トラッキング進捗更新時の処理"""  
        progress_text = f"Processing frame {current}/{total}..."  
        self.menu_panel.update_tracking_progress(progress_text)  
  
    def on_tracking_error(self, error_message: str):  
        """トラッキングエラー時の処理"""  
        self.menu_panel.update_tracking_progress("Tracking failed.")  
        ErrorHandler.show_error_dialog(f"Tracking error: {error_message}", "Tracking Error")  
        self.tracking_worker = None  
  
    def on_playback_frame_changed(self, frame_id: int):  
        """再生時のフレーム変更処理"""  
        self.video_control.set_current_frame(frame_id)  
        self.video_preview.set_frame(frame_id)  
          
        # オブジェクト一覧を更新  
        frame_annotation = self.annotation_repository.get_annotations(frame_id)  
        self.menu_panel.update_current_frame_objects(frame_id, frame_annotation)  
  
    def on_playback_finished(self):  
        """再生終了時の処理"""  
        self.menu_panel.basic_tab.set_play_button_state(False)  
  
    def on_export_progress(self, current: int, total: int):  
        """エクスポート進捗更新時の処理"""  
        progress_text = f"Exporting frame {current}/{total}..."  
        self.menu_panel.update_export_progress(progress_text)  
  
    def on_export_completed(self):  
        """エクスポート完了時の処理"""  
        self.menu_panel.update_export_progress("Export completed.")  
        ErrorHandler.show_info_dialog("Export completed successfully.", "Export Complete")  
  
    def on_export_error(self, error_message: str):  
        """エクスポートエラー時の処理"""  
        self.menu_panel.update_export_progress("Export failed.")  
        ErrorHandler.show_error_dialog(f"Export error: {error_message}", "Export Error")  
  
    def on_model_initialization_completed(self):  
        """モデル初期化完了時の処理"""  
        self.menu_panel.set_tracking_enabled(True)  
        ErrorHandler.show_info_dialog("MASA models initialized successfully.", "Initialization Complete")  
  
    def on_model_initialization_failed(self, error_message: str):  
        """モデル初期化失敗時の処理"""  
        self.menu_panel.set_tracking_enabled(False)  
        ErrorHandler.show_error_dialog(f"Failed to initialize MASA models: {error_message}", "Initialization Error")  
  
    def _filter_annotations_by_score_threshold(self):  
        """スコア閾値でアノテーションをフィルタリング"""  
        display_config = self.config_manager.get_full_config(config_type="display")  
        threshold = display_config.score_threshold  
          
        filtered_annotations = {}  
        for frame_id, frame_annotation in self.annotation_repository.frame_annotations.items():  
            filtered_objects = []  
            for obj_annotation in frame_annotation.objects:  
                if obj_annotation.is_manual or obj_annotation.bbox.confidence >= threshold:  
                    filtered_objects.append(obj_annotation)  
              
            if filtered_objects:  
                from DataClass import FrameAnnotation  
                filtered_annotations[frame_id] = FrameAnnotation(  
                    frame_id=frame_id,  
                    frame_path=frame_annotation.frame_path,  
                    objects=filtered_objects  
                )  
          
        return filtered_annotations  
  
    def closeEvent(self, event):  
        """アプリケーション終了時のクリーンアップ"""  
        # VideoManagerのリソースを解放  
        if self.video_manager:  
            self.video_manager.release()  
          
        # 再生コントローラーを停止  
        if self.playback_controller:  
            self.playback_controller.stop()  
          
        # トラッキングワーカーを停止  
        if self.tracking_worker and self.tracking_worker.isRunning():  
            self.tracking_worker.terminate()  
            self.tracking_worker.wait()  
          
        # イベントフィルターを削除  
        if hasattr(self, 'button_filter'):  
            QApplication.instance().removeEventFilter(self.button_filter)  
          
        super().closeEvent(event)