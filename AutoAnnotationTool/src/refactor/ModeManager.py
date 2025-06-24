# ModeManager.py  
from abc import ABC, abstractmethod  
from PyQt6.QtCore import Qt, QObject, pyqtSignal  
from PyQt6.QtGui import QMouseEvent  
from typing import Optional  
  
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
        return Qt.CursorShape.PointingHandCursor  
      
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
    """一括追加モード"""  
      
    def handle_mouse_press(self, event: QMouseEvent):  
        if event.button() == Qt.MouseButton.LeftButton:  
            pos = event.position().toPoint()  
            self.widget.bbox_editor.start_new_bbox_drawing(pos)  
            self.widget.bbox_editor.selected_annotation = None  
            self.widget.bbox_editor.selection_changed.emit(None)  
            self.widget.update_frame_display()  
      
    def handle_mouse_move(self, event: QMouseEvent):  
        pos = event.position().toPoint()  
        self.widget.bbox_editor.update_new_bbox_drawing(pos)  
        self.widget.update()  
      
    def handle_mouse_release(self, event: QMouseEvent):  
        if event.button() == Qt.MouseButton.LeftButton:  
            self.widget.bbox_editor.complete_new_bbox_drawing(  
                event.position().toPoint()  
            )  
            self.widget.setCursor(Qt.CursorShape.CrossCursor)  
      
    def get_cursor_shape(self) -> Qt.CursorShape:  
        return Qt.CursorShape.CrossCursor  
  
class ModeManager(QObject):  
    """モード管理クラス"""  
      
    mode_changed = pyqtSignal(str)  # モード名  
      
    def __init__(self, widget):  
        super().__init__()  
        self.widget = widget  
        self.current_mode: Optional[AnnotationMode] = None  
        self.modes = {  
            'view': ViewMode(widget),  
            'edit': EditMode(widget),  
            'batch_add': BatchAddMode(widget)  
        }  
      
    def set_mode(self, mode_type: str):  
        """モードを設定"""  
        if mode_type not in self.modes:  
            raise ValueError(f"Unknown mode: {mode_type}")  
          
        # 現在のモードを終了  
        if self.current_mode:  
            self.current_mode.exit_mode()  
          
        # 新しいモードを開始  
        self.current_mode = self.modes[mode_type]  
        self.current_mode.enter_mode()  
        self.mode_changed.emit(mode_type)  
      
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