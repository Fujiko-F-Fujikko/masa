# DataClass.py
import torch  
from dataclasses import dataclass  
from typing import List, Optional  
  
@dataclass  
class BoundingBox:  
    """バウンディングボックスのデータクラス（バリデーション付き）"""  
    x1: float  
    y1: float  
    x2: float  
    y2: float  
    confidence: float = 1.0  
      
    def __post_init__(self):  
        """初期化後のバリデーション"""  
        self.validate()  
      
    def validate(self):  
        """座標の妥当性をチェック"""  
        if self.x1 >= self.x2:  
            raise ValueError(f"Invalid x coordinates: x1({self.x1}) >= x2({self.x2})")  
        if self.y1 >= self.y2:  
            raise ValueError(f"Invalid y coordinates: y1({self.y1}) >= y2({self.y2})")  
        if not (0.0 <= self.confidence <= 1.0):  
            raise ValueError(f"Invalid confidence: {self.confidence}")  
        if any(coord < 0 for coord in [self.x1, self.y1, self.x2, self.y2]):  
            raise ValueError("Coordinates cannot be negative")  
      
    def to_xyxy(self) -> List[float]:  
        return [self.x1, self.y1, self.x2, self.y2]  
      
    def to_xywh(self) -> List[float]:  
        """xywh形式で返す"""  
        return [self.x1, self.y1, self.x2 - self.x1, self.y2 - self.y1]  
      
    def area(self) -> float:  
        return (self.x2 - self.x1) * (self.y2 - self.y1)  
      
    def center(self) -> tuple:  
        """中心座標を返す"""  
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)  
  
@dataclass  
class ObjectAnnotation:  
    """物体アノテーションのデータクラス"""  
    def __init__(self, object_id: int, label: str, bbox: BoundingBox, frame_id: int,  
                 is_manual: bool, track_confidence: float,  
                 is_batch_added: bool = False):  
        self.object_id = object_id  
        self.label = label  
        self.bbox = bbox  
        self.frame_id = frame_id  
        self.is_manual = is_manual  
        self.track_confidence = track_confidence  
        self.is_batch_added = is_batch_added  
        self.validate()  
      
    def __post_init__(self):  
        """初期化後のバリデーション"""  
        self.validate()  
      
    def validate(self):  
        """アノテーションの妥当性をチェック"""  
        # object_idは-1も来得る
        #if self.object_id < 0:  
        #    raise ValueError(f"Invalid object_id: {self.object_id}")  
        if not self.label or not self.label.strip():  
            raise ValueError("Label cannot be empty")  
        if self.frame_id < 0:  
            raise ValueError(f"Invalid frame_id: {self.frame_id}")  
        if not (0.0 <= self.track_confidence <= 1.0):  
            raise ValueError(f"Invalid track_confidence: {self.track_confidence}")  
        # BoundingBoxのバリデーションは__post_init__で自動実行される  
  
@dataclass  
class FrameAnnotation:  
    """フレームアノテーションのデータクラス（バリデーション付き）"""  
    frame_id: int  
    frame_path: Optional[str] = None  
    objects: List[ObjectAnnotation] = None  
      
    def __post_init__(self):  
        if self.objects is None:  
            self.objects = []  
        self.validate()  
      
    def validate(self):  
        """フレームアノテーションの妥当性をチェック"""  
        if self.frame_id < 0:  
            raise ValueError(f"Invalid frame_id: {self.frame_id}")  
          
        # 全オブジェクトのframe_idが一致することを確認  
        for obj in self.objects:  
            if obj.frame_id != self.frame_id:  
                raise ValueError(f"Object frame_id {obj.frame_id} doesn't match frame {self.frame_id}")  
  
class MASAConfig:  
    """MASA設定クラス（改善版）"""  
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
        self.custom_entities = True  
      
    def validate(self):  
        """設定の妥当性をチェック"""  
        if not (0.0 <= self.score_threshold <= 1.0):  
            raise ValueError(f"Invalid score_threshold: {self.score_threshold}")  
        if self.detector_type not in ["mmdet"]:  
            raise ValueError(f"Unsupported detector_type: {self.detector_type}")  
        if self.sam_type not in ["vit_h", "vit_l", "vit_b"]:  
            raise ValueError(f"Unsupported sam_type: {self.sam_type}")

@dataclass  
class DisplayConfig:  
    """UIの表示設定を管理するデータクラス"""  
    show_manual_annotations: bool = True  
    show_auto_annotations: bool = True  
    show_ids: bool = True  
    show_confidence: bool = True  
    score_threshold: float = 0.2 # 表示フィルタリング用の閾値