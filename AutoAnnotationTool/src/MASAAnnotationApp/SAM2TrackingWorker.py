# TrackingWorker.py (SAM2版)    
from typing import List, Tuple, Dict    
import torch    
import numpy as np    
import os  
import sys  
  
from PyQt6.QtCore import QThread, pyqtSignal    
  
# SAM2関連のインポート    
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "sam2"))    
from sam2.build_sam import build_sam2_video_predictor    
    
from DataClass import ObjectAnnotation, BoundingBox    
from AnnotationRepository import AnnotationRepository    
from ErrorHandler import ErrorHandler    
    
class SAM2TrackingWorker(QThread):    
    """SAM2を使用した自動追跡処理用ワーカースレッド"""    
        
    progress_updated = pyqtSignal(int, int)  # current_frame, total_frames    
    tracking_completed = pyqtSignal(dict)  # {frame_id: [ObjectAnnotation, ...]}    
    error_occurred = pyqtSignal(str)    
        
    def __init__(self, video_manager, annotation_repository: AnnotationRepository,    
                 start_frame: int, end_frame: int,    
                 initial_annotations: List[Tuple[int, BoundingBox]],    
                 assigned_track_id: int,    
                 assigned_label: str,    
                 video_width: int, video_height: int,    
                 parent=None):    
        super().__init__(parent)    
        self.video_manager = video_manager    
        self.annotation_repository = annotation_repository    
        self.start_frame = start_frame    
        self.end_frame = end_frame    
        self.initial_annotations = initial_annotations    
        self.assigned_track_id = assigned_track_id    
        self.assigned_label = assigned_label    
        self.max_used_track_id = assigned_track_id    
        self.video_width = video_width    
        self.video_height = video_height    
            
        # SAM2設定    
        #self.model_cfg = os.path.abspath("sam2/sam2/configs/samurai/sam2.1_hiera_l.yaml")  # SAMURAI mode = True
        self.model_cfg = os.path.abspath("sam2/sam2/configs/sam2.1/sam2.1_hiera_l.yaml")  # SAMURAI mode = False
        self.model_ckpt = os.path.abspath("sam2/checkpoints/sam2.1_hiera_large.pt")  
        self.device = "cuda" if torch.cuda.is_available() else "cpu"  
  
    @ErrorHandler.handle_with_dialog("Tracking Worker Error")    
    def run(self):    
        try:    
            tracked_annotations_by_frame = self.process_tracking_with_progress()    
            self.tracking_completed.emit(tracked_annotations_by_frame)  
            print(f"Tracking completed for frames {self.start_frame} to {self.end_frame}")  
            print(f"Total tracked frames: {len(tracked_annotations_by_frame)}")  
            for frame_id, annotations in tracked_annotations_by_frame.items():
              print(f"Frame {frame_id} has {len(annotations)} annotations")
              for annotation in annotations:
                  print(f"--- {annotation.bbox}")
        except Exception as e:    
            self.error_occurred.emit(str(e))    
            ErrorHandler.log_error(e, "TrackingWorker.run")    
        
    def process_tracking_with_progress(self) -> Dict[int, List[ObjectAnnotation]]:    
        """SAM2を使用した進捗報告付きの追跡処理"""    
        results = {}    
        total_frames = self.end_frame - self.start_frame + 1    
            
        # SAM2予測器の初期化    
        print(f"self.model_cfg: {self.model_cfg}")  
        print(f"self.model_ckpt: {self.model_ckpt}")  
        print(f"self.device: {self.device}")  
        predictor = build_sam2_video_predictor(    
            self.model_cfg,     
            self.model_ckpt,     
            device=self.device    
        )    
            
        # 動画パスを取得    
        video_path = self.video_manager.video_path    
        absolute_video_path = os.path.abspath(video_path)  
        print(f"Absolute video path: {absolute_video_path}")  
            
        with torch.inference_mode(), torch.autocast(self.device, dtype=torch.float16):    
            # 動画の初期化    
            state = predictor.init_state(    
                absolute_video_path,     
                offload_video_to_cpu=True,     
                offload_state_to_cpu=True    
            )    
                
            # start_frameの初期アノテーションのみを使用  
            start_frame_annotations = [  
                (frame_id, bbox) for frame_id, bbox in self.initial_annotations   
                if frame_id == self.start_frame  
            ]  
              
            if not start_frame_annotations:  
                raise ValueError(f"No initial annotation found for start_frame {self.start_frame}.\n Please provide at least one annotation for the starting frame.")  
              
            # 初期フレームでバウンディングボックスを設定  
            frame_id, init_bbox = start_frame_annotations[0]  # 最初のアノテーションのみ使用              
            sam2_bbox = [
                init_bbox.x1, 
                init_bbox.y1, 
                init_bbox.x2, 
                init_bbox.y2
            ]

            frame_idx, object_ids, masks = predictor.add_new_points_or_box(  
                state,  
                box=sam2_bbox,  
                frame_idx=self.start_frame,  # start_frameで初期化  
                obj_id=self.assigned_track_id  
            )  
                
            # 区間指定での追跡実行    
            frame_count = self.end_frame - self.start_frame + 1    
            processed_frames = 0    
                
            for frame_idx, object_ids, masks in predictor.propagate_in_video(    
                state,    
                start_frame_idx=self.start_frame,  # 直接start_frameから開始  
                max_frame_num_to_track=frame_count,  # 必要なフレーム数のみ  
                reverse=False    
            ):    
                processed_frames += 1    
                self.progress_updated.emit(processed_frames, total_frames)    
                    
                # フレームが範囲外の場合はスキップ（念のため）  
                if frame_idx < self.start_frame or frame_idx > self.end_frame:    
                    continue    
                    
                try:    
                    frame_annotations = []    
                        
                    # マスクからバウンディングボックスを計算  
                    for obj_id, mask in zip(object_ids, masks):  
                        if mask is not None:  
                            # ロジット値なので、正の値（物体部分）があるかチェック  
                            positive_mask = mask > 0.0  
                            if positive_mask.sum() > 0:  # 正の値があるかどうかをチェック  
                                bbox = self._mask_to_bbox(mask)  
                                if bbox is not None:  
                                    annotation = ObjectAnnotation(  
                                        object_id=self.assigned_track_id,  
                                        frame_id=frame_idx,  
                                        bbox=bbox,  
                                        label=self.assigned_label,  
                                        is_manual=True,  
                                        track_confidence=1.0  
                                    )  
                                    frame_annotations.append(annotation)
                        
                    results[frame_idx] = frame_annotations    
                        
                except Exception as e:    
                    ErrorHandler.log_error(e, f"Tracking frame {frame_idx}")    
                    self.error_occurred.emit(f"Error tracking frame {frame_idx}: {e}")    
                    continue    
            
        return results    
        
    def _mask_to_bbox(self, mask: torch.Tensor) -> BoundingBox:  
        """マスクからバウンディングボックスを計算"""  
        try:  
            # マスクをnumpy配列に変換  
            if isinstance(mask, torch.Tensor):  
                mask_np = mask.cpu().numpy()  
            else:  
                mask_np = mask  
              
            # 最初の次元が1の場合は除去（[1, H, W] -> [H, W]）  
            if mask_np.ndim == 3 and mask_np.shape[0] == 1:  
                mask_np = mask_np[0]  
              
            # ロジット値を二値化（0.0を閾値として使用）  
            binary_mask = mask_np > 0.0  
              
            # マスクから座標を取得  
            coords = np.where(binary_mask)  
            if len(coords[0]) == 0:  
                return None  
              
            y_min, y_max = coords[0].min(), coords[0].max()  
            x_min, x_max = coords[1].min(), coords[1].max()  
              
            # ピクセル座標のままBoundingBoxを作成（正規化しない）  
            return BoundingBox(  
                float(x_min),   
                float(y_min),   
                float(x_max),   
                float(y_max),   
                confidence=1.0  
            )  
              
        except Exception as e:  
            ErrorHandler.log_error(e, "mask_to_bbox conversion")  
            return None
