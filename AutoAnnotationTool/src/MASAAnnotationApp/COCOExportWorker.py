# ExportWorker.py  
from PyQt6.QtCore import QThread, pyqtSignal  
from typing import Dict  
from ExportService import ExportService  
  
class COCOExportWorker(QThread):  
    """エクスポート処理用ワーカースレッド"""  
      
    progress_updated = pyqtSignal(int, int)  # current_item, total_items  
    export_completed = pyqtSignal()  
    error_occurred = pyqtSignal(str)  
      
    def __init__(self, export_service, frame_annotations, video_path, file_path, video_manager):  
        super().__init__()  
        self.export_service = export_service  
        self.frame_annotations = frame_annotations  
        self.video_path = video_path  
        self.file_path = file_path  
        self.video_manager = video_manager  
      
    def run(self):  
        try:  
            # 進捗付きでエクスポート実行  
            self.export_service.export_coco_with_progress(  
                self.frame_annotations,  
                self.video_path,  
                self.file_path,  
                self.video_manager,  
                progress_callback=self.emit_progress  
            )  
            self.export_completed.emit()  
        except Exception as e:  
            self.error_occurred.emit(str(e))  
      
    def emit_progress(self, current, total):  
        self.progress_updated.emit(current, total)