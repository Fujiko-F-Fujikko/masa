import json  
import os  
from typing import Dict, List, Optional  
from DataClass import ObjectAnnotation, FrameAnnotation, BoundingBox  
  
class JSONLoader:  
    """MASA JSON形式のアノテーションファイルを読み込むクラス"""  
      
    def __init__(self):  
        self.loaded_data = None  
        self.video_name = None  
        self.label_mapping = {}  
          
    def load_json_annotations(self, json_path: str) -> Dict[int, FrameAnnotation]:  
        """JSONファイルからアノテーションを読み込み"""  
        try:  
            with open(json_path, 'r', encoding='utf-8') as f:  
                self.loaded_data = json.load(f)  
              
            self.video_name = self.loaded_data.get('video_name', '')  
            self.label_mapping = self.loaded_data.get('label_mapping', {})  
              
            frame_annotations = {}  
              
            for annotation_data in self.loaded_data.get('annotations', []):  
                frame_id = annotation_data['frame_id']  
                  
                # xywh形式からxyxy形式に変換  
                bbox_xywh = annotation_data['bbox']  
                bbox = BoundingBox(  
                    x1=bbox_xywh[0],  
                    y1=bbox_xywh[1],   
                    x2=bbox_xywh[0] + bbox_xywh[2],  
                    y2=bbox_xywh[1] + bbox_xywh[3],  
                    confidence=annotation_data.get('score', 1.0)  
                )  
                  
                object_annotation = ObjectAnnotation(  
                    object_id=annotation_data['track_id'],  
                    label=annotation_data.get('label_name', f"class_{annotation_data['label']}"),  
                    bbox=bbox,  
                    frame_id=frame_id,  
                    is_manual=False,  # JSONから読み込んだものは自動追跡結果として扱う  
                    track_confidence=annotation_data.get('score', 1.0)  
                )  
                  
                if frame_id not in frame_annotations:  
                    frame_annotations[frame_id] = FrameAnnotation(frame_id=frame_id)  
                  
                frame_annotations[frame_id].objects.append(object_annotation)  
              
            return frame_annotations  
              
        except Exception as e:  
            print(f"Error loading JSON file: {e}")  
            return {}  
      
    def get_video_name(self) -> str:  
        """読み込んだ動画名を取得"""  
        return self.video_name  
      
    def get_label_mapping(self) -> Dict:  
        """ラベルマッピングを取得"""  
        return self.label_mapping