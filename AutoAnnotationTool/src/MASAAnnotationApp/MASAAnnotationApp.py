from PyQt6.QtWidgets import QApplication  
import sys  
import argparse  
from MASAAnnotationWidget import MASAAnnotationWidget  
  
class MASAAnnotationApp(QApplication):    
    """MASAアノテーションアプリケーション"""    
        
    def __init__(self, argv):    
        super().__init__(argv)    
          
        # 引数解析  
        self.args = self.parse_args(argv)  
          
        self.main_widget = MASAAnnotationWidget()  
          
        # 引数で指定されたファイルを読み込み  
        if self.args.video:  
            self.main_widget.load_video_from_path(self.args.video)  
              
        if self.args.json and self.args.video:  
            self.main_widget.load_json_from_path(self.args.json)  
          
        self.main_widget.show()  
      
    def parse_args(self, argv):  
        """引数を解析"""  
        parser = argparse.ArgumentParser(description='MASA Annotation Tool')  
        parser.add_argument('--video', type=str, help='Video file path')  
        parser.add_argument('--json', type=str, help='JSON annotation file path')  
          
        # sys.argvの最初の要素（スクリプト名）を除いて解析  
        return parser.parse_args(argv[1:])
      
def run_gui_application():  
    """GUI版のアプリケーションを実行"""  
    app = MASAAnnotationApp(sys.argv)  
    sys.exit(app.exec())  
  
if __name__ == "__main__":  
    run_gui_application()