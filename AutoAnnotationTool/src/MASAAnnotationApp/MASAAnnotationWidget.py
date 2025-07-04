# MASAAnnotationWidget.py  
"""  
ファサードパターンによりリファクタリングされたメインウィジェット  
依存関係を大幅に削減し、可読性と保守性を向上  
"""  
from typing import Optional, List, Tuple, Dict  
from PyQt6.QtWidgets import QWidget, QPushButton, QApplication, QDialog, QMessageBox, QFileDialog  
from PyQt6.QtGui import QKeyEvent    
from PyQt6.QtCore import Qt, QObject, QEvent      
      
from DataClass import BoundingBox, ObjectAnnotation      
from AnnotationInputDialog import AnnotationInputDialog  
from VideoPlaybackController import VideoPlaybackController      
from TrackingWorker import TrackingWorker      
from TrackingResultConfirmDialog import TrackingResultConfirmDialog    
from ErrorHandler import ErrorHandler  
from VideoManager import VideoManager  
from CommandPattern import AddAnnotationCommand, DeleteAnnotationCommand, DeleteTrackCommand, UpdateBoundingBoxCommand, UpdateLabelByTrackCommand  
from COCOExportWorker import COCOExportWorker  
  
# ファサードパターンによる新しいアーキテクチャ  
from MASAApplicationService import MASAApplicationService  
from MainUIController import MainUIController  
from KeyboardShortcutManager import KeyboardShortcutManager  
    
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
    """ファサードパターンによりリファクタリングされたメインウィジェット"""      
          
    def __init__(self, parent=None):      
        super().__init__(parent)      
    
        # キーボードフォーカスを有効にする      
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)      
        self.setFocus()    
          
        # イベントフィルターを作成してアプリケーションに適用      
        self.button_filter = ButtonKeyEventFilter()      
        QApplication.instance().installEventFilter(self.button_filter)    
    
        # ファサード層の初期化（単一の依存関係）  
        self.app_service = MASAApplicationService()  
          
        # UI管理層  
        self.main_ui_controller = MainUIController(self, self.app_service)  
        self.keyboard_shortcut_manager = KeyboardShortcutManager(self.app_service, self.main_ui_controller)  
          
        # 残存する直接管理が必要な要素  
        self.playback_controller: Optional[VideoPlaybackController] = None      
        self.tracking_worker: Optional[TrackingWorker] = None      
        self.temp_bboxes_for_batch_add: List[Tuple[int, BoundingBox]] = []      
          
        self.video_manager = None  
  
        self.setup_ui()      
        self.setup_connections()  
            
    def setup_ui(self):    
        """UIの初期設定 - 新しいアーキテクチャでMainUIControllerに委譲"""    
        self.setWindowTitle("MASA Video Annotation Tool")    
        self.setGeometry(100, 100, 1400, 900)    
          
        # MainUIControllerにUI構築を委譲  
        self.main_ui_controller.setup_main_layout()  
            
    def setup_connections(self):    
        """シグナルとスロットを接続 - 新しいアーキテクチャでMainUIControllerに委譲"""    
        # MainUIControllerにシグナル接続を委譲  
        self.main_ui_controller.connect_components()  
          
        # VideoPreviewWidgetの設定  
        video_preview = self.main_ui_controller.get_video_preview()  
        if video_preview:  
            video_preview.set_config_manager(self.app_service.config_manager)  
            video_preview.set_annotation_repository(self.app_service.annotation_repository)  
  
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
                
            # 新しいアーキテクチャでの正しいアクセス方法  
            video_preview = self.main_ui_controller.get_video_preview()  
            video_control = self.main_ui_controller.get_video_control()  
            menu_panel = self.main_ui_controller.get_menu_panel()  
              
            if video_preview:  
                video_preview.set_video_manager(self.video_manager)    
                video_preview.set_annotation_repository(self.app_service.annotation_repository)    
              
            if video_control:  
                video_control.set_total_frames(self.video_manager.get_total_frames())    
                video_control.set_current_frame(0)    
              
            if menu_panel:  
                menu_panel.update_video_info(file_path, self.video_manager.get_total_frames())    
                
            ErrorHandler.show_info_dialog(f"Video loaded: {file_path}", "Success")    
        else:    
            ErrorHandler.show_error_dialog("Failed to load video file", "Error")    
                
    @ErrorHandler.handle_with_dialog("JSON Load Error")    
    def load_json_annotations(self, file_path: str):    
        """JSONアノテーションファイルを読み込み"""    
        if not self.video_manager:    
            ErrorHandler.show_warning_dialog("Please load a video file first", "Warning")    
            return    
            
        # 新しいアーキテクチャでの正しいアクセス方法  
        loaded_annotations = self.app_service.export_service.import_json(file_path)    
        if loaded_annotations:    
            self.app_service.annotation_repository.clear() # 既存のアノテーションをクリア    
            for frame_id, frame_ann in loaded_annotations.items():    
                for obj_ann in frame_ann.objects:    
                    self.app_service.annotation_repository.add_annotation(obj_ann)    
                
            menu_panel = self.main_ui_controller.get_menu_panel()  
            video_preview = self.main_ui_controller.get_video_preview()  
            video_control = self.main_ui_controller.get_video_control()  
            
            if menu_panel:  
                menu_panel.update_json_info(file_path, self.app_service.annotation_repository.get_statistics()["total"])    
                # 修正版：AnnotationEditTabManager経由でedit_mode_btnにアクセス  
                annotation_edit_tab = menu_panel.get_annotation_edit_tab()  
                if annotation_edit_tab and annotation_edit_tab.edit_mode_btn:  
                    annotation_edit_tab.edit_mode_btn.setChecked(False) # 編集モードをオフに    
            
            self.update_annotation_count()    
            
            if video_preview:  
                video_preview.set_mode('view') # JSON読み込み後は表示モードに    
                
            ErrorHandler.show_info_dialog(    
                f"Successfully loaded {self.app_service.annotation_repository.get_statistics()['total']} annotations from JSON file",    
                "JSON Loaded"    
            )  
            
            # JSON読み込み完了後にオブジェクト一覧を更新  
            if video_control and menu_panel:  
                current_frame = video_control.current_frame  
                frame_annotation = self.app_service.annotation_repository.get_annotations(current_frame)  
                menu_panel.update_current_frame_objects(current_frame, frame_annotation)  
        else:    
            ErrorHandler.show_error_dialog("Failed to load JSON annotation file", "Error")
                
    @ErrorHandler.handle_with_dialog("Export Error")    
    def export_annotations(self, format: str):    
        """アノテーションをエクスポート"""    
        if not self.app_service.annotation_repository.frame_annotations:    
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
                self.app_service.export_service.export_masa_json(    
                    self.app_service.annotation_repository.frame_annotations,    
                    self.video_manager.video_path,    
                    file_path    
                )    
            elif format == "coco":    
                menu_panel = self.main_ui_controller.get_menu_panel()  
                if menu_panel:  
                    # 進捗表示を開始    
                    menu_panel.update_export_progress("Exporting COCO JSON...")    
                    
                # スコア閾値でフィルタリングされたアノテーションを作成    
                filtered_annotations = self._filter_annotations_by_score_threshold()   
                # ワーカースレッドでエクスポート実行    
                self.export_worker = COCOExportWorker(    
                    self.app_service.export_service,    
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
        video_preview = self.main_ui_controller.get_video_preview()  
        score_threshold = video_preview.score_threshold if video_preview else 0.0  
            
        for frame_id, frame_annotation in self.app_service.annotation_repository.frame_annotations.items():    
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
        menu_panel = self.main_ui_controller.get_menu_panel()  
        if menu_panel:  
            menu_panel.update_export_progress(progress_text)    
        
    def on_export_completed(self):    
        """エクスポート完了時の処理"""    
        menu_panel = self.main_ui_controller.get_menu_panel()  
        if menu_panel:  
            menu_panel.update_export_progress("Export completed!")    
        
    def on_export_error(self, error_message: str):    
        """エクスポートエラー時の処理"""    
        menu_panel = self.main_ui_controller.get_menu_panel()  
        if menu_panel:  
            menu_panel.update_export_progress("")    
        ErrorHandler.show_error_dialog(f"Export failed: {error_message}", "Export Error")  
  
    @ErrorHandler.handle_with_dialog("Tracking Error")    
    def start_tracking(self,  assigned_track_id: int, assigned_label: str):    
        """自動追跡を開始"""    
        if not self.app_service.object_tracker:    
            ErrorHandler.show_warning_dialog("MASA models are still loading. Please wait.", "Warning")    
            return    
          
        # ObjectTrackerの実際の初期化（まだされていない場合）    
        if not self.app_service.object_tracker.initialized:    
            try:    
                self.app_service.object_tracker.initialize()    
            except Exception as e:    
                ErrorHandler.show_error_dialog(f"Failed to initialize MASA models: {str(e)}", "Initialization Error")    
                return    
  
        if not self.video_manager:    
            ErrorHandler.show_warning_dialog("Please load a video file first", "Warning")    
            return
        video_control = self.main_ui_controller.get_video_control()  
        if not video_control:  
            ErrorHandler.show_warning_dialog("Video control not available", "Warning")  
            return  
  
        current_frame = video_control.current_frame  
        start_frame = current_frame  
        end_frame = self.video_manager.get_total_frames() - 1  
  
        # 現在のフレームから追跡対象のアノテーションを取得  
        frame_annotation = self.app_service.annotation_repository.get_annotations(current_frame)  
        if not frame_annotation or not frame_annotation.objects:  
            ErrorHandler.show_warning_dialog("No annotations found in current frame for tracking", "Warning")  
            return  
  
        # 指定されたtrack_idのアノテーションを検索  
        target_annotation = None  
        for annotation in frame_annotation.objects:  
            if annotation.track_id == assigned_track_id:  
                target_annotation = annotation  
                break  
  
        if not target_annotation:  
            ErrorHandler.show_warning_dialog(f"No annotation found with track ID {assigned_track_id}", "Warning")  
            return  
  
        # 追跡用の初期アノテーションリストを作成  
        initial_annotations_for_worker = []  
        initial_annotations_for_worker.append((current_frame, target_annotation.bbox))  
  
        menu_panel = self.main_ui_controller.get_menu_panel()  
        if menu_panel:  
            menu_panel.update_tracking_progress("Starting tracking...")  
  
        # TrackingWorkerを作成して実行  
        self.tracking_worker = TrackingWorker(  
            self.app_service.object_tracker,  
            self.video_manager,  
            initial_annotations_for_worker,  
            assigned_track_id,  
            assigned_label,  
            start_frame,  
            end_frame  
        )  
  
        self.tracking_worker.progress_updated.connect(self.on_tracking_progress)  
        self.tracking_worker.tracking_completed.connect(self.on_tracking_completed)  
        self.tracking_worker.error_occurred.connect(self.on_tracking_error)  
        self.tracking_worker.start()  
  
    def on_playback_frame_changed(self, frame_id: int):  
        """再生フレーム変更時の処理"""  
        video_control = self.main_ui_controller.get_video_control()  
        video_preview = self.main_ui_controller.get_video_preview()  
        menu_panel = self.main_ui_controller.get_menu_panel()  
  
        if video_control:  
            video_control.set_current_frame(frame_id)  
          
        if video_preview:  
            video_preview.update_frame_display()  
          
        if menu_panel:  
            # オブジェクト一覧を更新  
            frame_annotation = self.app_service.annotation_repository.get_annotations(frame_id)  
            menu_panel.update_current_frame_objects(frame_id, frame_annotation)  
  
    def on_playback_finished(self):  
        """再生完了時の処理"""  
        menu_panel = self.main_ui_controller.get_menu_panel()  
        if menu_panel:  
            menu_panel.reset_playback_button()  
  
    def on_tracking_progress(self, current_frame: int, total_frames: int):  
        """追跡進捗更新"""  
        progress_percent = (current_frame / total_frames) * 100  
        progress_text = f"Tracking... {current_frame}/{total_frames} ({progress_percent:.1f}%)"  
        menu_panel = self.main_ui_controller.get_menu_panel()  
        if menu_panel:  
            menu_panel.update_tracking_progress(progress_text)  
  
    def on_tracking_completed(self, results: Dict[int, List[ObjectAnnotation]]):  
        """追跡完了時の処理（確認ダイアログ付き）"""  
        menu_panel = self.main_ui_controller.get_menu_panel()  
        if menu_panel:  
            menu_panel.update_tracking_progress("Tracking completed. Waiting for confirmation...")  
  
        # 確認ダイアログを表示  
        dialog = TrackingResultConfirmDialog(results, self.video_manager, self)  
  
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.approved:  
            # ユーザーが承認した場合のみ追加  
            added_count = 0  
            final_results_to_add = dialog.tracking_results  
  
            for frame_id, annotations in final_results_to_add.items():  
                for annotation in annotations:  
                    if self.app_service.annotation_repository.add_annotation(annotation):  
                        added_count += 1  
  
            self.update_annotation_count()  
            video_preview = self.main_ui_controller.get_video_preview()  
            if video_preview:  
                video_preview.update_frame_display()  
  
            ErrorHandler.show_info_dialog(  
                f"追跡が完了しました。{added_count}個のアノテーションを追加しました。",  
                "Tracking Complete"  
            )  
            if menu_panel:  
                menu_panel.update_tracking_progress("Tracking completed and annotations added!")  
        else:  
            # ユーザーが破棄を選択した場合  
            ErrorHandler.show_info_dialog(  
                "追跡結果を破棄しました。",  
                "Tracking Cancelled"  
            )  
            if menu_panel:  
                menu_panel.update_tracking_progress("Tracking results discarded.")  
  
    def on_tracking_error(self, message: str):  
        """追跡エラー時の処理"""  
        menu_panel = self.main_ui_controller.get_menu_panel()  
        if menu_panel:  
            menu_panel.update_tracking_progress("Tracking failed.")  
        ErrorHandler.show_error_dialog(f"Tracking encountered an error: {message}", "Tracking Error")  
  
    def on_bbox_created(self, x1: int, y1: int, x2: int, y2: int):  
        """バウンディングボックス作成時の処理（コマンドパターン対応）"""  
        bbox = BoundingBox(x1, y1, x2, y2)  
        video_control = self.main_ui_controller.get_video_control()  
        video_preview = self.main_ui_controller.get_video_preview()  
        menu_panel = self.main_ui_controller.get_menu_panel()  
          
        if not video_control:  
            return  
              
        current_frame = video_control.current_frame  
  
        # 現在のモードがEditModeの場合のみラベル入力ダイアログを表示  
        if video_preview and video_preview.mode_manager.current_mode_name == 'edit':  
            dialog = AnnotationInputDialog(bbox, self, existing_labels=self.app_service.annotation_repository.get_all_labels())  
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
                        is_batch_added=False  # 通常の手動アノテーション  
                    )  
  
                    # コマンドパターンを使用してアノテーション追加  
                    command = AddAnnotationCommand(self.app_service.annotation_repository, annotation)  
                    self.app_service.command_manager.execute_command(command)  
  
                    self.update_annotation_count()  
                    ErrorHandler.show_info_dialog(f"Added annotation: {label} at frame {current_frame}", "Annotation Added")  
  
                    if video_preview and hasattr(video_preview, 'bbox_editor'):  
                        video_preview.bbox_editor.selected_annotation = annotation  
                        video_preview.bbox_editor.selection_changed.emit(annotation)  
                        video_preview.update_frame_display()  
  
                    # オブジェクト一覧を更新  
                    if menu_panel:  
                        frame_annotation = self.app_service.annotation_repository.get_annotations(current_frame)  
                        menu_panel.update_current_frame_objects(current_frame, frame_annotation)  
                else:  
                    ErrorHandler.show_warning_dialog("Label cannot be empty.", "Input Error")  
        elif video_preview and video_preview.mode_manager.current_mode_name == 'batch_add':  
            # BatchAddModeの場合、ラベル入力ダイアログは表示しない(正常動作)  
            pass  
        else:  
            # その他のモードの場合（予期しないケース）  
            ErrorHandler.show_warning_dialog("不明なモードでbbox_createdが呼び出されました。", "Warning")  
  
    def start_playback(self):  
        """動画再生を開始"""  
        if self.playback_controller:  
            video_control = self.main_ui_controller.get_video_control()  
            if video_control:  
                self.playback_controller.play(video_control.current_frame)  
  
    def pause_playback(self):  
        """動画再生を一時停止"""  
        if self.playback_controller:  
            self.playback_controller.pause()  
            menu_panel = self.main_ui_controller.get_menu_panel()  
            if menu_panel:  
                menu_panel.reset_playback_button()  
  
    def on_config_changed(self, key: str, value: object, config_type: str):  
        """設定変更時の処理"""  
        if config_type == "display":  
            display_options = self.app_service.config_manager.get_full_config(config_type="display")  
            video_preview = self.main_ui_controller.get_video_preview()  
            menu_panel = self.main_ui_controller.get_menu_panel()  
            
            if video_preview:  
                video_preview.set_display_options(  
                    display_options.show_manual_annotations,  
                    display_options.show_auto_annotations,  
                    display_options.show_ids,  
                    display_options.show_confidence,  
                    display_options.score_threshold  
                )  
            # オブジェクト一覧のスコア閾値も更新  
            if menu_panel:  
                menu_panel.set_object_list_score_threshold(display_options.score_threshold)
  
    def on_annotation_selected(self, annotation: Optional[ObjectAnnotation]):  
        """アノテーション選択時の処理（中央集権的制御）"""  
        # ガード条件: 必要なオブジェクトが初期化されているかチェック  
        if not self.video_manager or not self.app_service.annotation_repository:  
            return  
  
        video_preview = self.main_ui_controller.get_video_preview()  
        menu_panel = self.main_ui_controller.get_menu_panel()  
          
        if not video_preview or not hasattr(video_preview, 'update_frame_display'):  
            return  
  
        # 循環呼び出し防止  
        if hasattr(self, '_updating_selection') and self._updating_selection:  
            return  
  
        self._updating_selection = True  
        try:  
            # MenuPanelの情報を更新  
            if menu_panel:  
                menu_panel.update_selected_annotation_info(annotation)  
                # オブジェクト一覧の選択状態も更新（双方向同期）  
                menu_panel.update_object_list_selection(annotation)  
  
            # VideoPreviewWidgetの選択状態を更新  
            if hasattr(video_preview, 'bbox_editor') and video_preview.bbox_editor:  
                video_preview.bbox_editor.selected_annotation = annotation  
                video_preview.bbox_editor.selection_changed.emit(annotation)  
  
            # VideoPreviewWidgetの表示も確実に更新  
            video_preview.update_frame_display()  
  
            # Undo/Redoボタンの状態も更新  
            if menu_panel and hasattr(menu_panel, 'update_undo_redo_buttons'):  
                menu_panel.update_undo_redo_buttons(self.app_service.command_manager)  
        finally:  
            self._updating_selection = False  
  
    def on_model_initialization_completed(self):  
        """モデル初期化完了時の処理"""  
        print("MASA models loaded successfully")  
        menu_panel = self.main_ui_controller.get_menu_panel()  
        if menu_panel:  
            menu_panel.set_tracking_enabled(True)  # トラッキング機能を有効化  
  
    def on_model_initialization_failed(self, error_message):  
        """モデル初期化失敗時の処理"""  
        ErrorHandler.show_error_dialog(f"Failed to initialize MASA models: {error_message}", "Initialization Error")  
        menu_panel = self.main_ui_controller.get_menu_panel()  
        if menu_panel:  
            menu_panel.set_tracking_enabled(False)  # トラッキング機能を無効化  
  
    def update_annotation_count(self):  
        """アノテーション数を更新し、UIに反映（Undo/Redoボタン状態も更新）"""  
        stats = self.app_service.annotation_repository.get_statistics()  
        menu_panel = self.main_ui_controller.get_menu_panel()  
        if menu_panel:  
            menu_panel.update_annotation_count(stats["total"], stats["manual"])  
            menu_panel.initialize_label_combo(self.app_service.annotation_repository.get_all_labels())  
    
            # Undo/Redoボタンの状態を更新  
            if hasattr(menu_panel, 'update_undo_redo_buttons'):  
                menu_panel.update_undo_redo_buttons(self.app_service.command_manager)  

    def on_bbox_position_updated(self, annotation: ObjectAnnotation, old_bbox: BoundingBox, new_bbox: BoundingBox):  
        """バウンディングボックス位置更新時の処理（コマンドパターン対応）"""  
        # 位置に変更があった場合のみコマンドを実行  
        if (old_bbox.x1 != new_bbox.x1 or old_bbox.y1 != new_bbox.y1 or  
            old_bbox.x2 != new_bbox.x2 or old_bbox.y2 != new_bbox.y2):  
  
            command = UpdateBoundingBoxCommand(self.app_service.annotation_repository, annotation, old_bbox, new_bbox)  
            self.app_service.command_manager.execute_command(command)  
  
            self.update_annotation_count()  
            video_preview = self.main_ui_controller.get_video_preview()  
            if video_preview:  
                video_preview.update_frame_display()  
  
            # オブジェクト一覧を更新  
            video_control = self.main_ui_controller.get_video_control()  
            menu_panel = self.main_ui_controller.get_menu_panel()  
            if video_control and menu_panel:  
                current_frame = video_control.current_frame  
                frame_annotation = self.app_service.annotation_repository.get_annotations(current_frame)  
                menu_panel.update_current_frame_objects(current_frame, frame_annotation)  
  
    def on_object_focus_requested(self, annotation: Optional[ObjectAnnotation]):  
        """オブジェクトフォーカス要求時の処理"""  
        if annotation:  
            video_preview = self.main_ui_controller.get_video_preview()  
            if video_preview and hasattr(video_preview, 'focus_on_annotation'):  
                # ビデオプレビューでオブジェクトにフォーカス  
                video_preview.focus_on_annotation(annotation)  
                # アノテーションを選択状態にする  
                self.on_annotation_selected(annotation)  
  
    def on_delete_annotation_requested(self, annotation: ObjectAnnotation):  
        """アノテーション削除要求時の処理（コマンドパターン対応）"""  
        if annotation:  
            # コマンドパターンを使用してアノテーション削除  
            command = DeleteAnnotationCommand(self.app_service.annotation_repository, annotation)  
            self.app_service.command_manager.execute_command(command)  
  
            self.update_annotation_count()  
            video_preview = self.main_ui_controller.get_video_preview()  
            if video_preview:  
                video_preview.update_frame_display()  
  
            # オブジェクト一覧を更新  
            video_control = self.main_ui_controller.get_video_control()  
            menu_panel = self.main_ui_controller.get_menu_panel()  
            if video_control and menu_panel:  
                current_frame = video_control.current_frame  
                frame_annotation = self.app_service.annotation_repository.get_annotations(current_frame)  
                menu_panel.update_current_frame_objects(current_frame, frame_annotation)  
  
            ErrorHandler.show_info_dialog("Annotation deleted successfully", "Delete Complete")  
  
    def on_delete_track_requested(self, track_id: int):  
        """トラック削除要求時の処理（コマンドパターン対応）"""  
        # コマンドパターンを使用してトラック削除  
        command = DeleteTrackCommand(self.app_service.annotation_repository, track_id)  
        deleted_count = self.app_service.command_manager.execute_command(command)  
  
        if deleted_count > 0:  
            self.update_annotation_count()  
            video_preview = self.main_ui_controller.get_video_preview()  
            if video_preview:  
                video_preview.update_frame_display()  
  
            # オブジェクト一覧を更新  
            video_control = self.main_ui_controller.get_video_control()  
            menu_panel = self.main_ui_controller.get_menu_panel()  
            if video_control and menu_panel:  
                current_frame = video_control.current_frame  
                frame_annotation = self.app_service.annotation_repository.get_annotations(current_frame)  
                menu_panel.update_current_frame_objects(current_frame, frame_annotation)  
  
            ErrorHandler.show_info_dialog(f"Track {track_id} deleted. {deleted_count} annotations removed.", "Track Deleted")  
        else:  
            ErrorHandler.show_warning_dialog(f"No annotations found for track ID {track_id}", "Warning")  
  
    def on_label_update_requested(self, annotation: ObjectAnnotation, new_label: str):  
        """ラベル更新要求時の処理（コマンドパターン対応）"""  
        if annotation and new_label:  
            old_label = annotation.label  
            command = UpdateLabelByTrackCommand(self.app_service.annotation_repository, annotation.track_id, old_label, new_label)  
            updated_count = self.app_service.command_manager.execute_command(command)  
  
            if updated_count > 0:  
                self.update_annotation_count()  
                video_preview = self.main_ui_controller.get_video_preview()  
                if video_preview:  
                    video_preview.update_frame_display()  
  
                # オブジェクト一覧を更新  
                video_control = self.main_ui_controller.get_video_control()  
                menu_panel = self.main_ui_controller.get_menu_panel()  
                if video_control and menu_panel:  
                    current_frame = video_control.current_frame  
                    frame_annotation = self.app_service.annotation_repository.get_annotations(current_frame)  
                    menu_panel.update_current_frame_objects(current_frame, frame_annotation)  
  
                ErrorHandler.show_info_dialog(f"Label updated for track {annotation.track_id}. {updated_count} annotations updated.", "Label Updated")  
  
    def keyPressEvent(self, event: QKeyEvent):  
        """キーボードショートカットの処理（KeyboardShortcutManagerに委譲）"""  
        # KeyboardShortcutManagerに処理を委譲  
        if self.keyboard_shortcut_manager.handle_key_event(event):  
            event.accept()  
        else:  
            super().keyPressEvent(event)  
  
    def closeEvent(self, event):  
        """アプリケーション終了時の処理"""  
        # VideoManagerのリソースを解放  
        if self.video_manager:  
            self.video_manager.release()  
          
        # TrackingWorkerが実行中の場合は停止  
        if self.tracking_worker and self.tracking_worker.isRunning():  
            self.tracking_worker.terminate()  
            self.tracking_worker.wait()  
          
        event.accept()