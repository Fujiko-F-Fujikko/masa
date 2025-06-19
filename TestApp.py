from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,   
                            QLabel, QSlider, QFileDialog, QInputDialog,   
                            QMessageBox, QFrame, QLineEdit, QComboBox,   
                            QCheckBox, QTextEdit, QSpinBox, QDialog,   
                            QFormLayout, QDialogButtonBox, QSplitter,  
                            QListWidget, QListWidgetItem, QGroupBox,  
                            QProgressBar, QApplication)  
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QPoint, QThread  
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont, QBrush  
import sys  


import cv2  
import numpy as np  
import sys  
from typing import List, Dict, Optional, Tuple
from pathlib import Path  
import json  

from DataClass import (BoundingBox, ObjectAnnotation, FrameAnnotation, ObjectTracker, MASAConfig)




# メインアプリケーション実行用のクラス（改善版）  
class EnhancedMASAAnnotationApp(QApplication):  
    """改善されたMASAアノテーションアプリケーション"""  
      
    def __init__(self, argv):  
        super().__init__(argv)  
        self.main_widget = FinalEnhancedMASAAnnotationWidget()  
        self.main_widget.show()  
  
def run_enhanced_gui_application():  
    """改善されたGUI版のアプリケーションを実行"""  
    app = EnhancedMASAAnnotationApp(sys.argv)  
    sys.exit(app.exec())  
  

  
if __name__ == "__main__":  
    run_enhanced_gui_application()  