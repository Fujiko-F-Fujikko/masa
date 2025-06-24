import torch  
import numpy as np  
from dataclasses import dataclass  
from typing import List, Optional


@dataclass  
class BoundingBox:  
    """バウンディングボックスのデータクラス"""  
    x1: float  
    y1: float  
    x2: float  
    y2: float  
    confidence: float = 1.0  
      
    def to_xyxy(self) -> List[float]:  
        return [self.x1, self.y1, self.x2, self.y2]  
      
    def area(self) -> float:  
        return (self.x2 - self.x1) * (self.y2 - self.y1)  
  
@dataclass  
class ObjectAnnotation:  
    """物体アノテーションのデータクラス"""  
    object_id: int  
    label: str  
    bbox: BoundingBox  
    frame_id: int  
    is_manual: bool = False  
    track_confidence: float = 1.0  
  
@dataclass  
class FrameAnnotation:  
    """フレームアノテーションのデータクラス"""  
    frame_id: int  
    frame_path: Optional[str] = None  
    objects: List[ObjectAnnotation] = None  
      
    def __post_init__(self):  
        if self.objects is None:  
            self.objects = []  
  
class MASAConfig:  
    """MASA設定クラス"""  
    def __init__(self):  
        # デモコードの設定を参考に初期化  
        self.masa_config_path = "configs/masa-gdino/masa_gdino_swinb_inference.py"  
        self.masa_checkpoint_path = "saved_models/masa_models/gdino_masa.pth"  
        self.det_config_path = None  
        self.det_checkpoint_path = None  
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"  
        self.score_threshold = 0.2  
        self.unified_mode = True  
        self.detector_type = "mmdet"  
        self.fp16 = False  
        self.sam_mask = False  
        self.sam_path = "saved_models/pretrain_weights/sam_vit_h_4b8939.pth"  
        self.sam_type = "vit_h"  
        self.custom_entities = True  # カスタムエンティティを有効化
  

