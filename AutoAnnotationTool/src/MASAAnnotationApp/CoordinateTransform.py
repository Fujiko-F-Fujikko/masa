# CoordinateTransform.py  
from typing import Tuple  
from PyQt6.QtCore import QPoint  
  
class CoordinateTransform:  
    """座標変換を統一管理するユーティリティクラス"""  
      
    def __init__(self, scale_x: float = 1.0, scale_y: float = 1.0,   
                 offset_x: int = 0, offset_y: int = 0,   
                 image_width: int = 0, image_height: int = 0):  
        self.scale_x = scale_x  
        self.scale_y = scale_y  
        self.offset_x = offset_x  
        self.offset_y = offset_y  
        self.image_width = image_width  
        self.image_height = image_height  
      
    def update_transform(self, scale_x: float, scale_y: float,   
                        offset_x: int, offset_y: int,   
                        image_width: int, image_height: int):  
        """変換パラメータを更新"""  
        self.scale_x = scale_x  
        self.scale_y = scale_y  
        self.offset_x = offset_x  
        self.offset_y = offset_y  
        self.image_width = image_width  
        self.image_height = image_height  
      
    def widget_to_image(self, pos: QPoint) -> Tuple[int, int]:  
        """ウィジェット座標を画像座標に変換"""  
        adjusted_x = max(0, pos.x() - self.offset_x)  
        adjusted_y = max(0, pos.y() - self.offset_y)  
        image_x = int(adjusted_x * self.scale_x)  
        image_y = int(adjusted_y * self.scale_y)  
        return image_x, image_y  
      
    def image_to_widget(self, x: float, y: float) -> Tuple[int, int]:  
        """画像座標をウィジェット座標に変換"""  
        widget_x = int(x / self.scale_x + self.offset_x)  
        widget_y = int(y / self.scale_y + self.offset_y)  
        return widget_x, widget_y  
      
    def clip_to_bounds(self, x: float, y: float) -> Tuple[float, float]:  
        """座標を画像境界内にクリップ"""  
        clipped_x = max(0, min(x, self.image_width))  
        clipped_y = max(0, min(y, self.image_height))  
        return clipped_x, clipped_y  