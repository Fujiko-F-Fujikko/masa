import os
import cv2
from typing import Dict
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QDialog,
    QMessageBox, QFileDialog
)

from DataClass import BoundingBox, MASAConfig
from MenuPanel import MenuPanel
from VideoControlPanel import VideoControlPanel
from VideoPreviewWidget import VideoPreviewWidget
from VideoAnnotationManager import VideoAnnotationManager
from TrackingWorker import TrackingWorker
from Dialog import AnnotationInputDialog
from VideoPlaybackController import VideoPlaybackController

class MASAAnnotationWidget(QWidget):
    """統合されたMASAアノテーションメインウィジェット"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.temp_bboxes_for_batch_add = [] # 一括追加モードで生成されたBBoxを一時的に保持
        self.video_manager = None
        self.playback_controller = None
        self.setup_ui()

    def setup_ui(self):
        """UIの初期設定"""
        self.setWindowTitle("MASA Video Annotation Tool")
        self.setGeometry(100, 100, 1400, 900)

        # メインレイアウト（水平分割）
        main_layout = QHBoxLayout()

        # 左側：メニューパネル
        self.menu_panel = MenuPanel()
        main_layout.addWidget(self.menu_panel)

        # 右側：動画プレビューエリア
        right_layout = QVBoxLayout()

        # 動画プレビューウィジェット
        self.video_preview = VideoPreviewWidget()
        right_layout.addWidget(self.video_preview)

        # 動画制御パネル
        self.video_control = VideoControlPanel()
        right_layout.addWidget(self.video_control)

        # 右側レイアウトをウィジェットに包む
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        main_layout.addWidget(right_widget)

        # レイアウト比率設定（左：右 = 1：3）
        main_layout.setStretch(0, 1) # 左側のメニューパネル(index 0)
        main_layout.setStretch(1, 3) # 右側の動画プレビューと制御パネル(index 1)

        self.setLayout(main_layout)

        # シグナル接続
        self.connect_signals()

    def connect_signals(self):
        """シグナルとスロットを接続"""
        # メニューパネルからのシグナル
        self.menu_panel.load_video_requested.connect(self.load_video)
        self.menu_panel.result_view_requested.connect(self.set_result_view_mode)
        self.menu_panel.tracking_requested.connect(self.start_tracking)
        self.menu_panel.export_requested.connect(self.export_annotations)
        self.menu_panel.load_json_requested.connect(self.load_json_annotations)

        # 動画プレビューからのシグナル
        self.video_preview.bbox_created.connect(self.on_bbox_created)
        self.video_preview.frame_changed.connect(self.on_frame_changed)
        self.video_preview.multi_frame_bbox_created.connect(self.on_multi_frame_bbox_created)

        # 動画制御からのシグナル
        self.video_control.frame_changed.connect(self.video_preview.set_frame)
        self.video_control.range_changed.connect(self.on_range_selection_changed)
        self.video_control.range_frame_preview.connect(self.on_range_frame_preview)

        # 表示オプションの変更
        for checkbox in [self.menu_panel.show_manual_cb, self.menu_panel.show_auto_cb,
                        self.menu_panel.show_ids_cb, self.menu_panel.show_confidence_cb]:
            checkbox.stateChanged.connect(self.update_display_options)
        # スコア閾値変更のシグナル接続を追加  
        self.menu_panel.score_threshold_changed.connect(self.on_score_threshold_changed)

        # 再生制御のシグナル接続を追加  
        self.menu_panel.play_requested.connect(self.start_playback)  
        self.menu_panel.pause_requested.connect(self.pause_playback)  
        
        # 編集モード関連のシグナル接続を追加  
        self.menu_panel.edit_mode_requested.connect(self.set_edit_mode)  
        self.video_preview.annotation_selected.connect(self.on_annotation_selected)  
        self.menu_panel.label_change_requested.connect(self.on_label_change_requested)

        # アノテーションを削除（単一）するシグナルを接続
        self.menu_panel.delete_single_annotation_requested.connect(self.on_delete_annotation_requested) # 新しいシグナルを既存のハンドラに接続
        
        # アノテーションを削除（一括）するシグナルを接続
        self.menu_panel.delete_track_requested.connect(self.on_delete_track_requested)
        
        # アノテーションラベルを変更（一括）するシグナルを接続
        self.menu_panel.propagate_label_requested.connect(self.on_propagate_label_requested)
        
        self.menu_panel.batch_add_annotation_requested.connect(self.set_batch_add_annotation_mode)  
        self.menu_panel.complete_batch_add_requested.connect(self.on_complete_batch_add)  
        # VideoPreviewWidgetからのbbox_createdシグナルは、このモードでも利用  
        self.video_preview.bbox_created.connect(self.on_bbox_created_for_batch_add) 


    def load_video(self):  
        """動画ファイルを読み込み"""  
        file_path, _ = QFileDialog.getOpenFileName(  
            self, "Select Video File", "",  
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"  
        )  
      
        if file_path:  
            config = MASAConfig()  
            self.video_manager = VideoAnnotationManager(file_path, config)  
      
            if self.video_manager.load_video():  
                # 再生制御を初期化  
                self.playback_controller = VideoPlaybackController(self.video_manager)  
                self.playback_controller.frame_updated.connect(self.on_playback_frame_changed)  
                self.playback_controller.playback_finished.connect(self.on_playback_finished)  
                  
                # 動画のFPSを取得して設定  
                if hasattr(self.video_manager.video_reader, 'fps'):  
                    fps = self.video_manager.video_reader.get(cv2.CAP_PROP_FPS)  
                    if fps > 0:  
                        self.playback_controller.set_fps(fps)  
                  
                self.video_preview.set_video_manager(self.video_manager)  
                self.video_control.set_total_frames(self.video_manager.total_frames)  
                self.video_control.set_current_frame(0)  
                self.menu_panel.update_video_info(file_path, self.video_manager.total_frames)  
      
                QMessageBox.information(self, "Success", f"Video loaded: {file_path}")  
            else:  
                QMessageBox.critical(self, "Error", "Failed to load video file")

    def set_annotation_mode(self, enabled: bool):
        """アノテーションモードの設定"""
        self.video_preview.set_annotation_mode(enabled)
        if enabled:
            QMessageBox.information(
                self, "Annotation Mode",
                "Click and drag on the video to create bounding boxes.\n"
                "You will be prompted to enter labels for each annotation."
            )

    def set_result_view_mode(self, enabled: bool):
        """結果確認モードの設定"""
        self.video_preview.set_result_view_mode(enabled)
        self.update_display_options()

    def on_bbox_created(self, x1: int, y1: int, x2: int, y2: int):  
        """バウンディングボックス作成時の処理"""  
        bbox = BoundingBox(x1, y1, x2, y2)  
        current_frame = self.video_control.current_frame  
      
        if self.video_preview.batch_add_annotation_mode:  
            # 新規アノテーション一括追加モードの場合  
            self.temp_bboxes_for_batch_add.append((current_frame, bbox)) # ここでframe_idとbboxをタプルで追加  
            self.video_preview.update_frame_display() # 一時的な描画を更新  
            QMessageBox.information(  
                self, "BBox追加",  
                f"フレーム {current_frame} にバウンディングボックスを追加しました。"  
            )  
        else:  
            # 従来のシングルフレームアノテーションモードの場合  
            # ラベル入力ダイアログを表示  
            existing_labels = []  
            if self.video_manager:  
                existing_labels = self.video_manager.get_all_labels()  
      
            dialog = AnnotationInputDialog(bbox, self, existing_labels=existing_labels)  
            if dialog.exec() == QDialog.DialogCode.Accepted:  
                label = dialog.get_label()  
                if label:  
                    annotation = self.video_manager.add_manual_annotation(current_frame, bbox, label)  
                    self.update_annotation_count()  
                    QMessageBox.information(  
                        self, "Annotation Added",  
                        f"Added annotation: {label} at frame {current_frame}"  
                    )  
                    if self.video_preview.edit_mode:  
                        self.video_preview.bbox_editor.selected_annotation = annotation  
                        self.video_preview.bbox_editor.selection_changed.emit(annotation)  
                        self.video_preview.update_frame_display()

    def on_frame_changed(self, frame_id: int):  
        """フレーム変更時の処理"""  
        self.video_control.set_current_frame(frame_id)  
          
        # MenuPanelのフレーム表示も更新  
        if self.video_manager:  
            self.menu_panel.update_frame_display(frame_id, self.video_manager.total_frames)

    def on_range_selection_changed(self, start_frame: int, end_frame: int):
        """範囲選択変更時の処理"""
        self.menu_panel.update_range_info(start_frame, end_frame)

    def on_range_frame_preview(self, frame_id: int):
        """範囲選択中のフレームプレビュー処理"""
        # 動画を更新
        self.video_preview.set_frame(frame_id)
        # 通常のフレームスライダーも同期
        self.video_control.set_current_frame(frame_id)

    def update_display_options(self):
        """表示オプションを更新"""
        options = self.menu_panel.get_display_options()
        self.video_preview.set_display_options(
            options['show_manual'],
            options['show_auto'],
            options['show_ids'],
            options['show_confidence'],
            options['score_threshold']
        )

    def update_annotation_count(self):  
        """アノテーション数を更新（ラベル更新も含む）"""  
        if not self.video_manager:  
            return  
      
        # 統計情報を取得  
        stats = self.video_manager.get_annotation_statistics()  
          
        # MenuPanelに詳細情報を渡す  
        self.menu_panel.update_annotation_count(  
            stats["total"],   
            stats["manual"]  
        )  
          
        # ラベルコンボボックスも更新  
        existing_labels = self.video_manager.get_all_labels()  
        if existing_labels:  
            self.menu_panel.initialize_label_combo(existing_labels)

    def start_tracking(self):  
        """自動追跡を開始"""  
        if not self.video_manager or not self.video_manager.manual_annotations:  
            QMessageBox.warning(self, "Warning", "Please add manual annotations first")  
            return  
  
        # 編集モードがONの場合は常に範囲選択スライダーが有効なので、直接範囲を取得  
        start_frame, end_frame = self.video_control.get_selected_range()  
          
        # 確認ダイアログ  
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
  
            # バックグラウンドで追跡処理を実行  
            self.tracking_worker = TrackingWorker(self.video_manager, start_frame, end_frame)  
            self.tracking_worker.tracking_completed.connect(self.on_tracking_completed)  
            self.tracking_worker.progress_updated.connect(self.on_tracking_progress)  
            self.tracking_worker.start()

    def on_tracking_progress(self, current_frame: int, total_frames: int):
        """追跡進捗更新"""
        progress_percent = (current_frame / total_frames) * 100
        progress_text = f"Tracking... {current_frame}/{total_frames} ({progress_percent:.1f}%)"
        self.menu_panel.update_tracking_progress(progress_text)

    def on_tracking_completed(self, results: Dict):
        """追跡完了時の処理"""
        self.menu_panel.update_tracking_progress(f"Completed! {len(results)} frames processed.")
        self.menu_panel.enable_result_view(True)

        QMessageBox.information(
            self, "Tracking Complete",
            f"Automatic tracking completed successfully!\n"
            f"Processed {len(results)} frames.\n"
            f"You can now view results using 'View Results Mode'."
        )

    def export_annotations(self, format: str):  
        """アノテーションをエクスポート（MASA JSON形式を追加）"""  
        if not self.video_manager:  
            return  
      
        if format == "json":  
            # 既存のカスタムJSON形式  
            file_path, _ = QFileDialog.getSaveFileName(  
                self, "Save JSON Annotations", "annotations.json",  
                "JSON Files (*.json);;All Files (*)"  
            )  
            if file_path:  
                try:  
                    self.video_manager.export_annotations(file_path, format=format)  
                    QMessageBox.information(self, "Export Complete", f"Annotations exported to {file_path}")  
                except Exception as e:  
                    QMessageBox.critical(self, "Export Error", f"Failed to export annotations: {e}")  
                      
        elif format == "masa_json":  
            # MASA形式のJSON  
            file_path, _ = QFileDialog.getSaveFileName(  
                self, "Save MASA JSON Annotations", "masa_annotations.json",  
                "JSON Files (*.json);;All Files (*)"  
            )  
            if file_path:  
                try:  
                    self.video_manager.export_masa_json(file_path)  
                    QMessageBox.information(self, "Export Complete", f"MASA JSON exported to {file_path}")  
                except Exception as e:  
                    QMessageBox.critical(self, "Export Error", f"Failed to export MASA JSON: {e}")  
        else:  
            # COCO形式  
            file_path, _ = QFileDialog.getSaveFileName(  
                self, "Save COCO Annotations", "annotations_coco.json",  
                "JSON Files (*.json);;All Files (*)"  
            )  
            if file_path:  
                try:  
                    self.video_manager.export_annotations(file_path, format=format)  
                    QMessageBox.information(self, "Export Complete", f"Annotations exported to {file_path}")  
                except Exception as e:  
                    QMessageBox.critical(self, "Export Error", f"Failed to export annotations: {e}")

    def set_multi_frame_mode(self, enabled: bool, label: str):
        """複数フレームモードの設定"""
        self.video_preview.set_multi_frame_mode(enabled, label)

        if enabled:
            QMessageBox.information(
                self, "Multi-Frame Mode",
                f"Multi-frame annotation mode for '{label}' is now active.\n"
                "Click and drag on different frames to create bounding boxes.\n"
                "Click 'Complete Multi-Frame' when finished."
            )

    def on_multi_frame_bbox_created(self, x1: int, y1: int, x2: int, y2: int, frame_id: int):
        """複数フレームバウンディングボックス作成時の処理"""
        bbox = BoundingBox(x1, y1, x2, y2)

        # 複数フレームアノテーションリストに追加
        annotation_data = {
            'frame_id': frame_id,
            'bbox': bbox
        }
        self.video_preview.multi_frame_annotations.append(annotation_data)

        # 表示を更新
        self.video_preview.update_frame_display()

        QMessageBox.information(
            self, "Frame Added",
            f"Added bounding box for frame {frame_id}.\n"
            f"Total frames: {len(self.video_preview.multi_frame_annotations)}"
        )

    def on_complete_multi_frame(self):
        """複数フレームアノテーション完了時の処理"""
        if not self.video_preview.multi_frame_annotations:
            QMessageBox.warning(self, "Warning", "No multi-frame annotations to complete")
            return

        # 複数フレームアノテーションをビデオマネージャーに追加
        frame_ids = [ann['frame_id'] for ann in self.video_preview.multi_frame_annotations]
        bboxes = [ann['bbox'] for ann in self.video_preview.multi_frame_annotations]
        label = self.video_preview.current_multi_frame_label

        if self.video_manager and hasattr(self.video_manager, 'add_multi_frame_annotation'):
            annotations = self.video_manager.add_multi_frame_annotation(frame_ids, bboxes, label)

            # アノテーション数を更新
            self.update_annotation_count()

            QMessageBox.information(
                self, "Multi-Frame Annotation Completed",
                f"Added {len(annotations)} annotations for '{label}' across {len(frame_ids)} frames"
            )

        # 複数フレームモードを終了
        self.menu_panel.multi_frame_btn.setChecked(False)
        self.menu_panel._on_multi_frame_clicked(False)

        # 作成中のアノテーションをクリア
        self.video_preview.multi_frame_annotations.clear()
        self.video_preview.update_frame_display()

    def load_json_annotations(self, json_path: str):  
        """JSONアノテーションファイルを読み込み"""  
        if not self.video_manager:  
            QMessageBox.warning(self, "Warning", "Please load a video file first")  
            return  
          
        if self.video_manager.load_json_annotations(json_path):  
            # UI更新  
            total_annotations = sum(  
                len(frame_annotation.objects)   
                for frame_annotation in self.video_manager.frame_annotations.values()  
            )  
              
            self.menu_panel.update_json_info(json_path, total_annotations)  
            self.update_annotation_count()  
              
            # 結果表示モードを有効化  
            self.video_preview.set_result_view_mode(True)  
            self.menu_panel.enable_result_view(True)  
              
            QMessageBox.information(  
                self, "JSON Loaded",   
                f"Successfully loaded {total_annotations} annotations from JSON file"  
            )  
        else:  
            QMessageBox.critical(self, "Error", "Failed to load JSON annotation file")

    def on_score_threshold_changed(self, threshold: float):  
        """スコア閾値変更時の処理"""  
        self.update_display_options()  
        
    def start_playback(self):  
        """再生開始"""  
        if self.playback_controller:  
            current_frame = self.video_control.current_frame  
            self.playback_controller.play(current_frame)  
      
    def pause_playback(self):  
        """再生一時停止"""  
        if self.playback_controller:  
            self.playback_controller.pause()  
      
    def on_playback_frame_changed(self, frame_id: int):  
        """再生中のフレーム変更処理"""  
        # VideoControlPanelとVideoPreviewWidgetを更新  
        self.video_control.set_current_frame(frame_id)  
        self.video_preview.set_frame(frame_id)  
          
        # MenuPanelのフレーム表示も更新  
        if self.video_manager:  
            self.menu_panel.update_frame_display(frame_id, self.video_manager.total_frames)

    def on_playback_finished(self):  
        """再生完了処理"""  
        self.menu_panel.reset_playback_button()  
        QMessageBox.information(self, "Playback", "Video playback completed")
    
    def set_edit_mode(self, enabled: bool):  
        """編集モードの設定"""  
        self.video_preview.set_edit_mode(enabled)  
        # 編集モードがONの場合のみ範囲選択スライダーを表示  
        self.video_control.range_slider.setVisible(enabled)
 
        if enabled:  
            QMessageBox.information(  
                self, "Edit Mode",  
                "Click on annotations in the video to select and edit them.\n"  
                "Selected annotations will be highlighted in yellow."  
            )  
      
    def on_annotation_selected(self, annotation):  
        """アノテーション選択時の処理"""  
        # MenuPanelの編集コントロールに選択されたアノテーションの情報を設定  
        # annotationがNoneの場合はUIをリセット 
        self.menu_panel.update_selected_annotation_info(annotation)

    def load_video_from_path(self, video_path: str):  
        """パスから動画ファイルを読み込み"""  
        if not os.path.exists(video_path):  
            QMessageBox.critical(self, "Error", f"Video file not found: {video_path}")  
            return False  
          
        config = MASAConfig()  
        self.video_manager = VideoAnnotationManager(video_path, config)  
      
        if self.video_manager.load_video():  
            # 再生制御を初期化  
            self.playback_controller = VideoPlaybackController(self.video_manager)  
            self.playback_controller.frame_updated.connect(self.on_playback_frame_changed)  
            self.playback_controller.playback_finished.connect(self.on_playback_finished)  
              
            # 動画のFPSを取得して設定  
            if hasattr(self.video_manager.video_reader, 'fps'):  
                fps = self.video_manager.video_reader.get(cv2.CAP_PROP_FPS)  
                if fps > 0:  
                    self.playback_controller.set_fps(fps)  
              
            self.video_preview.set_video_manager(self.video_manager)  
            self.video_control.set_total_frames(self.video_manager.total_frames)  
            self.video_control.set_current_frame(0)  
            self.menu_panel.update_video_info(video_path, self.video_manager.total_frames)  
              
            print(f"Video loaded: {video_path}")  
            return True  
        else:  
            QMessageBox.critical(self, "Error", "Failed to load video file")  
            return False  
      
    def load_json_from_path(self, json_path: str):  
        """パスからJSONアノテーションファイルを読み込み"""  
        if not os.path.exists(json_path):  
            QMessageBox.critical(self, "Error", f"JSON file not found: {json_path}")  
            return False  
          
        if not self.video_manager:  
            QMessageBox.warning(self, "Warning", "Please load a video file first")  
            return False  
          
        if self.video_manager.load_json_annotations(json_path):  
            # UI更新  
            total_annotations = sum(  
                len(frame_annotation.objects)   
                for frame_annotation in self.video_manager.frame_annotations.values()  
            )  
              
            self.menu_panel.update_json_info(json_path, total_annotations)  
            self.update_annotation_count()  
              
            # 結果表示モードを有効化  
            self.video_preview.set_result_view_mode(True)  
            self.menu_panel.enable_result_view(True)  
              
            print(f"JSON loaded: {json_path}")  
            return True  
        else:  
            QMessageBox.critical(self, "Error", "Failed to load JSON annotation file")  
            return False

    def on_label_change_requested(self, annotation, new_label):  
        """ラベル変更要求の処理"""  
        if annotation and new_label:  
            # VideoAnnotationManager を介してアノテーションのラベルを更新  
            if self.video_manager.update_annotation_label(  
                annotation.object_id, annotation.frame_id, new_label  
            ):  
                # 成功した場合のみ表示を更新  
                self.video_preview.update_frame_display()  
                # ここにあった QMessageBox.information は削除  
            else:  
                QMessageBox.warning(  
                    self, "ラベル変更失敗",  
                    f"アノテーションID {annotation.object_id} のラベル変更に失敗しました。"  
                )

    def on_delete_annotation_requested(self, annotation):  
        """アノテーション削除要求の処理"""  
        if annotation:  
            if self.video_manager.delete_annotation(annotation.object_id, annotation.frame_id):  
                QMessageBox.information(  
                    self, "アノテーション削除",  
                    f"フレーム {annotation.frame_id} のアノテーション (ID: {annotation.object_id}) を削除しました。"  
                )  
                self.update_annotation_count() # アノテーション数を更新  
                self.video_preview.update_frame_display() # 表示を更新  
            else:  
                QMessageBox.warning(  
                    self, "削除失敗",  
                    f"アノテーションID {annotation.object_id} の削除に失敗しました。"  
                )

    def on_delete_track_requested(self, track_id: int):  
        """Track IDによるアノテーション一括削除要求の処理"""  
        if track_id is not None:  
            deleted_count = self.video_manager.delete_annotations_by_track_id(track_id)  
            if deleted_count > 0:  
                QMessageBox.information(  
                    self, "Track一括削除",  
                    f"Track ID '{track_id}' を持つアノテーションを {deleted_count} 件削除しました。"  
                )  
                self.update_annotation_count() # アノテーション数を更新  
                self.video_preview.update_frame_display() # 表示を更新  
            else:  
                QMessageBox.warning(  
                    self, "Track一括削除失敗",  
                    f"Track ID '{track_id}' を持つアノテーションは見つかりませんでした。"  
                )

    def on_propagate_label_requested(self, track_id: int, new_label: str):  
        """Track IDによるアノテーション一括ラベル変更要求の処理"""  
        if track_id is not None and new_label:  
            updated_count = self.video_manager.update_annotations_label_by_track_id(track_id, new_label)  
            if updated_count > 0:  
                QMessageBox.information(  
                    self, "Track一括ラベル変更",  
                    f"Track ID '{track_id}' を持つアノテーション {updated_count} 件のラベルを '{new_label}' に変更しました。"  
                )  
                self.update_annotation_count() # アノテーション数を更新（ラベルキャッシュも更新される）  
                self.video_preview.update_frame_display() # 表示を更新  
            else:  
                QMessageBox.warning(  
                    self, "Track一括ラベル変更失敗",  
                    f"Track ID '{track_id}' を持つアノテーションは見つかりませんでした。"  
                )

    def set_batch_add_annotation_mode(self, enabled: bool):  
        """新規アノテーション一括追加モードの有効/無効を切り替える"""  
        self.video_preview.set_batch_add_annotation_mode(enabled) # VideoPreviewWidgetのモードを設定  
          
        # 他のモードボタンの状態を適切にリセット  
        # 例:  
        # self.single_frame_mode_button.setChecked(not enabled)  
        # self.multi_frame_mode_button.setChecked(not enabled)  
          
        # 「新規アノテーション一括追加」ボタン自体の有効/無効を制御  
        # このボタンがどのウィジェットに属しているかによるが、例えばmenu_panelにある場合  
        if hasattr(self, 'menu_panel') and hasattr(self.menu_panel, 'batch_add_button'):  
            self.menu_panel.batch_add_button.setEnabled(enabled)  
          
        # 編集モードがONの場合にのみ、このボタンが有効になるようにする  
        # このロジックは、ボタンがクリックされたときに呼び出される場所で制御されるべきだが、  
        # ここで明示的に設定することも可能  
        if enabled and self.video_preview.edit_mode:  
            # ボタンを有効にする  
            if hasattr(self, 'menu_panel') and hasattr(self.menu_panel, 'batch_add_button'):  
                self.menu_panel.batch_add_button.setEnabled(True)  
        else:  
            # ボタンを無効にする  
            if hasattr(self, 'menu_panel') and hasattr(self.menu_panel, 'batch_add_button'):  
                self.menu_panel.batch_add_button.setEnabled(False)  
      
        # UIの更新をトリガー  
        self.video_preview.update_frame_display()

    def on_bbox_created_for_batch_add(self, x1: int, y1: int, x2: int, y2: int):  
        """新規アノテーション一括追加モードでのバウンディングボックス作成時の処理"""  
        if self.video_preview.batch_add_annotation_mode: # このモードがONの場合のみ処理  
            bbox = BoundingBox(x1, y1, x2, y2)  
            # 一時リストに追加 (フレームIDは後で割り当てる)  
            self.temp_bboxes_for_batch_add.append((self.video_control.current_frame, bbox))  
            self.video_preview.update_frame_display() # 一時的な描画を更新  
            QMessageBox.information(  
                self, "BBox追加",  
                f"フレーム {self.video_control.current_frame} にバウンディングボックスを追加しました。"  
            )  
        else:  
            # 従来のシングルフレームアノテーションモードの処理  
            # ... 既存の on_bbox_created ロジック ...  
            pass # 既存の on_bbox_created の内容をここに移動または呼び出す

    def on_complete_batch_add(self, label: str, dummy_start_frame: int, dummy_end_frame: int):  
        """新規アノテーション一括追加完了時の処理"""  
        if not self.temp_bboxes_for_batch_add:  
            QMessageBox.warning(self, "警告", "追加するバウンディングボックスがありません。")  
            return  
      
        # フレーム範囲の取得  
        start_frame, end_frame = self.video_control.get_selected_range()  
        if start_frame == -1 or end_frame == -1: # RangeSliderが初期状態の場合  
            # temp_bboxes_for_batch_add に含まれるフレームIDの最小値と最大値を使用  
            frame_ids_in_temp = [item[0] for item in self.temp_bboxes_for_batch_add]  
            if frame_ids_in_temp:  
                start_frame = min(frame_ids_in_temp)  
                end_frame = max(frame_ids_in_temp)  
            else:  
                start_frame = 0  
                end_frame = self.video_manager.total_frames - 1  
      
      
        frame_count = end_frame - start_frame + 1  
        reply = QMessageBox.question(  
            self, "自動検出実行確認",  
            f"指定されたバウンディングボックスを元に、フレーム {start_frame} から {end_frame} まで自動検出を実行しますか？\n"  
            f"合計フレーム数: {frame_count}\n"  
            f"この処理には時間がかかる場合があります。",  
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
        )  
      
        if reply == QMessageBox.StandardButton.Yes:  
            self.menu_panel.update_tracking_progress("検出処理中...")  
            # 新しいTrack IDを生成  
            new_track_id = self.video_manager.get_next_object_id() # ここでTrack IDを生成  
      
            # TrackingWorkerに初期アノテーションとTrack IDを渡す  
            self.tracking_worker = TrackingWorker(  
                self.video_manager,  
                start_frame,  
                end_frame,  
                initial_annotations=self.temp_bboxes_for_batch_add,  
                assigned_track_id=new_track_id, # 生成したTrack IDを渡す  
                assigned_label=label  
            )  
            self.tracking_worker.tracking_completed.connect(self.on_batch_add_tracking_completed)  
            self.tracking_worker.progress_updated.connect(self.on_tracking_progress)  
            self.tracking_worker.start()  
              
            # UIをリセット  
            self.temp_bboxes_for_batch_add.clear()  
            self.video_preview.set_batch_add_annotation_mode(False)  
            self.video_preview.update_frame_display()  
        else:  
            QMessageBox.information(self, "キャンセル", "自動検出はキャンセルされました。")
  
    def on_batch_add_tracking_completed(self, tracked_annotations: dict):  
        """新規アノテーション一括追加モードでの追跡完了時の処理"""  
        if tracked_annotations:  
            added_count = 0  
            for frame_id, annotations_list in tracked_annotations.items():  
                for ann in annotations_list:  
                    # TrackingWorkerから返されたアノテーションをVideoAnnotationManagerに追加  
                    # TrackingWorkerがObjectAnnotationを返すように修正する必要がある  
                    self.video_manager.add_manual_annotation(  
                        ann.frame_id, ann.bbox, ann.label, ann.is_manual, ann.object_id  
                    )  
                    added_count += 1  
            QMessageBox.information(  
                self, "検出完了",  
                f"自動検出により {added_count} 件のアノテーションが追加されました。"  
            )  
        else:  
            QMessageBox.information(self, "検出完了", "検出されたアノテーションはありませんでした。")  
          
        self.update_annotation_count()  
        self.video_preview.update_frame_display()  
        self.menu_panel.update_tracking_progress("") # 進捗表示をクリア
        
        # VideoAnnotationManagerのnext_object_idを更新  
        if hasattr(self.tracking_worker, 'max_used_track_id'):  
            self.video_manager.next_object_id = max(  
                self.video_manager.next_object_id,   
                self.tracking_worker.max_used_track_id + 1  
            )
