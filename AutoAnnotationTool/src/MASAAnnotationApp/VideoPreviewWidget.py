import cv2
import numpy as np
from typing import Optional
from PyQt6.QtWidgets import QLabel, QSizePolicy
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor

from AnnotationVisualizer import AnnotationVisualizer
from VideoAnnotationManager import VideoAnnotationManager
from BoundingBoxEditor import BoundingBoxEditor
from DataClass import ObjectAnnotation

class VideoPreviewWidget(QLabel):  
    """統合された動画プレビューウィジェット"""  
      
    # シグナル定義  
    bbox_created = pyqtSignal(int, int, int, int)  # x1, y1, x2, y2  
    frame_changed = pyqtSignal(int)  # frame_id  
    multi_frame_bbox_created = pyqtSignal(int, int, int, int, int)  # x1, y1, x2, y2, frame_id 
    annotation_selected = pyqtSignal(object)  # ObjectAnnotation
    annotation_updated = pyqtSignal(object)  # ObjectAnnotation
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.setMinimumSize((int)(2688/2), (int)(1512/2))  
        self.setStyleSheet("border: 2px solid gray; background-color: black;")  
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        
        # サイズポリシーを設定してウィンドウサイズに追従  
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  

          
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
        self.result_view_mode = False  # 結果確認モード  

        # 表示オプション  
        self.show_manual_annotations = True  
        self.show_auto_annotations = True  
        self.show_ids = True  
        self.show_confidence = True  
        self.score_threshold = 0.2
        
        # 新しいモード追加 
        self.multi_frame_mode = False  # 複数フレームアノテーションモード  
        self.current_multi_frame_label = ""  
        self.multi_frame_annotations = []  # 現在作成中の複数フレームアノテーション  
        
        # 編集モード関連を追加  
        self.edit_mode = False  
        self.selected_annotation = None  
        
        # BoundingBoxEditor を追加  
        self.bbox_editor = BoundingBoxEditor(self)  
        self.bbox_editor.annotation_updated.connect(self.on_annotation_updated)  
        self.bbox_editor.selection_changed.connect(self.on_selection_changed)  
        # 新規描画関連のシグナルを接続  
        self.bbox_editor.new_bbox_drawing_started.connect(self._on_new_bbox_drawing_started)  
        self.bbox_editor.new_bbox_drawing_updated.connect(self._on_new_bbox_drawing_updated)  
        self.bbox_editor.new_bbox_drawing_completed.connect(self._on_new_bbox_drawing_completed)  

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

    def set_result_view_mode(self, enabled: bool):  
        """結果確認モードの設定"""  
        self.result_view_mode = enabled  
        self.annotation_mode = False  
        self.range_selection_mode = False  
        self.update_frame_display()  
      
    def set_display_options(self, show_manual: bool, show_auto: bool,   
                           show_ids: bool, show_confidence: bool, score_threshold: float = 0.2):
        """表示オプションの設定"""  
        self.show_manual_annotations = show_manual  
        self.show_auto_annotations = show_auto  
        self.show_ids = show_ids  
        self.show_confidence = show_confidence  
        self.score_threshold = score_threshold
        self.update_frame_display()  
      
    def set_frame(self, frame_id: int):  
        """指定フレームに移動"""  
        if not self.video_manager:  
            return  
          
        # 再帰防止フラグをチェック  
        if hasattr(self, '_updating_frame') and self._updating_frame:  
            return  
          
        self._updating_frame = True  
        try:  
            self.current_frame_id = max(0, min(frame_id, self.video_manager.total_frames - 1))  
            self.update_frame_display()  
            self.frame_changed.emit(self.current_frame_id)  
        finally:  
            self._updating_frame = False
    
    
    def update_frame_display(self):  
        """フレーム表示を更新"""  
        if not self.video_manager:  
            return  
          
        frame = self.video_manager.get_frame(self.current_frame_id)  
        if frame is None:  
            return  
          
        self.current_frame = frame.copy()  

        # 座標変換パラメータを BoundingBoxEditor に設定  
        self.bbox_editor.set_coordinate_transform(  
            self.scale_x, self.scale_y, self.offset_x, self.offset_y,  
            self.original_width, self.original_height  
        )  
      
        # 複数フレームモードの場合、作成中のアノテーションを表示  
        if self.multi_frame_mode and self.multi_frame_annotations:  
            frame = self._draw_multi_frame_annotations(frame)  
          
        # 結果確認モードまたは編集モードの場合、アノテーションを描画  
        if self.result_view_mode or self.edit_mode:  
            frame_annotation = self.video_manager.get_frame_annotations(self.current_frame_id)  
            if frame_annotation and frame_annotation.objects:  
                annotations_to_show = []  
                  
                for annotation in frame_annotation.objects:  
                    if annotation.bbox.confidence < self.score_threshold:  
                        continue  
                          
                    if annotation.is_manual and self.show_manual_annotations:  
                        annotations_to_show.append(annotation)  
                    elif not annotation.is_manual and self.show_auto_annotations:  
                        annotations_to_show.append(annotation)  
                  
                if annotations_to_show:  
                    frame = self.visualizer.draw_annotations(  
                        frame, annotations_to_show,  
                        show_ids=self.show_ids,  
                        show_confidence=self.show_confidence,  
                        selected_annotation=self.selected_annotation if self.edit_mode else None  
                    )
                    # 編集モードの場合、選択オーバーレイを描画  
                    if self.edit_mode:  
                        frame = self.bbox_editor.draw_selection_overlay(frame)  

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
        if self.edit_mode and event.button() == Qt.MouseButton.LeftButton:  
            pos = event.position().toPoint()  
              
            # 現在のフレームのアノテーションを取得  
            frame_annotation = self.video_manager.get_frame_annotations(self.current_frame_id)  
              
            # 表示されているアノテーションのみをフィルタリング  
            displayable_annotations = []  
            if frame_annotation and frame_annotation.objects:  
                for annotation in frame_annotation.objects:  
                    if annotation.bbox.confidence < self.score_threshold:  
                        continue  
                    if (annotation.is_manual and self.show_manual_annotations) or \
                       (not annotation.is_manual and self.show_auto_annotations):  
                        displayable_annotations.append(annotation)  
  
            # アノテーション選択を試行  
            selected = self.bbox_editor.select_annotation_at_position(pos, displayable_annotations)  
            if selected:  
                # 既存のアノテーションが選択された場合、ドラッグ操作を開始  
                operation_type = self.bbox_editor.start_drag_operation(pos)  
                if operation_type != "none":  
                    return  
            else:  
                # どのアノテーションも選択されなかった場合、新規バウンディングボックスの作成を開始  
                self.bbox_editor.start_new_bbox_drawing(pos)  
                # 既存のアノテーション選択をクリア  
                self.bbox_editor.selected_annotation = None  
                self.bbox_editor.selection_changed.emit(None) # 選択解除を通知  
                self.update_frame_display() # 表示を更新  
                return  
              
            self.update_frame_display()  
            return  
          
        # 既存のアノテーション作成モードまたはマルチフレームモードの場合の処理  
        if (not self.annotation_mode and not self.multi_frame_mode) or event.button() != Qt.MouseButton.LeftButton:  
            return  
          
        # 編集モード外での新規描画は VideoPreviewWidget が直接処理  
        self.drawing = True  
        self.start_point = event.position().toPoint()  
        self.current_rect = QRect()  
      
    def mouseMoveEvent(self, event):  
        """マウス移動イベント"""  
        if self.edit_mode:  
            pos = event.position().toPoint()  
              
            # ドラッグ操作中の場合（既存アノテーションの移動・リサイズ）  
            if self.bbox_editor.dragging_bbox or self.bbox_editor.resizing_bbox:  
                self.bbox_editor.update_drag_operation(pos)  
                self.update_frame_display()  
                return  
            # 新規バウンディングボックス描画中の場合  
            elif self.bbox_editor.drawing_new_bbox:  
                self.bbox_editor.update_new_bbox_drawing(pos)  
                self.update() # paintEvent をトリガー  
                return  
              
            # カーソル形状を更新  
            cursor = self.bbox_editor.get_cursor_for_position(pos)  
            self.setCursor(cursor)  
            return  
          
        # 編集モード外での新規描画中の場合  
        if self.drawing:  
            self.end_point = event.position().toPoint()  
            self.current_rect = QRect(self.start_point, self.end_point).normalized()  
            self.update()  
            return  
          
        if not self.drawing:  
            return  
  
    def mouseReleaseEvent(self, event):  
        """マウス離上イベント"""  
        if self.edit_mode:  
            if self.bbox_editor.dragging_bbox or self.bbox_editor.resizing_bbox:  
                # 編集モードでの既存アノテーションの移動・リサイズ操作完了  
                self.bbox_editor.end_drag_operation()  
                self.setCursor(Qt.CursorShape.PointingHandCursor)  
                return  
            elif self.bbox_editor.drawing_new_bbox:  
                # 編集モードでの新規バウンディングボックス描画完了  
                self.bbox_editor.complete_new_bbox_drawing(event.position().toPoint())  
                self.setCursor(Qt.CursorShape.PointingHandCursor)  
                return  
          
        # 編集モード外での新規描画完了  
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
                self.multi_frame_bbox_created.emit(x1, y1, x2, y2, self.current_frame_id)  
            else:  
                self.bbox_created.emit(x1, y1, x2, y2) # 編集モード外での新規作成  
          
        self.current_rect = QRect()  
        self.update()  
  
    def paintEvent(self, event):  
        """描画イベント"""  
        super().paintEvent(event)  
        painter = QPainter(self)  
          
        # BoundingBoxEditor に新規描画中の矩形を描画させる  
        self.bbox_editor.draw_new_bbox_overlay(painter)  
  
        # 編集モード外での新規描画中の矩形を描画  
        if self.drawing and not self.current_rect.isEmpty():  
            pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine)  
            painter.setPen(pen)  
            painter.drawRect(self.current_rect)  

    # 編集モード設定メソッドを追加  
    def set_edit_mode(self, enabled: bool):  
        """編集モードの設定"""  
        self.edit_mode = enabled  
        self.annotation_mode = False  
        self.range_selection_mode = False  
        self.result_view_mode = enabled  
          
        # 編集モードがOFFになる場合、選択中のアノテーションをクリア  
        if not enabled:  
            self.bbox_editor.selected_annotation = None  
            self.bbox_editor.selection_changed.emit(None) # 選択解除を通知  
          
        # BoundingBoxEditor の編集モードを設定  
        self.bbox_editor.set_editing_mode(enabled)  
          
        # 視覚的フィードバック  
        if enabled:  
            self.setCursor(Qt.CursorShape.PointingHandCursor)  
            self.setStyleSheet("border: 3px solid #FFD700; background-color: black;")  
        else:  
            self.setCursor(Qt.CursorShape.ArrowCursor)  
            self.setStyleSheet("border: 2px solid gray; background-color: black;")  
          
        self.update_frame_display()

    def on_annotation_updated(self, annotation):  
        """アノテーション更新時の処理"""  
        # フレーム表示を更新  
        self.update_frame_display()  
          
        # 親ウィジェットに更新を通知  
        if hasattr(self, 'annotation_updated'):  
            self.annotation_updated.emit(annotation)  
      
    def on_selection_changed(self, annotation):  
        """選択変更時の処理"""  
        # 親ウィジェットに選択変更を通知  
        if hasattr(self, 'annotation_selected'):  
            self.annotation_selected.emit(annotation)

    def resizeEvent(self, event):  
        """ウィンドウサイズ変更時の処理"""  
        super().resizeEvent(event)  
          
        # フレーム表示を更新（スケール比とオフセットの再計算）  
        if self.current_frame is not None:  
            self.update_frame_display()  

    # BoundingBoxEditor からのシグナルを受け取るスロット  
    def _on_new_bbox_drawing_started(self):  
        self.setCursor(Qt.CursorShape.CrossCursor)  
  
    def _on_new_bbox_drawing_updated(self, x1, y1, x2, y2):  
        # VideoPreviewWidget は描画を BoundingBoxEditor に委譲するため、ここでは何もしない  
        pass  
  
    def _on_new_bbox_drawing_completed(self, x1, y1, x2, y2):  
        # MASAAnnotationWidget に通知  
        self.bbox_created.emit(x1, y1, x2, y2)  
        self.setCursor(Qt.CursorShape.PointingHandCursor) # 編集モードのデフォルトカーソルに戻す