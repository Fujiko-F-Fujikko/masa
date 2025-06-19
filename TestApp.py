from PyQt6.QtWidgets import QApplication
import sys
from UnifiedMASAAnnotationWidget import FinalEnhancedMASAAnnotationWidget

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
