# MASAAnnotationApp.py  
import sys  
import argparse  
from PyQt6.QtWidgets import QApplication  
from MASAAnnotationWidget import MASAAnnotationWidget  
from ErrorHandler import ErrorHandler  
  
class MASAAnnotationApp(QApplication):  
    """MASAアノテーションアプリケーション（改善版）"""  
      
    def __init__(self, argv):  
        super().__init__(argv)  
          
        ErrorHandler.setup_logging() # ロギングを初期化  
          
        self.args = self.parse_args(argv)  
          
        self.main_widget = MASAAnnotationWidget()  
          
        # 引数で指定されたファイルを読み込み  
        if self.args.video:  
            self.main_widget.load_video(self.args.video)  
              
        if self.args.json and self.args.video:  
            self.main_widget.load_json_annotations(self.args.json)  
          
        self.main_widget.show()  
      
    def parse_args(self, argv):  
        """引数を解析"""  
        parser = argparse.ArgumentParser(description='MASA Annotation Tool')  
        parser.add_argument('--video', type=str, help='Video file path')  
        parser.add_argument('--json', type=str, help='JSON annotation file path')  
          
        return parser.parse_args(argv[1:])  
  
def run_gui_application():  
    """GUI版のアプリケーションを実行"""  
    app = MASAAnnotationApp(sys.argv)  
    sys.exit(app.exec())  
  
if __name__ == "__main__":  
    run_gui_application()