from PyQt6.QtWidgets import QApplication
import sys
from MASAAnnotationWidget import MASAAnnotationWidget

# メインアプリケーション実行用のクラス
class MASAAnnotationApp(QApplication):  
    """MASAアノテーションアプリケーション"""  
      
    def __init__(self, argv):  
        super().__init__(argv)  
        self.main_widget = MASAAnnotationWidget()  
        self.main_widget.show()  
  
def run_gui_application():  
    """GUI版のアプリケーションを実行"""  
    app = MASAAnnotationApp(sys.argv)  
    sys.exit(app.exec())  
  
if __name__ == "__main__":  
    run_gui_application()
