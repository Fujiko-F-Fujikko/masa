import os  
import cv2  
from typing import Dict, List, Optional, Tuple  
from PyQt6.QtWidgets import (  
    QWidget, QHBoxLayout, QVBoxLayout, QDialog,  
    QMessageBox, QFileDialog, QPushButton, QApplication 
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
  

# QtのデフォルトではSpaceキーでボタンクリックだが、Enterキーに変更する
class ButtonKeyEventFilter(QObject):  
    def eventFilter(self, obj, event):  
        if isinstance(obj, QPushButton) and event.type() == QEvent.Type.KeyPress:  
            if event.key() == Qt.Key.Key_Space:  
                # Spaceキーを無効化  
                return True  
            elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:  
                # Enterキーでクリック  
                obj.click()  
                return True  
        return super().eventFilter(obj, event)  

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
        self.temp_bboxes_for_batch_add: List[Tuple[int, BoundingBox]] = []  
          
        self.setup_ui()  
        self._connect_signals()  
          
    def setup_ui(self):  
        """UIの初期設定"""  
        self.setWindowTitle("MASA Video Annotation Tool")  
        self.setGeometry(100, 100, 1400, 900)  
          
        main_layout = QHBoxLayout()  
          
        self.menu_panel = MenuPanel(self.config_manager)  
        main_layout.addWidget(self.menu_panel)  
          
        right_layout = QVBoxLayout()  
          
        self.video_preview = VideoPreviewWidget(self)  
        right_layout.addWidget(self.video_preview)  
          
        self.video_control = VideoControlPanel()  
        right_layout.addWidget(self.video_control)  
          
        right_widget = QWidget()  
        right_widget.setLayout(right_layout)  
        main_layout.addWidget(right_widget)  
          
        main_layout.setStretch(0, 1)  
        main_layout.setStretch(1, 3)  
          
        self.setLayout(main_layout)  
          
    def _connect_signals(self):  
        """シグナルとスロットを接続"""  
        # MenuPanelからのシグナル  
        self.menu_panel.load_video_requested.connect(self.load_video)  
        self.menu_panel.load_json_requested.connect(self.load_json_annotations)  
        self.menu_panel.export_requested.connect(self.export_annotations)  
        self.menu_panel.edit_mode_requested.connect(self.set_edit_mode)  
        self.menu_panel.batch_add_mode_requested.connect(self.set_batch_add_mode)  
        self.menu_panel.tracking_requested.connect(self.start_tracking)  
        self.menu_panel.label_change_requested.connect(self.on_label_change_requested)  
        self.menu_panel.delete_single_annotation_requested.connect(self.on_delete_annotation_requested)  
        self.menu_panel.delete_track_requested.connect(self.on_delete_track_requested)  
        self.menu_panel.propagate_label_requested.connect(self.on_propagate_label_requested)  
        self.menu_panel.play_requested.connect(self.start_playback)  
        self.menu_panel.pause_requested.connect(self.pause_playback)  
        self.menu_panel.config_changed.connect(self.on_config_changed)  
          
        # VideoPreviewWidgetからのシグナル  
        self.video_preview.bbox_created.connect(self.on_bbox_created)  
        self.video_preview.frame_changed.connect(self.on_frame_changed)  
        self.video_preview.annotation_selected.connect(self.on_annotation_selected)  
        self.video_preview.annotation_updated.connect(self.on_annotation_updated)  
          
        # VideoControlPanelからのシグナル  
        self.video_control.frame_changed.connect(self.video_preview.set_frame)  
        self.video_control.range_changed.connect(self.on_range_selection_changed)  
        self.video_control.range_frame_preview.connect(self.video_preview.set_frame)

    @ErrorHandler.handle_with_dialog("Video Load Error")  
    def load_video(self, file_path: str):  
        """動画ファイルを読み込み"""  
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
          
        file_dialog_title = f"Save {format.upper()} Annotations"  
        default_filename = f"annotations.{format}"  
        file_path, _ = QFileDialog.getSaveFileName(  
            self, file_dialog_title, default_filename,  
            "JSON Files (*.json);;All Files (*)"  
        )  
          
        if file_path:  
            if format == "masa_json":  
                self.export_service.export_masa_json(  
                    self.annotation_repository.frame_annotations,  
                    self.video_manager.video_path,  
                    file_path  
                )  
            elif format == "coco_json":  
                self.export_service.export_coco(  
                    self.annotation_repository.frame_annotations,  
                    self.video_manager.video_path,  
                    file_path,  
                    self.video_manager  
                )  
            else:  
                ErrorHandler.show_error_dialog(f"Unsupported export format: {format}", "Error")  
                return

            ErrorHandler.show_info_dialog(f"Annotations exported to {file_path}", "Export Complete")  

    @ErrorHandler.handle_with_dialog("Tracking Error")  
    def start_tracking(self,  assigned_track_id: int, assigned_label: str):  
        """自動追跡を開始"""  
        if not self.video_manager:  
            ErrorHandler.show_warning_dialog("Please load a video file first", "Warning")  
            return  
          
        start_frame, end_frame = self.video_control.get_selected_range()  
          
        # temp_bboxes_for_batch_add に含まれるアノテーションのラベルを assigned_label で上書き  
        initial_annotations_for_worker = []  
        for frame_id, ann_obj in self.temp_bboxes_for_batch_add:  
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
            if assigned_track_id != -1:  
                self.temp_bboxes_for_batch_add.clear()  
                self.video_preview.clear_temp_batch_annotations() # ここもクリア
                self.video_preview.set_mode('edit') # 編集モードに戻す  
                self.menu_panel.batch_add_annotation_btn.setChecked(False)  
                self.menu_panel.complete_batch_add_btn.setEnabled(False)  
                self.video_preview.update_frame_display()

    def on_tracking_progress(self, current_frame: int, total_frames: int):  
        """追跡進捗更新"""  
        progress_percent = (current_frame / total_frames) * 100  
        progress_text = f"Tracking... {current_frame}/{total_frames} ({progress_percent:.1f}%)"  
        self.menu_panel.update_tracking_progress(progress_text)  
          
    def on_tracking_completed(self, results: Dict[int, List[ObjectAnnotation]]):  
        """追跡完了時の処理"""  
        added_count = 0  
        for frame_id, annotations_list in results.items():  
            for ann in annotations_list:  
                self.annotation_repository.add_annotation(ann)  
                added_count += 1  
          
        self.menu_panel.update_tracking_progress(f"Completed! {added_count} annotations added.")  
        self.update_annotation_count()  
        self.video_preview.update_frame_display()  
          
        # AnnotationRepositoryのnext_object_idを更新  
        if hasattr(self.tracking_worker, 'max_used_track_id'):  
            self.annotation_repository.next_object_id = max(  
                self.annotation_repository.next_object_id,  
                self.tracking_worker.max_used_track_id + 1  
            )  
          
        ErrorHandler.show_info_dialog(  
            f"Automatic tracking completed successfully!\n"  
            f"Added {added_count} annotations.\n"  
            f"You can now view results in Edit Mode.",  
            "Tracking Complete"  
        )  
          
    def on_tracking_error(self, message: str):  
        """追跡エラー時の処理"""  
        self.menu_panel.update_tracking_progress("Tracking failed.")  
        ErrorHandler.show_error_dialog(f"Tracking encountered an error: {message}", "Tracking Error")  
          
    def on_bbox_created(self, x1: int, y1: int, x2: int, y2: int):  
        """バウンディングボックス作成時の処理"""  
        bbox = BoundingBox(x1, y1, x2, y2)  
        current_frame = self.video_control.current_frame  
          
        # 現在のモードがEditModeの場合のみラベル入力ダイアログを表示  
        if self.video_preview.mode_manager.current_mode_name == 'edit': # current_mode_name を使用  
            dialog = AnnotationInputDialog(bbox, self, existing_labels=self.annotation_repository.get_all_labels())  
            if dialog.exec() == QDialog.DialogCode.Accepted:  
                label = dialog.get_label()  
                if label:  
                    annotation = ObjectAnnotation(  
                        object_id=-1, # 新規IDを意味  
                        frame_id=current_frame,  
                        bbox=bbox,  
                        label=label,  
                        is_manual=True,  
                        track_confidence=1.0,  
                        is_batch_added=False # 通常の手動アノテーション  
                    )  
                    self.annotation_repository.add_annotation(annotation)  
                    self.update_annotation_count()  
                    ErrorHandler.show_info_dialog(f"Added annotation: {label} at frame {current_frame}", "Annotation Added")  
                      
                    self.video_preview.bbox_editor.selected_annotation = annotation  
                    self.video_preview.bbox_editor.selection_changed.emit(annotation)  
                    self.video_preview.update_frame_display()  

                else:  
                    ErrorHandler.show_warning_dialog("Label cannot be empty.", "Input Error")  
        elif self.video_preview.mode_manager.current_mode_name == 'batch_add':  
            # BatchAddModeの場合、ラベル入力ダイアログは表示しない  
            # BatchAddModeで既に仮のラベルが設定されているはずなので、ここでは何もしない  
            # ただし、temp_bboxes_for_batch_addへの追加はBatchAddMode内で直接行われるため、  
            # ここでは何もしないか、エラーログを出す  
            #ErrorHandler.show_warning_dialog("BatchAddMode中にbbox_createdが呼び出されましたが、処理はスキップされました。", "Warning")  
            pass
        else:  
            # その他のモードの場合（予期しないケース）  
            ErrorHandler.show_warning_dialog("不明なモードでbbox_createdが呼び出されました。", "Warning")

    def on_frame_changed(self, frame_id: int):  
        """フレーム変更時の処理"""  
        self.video_control.set_current_frame(frame_id)  
        self.menu_panel.update_frame_display(frame_id, self.video_manager.get_total_frames())

    def set_edit_mode(self, enabled: bool):  
        """編集モードの設定とUIの更新"""  
        if enabled:  
            # BatchAddModeがONの場合はOFFにする  
            if self.menu_panel.batch_add_annotation_btn.isChecked():  
                self.menu_panel.batch_add_annotation_btn.setChecked(False)  
                self.set_batch_add_mode(False)  
              
            self.video_preview.set_mode('edit')  
            self.video_control.range_slider.setVisible(False)  
            self.video_preview.clear_temp_batch_annotations()  
            ErrorHandler.show_info_dialog("編集モードが有効になりました。", "モード変更")  
        else:  
            self.video_preview.set_mode('view')  
            self.video_control.range_slider.setVisible(False)  
            ErrorHandler.show_info_dialog("編集モードが無効になりました。", "モード変更")  
        self.video_preview.bbox_editor.set_editing_mode(enabled)  
        self.video_preview.update_frame_display()  
      
    def set_batch_add_mode(self, enabled: bool):  
        """一括追加モードの設定とUIの更新"""  
        if enabled:  
            # EditModeがONの場合はOFFにする  
            if self.menu_panel.edit_mode_btn.isChecked():  
                self.menu_panel.edit_mode_btn.setChecked(False)  
                self.set_edit_mode(False)  
              
            self.video_preview.set_mode('batch_add')  
            self.video_control.range_slider.setVisible(True)
            self.video_preview.clear_temp_batch_annotations()  
            ErrorHandler.show_info_dialog("新規アノテーション一括追加モードが有効になりました。\n"
                  "1. 動画プレビュー上でバウンディングボックスを描画してください。\n"
                  "2. 追加したいフレーム範囲を指定して下さい。\n"
                  "3. 実行ボタンを押してください。", "モード変更")  
            self.temp_bboxes_for_batch_add.clear()  
        else:  
            self.video_preview.set_mode('view')  
            ErrorHandler.show_info_dialog("新規アノテーション一括追加モードが無効になりました。", "モード変更")  
        self.video_preview.bbox_editor.set_editing_mode(enabled)  
        self.video_preview.update_frame_display()

    def on_label_change_requested(self, annotation: ObjectAnnotation, new_label: str):  
        """アノテーションのラベル変更要求時の処理"""  
        try:  
            annotation.label = new_label  
            if self.annotation_repository.update_annotation(annotation):  
                self.video_preview.update_frame_display()  
                self.update_annotation_count()  
            else:  
                ErrorHandler.show_warning_dialog("アノテーションの更新に失敗しました。", "エラー")  
        except Exception as e:  
            ErrorHandler.show_error_dialog(f"ラベル変更中にエラーが発生しました: {e}", "エラー")

    def on_delete_annotation_requested(self, annotation: ObjectAnnotation):  
        """単一アノテーション削除要求時の処理"""  
        if self.annotation_repository.delete_annotation(annotation.object_id, annotation.frame_id):  
            ErrorHandler.show_info_dialog("アノテーションを削除しました。", "削除完了")  
            self.update_annotation_count()  
            self.video_preview.update_frame_display()  
        else:  
            ErrorHandler.show_warning_dialog("アノテーションの削除に失敗しました。", "エラー")

    def on_delete_track_requested(self, track_id: int):  
        """Track IDによる一括削除要求時の処理"""  
        deleted_count = self.annotation_repository.delete_by_track_id(track_id)  
        if deleted_count > 0:  
            ErrorHandler.show_info_dialog(f"Track ID '{track_id}' のアノテーションを {deleted_count} 件削除しました。", "削除完了")  
            self.update_annotation_count()  
            self.video_preview.update_frame_display()  
        else:  
            ErrorHandler.show_warning_dialog(f"Track ID '{track_id}' のアノテーションは見つかりませんでした。", "エラー")

    def on_propagate_label_requested(self, track_id: int, new_label: str):  
        """Track IDによる一括ラベル変更要求時の処理"""  
        updated_count = self.annotation_repository.update_label_by_track_id(track_id, new_label)  
        if updated_count > 0:  
            ErrorHandler.show_info_dialog(f"Track ID '{track_id}' のアノテーション {updated_count} 件のラベルを '{new_label}' に変更しました。", "ラベル変更完了")  
            self.update_annotation_count()  
            self.video_preview.update_frame_display()  
        else:  
            ErrorHandler.show_warning_dialog(f"Track ID '{track_id}' のアノテーションは見つかりませんでした。", "エラー")

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
        # 他のconfig_typeの変更もここに追加

    def on_annotation_selected(self, annotation: Optional[ObjectAnnotation]):  
        """アノテーション選択時の処理"""  
        self.menu_panel.update_selected_annotation_info(annotation)

    def on_annotation_updated(self, annotation: ObjectAnnotation):  
        """アノテーション更新時の処理"""  
        # 一時的なバッチアノテーションの場合は、アノテーションリポジトリ更新をスキップ  
        if hasattr(annotation, 'is_batch_added') and annotation.is_batch_added:  
            self.update_annotation_count()  
            return  
          
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
        ErrorHandler.show_info_dialog("動画の再生が完了しました。", "再生完了")

    def update_annotation_count(self):  
        """アノテーション数を更新し、UIに反映"""  
        stats = self.annotation_repository.get_statistics()  
        self.menu_panel.update_annotation_count(stats["total"], stats["manual"])  
        self.menu_panel.initialize_label_combo(self.annotation_repository.get_all_labels())

    def keyPressEvent(self, event: QKeyEvent):  
        """キーボードショートカットの処理"""  
        if event.key() == Qt.Key.Key_Space:  
            # Spaceキー：再生・一時停止の切り替え  
            if self.playback_controller and self.playback_controller.is_playing:  
                self.pause_playback()  
            else:  
                self.start_playback()  
            event.accept()  
              
        elif event.key() == Qt.Key.Key_Left:  
            # 左キー：前のフレームに移動  
            self.video_control.prev_frame()  
            event.accept()  
              
        elif event.key() == Qt.Key.Key_Right:  
            # 右キー：次のフレームに移動  
            self.video_control.next_frame()  
            event.accept()  
              
        else:  
            super().keyPressEvent(event)