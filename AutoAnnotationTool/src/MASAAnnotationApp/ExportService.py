# ExportService.py  
import json  
import os  
from typing import Dict, List  
from DataClass import FrameAnnotation, ObjectAnnotation  
from ErrorHandler import ErrorHandler  
  
class ExportService:  
    """アノテーションエクスポート専用クラス"""  
      
    @ErrorHandler.handle_with_dialog("Export Error")  
    def export_json(self, annotations: Dict[int, FrameAnnotation],   
                   video_path: str, output_path: str):  
        """カスタムJSON形式でエクスポート"""  
        export_data = {  
            "video_path": video_path,  
            "total_frames": len(annotations),  
            "annotations": {}  
        }  
          
        for frame_id, frame_annotation in annotations.items():  
            export_data["annotations"][str(frame_id)] = {  
                "frame_id": frame_annotation.frame_id,  
                "objects": [  
                    {  
                        "object_id": obj.object_id,  
                        "label": obj.label,  
                        "bbox": {  
                            "x1": obj.bbox.x1,  
                            "y1": obj.bbox.y1,  
                            "x2": obj.bbox.x2,  
                            "y2": obj.bbox.y2,  
                            "confidence": obj.bbox.confidence  
                        },  
                        "is_manual": obj.is_manual,  
                        "track_confidence": obj.track_confidence  
                    }  
                    for obj in frame_annotation.objects  
                ]  
            }  
          
        with open(output_path, 'w', encoding='utf-8') as f:  
            json.dump(export_data, f, indent=2, ensure_ascii=False)  
          
        print(f"Annotations exported to {output_path}")  
      
    @ErrorHandler.handle_with_dialog("Export Error")  
    def export_coco(self, annotations: Dict[int, FrameAnnotation],   
                   video_path: str, output_path: str, video_manager):  
        """COCO形式でエクスポート"""  
        coco_data = {  
            "info": {  
                "description": "MASA Auto Annotation",  
                "version": "1.0",  
                "year": 2024  
            },  
            "licenses": [],  
            "images": [],  
            "annotations": [],  
            "categories": []  
        }  
          
        # カテゴリの収集  
        all_labels = set()  
        for frame_annotation in annotations.values():  
            for obj in frame_annotation.objects:  
                all_labels.add(obj.label)  
          
        # カテゴリIDマッピング  
        label_to_id = {label: idx + 1 for idx, label in enumerate(sorted(all_labels))}  
          
        for label, cat_id in label_to_id.items():  
            coco_data["categories"].append({  
                "id": cat_id,  
                "name": label,  
                "supercategory": "object"  
            })  
          
        annotation_id = 1  
          
        # フレームごとの処理  
        for frame_id, frame_annotation in annotations.items():  
            frame = video_manager.get_frame(frame_id)  
            if frame is not None:  
                height, width = frame.shape[:2]  
                coco_data["images"].append({  
                    "id": frame_id,  
                    "width": width,  
                    "height": height,  
                    "file_name": f"frame_{frame_id:06d}.jpg"  
                })  
                  
                # アノテーション情報  
                for obj in frame_annotation.objects:  
                    bbox_width = obj.bbox.x2 - obj.bbox.x1  
                    bbox_height = obj.bbox.y2 - obj.bbox.y1  
                      
                    coco_data["annotations"].append({  
                        "id": annotation_id,  
                        "image_id": frame_id,  
                        "category_id": label_to_id[obj.label],  
                        "bbox": [obj.bbox.x1, obj.bbox.y1, bbox_width, bbox_height],  
                        "area": bbox_width * bbox_height,  
                        "iscrowd": 0,  
                        "track_id": obj.object_id  
                    })  
                    annotation_id += 1  
          
        with open(output_path, 'w', encoding='utf-8') as f:  
            json.dump(coco_data, f, indent=2)  
          
        print(f"COCO annotations exported to {output_path}")  
      
    @ErrorHandler.handle_with_dialog("Export Error")  
    def export_masa_json(self, annotations: Dict[int, FrameAnnotation],   
                        video_path: str, output_path: str):  
        """MASA形式のJSONでエクスポート"""  
        # ラベルマッピングを作成  
        all_labels = set()  
        for frame_annotation in annotations.values():  
            for obj in frame_annotation.objects:  
                all_labels.add(obj.label)  
          
        label_mapping = {str(i): label for i, label in enumerate(sorted(all_labels))}  
        label_to_id = {label: i for i, label in enumerate(sorted(all_labels))}  
          
        annotations_list = []  
        for frame_annotation in annotations.values():  
            for obj in frame_annotation.objects:  
                # xyxy形式からxywh形式に変換  
                bbox_xywh = obj.bbox.to_xywh()  
                  
                annotation_data = {  
                    "frame_id": obj.frame_id,  
                    "track_id": obj.object_id,  
                    "bbox": bbox_xywh,  
                    "score": obj.bbox.confidence,  
                    "label": label_to_id.get(obj.label, 0),  
                    "label_name": obj.label  
                }  
                  
                annotations_list.append(annotation_data)  
          
        result_data = {  
            "video_name": os.path.basename(video_path),  
            "label_mapping": label_mapping,  
            "annotations": annotations_list  
        }  
          
        with open(output_path, 'w', encoding='utf-8') as f:  
            json.dump(result_data, f, indent=2, ensure_ascii=False)  
          
        print(f"MASA JSON exported to {output_path}")  
      
    def import_json(self, json_path: str) -> Dict[int, FrameAnnotation]:  
        """JSONファイルからアノテーションを読み込み"""  
        from JSONLoader import JSONLoader  
          
        loader = JSONLoader()  
        return loader.load_json_annotations(json_path)  