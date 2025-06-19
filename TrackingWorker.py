from PyQt6.QtCore import QThread, pyqtSignal
from DataClass import FrameAnnotation

class TrackingWorker(QThread):  
    """自動追跡処理用ワーカースレッド"""  
      
    progress_updated = pyqtSignal(int, int)  # current_frame, total_frames  
    tracking_completed = pyqtSignal(dict)  
    error_occurred = pyqtSignal(str)  
      
    def __init__(self, video_manager, start_frame, end_frame):  
        super().__init__()  
        self.video_manager = video_manager  
        self.start_frame = start_frame  
        self.end_frame = end_frame  
      
    def run(self):  
        try:  
            results = self.process_tracking_with_progress()  
            self.tracking_completed.emit(results)  
        except Exception as e:  
            self.error_occurred.emit(str(e))
    def process_tracking_with_progress(self):  
        """進捗報告付きの追跡処理"""  
        # 初期化  
        if not self.video_manager.tracker.initialized:  
            self.video_manager.tracker.initialize()  
          
        # 手動アノテーションを取得  
        manual_objects = self.video_manager.manual_annotations[self.start_frame]  
        unique_labels = list(set([obj.label for obj in manual_objects]))  
        text_prompt = " . ".join(unique_labels) if unique_labels else None  
          
        results = {}  
        total_frames = self.end_frame - self.start_frame + 1  
          
        for i, frame_id in enumerate(range(self.start_frame, self.end_frame + 1)):  
            # 進捗を報告  
            self.progress_updated.emit(i + 1, total_frames)  
              
            frame = self.video_manager.get_frame(frame_id)  
            if frame is None:  
                continue  
              
            try:  
                tracked_annotations = self.video_manager.tracker.track_objects(  
                    frame=frame,  
                    frame_id=frame_id,  
                    initial_annotations=manual_objects if frame_id == self.start_frame else None,  
                    texts=text_prompt  
                )  
                  
                results[frame_id] = tracked_annotations  
                  
                # フレームアノテーションを更新  
                if frame_id not in self.video_manager.frame_annotations:  
                    self.video_manager.frame_annotations[frame_id] = FrameAnnotation(frame_id=frame_id)  
                  
                all_annotations = []  
                if frame_id in self.video_manager.manual_annotations:  
                    all_annotations.extend(self.video_manager.manual_annotations[frame_id])  
                all_annotations.extend(tracked_annotations)  
                  
                self.video_manager.frame_annotations[frame_id].objects = all_annotations  
                  
            except Exception as e:  
                print(f"Error tracking frame {frame_id}: {e}")  
                continue  
          
        return results
