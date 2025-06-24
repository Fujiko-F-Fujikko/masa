# 改善されたRangeSlider.py  
from typing import Tuple
from PyQt6.QtWidgets import QWidget  
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect  
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor  
  
class RangeSlider(QWidget):  
    """範囲選択可能なスライダーウィジェット（改善版）"""  
      
    range_changed = pyqtSignal(int, int)  # start_frame, end_frame  
    current_frame_changed = pyqtSignal(int)  # ドラッグ中のフレーム変更用シグナル  
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.setMinimumHeight(40)  
        self.setMinimumWidth(300)  
          
        self.minimum = 0  
        self.maximum = 100  
        self.start_value = 0  
        self.end_value = 100  
          
        self.dragging_start = False  
        self.dragging_end = False  
        self.dragging_range = False  
        self.drag_offset = 0  
          
        self.handle_width = 12  
        self.handle_height = 20  
        self.track_height = 6  
          
    def set_range(self, minimum: int, maximum: int):  
        """スライダーの範囲を設定"""  
        self.minimum = minimum  
        self.maximum = maximum  
        self.start_value = minimum  
        self.end_value = maximum  
        self.update()  
      
    def set_values(self, start: int, end: int):  
        """選択範囲を設定"""  
        self.start_value = max(self.minimum, min(start, self.maximum))  
        self.end_value = max(self.minimum, min(end, self.maximum))  
        if self.start_value > self.end_value:  
            self.start_value, self.end_value = self.end_value, self.start_value  
        self.update()  
        self.range_changed.emit(self.start_value, self.end_value)  
      
    def get_values(self) -> Tuple[int, int]:  
        """現在の選択範囲を取得"""  
        return (self.start_value, self.end_value)  
      
    def _value_to_pixel(self, value: int) -> int:  
        """値をピクセル位置に変換"""  
        if self.maximum == self.minimum:  
            return self.handle_width // 2  
          
        track_width = self.width() - self.handle_width  
        ratio = (value - self.minimum) / (self.maximum - self.minimum)  
        return int(self.handle_width // 2 + ratio * track_width)  
      
    def _pixel_to_value(self, pixel: int) -> int:  
        """ピクセル位置を値に変換"""  
        track_width = self.width() - self.handle_width  
        if track_width <= 0:  
            return self.minimum  
          
        ratio = (pixel - self.handle_width // 2) / track_width  
        ratio = max(0, min(1, ratio))  
        return int(self.minimum + ratio * (self.maximum - self.minimum))  
      
    def _get_start_handle_rect(self) -> QRect:  
        """開始ハンドルの矩形を取得"""  
        x = self._value_to_pixel(self.start_value) - self.handle_width // 2  
        y = (self.height() - self.handle_height) // 2  
        return QRect(x, y, self.handle_width, self.handle_height)  
      
    def _get_end_handle_rect(self) -> QRect:  
        """終了ハンドルの矩形を取得"""  
        x = self._value_to_pixel(self.end_value) - self.handle_width // 2  
        y = (self.height() - self.handle_height) // 2  
        return QRect(x, y, self.handle_width, self.handle_height)  
      
    def _get_range_rect(self) -> QRect:  
        """選択範囲の矩形を取得"""  
        start_x = self._value_to_pixel(self.start_value)  
        end_x = self._value_to_pixel(self.end_value)  
        y = (self.height() - self.track_height) // 2  
        return QRect(start_x, y, end_x - start_x, self.track_height)  
      
    def mouseMoveEvent(self, event):  
        pos = event.position().toPoint()  
          
        if self.dragging_start:  
            new_value = self._pixel_to_value(pos.x() - self.drag_offset)  
            self.start_value = max(self.minimum, min(new_value, self.end_value))  
            self.update()  
            self.range_changed.emit(self.start_value, self.end_value)  
            self.current_frame_changed.emit(self.start_value)  
              
        elif self.dragging_end:  
            new_value = self._pixel_to_value(pos.x() - self.drag_offset)  
            self.end_value = max(self.start_value, min(new_value, self.maximum))  
            self.update()  
            self.range_changed.emit(self.start_value, self.end_value)  
            self.current_frame_changed.emit(self.end_value)  
              
        elif self.dragging_range:  
            center_x = pos.x() - self.drag_offset  
            current_range = self.end_value - self.start_value  
            center_value = self._pixel_to_value(center_x)  
              
            new_start = center_value - current_range // 2  
            new_end = center_value + current_range // 2  
              
            if new_start < self.minimum:  
                new_start = self.minimum  
                new_end = new_start + current_range  
            elif new_end > self.maximum:  
                new_end = self.maximum  
                new_start = new_end - current_range  
              
            self.start_value = new_start  
            self.end_value = new_end  
            self.update()  
            self.range_changed.emit(self.start_value, self.end_value)  
            self.current_frame_changed.emit(self.start_value)  
      
    def mousePressEvent(self, event):  
        if event.button() == Qt.MouseButton.LeftButton:  
            pos = event.position().toPoint()  
              
            start_handle = self._get_start_handle_rect()  
            end_handle = self._get_end_handle_rect()  
            range_rect = self._get_range_rect()  
              
            if start_handle.contains(pos):  
                self.dragging_start = True  
                self.drag_offset = pos.x() - start_handle.center().x()  
            elif end_handle.contains(pos):  
                self.dragging_end = True  
                self.drag_offset = pos.x() - end_handle.center().x()  
            elif range_rect.contains(pos):  
                self.dragging_range = True  
                self.drag_offset = pos.x() - range_rect.center().x()  
            else:  
                value = self._pixel_to_value(pos.x())  
                  
                if abs(value - self.start_value) < abs(value - self.end_value):  
                    self.start_value = value  
                else:  
                    self.end_value = value  
                  
                if self.start_value > self.end_value:  
                    self.start_value, self.end_value = self.end_value, self.start_value  
                  
                self.update()  
                self.range_changed.emit(self.start_value, self.end_value)  
                self.current_frame_changed.emit(value)  
      
    def mouseReleaseEvent(self, event):  
        self.dragging_start = False  
        self.dragging_end = False  
        self.dragging_range = False  
          
    def paintEvent(self, event):  
        painter = QPainter(self)  
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)  
          
        track_rect = QRect(  
            self.handle_width // 2,  
            (self.height() - self.track_height) // 2,  
            self.width() - self.handle_width,  
            self.track_height  
        )  
        painter.fillRect(track_rect, QColor(200, 200, 200))  
          
        range_rect = self._get_range_rect()  
        painter.fillRect(range_rect, QColor(100, 150, 255))  
          
        start_handle = self._get_start_handle_rect()  
        end_handle = self._get_end_handle_rect()  
          
        painter.setBrush(QBrush(QColor(50, 100, 200)))  
        painter.setPen(QPen(QColor(30, 70, 150), 2))  
        painter.drawRoundedRect(start_handle, 3, 3)  
        painter.drawRoundedRect(end_handle, 3, 3)  
          
        painter.setPen(QPen(QColor(0, 0, 0)))  
        painter.drawText(10, self.height() - 5, f"Start: {self.start_value}")  
        painter.drawText(self.width() - 80, self.height() - 5, f"End: {self.end_value}")  