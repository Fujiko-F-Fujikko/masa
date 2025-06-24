import cv2  
import numpy as np  
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QObject  
from PyQt6.QtGui import QPainter, QPen, QColor  
from typing import Optional, Tuple  
from DataClass import ObjectAnnotation, BoundingBox  
  
class BoundingBoxEditor(QObject):  
    """バウンディングボックス編集機能を提供するクラス"""  
      
    # シグナル定義  
    annotation_updated = pyqtSignal(object)  # ObjectAnnotation  
    selection_changed = pyqtSignal(object)   # ObjectAnnotation or None  
    new_bbox_drawing_started = pyqtSignal()  
    new_bbox_drawing_updated = pyqtSignal(int, int, int, int) # x1, y1, x2, y2  
    new_bbox_drawing_completed = pyqtSignal(int, int, int, int) # x1, y1, x2, y2 
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
          
        # 編集状態  
        self.selected_annotation = None  
        self.is_editing = False  
          
        # ドラッグ・リサイズ状態  
        self.dragging_bbox = False  
        self.resizing_bbox = False  
        self.resize_handle = None  # 'top-left', 'top-right', 'bottom-left', 'bottom-right'  
        self.drag_start_pos = QPoint()  
        self.original_bbox = None  
          
        # 表示設定  
        self.handle_size = 24  
        self.selection_color = (255, 255, 0)  # 黄色  
        self.handle_color = (255, 255, 255)   # 白色  
        self.handle_border_color = (0, 0, 0)  # 黒色  
          
        # 座標変換パラメータ（親ウィジェットから設定）  
        self.scale_x = 1.0  
        self.scale_y = 1.0  
        self.offset_x = 0  
        self.offset_y = 0  
        self.image_width = 0  
        self.image_height = 0  

        # 新規描画関連を追加  
        self.drawing_new_bbox = False  
        self.new_bbox_start_point = QPoint()  
        self.new_bbox_current_rect = QRect()  
      
    def set_coordinate_transform(self, scale_x: float, scale_y: float,   
                               offset_x: int, offset_y: int,   
                               image_width: int, image_height: int):  
        """座標変換パラメータを設定"""  
        self.scale_x = scale_x  
        self.scale_y = scale_y  
        self.offset_x = offset_x  
        self.offset_y = offset_y  
        self.image_width = image_width  
        self.image_height = image_height  
      
    def set_editing_mode(self, enabled: bool):  
        """編集モードの設定"""  
        self.is_editing = enabled  
        if not enabled:  
            self.selected_annotation = None  
            self.dragging_bbox = False  
            self.resizing_bbox = False  
            self.resize_handle = None  
      
    def select_annotation_at_position(self, pos: QPoint, annotations: list) -> Optional[ObjectAnnotation]:  
        """指定位置のアノテーションを選択（リサイズハンドル領域も考慮）"""  
        if not self.is_editing:  
            return None  
          
        # ウィジェット座標を画像座標に変換  
        image_x, image_y = self._widget_to_image_coords(pos)  
          
        # 既に選択されているアノテーションがある場合、リサイズハンドル領域もチェック  
        if self.selected_annotation:  
            # リサイズハンドル領域内かチェック  
            if self._get_resize_handle_at_position(pos):  
                # ハンドル領域内の場合は現在の選択を維持  
                return self.selected_annotation  
              
            # バウンディングボックス内かチェック  
            if (self.selected_annotation.bbox.x1 <= image_x <= self.selected_annotation.bbox.x2 and  
                self.selected_annotation.bbox.y1 <= image_y <= self.selected_annotation.bbox.y2):  
                return self.selected_annotation  
          
        # 他のアノテーションを検索  
        for annotation in annotations:  
            if (annotation.bbox.x1 <= image_x <= annotation.bbox.x2 and  
                annotation.bbox.y1 <= image_y <= annotation.bbox.y2):  
                self.selected_annotation = annotation  
                self.selection_changed.emit(annotation)  
                return annotation  
          
        # 空の場所をクリック → 選択解除  
        self.selected_annotation = None  
        self.selection_changed.emit(None)  
        return None
    
    def start_drag_operation(self, pos: QPoint) -> str:  
        """ドラッグ操作を開始（戻り値：操作タイプ）"""  
        if not self.selected_annotation:  
            return "none"  
          
        # リサイズハンドルをチェック  
        resize_handle = self._get_resize_handle_at_position(pos)  
        if resize_handle:  
            self.resizing_bbox = True  
            self.resize_handle = resize_handle  
            self.drag_start_pos = pos  
            self._save_original_bbox()  
            return "resize"  
          
        # バウンディングボックス内をチェック  
        image_x, image_y = self._widget_to_image_coords(pos)  
        if (self.selected_annotation.bbox.x1 <= image_x <= self.selected_annotation.bbox.x2 and  
            self.selected_annotation.bbox.y1 <= image_y <= self.selected_annotation.bbox.y2):  
            self.dragging_bbox = True  
            self.drag_start_pos = pos  
            self._save_original_bbox()  
            return "move"  
          
        return "none"  
      
    def update_drag_operation(self, pos: QPoint):  
        """ドラッグ操作を更新"""  
        if self.resizing_bbox:  
            self._resize_bbox(pos)  
        elif self.dragging_bbox:  
            self._move_bbox(pos)  
      
    def end_drag_operation(self):  
        """ドラッグ操作を終了"""  
        if (self.dragging_bbox or self.resizing_bbox) and self.selected_annotation:  
            self.annotation_updated.emit(self.selected_annotation)  
          
        self.dragging_bbox = False  
        self.resizing_bbox = False  
        self.resize_handle = None  
      
    def get_cursor_for_position(self, pos: QPoint) -> Qt.CursorShape:  
        """位置に応じた適切なカーソルを取得"""  
        if not self.selected_annotation:  
            return Qt.CursorShape.ArrowCursor  
          
        # リサイズハンドル上かチェック  
        if self._get_resize_handle_at_position(pos):  
            return Qt.CursorShape.SizeFDiagCursor  
          
        # バウンディングボックス内かチェック  
        image_x, image_y = self._widget_to_image_coords(pos)  
        if (self.selected_annotation.bbox.x1 <= image_x <= self.selected_annotation.bbox.x2 and  
            self.selected_annotation.bbox.y1 <= image_y <= self.selected_annotation.bbox.y2):  
            return Qt.CursorShape.OpenHandCursor if not self.dragging_bbox else Qt.CursorShape.ClosedHandCursor  
          
        return Qt.CursorShape.PointingHandCursor  
      
    def draw_selection_overlay(self, frame: np.ndarray) -> np.ndarray:  
        """選択されたアノテーションのオーバーレイを描画"""  
        if not self.selected_annotation or not self.is_editing:  
            return frame  
          
        result_frame = frame.copy()  
          
        # 選択されたバウンディングボックスを強調表示  
        x1, y1 = int(self.selected_annotation.bbox.x1), int(self.selected_annotation.bbox.y1)  
        x2, y2 = int(self.selected_annotation.bbox.x2), int(self.selected_annotation.bbox.y2)  
          
        # 選択枠を描画  
        cv2.rectangle(result_frame, (x1, y1), (x2, y2), self.selection_color, 3)  
          
        # リサイズハンドルを描画  
        handles = {  
            'top-left': (x1, y1),  
            'top-right': (x2, y1),  
            'bottom-left': (x1, y2),  
            'bottom-right': (x2, y2)  
        }  
          
        for handle_name, (hx, hy) in handles.items():  
            # ハンドル本体（白）  
            cv2.rectangle(  
                result_frame,  
                (hx - self.handle_size//2, hy - self.handle_size//2),  
                (hx + self.handle_size//2, hy + self.handle_size//2),  
                self.handle_color,  
                -1  
            )  
            # ハンドル境界線（黒）  
            cv2.rectangle(  
                result_frame,  
                (hx - self.handle_size//2, hy - self.handle_size//2),  
                (hx + self.handle_size//2, hy + self.handle_size//2),  
                self.handle_border_color,  
                1  
            )  
          
        return result_frame  
      
    def _widget_to_image_coords(self, pos: QPoint) -> Tuple[int, int]:  
        """ウィジェット座標を画像座標に変換"""  
        adjusted_x = max(0, pos.x() - self.offset_x)  
        adjusted_y = max(0, pos.y() - self.offset_y)  
        image_x = int(adjusted_x * self.scale_x)  
        image_y = int(adjusted_y * self.scale_y)  
        return image_x, image_y  
      
    def _get_resize_handle_at_position(self, pos: QPoint) -> Optional[str]:  
        """指定位置にあるリサイズハンドルを取得（拡張判定領域対応）"""  
        if not self.selected_annotation:  
            return None  
          
        image_x, image_y = self._widget_to_image_coords(pos)  
          
        # 拡張判定領域のサイズ（ハンドルサイズの1.5倍程度）  
        extended_handle_size = int(self.handle_size * 1.5)  
          
        handles = {  
            'top-left': (self.selected_annotation.bbox.x1, self.selected_annotation.bbox.y1),  
            'top-right': (self.selected_annotation.bbox.x2, self.selected_annotation.bbox.y1),  
            'bottom-left': (self.selected_annotation.bbox.x1, self.selected_annotation.bbox.y2),  
            'bottom-right': (self.selected_annotation.bbox.x2, self.selected_annotation.bbox.y2)  
        }  
          
        for handle_name, (hx, hy) in handles.items():  
            # 拡張された判定領域でチェック  
            if (abs(image_x - hx) <= extended_handle_size and   
                abs(image_y - hy) <= extended_handle_size):  
                return handle_name  
          
        return None
    
    def _save_original_bbox(self):  
        """元のバウンディングボックスを保存"""  
        if self.selected_annotation:  
            self.original_bbox = BoundingBox(  
                self.selected_annotation.bbox.x1,  
                self.selected_annotation.bbox.y1,  
                self.selected_annotation.bbox.x2,  
                self.selected_annotation.bbox.y2,  
                self.selected_annotation.bbox.confidence  
            )  
      
    def _move_bbox(self, current_pos: QPoint):  
        """バウンディングボックスを移動"""  
        if not self.selected_annotation or not self.original_bbox:  
            return  
          
        # 移動量を計算  
        delta_x = (current_pos.x() - self.drag_start_pos.x()) * self.scale_x  
        delta_y = (current_pos.y() - self.drag_start_pos.y()) * self.scale_y  
          
        # 新しい座標を計算  
        bbox_width = self.original_bbox.x2 - self.original_bbox.x1  
        bbox_height = self.original_bbox.y2 - self.original_bbox.y1  
          
        new_x1 = self.original_bbox.x1 + delta_x  
        new_y1 = self.original_bbox.y1 + delta_y  
        new_x2 = new_x1 + bbox_width  
        new_y2 = new_y1 + bbox_height  
          
        # 画像境界内にクリップ  
        if new_x1 < 0:  
            new_x1 = 0  
            new_x2 = bbox_width  
        elif new_x2 > self.image_width:  
            new_x2 = self.image_width  
            new_x1 = new_x2 - bbox_width  
          
        if new_y1 < 0:  
            new_y1 = 0  
            new_y2 = bbox_height  
        elif new_y2 > self.image_height:  
            new_y2 = self.image_height  
            new_y1 = new_y2 - bbox_height  
          
        # バウンディングボックスを更新  
        self.selected_annotation.bbox.x1 = new_x1  
        self.selected_annotation.bbox.y1 = new_y1  
        self.selected_annotation.bbox.x2 = new_x2  
        self.selected_annotation.bbox.y2 = new_y2  
      
    def _resize_bbox(self, current_pos: QPoint):  
        """バウンディングボックスをリサイズ"""  
        if not self.selected_annotation or not self.original_bbox or not self.resize_handle:  
            return  
          
        # 移動量を計算  
        delta_x = (current_pos.x() - self.drag_start_pos.x()) * self.scale_x  
        delta_y = (current_pos.y() - self.drag_start_pos.y()) * self.scale_y  
          
        # ハンドルに応じてリサイズ  
        new_x1, new_y1 = self.original_bbox.x1, self.original_bbox.y1  
        new_x2, new_y2 = self.original_bbox.x2, self.original_bbox.y2  
          
        if self.resize_handle == 'top-left':  
            new_x1 += delta_x  
            new_y1 += delta_y  
        elif self.resize_handle == 'top-right':  
            new_x2 += delta_x  
            new_y1 += delta_y  
        elif self.resize_handle == 'bottom-left':  
            new_x1 += delta_x  
            new_y2 += delta_y  
        elif self.resize_handle == 'bottom-right':  
            new_x2 += delta_x  
            new_y2 += delta_y  
          
        # 最小サイズと境界チェック  
        min_size = 10  
        new_x1 = max(0, min(new_x1, new_x2 - min_size))  
        new_y1 = max(0, min(new_y1, new_y2 - min_size))  
        new_x2 = min(self.image_width, max(new_x2, new_x1 + min_size))  
        new_y2 = min(self.image_height, max(new_y2, new_y1 + min_size))  
          
        # バウンディングボックスを更新  
        self.selected_annotation.bbox.x1 = new_x1  
        self.selected_annotation.bbox.y1 = new_y1  
        self.selected_annotation.bbox.x2 = new_x2
        self.selected_annotation.bbox.y2 = new_y2

    def start_new_bbox_drawing(self, pos: QPoint):  
        """新規バウンディングボックスの描画を開始"""  
        self.drawing_new_bbox = True  
        self.new_bbox_start_point = pos  
        self.new_bbox_current_rect = QRect()  
        self.new_bbox_drawing_started.emit()  
  
    def update_new_bbox_drawing(self, pos: QPoint):  
        """新規バウンディングボックスの描画を更新"""  
        if self.drawing_new_bbox:  
            self.new_bbox_current_rect = QRect(self.new_bbox_start_point, pos).normalized()  
            # ウィジェット座標を画像座標に変換してシグナルを発信  
            x1, y1 = self._widget_to_image_coords(self.new_bbox_current_rect.topLeft())  
            x2, y2 = self._widget_to_image_coords(self.new_bbox_current_rect.bottomRight())  
            self.new_bbox_drawing_updated.emit(x1, y1, x2, y2)  
  
    def complete_new_bbox_drawing(self, pos: QPoint):  
        """新規バウンディングボックスの描画を完了"""  
        if self.drawing_new_bbox:  
            self.drawing_new_bbox = False  
            final_rect = QRect(self.new_bbox_start_point, pos).normalized()  
              
            # ウィジェット座標を画像座標に変換  
            x1, y1 = self._widget_to_image_coords(final_rect.topLeft())  
            x2, y2 = self._widget_to_image_coords(final_rect.bottomRight())  
  
            # 画像境界内にクリップ  
            x1 = max(0, min(x1, self.image_width))  
            y1 = max(0, min(y1, self.image_height))  
            x2 = max(0, min(x2, self.image_width))  
            y2 = max(0, min(y2, self.image_height))  
  
            # 有効なバウンディングボックスかチェック  
            if abs(x2 - x1) > 10 and abs(y2 - y1) > 10:  
                self.new_bbox_drawing_completed.emit(x1, y1, x2, y2)  
              
            self.new_bbox_current_rect = QRect() # クリア  
  
    def draw_new_bbox_overlay(self, painter: QPainter):  
        """新規描画中のバウンディングボックスをオーバーレイとして描画"""  
        if self.drawing_new_bbox and not self.new_bbox_current_rect.isEmpty():  
            pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine)  
            painter.setPen(pen)  
            painter.drawRect(self.new_bbox_current_rect)