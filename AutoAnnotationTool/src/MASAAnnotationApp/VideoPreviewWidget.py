import cv2
import numpy as np
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor

from AnnotationVisualizer import AnnotationVisualizer
from VideoAnnotationManager import VideoAnnotationManager

class VideoPreviewWidget(QLabel):  
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