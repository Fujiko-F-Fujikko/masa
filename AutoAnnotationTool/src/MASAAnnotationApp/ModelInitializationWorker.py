from PyQt6.QtCore import QThread, pyqtSignal  

from ObjectTracker import ObjectTracker
  
class ModelInitializationWorker(QThread):  
    """MASAモデル初期化用のワーカー"""  
      
    initialization_completed = pyqtSignal(object)  # ObjectTrackerを返す  
    initialization_failed = pyqtSignal(str)  # エラーメッセージ  
      
    def __init__(self, config_manager):  
        super().__init__()  
        self.config_manager = config_manager  
      
    def run(self):  
        try: 
            object_tracker = ObjectTracker(  
                self.config_manager.get_full_config(config_type="masa")  
            )  
            object_tracker.initialize()  # MASAモデルの初期化を実行
            self.initialization_completed.emit(object_tracker)  
        except Exception as e:  
            self.initialization_failed.emit(str(e))