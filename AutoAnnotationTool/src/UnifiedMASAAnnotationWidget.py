from typing import Dict
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QDialog,
    QMessageBox, QFileDialog
)

from DataClass import BoundingBox, MASAConfig
from MenuPanel import MenuPanel, EnhancedMenuPanel
from EnhancedVideoControlPanel import EnhancedVideoControlPanel
from PreviewWidget import UnifiedVideoPreviewWidget
from VideoAnnotationManager import VideoAnnotationManager, EnhancedVideoAnnotationManager
from TrackingWorker import TrackingWorker
from Dialog import AnnotationInputDialog, TrackingSettingsDialog

class UnifiedMASAAnnotationWidget(QWidget):  
    """統合されたMASAアノテーションメインウィジェット"""  
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.video_manager = None  
        self.pending_bbox = None  
        self.setup_ui()  
          
    def setup_ui(self):  
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
        self.video_preview = UnifiedVideoPreviewWidget()  
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
          
        # 動画プレビューからのシグナル  
        self.video_preview.bbox_created.connect(self.on_bbox_created)  
        self.video_preview.frame_changed.connect(self.on_frame_changed)  
        self.video_preview.range_selection_changed.connect(self.on_range_selection_changed)  
          
        # 動画制御からのシグナル  
        self.video_control.frame_changed.connect(self.video_preview.set_frame)  
          
        # 表示オプションの変更  
        for checkbox in [self.menu_panel.show_manual_cb, self.menu_panel.show_auto_cb,  
                        self.menu_panel.show_ids_cb, self.menu_panel.show_confidence_cb]:  
            checkbox.stateChanged.connect(self.update_display_options)  
      
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
                # 動画プレビューに設定  
                self.video_preview.set_video_manager(self.video_manager)  
                  
                # 動画制御パネルに設定  
                self.video_control.set_total_frames(self.video_manager.total_frames)  
                self.video_control.set_current_frame(0)  
                  
                # メニューパネルの情報更新  
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
        self.video_preview.set_range_selection_mode(enabled)  
        if enabled:  
            QMessageBox.information(  
                self, "Range Selection Mode",   
                "Use the frame slider to select the range for auto tracking.\n"  
                "The selected range will be highlighted on the video."  
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
      
    def on_range_selection_changed(self, start_frame: int, end_frame: int):  
        """範囲選択変更時の処理"""  
        self.menu_panel.update_range_info(start_frame, end_frame)  
      
    def update_display_options(self):  
        """表示オプションを更新"""  
        options = self.menu_panel.get_display_options()  
        self.video_preview.set_display_options(  
            options['show_manual'],  
            options['show_auto'],  
            options['show_ids'],  
            options['show_confidence']  
        )  
      
    def update_annotation_count(self):  
        """アノテーション数を更新"""  
        if not self.video_manager:  
            return  
          
        total_annotations = sum(  
            len(annotations) for annotations in self.video_manager.manual_annotations.values()  
        )  
        self.menu_panel.update_annotation_count(total_annotations)  
      
    def start_tracking(self):  
        """自動追跡を開始"""  
        if not self.video_manager or not self.video_manager.manual_annotations:  
            QMessageBox.warning(self, "Warning", "Please add manual annotations first")  
            return  
          
        # 開始フレームを取得  
        start_frame = min(self.video_manager.manual_annotations.keys())  
          
        # 設定ダイアログを表示  
        settings_dialog = TrackingSettingsDialog(  
            self.video_manager.total_frames,   
            start_frame,   
            self  
        )  
          
        if settings_dialog.exec() == QDialog.DialogCode.Accepted:  
            end_frame = settings_dialog.get_end_frame()  
              
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
        """アノテーションをエクスポート"""  
        if not self.video_manager:  
            return  
          
        if format == "json":  
            file_path, _ = QFileDialog.getSaveFileName(  
                self, "Save JSON Annotations", "annotations.json",  
                "JSON Files (*.json);;All Files (*)"  
            )  
        else:  # COCO  
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

# UnifiedMASAAnnotationWidgetクラスの修正版  
class EnhancedUnifiedMASAAnnotationWidget(UnifiedMASAAnnotationWidget):  
    """範囲選択機能を改善したMASAアノテーションウィジェット"""  
      
    def setup_ui(self):  
        """UI設定（範囲選択機能を改善）"""  
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
        self.video_preview = UnifiedVideoPreviewWidget()  
        right_layout.addWidget(self.video_preview)  
          
        # 改善された動画制御パネル  
        self.video_control = EnhancedVideoControlPanel()  
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
        """シグナルとスロットを接続（範囲選択機能を追加）"""  
        # 親クラスのシグナル接続  
        super().connect_signals()  
          
        # 範囲選択関連のシグナル接続  
        self.video_control.range_changed.connect(self.on_range_selection_changed)  
        self.video_control.range_frame_preview.connect(self.on_range_frame_preview)
        self.menu_panel.range_selection_requested.connect(self.set_range_selection_mode)  
      
    def set_range_selection_mode(self, enabled: bool):  
        """範囲選択モードの設定（改善版）"""  
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
    def on_range_frame_preview(self, frame_id: int):  
        """範囲選択中のフレームプレビュー処理"""  
        # 範囲選択モードの場合のみ動画を更新  
        if self.video_control.range_selection_mode:  
            self.video_preview.set_frame(frame_id)  
            # 通常のフレームスライダーも同期  
            self.video_control.set_current_frame(frame_id)

    def start_tracking(self):  
        """自動追跡を開始（範囲選択機能を改善）"""  
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

class FinalEnhancedMASAAnnotationWidget(EnhancedUnifiedMASAAnnotationWidget):  
    """複数フレーム機能を統合した最終版ウィジェット"""  
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.multi_frame_dialog = None  
      
    def setup_ui(self):  
        # 基本UIは親クラスと同じだが、MenuPanelを拡張版に変更  
        self.setWindowTitle("MASA Video Annotation Tool - Enhanced")  
        self.setGeometry(100, 100, 1400, 900)  
          
        main_layout = QHBoxLayout()  
          
        # 拡張メニューパネル  
        self.menu_panel = EnhancedMenuPanel()  
        main_layout.addWidget(self.menu_panel)  
          
        # 右側は既存と同じ  
        right_layout = QVBoxLayout()  
        self.video_preview = UnifiedVideoPreviewWidget()  
        right_layout.addWidget(self.video_preview)  
          
        self.video_control = EnhancedVideoControlPanel()  
        right_layout.addWidget(self.video_control)  
          
        right_widget = QWidget()  
        right_widget.setLayout(right_layout)  
        main_layout.addWidget(right_widget)  
          
        main_layout.setStretch(0, 1)  
        main_layout.setStretch(1, 3)  
          
        self.setLayout(main_layout)  
        self.connect_signals()  
      
    def load_video(self):  
        """動画読み込み（拡張版マネージャーを使用）"""  
        file_path, _ = QFileDialog.getOpenFileName(  
            self, "Select Video File", "",   
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"  
        )  
          
        if file_path:  
            config = MASAConfig()  
            # 拡張版マネージャーを使用  
            self.video_manager = EnhancedVideoAnnotationManager(file_path, config)  
              
            if self.video_manager.load_video():  
                self.video_preview.set_video_manager(self.video_manager)  
                self.video_control.set_total_frames(self.video_manager.total_frames)  
                self.video_control.set_current_frame(0)  
                self.menu_panel.update_video_info(file_path, self.video_manager.total_frames)  
                  
                QMessageBox.information(self, "Success", f"Video loaded: {file_path}")  
            else:  
                QMessageBox.critical(self, "Error", "Failed to load video file")  
      
    def connect_signals(self):  
        super().connect_signals()  
          
        # 複数フレーム関連のシグナル接続  
        self.menu_panel.multi_frame_mode_requested.connect(self.set_multi_frame_mode)  
        self.video_preview.multi_frame_bbox_created.connect(self.on_multi_frame_bbox_created)  
        
        # Complete Multi-Frame ボタンのシグナル接続を追加  
        self.menu_panel.complete_multi_frame_btn.clicked.connect(self.on_complete_multi_frame)  
      
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
              
            # アノテーション数を更新（重要！）  
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
