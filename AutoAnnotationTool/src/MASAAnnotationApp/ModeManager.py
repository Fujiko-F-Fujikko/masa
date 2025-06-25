# ModeManager.py  
from abc import ABC, abstractmethod  
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QMouseEvent

from DataClass import ObjectAnnotation
from ErrorHandler import ErrorHandler
from BoundingBoxEditor import BoundingBox
  
class AnnotationMode(ABC):  
    """アノテーションモードの抽象基底クラス"""  
      
    def __init__(self, widget):  
        self.widget = widget  
      
    @abstractmethod  
    def handle_mouse_press(self, event: QMouseEvent):  
        """マウス押下イベントの処理"""  
        pass  
      
    @abstractmethod  
    def handle_mouse_move(self, event: QMouseEvent):  
        """マウス移動イベントの処理"""  
        pass  
      
    @abstractmethod  
    def handle_mouse_release(self, event: QMouseEvent):  
        """マウス離上イベントの処理"""  
        pass  
      
    @abstractmethod  
    def get_cursor_shape(self) -> Qt.CursorShape:  
        """カーソル形状を取得"""  
        pass  
      
    def enter_mode(self):  
        """モード開始時の処理"""  
        self.widget.setCursor(self.get_cursor_shape())  
      
    def exit_mode(self):  
        """モード終了時の処理"""  
        self.widget.setCursor(Qt.CursorShape.ArrowCursor)  
  
class ViewMode(AnnotationMode):  
    """表示専用モード"""  
      
    def handle_mouse_press(self, event: QMouseEvent):  
        pass  
      
    def handle_mouse_move(self, event: QMouseEvent):  
        pass  
      
    def handle_mouse_release(self, event: QMouseEvent):  
        pass  
      
    def get_cursor_shape(self) -> Qt.CursorShape:  
        return Qt.CursorShape.ArrowCursor  
  
class EditMode(AnnotationMode):  
    """編集モード"""  
      
    def handle_mouse_press(self, event: QMouseEvent):  
        if event.button() == Qt.MouseButton.LeftButton:  
            pos = event.position().toPoint()  
              
            # 現在のフレームのアノテーションを取得    
            frame_annotation = self.widget.annotation_repository.get_annotations(
                self.widget.current_frame_id     
            )
            # 表示されているアノテーションのみをフィルタリング  
            displayable_annotations = self._get_displayable_annotations(frame_annotation)  
              
            # アノテーション選択を試行  
            selected = self.widget.bbox_editor.select_annotation_at_position(  
                pos, displayable_annotations  
            )  
              
            if selected:  
                operation_type = self.widget.bbox_editor.start_drag_operation(pos)  
                if operation_type != "none":  
                    return  
            else:  
                # 新規バウンディングボックスの作成を開始  
                self.widget.bbox_editor.start_new_bbox_drawing(pos)  
                self.widget.bbox_editor.selected_annotation = None  
                self.widget.bbox_editor.selection_changed.emit(None)  
                self.widget.update_frame_display()  
      
    def handle_mouse_move(self, event: QMouseEvent):  
        pos = event.position().toPoint()  
          
        # ドラッグ操作中の場合  
        if (self.widget.bbox_editor.dragging_bbox or   
            self.widget.bbox_editor.resizing_bbox):  
            self.widget.bbox_editor.update_drag_operation(pos)  
            self.widget.update_frame_display()  
            return  
          
        # 新規バウンディングボックス描画中の場合  
        elif self.widget.bbox_editor.drawing_new_bbox:  
            self.widget.bbox_editor.update_new_bbox_drawing(pos)  
            self.widget.update()  
            return  
          
        # カーソル形状を更新  
        cursor = self.widget.bbox_editor.get_cursor_for_position(pos)  
        self.widget.setCursor(cursor)  
      
    def handle_mouse_release(self, event: QMouseEvent):  
        if event.button() == Qt.MouseButton.LeftButton:  
            if (self.widget.bbox_editor.dragging_bbox or   
                self.widget.bbox_editor.resizing_bbox):  
                self.widget.bbox_editor.end_drag_operation()  
                self.widget.setCursor(Qt.CursorShape.PointingHandCursor)  
            elif self.widget.bbox_editor.drawing_new_bbox:  
                self.widget.bbox_editor.complete_new_bbox_drawing(  
                    event.position().toPoint()  
                )  
                self.widget.setCursor(Qt.CursorShape.PointingHandCursor)  
      
    def get_cursor_shape(self) -> Qt.CursorShape:  
        return Qt.CursorShape.CrossCursor  
      
    def _get_displayable_annotations(self, frame_annotation):  
        """表示可能なアノテーションをフィルタリング"""  
        displayable_annotations = []  
        if frame_annotation and frame_annotation.objects:  
            for annotation in frame_annotation.objects:  
                if annotation.bbox.confidence < self.widget.score_threshold:  
                    continue  
                if ((annotation.is_manual and self.widget.show_manual_annotations) or  
                    (not annotation.is_manual and self.widget.show_auto_annotations)):  
                    displayable_annotations.append(annotation)  
        return displayable_annotations  
  
class BatchAddMode(AnnotationMode):  
    """一括追加モード（既存アノテーションの編集機能付き）"""  
    def __init__(self, widget):  
        super().__init__(widget)  
        self.start_point = None  
        self.end_point = None  
      
    def handle_mouse_press(self, event: QMouseEvent):  
        if event.button() == Qt.MouseButton.LeftButton:  
            pos = event.position().toPoint()  
              
            # BatchAddMode中は一時的なバッチアノテーションのみを選択対象とする  
            current_mode = self.widget.mode_manager.current_mode_name  
              
            if current_mode == 'batch_add':  
                # BatchAddMode: 一時的なバッチアノテーションのみを対象  
                temp_annotations = [  
                    ann for ann in self.widget.temp_batch_annotations   
                    if ann.frame_id == self.widget.current_frame_id  
                ]  
                  
                # アノテーション選択を試行（一時アノテーションのみ）  
                selected = self.widget.bbox_editor.select_annotation_at_position(  
                    pos, temp_annotations  
                )  
                  
                if selected:  
                    operation_type = self.widget.bbox_editor.start_drag_operation(pos)  
                    if operation_type != "none":  
                        return  
                else:  
                    # 新規バウンディングボックスの作成を開始  
                    self.start_point = pos  
                    self.widget.bbox_editor.start_new_bbox_drawing(self.start_point)  
                    self.widget.bbox_editor.selected_annotation = None  
                    self.widget.bbox_editor.selection_changed.emit(None)  
                    self.widget.update_frame_display()
  
    def handle_mouse_move(self, event: QMouseEvent):  
        pos = event.position().toPoint()  
          
        # ドラッグ操作中の場合  
        if (self.widget.bbox_editor.dragging_bbox or   
            self.widget.bbox_editor.resizing_bbox):  
            self.widget.bbox_editor.update_drag_operation(pos)  
            self.widget.update_frame_display()  
            return  
          
        # 新規バウンディングボックス描画中の場合  
        elif self.widget.bbox_editor.drawing_new_bbox:  
            self.end_point = pos  
            self.widget.bbox_editor.update_new_bbox_drawing(self.end_point)  
            self.widget.update()  
            return  
          
        # カーソル形状を更新  
        cursor = self.widget.bbox_editor.get_cursor_for_position(pos)  
        self.widget.setCursor(cursor)  
  
    def handle_mouse_release(self, event: QMouseEvent):  
        if event.button() == Qt.MouseButton.LeftButton:  
            # ドラッグ・リサイズ操作の終了  
            if (self.widget.bbox_editor.dragging_bbox or   
                self.widget.bbox_editor.resizing_bbox):  
                self.widget.bbox_editor.end_drag_operation()  
                self.widget.setCursor(Qt.CursorShape.CrossCursor)  
                return  
              
            # 新規バウンディングボックス作成の完了  
            elif self.widget.bbox_editor.drawing_new_bbox:  
                self.end_point = event.position().toPoint()  
                self.widget.bbox_editor.complete_new_bbox_drawing(  
                    event.position().toPoint()  
                )  
                self.widget.setCursor(Qt.CursorShape.CrossCursor)  
  
                # 新規アノテーション作成処理  
                final_rect = QRect(self.start_point, event.position().toPoint()).normalized()  
                  
                # ウィジェット座標を画像座標に変換  
                x1, y1 = self.widget.coordinate_transform.widget_to_image(final_rect.topLeft())  
                x2, y2 = self.widget.coordinate_transform.widget_to_image(final_rect.bottomRight())  
                  
                # 画像境界内にクリップ  
                x1, y1 = self.widget.coordinate_transform.clip_to_bounds(x1, y1)  
                x2, y2 = self.widget.coordinate_transform.clip_to_bounds(x2, y2)  
  
                # 有効なバウンディングボックスかチェック  
                if abs(x2 - x1) <= 10 or abs(y2 - y1) <= 10:  
                    return  # バウンディングボックスが小さすぎる場合は無視  
                  
                bbox = BoundingBox(x1, y1, x2, y2)  
  
                # 仮のラベルを設定  
                temp_label = "batch_temp"  
                # 仮のTrack IDを設定(-1, -2, -3...)
                temp_object_id = -(len(self.widget.temp_batch_annotations) + 1)
  
                # ObjectAnnotationを作成し、temp_bboxes_for_batch_addに追加  
                annotation = ObjectAnnotation(  
                    object_id=temp_object_id,  # 仮のID、後で割り当てられる  
                    frame_id=self.widget.current_frame_id,  
                    bbox=bbox,  
                    label=temp_label,  # 仮のラベルを使用  
                    is_manual=True,  # 手動で追加されたものとして扱う  
                    track_confidence=1.0,  
                    is_batch_added=True  # バッチ追加されたアノテーションとしてマーク  
                )  
                self.widget.parent_ma_widget.temp_bboxes_for_batch_add.append(  
                    (self.widget.current_frame_id, annotation)  
                )  
                # MASAAnnotationWidgetのtemp_bboxes_for_batch_addにも追加  
                self.widget.add_temp_batch_annotation(annotation)  
  
                self.widget.update_frame_display()  
  
    def get_cursor_shape(self) -> Qt.CursorShape:  
        return Qt.CursorShape.CrossCursor  
      
    def _get_displayable_annotations(self, frame_annotation):  
        """表示可能なアノテーションをフィルタリング"""  
        displayable_annotations = []  
        if frame_annotation and frame_annotation.objects:  
            for annotation in frame_annotation.objects:  
                if annotation.bbox.confidence < self.widget.score_threshold:  
                    continue  
                if ((annotation.is_manual and self.widget.show_manual_annotations) or  
                    (not annotation.is_manual and self.widget.show_auto_annotations)):  
                    displayable_annotations.append(annotation)  
        return displayable_annotations
  
class ModeManager:  
    """現在のアノテーションモードを管理し、マウスイベントを適切なモードに委譲するクラス"""  

    def __init__(self, video_preview_widget):  
        self.video_preview_widget = video_preview_widget  
        self.modes = {  
            'view': ViewMode(video_preview_widget),  
            'edit': EditMode(video_preview_widget),  
            'batch_add': BatchAddMode(video_preview_widget)  
        }  
        self._current_mode_name = 'view' # 初期モード名  
        self.current_mode = self.modes[self._current_mode_name]  
  
    def set_mode(self, mode_name: str):  
        if mode_name in self.modes:  
            self._current_mode_name = mode_name  
            self.current_mode = self.modes[mode_name]  
            self.current_mode.enter_mode()  

        else:  
            raise ValueError(f"Unknown mode: {mode_name}")  
  
    @property  
    def current_mode_name(self) -> str:  
        return self._current_mode_name  
    
    def handle_mouse_event(self, event_type: str, event: QMouseEvent):  
        """マウスイベントを現在のモードに委譲"""  
        if not self.current_mode:  
            return  
          
        if event_type == 'press':  
            self.current_mode.handle_mouse_press(event)  
        elif event_type == 'move':  
            self.current_mode.handle_mouse_move(event)  
        elif event_type == 'release':  
            self.current_mode.handle_mouse_release(event)  
      
    def get_cursor_shape(self) -> Qt.CursorShape:  
        """現在のモードのカーソル形状を取得"""  
        if self.current_mode:  
            return self.current_mode.get_cursor_shape()  
        return Qt.CursorShape.ArrowCursor  