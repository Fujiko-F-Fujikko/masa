# ExportService.py  
import json  
import os  
from datetime import datetime
from typing import Dict
from DataClass import FrameAnnotation  
from ErrorHandler import ErrorHandler  
  
class ExportService:  
    """アノテーションエクスポート専用クラス"""  
      
    @ErrorHandler.handle_with_dialog("Export Error")  
    def export_coco_with_progress(self, frame_annotations, video_path, file_path, video_manager, progress_callback=None):  
        """進捗付きCOCO JSONエクスポート"""  
        # COCO形式の基本構造を初期化  
        coco_data = {  
            "info": {  
                "description": "MASA Video Annotation Export",  
                "version": "1.0",  
                "year": datetime.now().year,  
                "contributor": "MASA Annotation Tool",  
                "date_created": datetime.now().isoformat()  
            },  
            "licenses": [],  
            "images": [],  
            "annotations": [],  
            "categories": []  
        }  
          
        # 動画情報を取得  
        video_width = video_manager.get_video_width()  
        video_height = video_manager.get_video_height()  
        total_frames = video_manager.get_total_frames()  
          
        # カテゴリ情報を収集  
        categories = set()  
        for frame_annotation in frame_annotations.values():  
            if frame_annotation and frame_annotation.objects:  
                for annotation in frame_annotation.objects:  
                    categories.add(annotation.label)  
          
        # カテゴリをCOCO形式に変換  
        category_id_map = {}  
        for i, category_name in enumerate(sorted(categories), 1):  
            category_id_map[category_name] = i  
            coco_data["categories"].append({  
                "id": i,  
                "name": category_name,  
                "supercategory": "object"  
            })  
          
        # 進捗計算用  
        total_items = len(frame_annotations)  
        current_item = 0  
        annotation_id = 1  
          
        # フレームごとの処理  
        for frame_id, frame_annotation in frame_annotations.items():  
            # 進捗更新  
            current_item += 1  
            if progress_callback:  
                progress_callback(current_item, total_items)  
              
            # 画像情報を追加  
            image_info = {  
                "id": frame_id,  
                "width": video_width,  
                "height": video_height,  
                "file_name": f"frame_{frame_id:06d}.jpg",  
                "video_path": video_path,  
                "frame_id": frame_id  
            }  
            coco_data["images"].append(image_info)  
              
            # アノテーション情報を追加  
            if frame_annotation and frame_annotation.objects:  
                for obj_annotation in frame_annotation.objects:  
                    # バウンディングボックスをCOCO形式（x, y, width, height）に変換  
                    bbox_x = obj_annotation.bbox.x1  
                    bbox_y = obj_annotation.bbox.y1  
                    bbox_width = obj_annotation.bbox.x2 - obj_annotation.bbox.x1  
                    bbox_height = obj_annotation.bbox.y2 - obj_annotation.bbox.y1  
                      
                    # 面積計算  
                    area = bbox_width * bbox_height  
                      
                    annotation_data = {  
                        "id": annotation_id,  
                        "image_id": frame_id,  
                        "category_id": category_id_map[obj_annotation.label],  
                        "bbox": [bbox_x, bbox_y, bbox_width, bbox_height],  
                        "area": area,  
                        "iscrowd": 0,  
                        "track_id": obj_annotation.object_id,  
                        "confidence": obj_annotation.bbox.confidence,  
                        "is_manual": obj_annotation.is_manual  
                    }  
                      
                    coco_data["annotations"].append(annotation_data)  
                    annotation_id += 1  
          
        # JSONファイルに保存  
        try:  
            with open(file_path, 'w', encoding='utf-8') as f:  
                json.dump(coco_data, f, indent=2, ensure_ascii=False)  
              
            # 最終進捗更新  
            if progress_callback:  
                progress_callback(total_items, total_items)  
                  
        except Exception as e:  
            raise RuntimeError(f"Failed to save COCO JSON file: {str(e)}")
      
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