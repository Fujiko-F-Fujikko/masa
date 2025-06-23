from PyQt6.QtCore import QThread, pyqtSignal  
from typing import List, Tuple, Optional  
import numpy as np  
import torch  
from DataClass import MASAConfig, ObjectAnnotation, BoundingBox, FrameAnnotation  
from ObjectTracker import ObjectTracker  
  
class TrackingWorker(QThread):  
    """自動追跡処理用ワーカースレッド"""  
  
    progress_updated = pyqtSignal(int, int)  # current_frame, total_frames  
    tracking_completed = pyqtSignal(dict)  # {frame_id: [ObjectAnnotation, ...]}  
    error_occurred = pyqtSignal(str)  
  
    def __init__(self, video_manager, start_frame: int, end_frame: int,  
                 initial_annotations: List[Tuple[int, BoundingBox]],  
                 assigned_track_id: int, # assigned_track_idを受け取る  
                 assigned_label: str,  
                 parent=None):  
        super().__init__(parent)  
        self.video_manager = video_manager  
        self.start_frame = start_frame  
        self.end_frame = end_frame  
        self.initial_annotations = initial_annotations # (frame_id, BoundingBox)のリスト  
        self.assigned_track_id = assigned_track_id # assigned_track_idを保持  
        self.assigned_label = assigned_label  
        self.object_tracker = ObjectTracker(self.video_manager.config)  
  
    def run(self):  
        try:  
            self.object_tracker.initialize()  
            tracked_annotations_by_frame = self.process_tracking_with_progress()  
            self.tracking_completed.emit(tracked_annotations_by_frame)  
        except Exception as e:  
            self.error_occurred.emit(str(e))  
  
    def process_tracking_with_progress(self) -> dict:  
        """進捗報告付きの追跡処理"""  
        print("assign_track_id:", self.assigned_track_id)  # デバッグ用
        results = {}  
        total_frames = self.end_frame - self.start_frame + 1  
        max_used_id = self.assigned_track_id  

        text_prompt = self.assigned_label  

        initial_object_annotations_map = {}  
        for frame_id, bbox in self.initial_annotations:  
            if frame_id not in initial_object_annotations_map:  
                initial_object_annotations_map[frame_id] = []  
            initial_object_annotations_map[frame_id].append(  
                ObjectAnnotation(  
                    object_id= -1, # MASAモデルが新しいトラックとして扱うように-1を設定  
                    frame_id=frame_id,  
                    bbox=bbox,  
                    label=self.assigned_label,  
                    is_manual=True,  
                    confidence=1.0  
                )  
            )  

        for i, frame_id in enumerate(range(self.start_frame, self.end_frame + 1)):  
            self.progress_updated.emit(i + 1, total_frames)  

            frame_image = self.video_manager.get_frame(frame_id)  
            if frame_image is None:  
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
                # MASAモデルが生成したTrack IDをそのまま利用し、ラベルのみ上書き  
                # ここでMASAモデルが生成したIDを上書きする。  
                for ann in tracked_annotations:  
                    # MASAモデルが生成したIDに基準IDを加算してオフセット  
                    ann.object_id = ann.object_id + self.assigned_track_id  
                    max_used_id = max(max_used_id, ann.object_id)
                    ann.label = self.assigned_label  
                    final_annotations_for_frame.append(ann)  
                  
                # 最大使用IDを記録  
                self.max_used_track_id = max_used_id  

                results[frame_id] = final_annotations_for_frame  

            except Exception as e:  
                print(f"Error tracking frame {frame_id}: {e}")  
                self.error_occurred.emit(f"Error tracking frame {frame_id}: {e}")  
                continue  
        return results