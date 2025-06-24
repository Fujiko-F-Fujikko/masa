# JSONLoader.py  
import json  
from typing import Dict, List, Optional  
from DataClass import FrameAnnotation, ObjectAnnotation, BoundingBox  
from ErrorHandler import ErrorHandler  
  
class JSONLoader:  
    """JSONファイルからアノテーションを読み込むクラス"""  
  
    def __init__(self):  
        self.loaded_data: Optional[Dict] = None  
        self.video_name: Optional[str] = None  
        self.label_mapping: Optional[Dict[str, str]] = None  
  
    @ErrorHandler.handle_with_dialog("JSON Load Error")  
    def load_json_annotations(self, json_path: str) -> Dict[int, FrameAnnotation]:  
        """  
        JSONファイルからアノテーションデータを読み込み、FrameAnnotationの辞書として返す。  
        MASA形式またはカスタムJSON形式に対応。  
        """  
        with open(json_path, 'r', encoding='utf-8') as f:  
            self.loaded_data = json.load(f)  
  
        annotations_dict: Dict[int, FrameAnnotation] = {}  
  
        if "annotations" in self.loaded_data and isinstance(self.loaded_data["annotations"], list):  
            # MASA形式のJSONを想定  
            self.video_name = self.loaded_data.get("video_name")  
            self.label_mapping = self.loaded_data.get("label_mapping")  
  
            for ann_data in self.loaded_data["annotations"]:  
                frame_id = ann_data["frame_id"]  
                object_id = ann_data["track_id"]  
                bbox_data = ann_data["bbox"]  
                score = ann_data.get("score", 1.0)  
                label_id = str(ann_data["label"])  
                label_name = ann_data.get("label_name", self.label_mapping.get(label_id, "unknown"))  
  
                bbox = BoundingBox(  
                    x1=float(bbox_data[0]),  
                    y1=float(bbox_data[1]),  
                    x2=float(bbox_data[0] + bbox_data[2]),  
                    y2=float(bbox_data[1] + bbox_data[3]),  
                    confidence=float(score)  
                )  
                annotation = ObjectAnnotation(  
                    object_id=int(object_id),  
                    label=label_name,  
                    bbox=bbox,  
                    frame_id=int(frame_id),  
                    is_manual=False, # MASA形式は通常自動生成されたものと仮定  
                    track_confidence=float(score)  
                )  
  
                if frame_id not in annotations_dict:  
                    annotations_dict[frame_id] = FrameAnnotation(frame_id=frame_id, objects=[])  
                annotations_dict[frame_id].objects.append(annotation)  
  
        elif "annotations" in self.loaded_data and isinstance(self.loaded_data["annotations"], dict):  
            # カスタムJSON形式を想定  
            self.video_name = self.loaded_data.get("video_path")  
            self.label_mapping = None # カスタム形式ではラベルマッピングは通常含まれない  
  
            for frame_id_str, frame_data in self.loaded_data["annotations"].items():  
                frame_id = int(frame_id_str)  
                frame_ann = FrameAnnotation(frame_id=frame_id, objects=[])  
                  
                for obj_data in frame_data["objects"]:  
                    bbox_data = obj_data["bbox"]  
                    bbox = BoundingBox(  
                        x1=float(bbox_data["x1"]),  
                        y1=float(bbox_data["y1"]),  
                        x2=float(bbox_data["x2"]),  
                        y2=float(bbox_data["y2"]),  
                        confidence=float(bbox_data.get("confidence", 1.0))  
                    )  
                    annotation = ObjectAnnotation(  
                        object_id=int(obj_data["object_id"]),  
                        label=obj_data["label"],  
                        bbox=bbox,  
                        frame_id=int(frame_id),  
                        is_manual=obj_data.get("is_manual", False),  
                        track_confidence=obj_data.get("track_confidence", 1.0)  
                    )  
                    frame_ann.objects.append(annotation)  
                annotations_dict[frame_id] = frame_ann  
        else:  
            raise ValueError("Unsupported JSON format. 'annotations' key not found or has unexpected type.")  
  
        return annotations_dict  
  
    def get_video_name(self) -> Optional[str]:  
        """読み込んだJSONから動画名を取得"""  
        return self.video_name  
  
    def get_label_mapping(self) -> Optional[Dict[str, str]]:  
        """読み込んだJSONからラベルマッピングを取得（MASA形式の場合）"""  
        return self.label_mapping