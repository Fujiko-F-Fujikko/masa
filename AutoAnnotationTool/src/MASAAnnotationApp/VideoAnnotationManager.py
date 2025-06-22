import os
import json
import cv2
import numpy as np
from typing import Dict, List, Optional
from DataClass import MASAConfig, ObjectAnnotation, FrameAnnotation, BoundingBox
from ObjectTracker import ObjectTracker
from JSONLoader import JSONLoader

class VideoAnnotationManager:  
    """複数フレーム機能を統合したアノテーション管理クラス"""  
      
    def __init__(self, video_path: str, config: MASAConfig = None):  
        self.video_path = video_path  
        self.config = config or MASAConfig()  
        self.tracker = ObjectTracker(self.config)  
        self.video_reader = None  
        self.frame_annotations: Dict[int, FrameAnnotation] = {}  
        self.manual_annotations: Dict[int, List[ObjectAnnotation]] = {}  
        self.total_frames = 0  
        self.next_object_id = 1
        self.multi_frame_objects = {}  # オブジェクトIDごとの複数フレーム情報

        # ラベルキャッシュの初期化
        self._all_labels_cache = set()
        self._is_labels_cache_dirty = True

    def load_video(self) -> bool:  
        """動画ファイルを読み込み"""  
        try:  
            self.video_reader = cv2.VideoCapture(self.video_path)  
            if not self.video_reader.isOpened():  
                print(f"Failed to open video: {self.video_path}")  
                return False  
              
            self.total_frames = int(self.video_reader.get(cv2.CAP_PROP_FRAME_COUNT))  
            print(f"Video loaded: {self.total_frames} frames")  
            return True  
              
        except Exception as e:  
            print(f"Error loading video: {e}")  
            return False  
      
    def get_frame(self, frame_id: int) -> Optional[np.ndarray]:  
        """指定フレームを取得"""  
        if self.video_reader is None:  
            return None  
              
        self.video_reader.set(cv2.CAP_PROP_POS_FRAMES, frame_id)  
        ret, frame = self.video_reader.read()  
          
        if ret:  
            return frame  
        return None  
      
    def add_manual_annotation(self, frame_id: int, bbox: BoundingBox, label: str) -> ObjectAnnotation:  
        """手動アノテーションを追加"""  
        annotation = ObjectAnnotation(  
            object_id=self.next_object_id,  
            label=label,  
            bbox=bbox,  
            frame_id=frame_id,  
            is_manual=True,  
            track_confidence=1.0  
        )  
          
        if frame_id not in self.manual_annotations:  
            self.manual_annotations[frame_id] = []  
          
        self.manual_annotations[frame_id].append(annotation)  
        self.next_object_id += 1  
          
        # フレームアノテーションも更新  
        if frame_id not in self.frame_annotations:  
            self.frame_annotations[frame_id] = FrameAnnotation(frame_id=frame_id)  
          
        self.frame_annotations[frame_id].objects.append(annotation)  
        self._is_labels_cache_dirty = True
        return annotation  
      
      
    def get_frame_annotations(self, frame_id: int) -> Optional[FrameAnnotation]:  
        """指定フレームのアノテーションを取得"""  
        return self.frame_annotations.get(frame_id)  
      
    def export_annotations(self, output_path: str, format: str = "json"):  
        """アノテーションをエクスポート"""  
        if format == "json":  
            self._export_json(output_path)  
        elif format == "coco":  
            self._export_coco(output_path)  
        else:  
            raise ValueError(f"Unsupported format: {format}")  
      
    def _export_json(self, output_path: str):  
        """JSON形式でエクスポート"""  
        export_data = {  
            "video_path": self.video_path,  
            "total_frames": self.total_frames,  
            "annotations": {}  
        }  
          
        for frame_id, frame_annotation in self.frame_annotations.items():  
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
      
    def _export_coco(self, output_path: str):  
        """COCO形式でエクスポート"""  
        # COCO形式の基本構造  
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
        for frame_annotation in self.frame_annotations.values():  
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
        for frame_id, frame_annotation in self.frame_annotations.items():  
            # 画像情報  
            frame = self.get_frame(frame_id)  
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

    def add_multi_frame_annotation(self, frame_ids: List[int], bboxes: List[BoundingBox], label: str) -> List[ObjectAnnotation]:  
        """複数フレームからアノテーションを追加"""  
        annotations = []  
        object_id = self.next_object_id  
          
        for frame_id, bbox in zip(frame_ids, bboxes):  
            annotation = ObjectAnnotation(  
                object_id=object_id,  
                label=label,  
                bbox=bbox,  
                frame_id=frame_id,  
                is_manual=True,  
                track_confidence=1.0  
            )  
              
            if frame_id not in self.manual_annotations:  
                self.manual_annotations[frame_id] = []  
              
            self.manual_annotations[frame_id].append(annotation)  
            annotations.append(annotation)  
              
            # フレームアノテーションも更新  
            if frame_id not in self.frame_annotations:  
                self.frame_annotations[frame_id] = FrameAnnotation(frame_id=frame_id)  
            self.frame_annotations[frame_id].objects.append(annotation)  
          
        # 複数フレーム情報を記録  
        self.multi_frame_objects[object_id] = annotations  
        self.next_object_id += 1  
        self._is_labels_cache_dirty = True
        return annotations  

    def load_json_annotations(self, json_path: str) -> bool:  
        """JSONファイルからアノテーションを読み込み"""  
        loader = JSONLoader()  
        loaded_annotations = loader.load_json_annotations(json_path)  
          
        if not loaded_annotations:  
            return False  
          
        # 既存のアノテーションをクリア  
        self.frame_annotations.clear()  
        self.manual_annotations.clear()  
          
        # 読み込んだアノテーションを設定  
        self.frame_annotations = loaded_annotations  
          
        # デバッグ用：読み込んだアノテーション数を確認  
        total_loaded = sum(len(frame_ann.objects) for frame_ann in loaded_annotations.values())  
        print(f"Loaded {total_loaded} annotations from JSON")  
          
        # next_object_idを更新  
        max_id = 0  
        for frame_annotation in self.frame_annotations.values():  
            for obj in frame_annotation.objects:  
                max_id = max(max_id, obj.object_id)  
        self.next_object_id = max_id + 1  
        self._is_labels_cache_dirty = True
        return True

    def export_masa_json(self, output_path: str):  
        """MASA形式のJSONでエクスポート（demo/video_demo_with_text.pyと同じ形式）"""  
        # ラベルマッピングを作成  
        all_labels = set()  
        for frame_annotation in self.frame_annotations.values():  
            for obj in frame_annotation.objects:  
                all_labels.add(obj.label)  
          
        label_mapping = {str(i): label for i, label in enumerate(sorted(all_labels))}  
        label_to_id = {label: i for i, label in enumerate(sorted(all_labels))}  
          
        annotations = []  
        for frame_annotation in self.frame_annotations.values():  
            for obj in frame_annotation.objects:  
                # xyxy形式からxywh形式に変換  
                bbox_xywh = [  
                    obj.bbox.x1,  
                    obj.bbox.y1,  
                    obj.bbox.x2 - obj.bbox.x1,  
                    obj.bbox.y2 - obj.bbox.y1  
                ]  
                  
                annotation_data = {  
                    "frame_id": obj.frame_id,  
                    "track_id": obj.object_id,  
                    "bbox": bbox_xywh,  
                    "score": obj.bbox.confidence,  
                    "label": label_to_id.get(obj.label, 0),  
                    "label_name": obj.label  
                }  
                  
                # マスクがある場合は追加  
                if hasattr(obj, 'has_mask') and obj.has_mask:  
                    annotation_data["has_mask"] = True  
                  
                annotations.append(annotation_data)  
          
        result_data = {  
            "video_name": os.path.basename(self.video_path),  
            "label_mapping": label_mapping,  
            "annotations": annotations  
        }  
          
        with open(output_path, 'w', encoding='utf-8') as f:  
            json.dump(result_data, f, indent=2, ensure_ascii=False)  
          
        print(f"MASA JSON exported to {output_path}")
    
    def get_annotation_statistics(self):  
        """アノテーション統計を取得"""  
        if not self.frame_annotations:  
            return {"total": 0, "manual": 0, "loaded": 0}  
          
        total = 0  
        manual = 0  
        loaded = 0  
          
        for frame_annotation in self.frame_annotations.values():  
            for obj in frame_annotation.objects:  
                total += 1  
                if obj.is_manual:  
                    manual += 1  
                else:  
                    loaded += 1  
          
        return {"total": total, "manual": manual, "loaded": loaded}

    def get_all_labels(self) -> List[str]:  
        """全フレームから既存のラベルを取得（キャッシュ対応）"""  
        if not self._is_labels_cache_dirty:  
            return sorted(list(self._all_labels_cache))  
      
        print("Updating labels cache...")
        self._all_labels_cache.clear()  
        for frame_annotation in self.frame_annotations.values():  
            for obj in frame_annotation.objects:  
                self._all_labels_cache.add(obj.label)  
          
        self._is_labels_cache_dirty = False  
        return sorted(list(self._all_labels_cache))

    def update_annotation_label(self, object_id: int, frame_id: int, new_label: str):  
        """指定されたアノテーションのラベルを更新します。"""  
        if frame_id in self.frame_annotations:  
            for obj in self.frame_annotations[frame_id].objects:  
                if obj.object_id == object_id:  
                    obj.label = new_label  
                    return True  
        self._is_labels_cache_dirty = True
        return False

    def delete_annotation(self, object_id: int, frame_id: int) -> bool:  
        """指定されたアノテーションを削除します。"""  
        if frame_id in self.frame_annotations:  
            initial_count = len(self.frame_annotations[frame_id].objects)  
            self.frame_annotations[frame_id].objects = [  
                obj for obj in self.frame_annotations[frame_id].objects  
                if not (obj.object_id == object_id and obj.frame_id == frame_id)  
            ]  
            if len(self.frame_annotations[frame_id].objects) < initial_count:  
                # manual_annotationsからも削除（もしあれば）  
                if frame_id in self.manual_annotations:  
                    self.manual_annotations[frame_id] = [  
                        obj for obj in self.manual_annotations[frame_id]  
                        if not (obj.object_id == object_id and obj.frame_id == frame_id)  
                    ]  
                return True  
        self._is_labels_cache_dirty = True
        return False

    def delete_annotations_by_track_id(self, track_id: int) -> int:  
        """指定されたTrack IDを持つすべてのアノテーションを削除します。  
        削除されたアノテーションの総数を返します。  
        """  
        deleted_count = 0  
        frames_to_update = set() # 変更があったフレームを記録  
  
        # frame_annotations から削除  
        for frame_id, frame_annotation in list(self.frame_annotations.items()): # list()でコピーしてイテレート  
            initial_frame_objects_count = len(frame_annotation.objects)  
            frame_annotation.objects = [  
                obj for obj in frame_annotation.objects if obj.object_id != track_id  
            ]  
            if len(frame_annotation.objects) < initial_frame_objects_count:  
                deleted_count += (initial_frame_objects_count - len(frame_annotation.objects))  
                frames_to_update.add(frame_id)  
                # もしフレームにアノテーションが残っていなければ、フレーム自体を削除  
                if not frame_annotation.objects:  
                    del self.frame_annotations[frame_id]  
  
        # manual_annotations からも削除（もしあれば）  
        for frame_id, manual_anns in list(self.manual_annotations.items()): # list()でコピーしてイテレート  
            initial_manual_anns_count = len(manual_anns)  
            self.manual_annotations[frame_id] = [  
                obj for obj in manual_anns if obj.object_id != track_id  
            ]  
            if len(self.manual_annotations[frame_id]) < initial_manual_anns_count:  
                frames_to_update.add(frame_id)  
                # もしフレームにアノテーションが残っていなければ、フレーム自体を削除  
                if not self.manual_annotations[frame_id]:  
                    del self.manual_annotations[frame_id]  
  
        if deleted_count > 0:  
            self._is_labels_cache_dirty = True # ラベルキャッシュをダーティに  
        return deleted_count

    def update_annotations_label_by_track_id(self, track_id: int, new_label: str) -> int:  
        """指定されたTrack IDを持つすべてのアノテーションのラベルを更新します。  
        変更されたアノテーションの総数を返します。  
        """  
        updated_count = 0  
          
        # frame_annotations 内の ObjectAnnotation を更新  
        for frame_annotation in self.frame_annotations.values():  
            for obj in frame_annotation.objects:  
                if obj.object_id == track_id:  
                    obj.label = new_label  
                    updated_count += 1  
          
        # manual_annotations 内の ObjectAnnotation も更新（もしあれば）  
        for manual_anns in self.manual_annotations.values():  
            for obj in manual_anns:  
                if obj.object_id == track_id:  
                    obj.label = new_label  
                    # updated_count は frame_annotations でカウント済みのため、ここでは加算しない  
          
        if updated_count > 0:  
            self._is_labels_cache_dirty = True # ラベルキャッシュをダーティに  
        return updated_count