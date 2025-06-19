import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QLabel, QWidget, QHBoxLayout, QVBoxLayout,
    QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor

from DataClass import MASAConfig, BoundingBox
from AnnotationVisualizer import AnnotationVisualizer
from VideoAnnotationManager import VideoAnnotationManager
from MenuPanel import MenuPanel, EnhancedMenuPanel
from TrackingWorker import TrackingWorker
from EnhancedVideoControlPanel import EnhancedVideoControlPanel
from UnifiedMASAAnnotationWidget import UnifiedMASAAnnotationWidget

class UnifiedVideoPreviewWidget(QLabel):  
    """統合された動画プレビューウィジェット"""  
      
    # シグナル定義  
    bbox_created = pyqtSignal(int, int, int, int)  # x1, y1, x2, y2  
    frame_changed = pyqtSignal(int)  # frame_id  
    range_selection_changed = pyqtSignal(int, int)  # start_frame, end_frame  
    multi_frame_bbox_created = pyqtSignal(int, int, int, int, int)  # x1, y1, x2, y2, frame_id 
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.setMinimumSize(800, 600)  
        self.setStyleSheet("border: 2px solid gray; background-color: black;")  
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)  
          
        # 動画関連  
        self.video_manager = None  
        self.current_frame_id = 0  
        self.current_frame = None  
          
        # 描画関連  
        self.drawing = False  
        self.start_point = QPoint()  
        self.end_point = QPoint()  
        self.current_rect = QRect()  
        self.scale_x = 1.0  
        self.scale_y = 1.0  
        self.offset_x = 0  
        self.offset_y = 0  
        self.original_width = 0  
        self.original_height = 0  
          
        # 表示モード  
        self.annotation_mode = False  # アノテーション作成モード  
        self.range_selection_mode = False  # 範囲選択モード  
        self.result_view_mode = False  # 結果確認モード  
          
        # 範囲選択関連  
        self.range_start_frame = 0  
        self.range_end_frame = 0  
        self.range_selecting = False  
          
        # 表示オプション  
        self.show_manual_annotations = True  
        self.show_auto_annotations = True  
        self.show_ids = True  
        self.show_confidence = True  
        
        # 新しいモード追加 
        self.multi_frame_mode = False  # 複数フレームアノテーションモード  
        self.current_multi_frame_label = ""  
        self.multi_frame_annotations = []  # 現在作成中の複数フレームアノテーション  

        # 可視化  
        self.visualizer = AnnotationVisualizer()  

    def set_multi_frame_mode(self, enabled: bool, label: str = ""):  
        """複数フレームアノテーションモードの設定"""  
        self.multi_frame_mode = enabled  
        self.annotation_mode = False  
        self.range_selection_mode = False  
        self.result_view_mode = False  
        self.current_multi_frame_label = label  
          
        if enabled:  
            self.setCursor(Qt.CursorShape.CrossCursor)  
            # 既存の複数フレームアノテーションをクリア  
            self.multi_frame_annotations.clear()  
        else:  
            self.setCursor(Qt.CursorShape.ArrowCursor) 

    def set_video_manager(self, video_manager: VideoAnnotationManager):  
        """動画マネージャーを設定"""  
        self.video_manager = video_manager  
        if video_manager:  
            self.current_frame_id = 0  
            self.update_frame_display()  
      
    def set_annotation_mode(self, enabled: bool):  
        """アノテーション作成モードの設定"""  
        self.annotation_mode = enabled  
        self.range_selection_mode = False  
        self.result_view_mode = False  
        self.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)  
      
    def set_range_selection_mode(self, enabled: bool):  
        """範囲選択モードの設定"""  
        self.range_selection_mode = enabled  
        self.annotation_mode = False  
        self.result_view_mode = False  
        if enabled:  
            self.range_start_frame = self.current_frame_id  
            self.range_end_frame = self.current_frame_id  
      
    def set_result_view_mode(self, enabled: bool):  
        """結果確認モードの設定"""  
        self.result_view_mode = enabled  
        self.annotation_mode = False  
        self.range_selection_mode = False  
        self.update_frame_display()  
      
    def set_display_options(self, show_manual: bool, show_auto: bool,   
                           show_ids: bool, show_confidence: bool):  
        """表示オプションの設定"""  
        self.show_manual_annotations = show_manual  
        self.show_auto_annotations = show_auto  
        self.show_ids = show_ids  
        self.show_confidence = show_confidence  
        self.update_frame_display()  
      
    def set_frame(self, frame_id: int):  
        """指定フレームに移動"""  
        if not self.video_manager:  
            return  
          
        self.current_frame_id = max(0, min(frame_id, self.video_manager.total_frames - 1))  
        self.update_frame_display()  
        self.frame_changed.emit(self.current_frame_id)  
          
        # 範囲選択モードの場合  
        if self.range_selection_mode:  
            self.range_end_frame = self.current_frame_id  
            self.range_selection_changed.emit(  
                min(self.range_start_frame, self.range_end_frame),  
                max(self.range_start_frame, self.range_end_frame)  
            )  
      
    def update_frame_display(self):  
        """フレーム表示を更新"""  
        if not self.video_manager:  
            return  
          
        frame = self.video_manager.get_frame(self.current_frame_id)  
        if frame is None:  
            return  
          
        self.current_frame = frame.copy()  
      
        # 複数フレームモードの場合、作成中のアノテーションを表示  
        if self.multi_frame_mode and self.multi_frame_annotations:  
            frame = self._draw_multi_frame_annotations(frame)  
          
        # 結果確認モードの場合、アノテーションを描画  
        if self.result_view_mode:  
            frame_annotation = self.video_manager.get_frame_annotations(self.current_frame_id)  
            if frame_annotation and frame_annotation.objects:  
                annotations_to_show = []  
                  
                for annotation in frame_annotation.objects:  
                    if annotation.is_manual and self.show_manual_annotations:  
                        annotations_to_show.append(annotation)  
                    elif not annotation.is_manual and self.show_auto_annotations:  
                        annotations_to_show.append(annotation)  
                  
                if annotations_to_show:  
                    frame = self.visualizer.draw_annotations(  
                        frame, annotations_to_show,  
                        show_ids=self.show_ids,  
                        show_confidence=self.show_confidence  
                    )  
          
        # 範囲選択モードの場合、範囲を視覚的に表示  
        if self.range_selection_mode:  
            frame = self._draw_range_indicator(frame)  
          
        self._display_frame_on_widget(frame)  

    def _draw_multi_frame_annotations(self, frame: np.ndarray) -> np.ndarray:  
        """作成中の複数フレームアノテーションを描画"""  
        result_frame = frame.copy()  
          
        for annotation in self.multi_frame_annotations:  
            if annotation['frame_id'] == self.current_frame_id:  
                # 現在のフレームのアノテーションを緑色で描画  
                color = (0, 255, 0)  
                thickness = 3  
            else:  
                # 他のフレームのアノテーションを薄い緑色で描画（参考用）  
                color = (0, 200, 0)  
                thickness = 1  
              
            bbox = annotation['bbox']  
            pt1 = (int(bbox.x1), int(bbox.y1))  
            pt2 = (int(bbox.x2), int(bbox.y2))  
            cv2.rectangle(result_frame, pt1, pt2, color, thickness)  
              
            # フレーム番号を表示  
            cv2.putText(result_frame, f"F{annotation['frame_id']}",   
                       (pt1[0], pt1[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)  
          
        return result_frame
      
    def _draw_range_indicator(self, frame: np.ndarray) -> np.ndarray:  
        """範囲選択の視覚的インジケーターを描画"""  
        result_frame = frame.copy()  
          
        # 範囲内のフレームかどうかで色を変える  
        start_frame = min(self.range_start_frame, self.range_end_frame)  
        end_frame = max(self.range_start_frame, self.range_end_frame)  
          
        if start_frame <= self.current_frame_id <= end_frame:  
            # 範囲内：緑の枠  
            color = (0, 255, 0)  
            thickness = 5  
        else:  
            # 範囲外：赤の枠  
            color = (255, 0, 0)  
            thickness = 3  
          
        h, w = result_frame.shape[:2]  
        cv2.rectangle(result_frame, (10, 10), (w-10, h-10), color, thickness)  
          
        # 範囲情報をテキストで表示  
        range_text = f"Range: {start_frame} - {end_frame} (Current: {self.current_frame_id})"  
        cv2.putText(result_frame, range_text, (20, 50),   
                   cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)  
          
        return result_frame  
      
    def _display_frame_on_widget(self, frame: np.ndarray):  
        """フレームをウィジェットに表示"""  
        # 元の画像サイズを保存  
        self.original_height, self.original_width = frame.shape[:2]  
          
        # OpenCV BGR to RGB  
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  
        h, w, ch = rgb_frame.shape  
        bytes_per_line = ch * w  
          
        # QImageに変換  
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)  
          
        # ウィジェットサイズに合わせてスケール（アスペクト比を保持）  
        widget_size = self.size()  
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(  
            widget_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation  
        )  
          
        # スケール比とオフセットを計算  
        self.scale_x = self.original_width / scaled_pixmap.width()  
        self.scale_y = self.original_height / scaled_pixmap.height()  
          
        # 中央配置のためのオフセットを計算  
        self.offset_x = (widget_size.width() - scaled_pixmap.width()) // 2  
        self.offset_y = (widget_size.height() - scaled_pixmap.height()) // 2  
          
        self.setPixmap(scaled_pixmap)  
      
    def mousePressEvent(self, event):  
        """マウス押下イベント"""  
        # 複数フレームモードまたは通常のアノテーションモードの場合のみ処理  
        if (not self.annotation_mode and not self.multi_frame_mode) or event.button() != Qt.MouseButton.LeftButton:  
            return  
          
        self.drawing = True  
        self.start_point = event.position().toPoint()  
        self.current_rect = QRect()  
      
    def mouseMoveEvent(self, event):  
        """マウス移動イベント"""  
        if not self.drawing:  
            return  
          
        self.end_point = event.position().toPoint()  
        self.current_rect = QRect(self.start_point, self.end_point).normalized()  
        self.update()  
      
    def mouseReleaseEvent(self, event):  
        """マウス離上イベント"""  
        if not self.drawing or event.button() != Qt.MouseButton.LeftButton:  
            return  
          
        self.drawing = False  
        self.end_point = event.position().toPoint()  
          
        # 最終的な矩形を計算  
        rect = QRect(self.start_point, self.end_point).normalized()  
          
        # オフセットを考慮して座標を調整  
        adjusted_x1 = max(0, rect.x() - self.offset_x)  
        adjusted_y1 = max(0, rect.y() - self.offset_y)  
        adjusted_x2 = max(0, (rect.x() + rect.width()) - self.offset_x)  
        adjusted_y2 = max(0, (rect.y() + rect.height()) - self.offset_y)  
          
        # 元の画像座標系に変換  
        x1 = int(adjusted_x1 * self.scale_x)  
        y1 = int(adjusted_y1 * self.scale_y)  
        x2 = int(adjusted_x2 * self.scale_x)  
        y2 = int(adjusted_y2 * self.scale_y)  
          
        # 画像境界内にクリップ  
        x1 = max(0, min(x1, self.original_width))  
        y1 = max(0, min(y1, self.original_height))  
        x2 = max(0, min(x2, self.original_width))  
        y2 = max(0, min(y2, self.original_height))  
          
        # 有効なバウンディングボックスかチェック  
        if abs(x2 - x1) > 10 and abs(y2 - y1) > 10:  
            if self.multi_frame_mode:  
                # 複数フレームモードの場合  
                self.multi_frame_bbox_created.emit(x1, y1, x2, y2, self.current_frame_id)  
            else:  
                # 通常のアノテーションモード  
                self.bbox_created.emit(x1, y1, x2, y2)  
          
        self.current_rect = QRect()  
        self.update()
      
    def paintEvent(self, event):  
        """描画イベント"""  
        super().paintEvent(event)  
          
        if self.drawing and not self.current_rect.isEmpty():  
            painter = QPainter(self)  
            pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine)  
            painter.setPen(pen)  
            painter.drawRect(self.current_rect)

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
