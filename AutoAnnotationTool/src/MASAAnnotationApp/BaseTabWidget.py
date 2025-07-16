# BaseTabWidget.py  
from typing import Optional  
from PyQt6.QtWidgets import QWidget  
from PyQt6.QtCore import pyqtSignal  
from ConfigManager import ConfigManager  
  
class BaseTabWidget(QWidget):  
    """タブウィジェットの基底クラス"""  
      
    def __init__(self, config_manager: ConfigManager, parent=None):  
        super().__init__(parent)  
        self.config_manager = config_manager  
        self.annotation_repository = None  
        self.setup_ui()  
          
    def setup_ui(self):  
        """サブクラスで実装"""  
        raise NotImplementedError  
          
    def set_annotation_repository(self, repository):  
        """AnnotationRepositoryの参照を設定"""  
        self.annotation_repository = repository