# MASAAnnotationWidget.py    
from typing import List, Optional, Tuple, Dict  
  
from PyQt6.QtWidgets import (        
    QWidget, QHBoxLayout, QVBoxLayout,  
    QPushButton, QApplication, QSplitter,  
    QMessageBox, QDialog  
)    
from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtGui import QKeyEvent        
  
from DataClass import BoundingBox, ObjectAnnotation        
from MenuPanel import MenuPanel        
from VideoControlPanel import VideoControlPanel        
from VideoPreviewWidget import VideoPreviewWidget        
from VideoPlaybackController import VideoPlaybackController        
from VideoManager import VideoManager        
from AnnotationRepository import AnnotationRepository        
from ExportService import ExportService        
from SAM2TrackingWorker import SAM2TrackingWorker        
from ConfigManager import ConfigManager        
from ErrorHandler import ErrorHandler        
from TrackingResultConfirmDialog import TrackingResultConfirmDialog    
from KeyboardShortcutHandler import KeyboardShortcutHandler
from CommandPattern import CommandManager, DeleteAnnotationCommand, DeleteTrackCommand, \
                            UpdateLabelCommand, UpdateLabelByTrackCommand, AlignTrackIdsByLabelCommand, \
                            AddAnnotationCommand    
  
    
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
        self.playback_controller: Optional[VideoPlaybackController] = None        
        self.tracking_worker: Optional[SAM2TrackingWorker] = None        
        self.temp_bboxes_for_tracking: List[Tuple[int, BoundingBox]] = []        
            
        self.command_manager = CommandManager()      

        self.setup_ui()        
        self._connect_signals()    

        # キーボードショートカットハンドラーを初期化  
        self.keyboard_handler = KeyboardShortcutHandler(self)

              
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
        # VideoPreviewWidgetにConfigManagerを設定    
        self.video_preview.set_config_manager(self.config_manager)    
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
        self.video_control.play_requested.connect(self.start_playback)  
        self.video_control.pause_requested.connect(self.pause_playback)  

        # アノテーション操作関連（削除・ラベル変更・Track ID統一）    
        self.menu_panel.label_change_requested.connect(self.on_label_change_requested)      
        self.menu_panel.delete_single_annotation_requested.connect(self.on_delete_annotation_requested)      
        self.menu_panel.delete_track_requested.connect(self.on_delete_track_requested)      
        self.menu_panel.propagate_label_requested.connect(self.on_propagate_label_requested)      
        self.menu_panel.align_track_ids_requested.connect(self.on_align_track_ids_requested)    
  
        # 設定変更関連  
        self.menu_panel.config_changed.connect(self.on_config_changed)  
  
        # VideoPreviewWidgetからのアノテーション選択シグナルを接続    
        self.video_preview.annotation_selected.connect(self.on_annotation_selected)  
  
        # コピー・ペースト関連のシグナル接続  
        self.menu_panel.copy_annotation_requested.connect(self.copy_selected_annotation)    
        self.menu_panel.paste_annotation_requested.connect(self.paste_annotation)  
  
        # トラッキングとコピー関連のシグナル接続を追加    
        self.menu_panel.tracking_requested.connect(self.start_tracking)    
        self.menu_panel.copy_annotations_requested.connect(self.start_copy_annotations)  
  
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
            self.playback_controller.play(self.video_control.current_frame)  
            self.video_control.set_play_button_state(True)  
    
    def pause_playback(self):  
        """動画再生を一時停止"""  
        if self.playback_controller:  
            self.playback_controller.pause()  
            self.video_control.set_play_button_state(False)
  
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
  
    def on_tracking_completed(self, results: Dict[int, List[ObjectAnnotation]]):    
        """追跡完了時の処理（確認ダイアログ付き）"""    
        # 確認ダイアログを表示    
        dialog = TrackingResultConfirmDialog(results, self.video_manager, self)    
          
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.approved:    
            # ユーザーが承認した場合のみ追加    
            # dialog.tracking_resultsにはユーザーが選択した結果が含まれる    
            for frame_id, annotations in dialog.tracking_results.items():    
                for annotation in annotations:    
                    self.annotation_repository.add_annotation(annotation)    
              
            self.update_annotation_count()    
            self.video_preview.update_frame_display()    
            ErrorHandler.show_info_dialog("Tracking completed and annotations added!", "Tracking Complete")    
        else:    
            ErrorHandler.show_info_dialog("Tracking results were discarded.", "Tracking Cancelled")  
  
    def on_tracking_progress(self, current: int, total: int):    
        """トラッキング進捗更新時の処理"""    
        progress_text = f"Processing frame {current}/{total}..."    
        self.menu_panel.update_tracking_progress(progress_text)    
  
    def on_tracking_error(self, error_message: str):    
        """トラッキングエラー時の処理"""    
        self.menu_panel.update_tracking_progress("Tracking failed.")    
        ErrorHandler.show_error_dialog(f"Tracking error: {error_message}", "Tracking Error")    
  
    def on_playback_frame_changed(self, frame_id: int):    
        """再生時のフレーム変更処理"""    
        self.video_control.set_current_frame(frame_id)    
        self.video_preview.set_frame(frame_id)    
            
        # オブジェクト一覧を更新    
        frame_annotation = self.annotation_repository.get_annotations(frame_id)    
        self.menu_panel.update_current_frame_objects(frame_id, frame_annotation)    
  
    def on_playback_finished(self):    
        """再生終了時の処理"""    
        self.video_control.set_play_button_state(False)    
  
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
  
    def on_config_changed(self, key: str, value: object, config_type: str):    
        """設定変更時の処理"""    
        if config_type == "display":    
            display_options = self.config_manager.get_full_config(config_type="display")    
              
            # VideoPreviewWidgetの設定更新    
            self.video_preview.set_display_options(    
                display_options.show_manual_annotations,    
                display_options.show_auto_annotations,    
                display_options.show_ids,    
                display_options.show_confidence,    
                display_options.score_threshold    
            )    
  
    def on_annotation_selected(self, annotation: Optional[ObjectAnnotation]):    
        """アノテーション選択時の処理（中央集権的制御）"""    
        if hasattr(self, '_updating_selection') and self._updating_selection:    
            return    
              
        self._updating_selection = True    
        try:    
            # MenuPanelの情報を更新    
            self.menu_panel.update_selected_annotation_info(annotation)    
              
            # ObjectListTabWidgetの選択状態も更新（双方向同期）    
            self.menu_panel.update_object_list_selection(annotation)    
              
            # Undo/Redoボタンの状態も更新    
            if hasattr(self.menu_panel, 'update_undo_redo_buttons'):    
                self.menu_panel.update_undo_redo_buttons(self.command_manager)    
        finally:    
            self._updating_selection = False  
  
    def copy_selected_annotation(self):    
        """選択中のアノテーションをクリップボードにコピー"""    
        selected_annotation = self.menu_panel.current_selected_annotation    
        if not selected_annotation:    
            ErrorHandler.show_warning_dialog("No annotation selected to copy.", "Copy Error")    
            return    
          
        # MenuPanelのクリップボードに保存（ディープコピー）    
        self.menu_panel.clipboard_annotation = ObjectAnnotation(    
            object_id=selected_annotation.object_id,    
            frame_id=selected_annotation.frame_id,    
            bbox=BoundingBox(    
                selected_annotation.bbox.x1,    
                selected_annotation.bbox.y1,    
                selected_annotation.bbox.x2,    
                selected_annotation.bbox.y2,    
                confidence=selected_annotation.bbox.confidence    
            ),    
            label=selected_annotation.label,    
            is_manual=selected_annotation.is_manual,    
            track_confidence=selected_annotation.track_confidence,    
            is_manual_added=selected_annotation.is_manual_added    
        )    
          
        # paste_annotation_btnの状態を更新    
        self._update_paste_button_state()    
        print(f"--- Copied annotation: {selected_annotation.label} ---")  
  
    def _update_paste_button_state(self):    
        """paste_annotation_btnの状態を更新"""    
        if hasattr(self.menu_panel, 'paste_annotation_btn'):    
            paste_enabled = (self.menu_panel.clipboard_annotation is not None and     
                            self.menu_panel.edit_mode_btn.isChecked())    
            self.menu_panel.paste_annotation_btn.setEnabled(paste_enabled)  
  
    def paste_annotation(self):    
        """クリップボードのアノテーションを現在のフレームにペースト"""    
        if not self.menu_panel.clipboard_annotation:    
            ErrorHandler.show_warning_dialog("No annotation in clipboard.", "Paste Error")    
            return    
          
        if not self.video_manager:    
            ErrorHandler.show_warning_dialog("Please load a video file first.", "Paste Error")    
            return    
          
        current_frame = self.video_control.current_frame    
          
        # 現在のconfidence閾値を取得    
        display_config = self.config_manager.get_full_config(config_type="display")    
        threshold = display_config.score_threshold    
          
        # 現在のフレームのアノテーションを取得して重複チェック    
        frame_annotation = self.annotation_repository.get_annotations(current_frame)    
        use_original_track_id = True    
          
        if frame_annotation and frame_annotation.objects:    
            for existing_annotation in frame_annotation.objects:    
                # confidence閾値以上のアノテーションのみをチェック対象とする    
                if (existing_annotation.is_manual or existing_annotation.bbox.confidence >= threshold):    
                    # 同じラベルで同じTrack IDのアノテーションが既に存在するかチェック    
                    if (existing_annotation.label == self.menu_panel.clipboard_annotation.label and     
                        existing_annotation.object_id == self.menu_panel.clipboard_annotation.object_id):    
                        use_original_track_id = False    
                        break   
          
        # Track IDを決定    
        target_object_id = self.menu_panel.clipboard_annotation.object_id if use_original_track_id else -1    
          
        # 新しいアノテーションを作成    
        new_annotation = ObjectAnnotation(    
            object_id=target_object_id,    
            frame_id=current_frame,    
            bbox=BoundingBox(    
                self.menu_panel.clipboard_annotation.bbox.x1,    
                self.menu_panel.clipboard_annotation.bbox.y1,    
                self.menu_panel.clipboard_annotation.bbox.x2,    
                self.menu_panel.clipboard_annotation.bbox.y2,    
                confidence=1.0    
            ),    
            label=self.menu_panel.clipboard_annotation.label,    
            is_manual=True,    
            track_confidence=1.0,    
            is_manual_added=True    
        )    
          
        # コマンドパターンでアノテーション追加    
        command = AddAnnotationCommand(self.annotation_repository, new_annotation)    
        if self.command_manager.execute_command(command):    
            self.update_annotation_count()    
            self.video_preview.update_frame_display()    
              
            # 新しく作成されたアノテーションを選択状態にする    
            self.video_preview.bbox_editor.selected_annotation = new_annotation    
            self.video_preview.bbox_editor.selection_changed.emit(new_annotation)    
              
            track_id_info = f"(Track ID: {new_annotation.object_id})" if use_original_track_id else f"(New Track ID: {new_annotation.object_id})"    
            print(f"--- Pasted annotation: {new_annotation.label} at frame {current_frame} {track_id_info} ---")    
        else:    
            ErrorHandler.show_error_dialog("Failed to paste annotation.", "Paste Error")  
  
    @ErrorHandler.handle_with_dialog("Tracking Error")    
    def start_tracking(self, assigned_track_id: int, assigned_label: str):    
        """自動追跡を開始"""    
        if not self.video_manager:    
            ErrorHandler.show_warning_dialog("Please load a video file first", "Warning")    
            return    
              
        start_frame, end_frame = self.video_control.get_selected_range()    
          
        # temp_tracking_annotationsから初期アノテーションを取得    
        initial_annotations_for_worker = []    
        temp_annotations = self.video_preview.temp_tracking_annotations    
        for ann_obj in temp_annotations:  # タプル展開を削除    
            ann_obj.label = assigned_label  # ラベルを上書き    
            initial_annotations_for_worker.append((ann_obj.frame_id, ann_obj.bbox))  # frame_idはann_objから取得  
      
        frame_count = end_frame - start_frame + 1    
        reply = QMessageBox.question(    
            self, "Confirm Tracking",    
            f"Start automatic tracking from frame {start_frame} to {end_frame}?\n"    
            f"Total frames to process: {frame_count}\n"    
            f"This may take several minutes.",    
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No    
        )    
          
        if reply == QMessageBox.StandardButton.Yes:    
            # 動画の幅と高さを取得    
            video_width = self.video_manager.get_video_width()    
            video_height = self.video_manager.get_video_height()    
          
            self.tracking_worker = SAM2TrackingWorker(    
                self.video_manager,    
                self.annotation_repository,    
                start_frame,    
                end_frame,    
                initial_annotations_for_worker,    
                assigned_track_id,    
                assigned_label,    
                video_width, video_height    
            )    
            self.tracking_worker.tracking_completed.connect(self.on_tracking_completed)    
            self.tracking_worker.progress_updated.connect(self.on_tracking_progress)    
            self.tracking_worker.error_occurred.connect(self.on_tracking_error)    
            self.tracking_worker.start()    
              
    def start_copy_annotations(self, assigned_track_id: int, assigned_label: str):    
        """選択されたアノテーションを指定範囲にコピー"""    
        if not self.video_manager:    
            ErrorHandler.show_warning_dialog("Please load a video file first.", "Warning")    
            return    
          
        # 選択されたアノテーションを取得    
        selected_annotation = self.menu_panel.annotation_tab.current_selected_annotation    
        if not selected_annotation:    
            ErrorHandler.show_warning_dialog("Please select an annotation to copy.", "Warning")    
            return    
          
        # フレーム範囲の取得    
        start_frame, end_frame = self.video_control.get_selected_range()    
        if start_frame == -1 or end_frame == -1:    
            ErrorHandler.show_warning_dialog("No frame range selected.", "Warning")    
            return    
          
        frame_count = end_frame - start_frame + 1    
        reply = QMessageBox.question(    
            self, "Confirm Copy",    
            f"Copy annotation '{assigned_label}' from frame {start_frame} to {end_frame}?\n"    
            f"Total frames to process: {frame_count}",    
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No    
        )    
          
        if reply == QMessageBox.StandardButton.Yes:    
            # 各フレームにアノテーションをコピー    
            from DataClass import ObjectAnnotation, BoundingBox    
            from CommandPattern import AddAnnotationCommand    
              
            for frame_id in range(start_frame, end_frame + 1):    
                new_annotation = ObjectAnnotation(    
                    object_id=assigned_track_id,    
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
                    is_manual_added=True    
                )    
                  
                command = AddAnnotationCommand(self.annotation_repository, new_annotation)    
                self.command_manager.execute_command(command)    
              
            self.update_annotation_count()    
            self.video_preview.update_frame_display()    
                          
            ErrorHandler.show_info_dialog(f"Copied {frame_count} annotations with label '{assigned_label}'", "Copy Complete")  
  
    def reset_all_modes_to_initial_state(self):    
        """すべてのモードを初期状態に戻す"""    
        # すべてのモードボタンをOFFにする    
        self.menu_panel.annotation_tab.edit_mode_btn.setChecked(False)    
        self.menu_panel.annotation_tab.tracking_annotation_btn.setChecked(False)    
        self.menu_panel.annotation_tab.copy_annotations_btn.setChecked(False)    
          
        # すべてのモードボタンを有効化    
        self.menu_panel.annotation_tab.edit_mode_btn.setEnabled(True)    
        self.menu_panel.annotation_tab.tracking_annotation_btn.setEnabled(True)    
        self.menu_panel.annotation_tab.copy_annotations_btn.setEnabled(True)    
          
        # execute_add_btnを無効化    
        self.menu_panel.annotation_tab.execute_add_btn.setEnabled(False)    
          
        # VideoPreviewWidgetをviewモードに設定    
        self.video_preview.set_mode('view')    
          
        # 一時的なアノテーションをクリア    
        self.video_preview.clear_temp_tracking_annotations()    
  
        # workerをクリア  
        self.tracking_worker = None    
          
        # 選択状態をクリア    
        self.video_preview.bbox_editor.selected_annotation = None    
        self.video_preview.bbox_editor.selection_changed.emit(None)    
          
        # 表示を更新    
        self.video_preview.update_frame_display()  
  
    def keyPressEvent(self, event: QKeyEvent):  
        """キーボードイベントをハンドラーに委譲"""  
        if not self.keyboard_handler.handle_key_press(event):  
            super().keyPressEvent(event)

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