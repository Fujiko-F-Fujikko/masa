# TrackingWorker.py  
from PyQt6.QtCore import QThread, pyqtSignal  
from typing import List, Tuple, Optional, Dict  
import numpy as np  
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
                 video_width: int, video_height: int,
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
        self.video_width = video_width  
        self.video_height = video_height  
          
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
        """進捗報告付きの追跡処理（単一物体版）"""  
        results = {}  
        total_frames = self.end_frame - self.start_frame + 1  
          
        text_prompt = self.assigned_label  
          
        # 単一物体なので、すべての初期アノテーションに統一されたIDを付与  
        initial_object_annotations_map = {}  
        for frame_id, bbox in self.initial_annotations:  
            if frame_id not in initial_object_annotations_map:  
                initial_object_annotations_map[frame_id] = []  
              
            initial_object_annotations_map[frame_id].append(  
                ObjectAnnotation(  
                    object_id=self.assigned_track_id,  # 統一されたIDを使用  
                    frame_id=frame_id,  
                    bbox=self.normalize_bbox_coords(bbox.x1, bbox.y1, bbox.x2, bbox.y2),  
                    label=self.assigned_label,  
                    is_manual=True,  
                    track_confidence=1.0  
                )  
            )  
          
        # 前フレームの追跡結果を保持  
        previous_frame_annotations = []  
          
        for i, frame_id in enumerate(range(self.start_frame, self.end_frame + 1)):  
            self.progress_updated.emit(i + 1, total_frames)  
              
            frame_image = self.video_manager.get_frame(frame_id)  
            if frame_image is None:  
                ErrorHandler.show_warning_dialog(f"Frame {frame_id} could not be read. Skipping.", "Frame Read Warning")  
                continue  
              
            try:  
                # 現在フレームの初期アノテーションを取得  
                current_frame_initial_annotations = initial_object_annotations_map.get(frame_id, [])  
                  
                # 前フレームの結果がある場合は、それを優先的に使用  
                # これにより物体の連続性が保たれる  
                if previous_frame_annotations:  
                    current_frame_initial_annotations = previous_frame_annotations  
                  
                tracked_annotations = self.object_tracker.track_objects(  
                    frame=frame_image,  
                    frame_id=frame_id,  
                    initial_annotations=current_frame_initial_annotations,  
                    texts=text_prompt  
                )  
                  
                final_annotations_for_frame = []  
                for ann in tracked_annotations:  
                    # 単一物体なので、IDは常に統一  
                    ann.object_id = ann.object_id + self.assigned_track_id  
                    ann.label = self.assigned_label  
                    ann.is_manual = True  
                    final_annotations_for_frame.append(ann)  
                  
                results[frame_id] = final_annotations_for_frame  
                  
                # 次フレームのために現在の結果を保存  
                previous_frame_annotations = final_annotations_for_frame.copy()  
                  
            except Exception as e:  
                ErrorHandler.log_error(e, f"Tracking frame {frame_id}")  
                self.error_occurred.emit(f"Error tracking frame {frame_id}: {e}")  
                continue  
                  
        return results

    def normalize_bbox_coords(self, x1: int, y1: int, x2: int, y2: int) -> BoundingBox:  
        """  
        ピクセル座標を0.0-1.0の範囲に正規化し、BoundingBoxオブジェクトとして返す。  
        """  
        if self.video_width == 0 or self.video_height == 0:  
            # エラーハンドリングまたはデフォルト値の提供  
            return BoundingBox(0.0, 0.0, 0.0, 0.0)  
  
        # 0.0-1.0の範囲に正規化  
        norm_x1 = x1 / self.video_width  
        norm_y1 = y1 / self.video_height  
        norm_x2 = x2 / self.video_width  
        norm_y2 = y2 / self.video_height  
          
        # 妥当な範囲にクランプ  
        norm_x1 = max(0.0, min(1.0, norm_x1))  
        norm_y1 = max(0.0, min(1.0, norm_y1))  
        norm_x2 = max(0.0, min(1.0, norm_x2))  
        norm_y2 = max(0.0, min(1.0, norm_y2))  
          
        return BoundingBox(norm_x1, norm_y1, norm_x2, norm_y2)  