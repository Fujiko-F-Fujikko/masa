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
        self.video_manager = None
        self.pending_bbox = None
        self.multi_frame_dialog = None
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
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 3)

        self.setLayout(main_layout)

        # シグナル接続
        self.connect_signals()

    def connect_signals(self):
        """シグナルとスロットを接続"""
        # メニューパネルからのシグナル
        self.menu_panel.load_video_requested.connect(self.load_video)
        self.menu_panel.annotation_mode_requested.connect(self.set_annotation_mode)
        self.menu_panel.range_selection_requested.connect(self.set_range_selection_mode)
        self.menu_panel.result_view_requested.connect(self.set_result_view_mode)
        self.menu_panel.tracking_requested.connect(self.start_tracking)
        self.menu_panel.export_requested.connect(self.export_annotations)
        self.menu_panel.multi_frame_mode_requested.connect(self.set_multi_frame_mode)
        self.menu_panel.load_json_requested.connect(self.load_json_annotations)

        # 動画プレビューからのシグナル
        self.video_preview.bbox_created.connect(self.on_bbox_created)
        self.video_preview.frame_changed.connect(self.on_frame_changed)
        self.video_preview.range_selection_changed.connect(self.on_range_selection_changed)
        self.video_preview.multi_frame_bbox_created.connect(self.on_multi_frame_bbox_created)

        # 動画制御からのシグナル
        self.video_control.frame_changed.connect(self.video_preview.set_frame)
        self.video_control.range_changed.connect(self.on_range_selection_changed)
        self.video_control.range_frame_preview.connect(self.on_range_frame_preview)

        # Complete Multi-Frame ボタンのシグナル接続
        self.menu_panel.complete_multi_frame_btn.clicked.connect(self.on_complete_multi_frame)

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

    def set_range_selection_mode(self, enabled: bool):
        """範囲選択モードの設定"""
        # 動画制御パネルの範囲選択モードを設定
        self.video_control.toggle_range_mode(enabled)
        
        # 動画プレビューの範囲選択モードは無効化（スライダーで制御）
        self.video_preview.set_range_selection_mode(False)

        if enabled:
            QMessageBox.information(
                self, "Range Selection Mode",
                "Use the range slider below the video to select frames for auto tracking.\n"
                "Drag the handles to adjust start and end frames.\n"
                "You can also drag the blue range area to move the entire selection."
            )

    def set_result_view_mode(self, enabled: bool):
        """結果確認モードの設定"""
        self.video_preview.set_result_view_mode(enabled)
        self.update_display_options()

    def on_bbox_created(self, x1: int, y1: int, x2: int, y2: int):
        """バウンディングボックス作成時の処理"""
        bbox = BoundingBox(x1, y1, x2, y2)

        # ラベル入力ダイアログを表示
        dialog = AnnotationInputDialog(bbox, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            label = dialog.get_label()
            if label:
                # アノテーションを追加
                current_frame = self.video_control.current_frame
                annotation = self.video_manager.add_manual_annotation(current_frame, bbox, label)

                # UI更新
                self.update_annotation_count()

                QMessageBox.information(
                    self, "Annotation Added",
                    f"Added annotation: {label} at frame {current_frame}"
                )

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
        # 範囲選択モードの場合のみ動画を更新
        if self.video_control.range_selection_mode:
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
        """アノテーション数を更新"""  
        if not self.video_manager:  
            return  
      
        # 統計情報を取得  
        stats = self.video_manager.get_annotation_statistics()  
          
        # MenuPanelに詳細情報を渡す  
        self.menu_panel.update_annotation_count(  
            stats["total"],   
            stats["manual"]  
        )

    def start_tracking(self):
        """自動追跡を開始"""
        if not self.video_manager or not self.video_manager.manual_annotations:
            QMessageBox.warning(self, "Warning", "Please add manual annotations first")
            return

        # 範囲選択モードが有効な場合は、選択された範囲を使用
        if self.video_control.range_selection_mode:
            start_frame, end_frame = self.video_control.get_selected_range()
        else:
            # 警告を表示
            QMessageBox.warning(self, "Warning", "Please select a frame range for auto tracking")
            return

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
        if enabled:  
            QMessageBox.information(  
                self, "Edit Mode",  
                "Click on annotations in the video to select and edit them.\n"  
                "Selected annotations will be highlighted in yellow."  
            )  
      
    def on_annotation_selected(self, annotation):  
        """アノテーション選択時の処理"""  
        # annotationがNoneの場合は処理をスキップ  
        if annotation is None:  
            return  
          
        # MenuPanelの編集コントロールに選択されたアノテーションの情報を設定  
        if hasattr(self.menu_panel, 'label_combo'):  
            # ラベルコンボボックスに現在のラベルを設定  
            index = self.menu_panel.label_combo.findText(annotation.label)  
            if index >= 0:  
                self.menu_panel.label_combo.setCurrentIndex(index)  
          
        if hasattr(self.menu_panel, 'track_id_edit'):  
            # Track ID入力欄に現在のIDを設定  
            self.menu_panel.track_id_edit.setText(str(annotation.object_id))