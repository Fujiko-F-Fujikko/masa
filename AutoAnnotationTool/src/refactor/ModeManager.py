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
    """一括追加モード"""  
    def __init__(self, widget):  
        super().__init__(widget)  
        self.start_point = None  
        self.end_point = None  
      
    def handle_mouse_press(self, event: QMouseEvent):  
        if event.button() == Qt.MouseButton.LeftButton:  
            self.start_point = event.position().toPoint()  
            self.widget.bbox_editor.start_new_bbox_drawing(self.start_point)  
            self.widget.bbox_editor.selected_annotation = None  
            self.widget.bbox_editor.selection_changed.emit(None)  
            self.widget.update_frame_display()  

    def handle_mouse_move(self, event: QMouseEvent): 
        self.end_point = event.position().toPoint()  
        self.widget.bbox_editor.update_new_bbox_drawing(self.end_point)  
        self.widget.update()  
      
    def handle_mouse_release(self, event: QMouseEvent):  
        if event.button() == Qt.MouseButton.LeftButton:  
            self.end_point = event.position().toPoint()  
            self.drawing_new_bbox = False # BatchAddModeではdrawing_new_bboxフラグは不要ですが、EditModeとの整合性を保つため残します
            self.widget.bbox_editor.complete_new_bbox_drawing(  
                event.position().toPoint()  
            )  
            self.widget.setCursor(Qt.CursorShape.CrossCursor)  

            # BoundingBoxEditor::complete_new_bbox_drawingと同じ処理
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

            # ラベル入力ダイアログは出さない (削除)  
            # ここで仮のラベルを設定  
            temp_label = "batch_temp" # 仮のラベル  
  
            # ObjectAnnotationを作成し、temp_bboxes_for_batch_addに追加  
            # is_batch_added フラグを True に設定  
            annotation = ObjectAnnotation(  
                object_id=-1, # 仮のID、後で割り当てられる  
                frame_id=self.widget.current_frame_id,  
                bbox=bbox,  
                label=temp_label, # 仮のラベルを使用  
                is_manual=True, # 手動で追加されたものとして扱う  
                track_confidence=1.0,  
                is_batch_added=True # バッチ追加されたアノテーションとしてマーク  
            )  
            self.widget.parent.temp_bboxes_for_batch_add.append(  
                (self.widget.current_frame_id, annotation) # ObjectAnnotationを直接追加  
            )  
            # MASAAnnotationWidgetのtemp_bboxes_for_batch_addにも追加（追跡開始時に使用するため）  
            self.widget.add_temp_batch_annotation(annotation)

            self.widget.update_frame_display()  
            ErrorHandler.show_info_dialog(f"バウンディングボックスを追加しました。ラベル: {temp_label}", "追加完了")  

    def get_cursor_shape(self) -> Qt.CursorShape:  
        return Qt.CursorShape.CrossCursor  
  
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