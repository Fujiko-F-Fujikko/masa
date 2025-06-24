# TrackingWorker.py  
from PyQt6.QtCore import QThread, pyqtSignal  
from typing import List, Tuple, Optional, Dict  
import numpy as np  
import torch  
from DataClass import ObjectAnnotation, BoundingBox  
from ObjectTracker import ObjectTracker  
from AnnotationRepository import AnnotationRepository  
from ErrorHandler import ErrorHandler  
  
class TrackingWorker(QThread):  
    """自動追跡処理用ワーカースレッド（改善版）"""  
      
    progress_updated = pyqtSignal(int, int)  # current_frame, total_frames  
    tracking_completed = pyqtSignal(dict)  # {frame_id: [ObjectAnnotation, ...]}  
    error_occurred = pyqtSignal(str)  
      
    def __init__(self, video_manager, annotation_repository: AnnotationRepository,  
                 object_tracker: ObjectTracker,  
                 start_frame: int, end_frame: int,  
                 initial_annotations: List[Tuple[int, BoundingBox]],  
                 assigned_track_id: int,  
                 assigned_label: str,  
                 parent=None):  
        super().__init__(parent)  
        self.video_manager = video_manager  
        self.annotation_repository = annotation_repository  
        self.object_tracker = object_tracker  
        self.start_frame = start_frame  
        self.end_frame = end_frame  
        self.initial_annotations = initial_annotations  
        self.assigned_track_id = assigned_track_id  
        self.assigned_label = assigned_label  
        self.max_used_track_id = assigned_track_id # 追跡中に使用された最大IDを記録  
          
    @ErrorHandler.handle_with_dialog("Tracking Worker Error")  
    def run(self):  
        try:  
            self.object_tracker.initialize()  
            tracked_annotations_by_frame = self.process_tracking_with_progress()  
            self.tracking_completed.emit(tracked_annotations_by_frame)  
        except Exception as e:  
            self.error_occurred.emit(str(e))  
            ErrorHandler.log_error(e, "TrackingWorker.run")  
      
    def process_tracking_with_progress(self) -> Dict[int, List[ObjectAnnotation]]:  
        """進捗報告付きの追跡処理"""  
        results = {}  
        total_frames = self.end_frame - self.start_frame + 1  
          
        text_prompt = self.assigned_label  
          
        initial_object_annotations_map = {}  
        for frame_id, bbox in self.initial_annotations:  
            if frame_id not in initial_object_annotations_map:  
                initial_object_annotations_map[frame_id] = []  
            initial_object_annotations_map[frame_id].append(  
                ObjectAnnotation(  
                    object_id=-1, # MASAモデルが新しいトラックとして扱うように-1を設定  
                    frame_id=frame_id,  
                    bbox=bbox,  
                    label=self.assigned_label,  
                    is_manual=True,  
                    track_confidence=1.0  
                )  
            )  
          
        for i, frame_id in enumerate(range(self.start_frame, self.end_frame + 1)):  
            self.progress_updated.emit(i + 1, total_frames)  
              
            frame_image = self.video_manager.get_frame(frame_id)  
            if frame_image is None:  
                ErrorHandler.show_warning_dialog(f"Frame {frame_id} could not be read. Skipping.", "Frame Read Warning")  
                continue  
              
            try:  
                current_frame_initial_annotations = initial_object_annotations_map.get(frame_id, [])  
                  
                tracked_annotations = self.object_tracker.track_objects(  
                    frame=frame_image,  
                    frame_id=frame_id,  
                    initial_annotations=current_frame_initial_annotations,  
                    texts=text_prompt  
                )  
                  
                final_annotations_for_frame = []  
                for ann in tracked_annotations:  
                    # MASAモデルが生成したIDに基準IDを加算してオフセット  
                    # 新規ID (-1) の場合は、assigned_track_idをそのまま使用  
                    if ann.object_id == -1:  
                        ann.object_id = self.assigned_track_id  
                    else:  
                        ann.object_id = ann.object_id + self.assigned_track_id  
                      
                    self.max_used_track_id = max(self.max_used_track_id, ann.object_id)  
                    ann.label = self.assigned_label # ラベルを上書き  
                    ann.is_manual = False # 自動追跡結果としてマーク  
                    final_annotations_for_frame.append(ann)  
                  
                results[frame_id] = final_annotations_for_frame  
                  
            except Exception as e:  
                ErrorHandler.log_error(e, f"Tracking frame {frame_id}")  
                self.error_occurred.emit(f"Error tracking frame {frame_id}: {e}")  
                continue  
        return results