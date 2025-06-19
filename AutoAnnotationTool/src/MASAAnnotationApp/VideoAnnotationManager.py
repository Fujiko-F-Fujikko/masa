import json
import cv2
import numpy as np
from typing import Dict, List, Optional
from DataClass import MASAConfig, ObjectAnnotation, FrameAnnotation, BoundingBox
from ObjectTracker import ObjectTracker

class VideoAnnotationManager:  
    """複数フレーム機能を統合したアノテーション管理クラス"""  
      
    def __init__(self, video_path: str, config: MASAConfig = None):  
        self.video_path = video_path  
        self.config = config or MASAConfig()  
        self.tracker = ObjectTracker(self.config)  
        self.video_reader = None  
        self.frame_annotations: Dict[int, FrameAnnotation] = {}  
        self.manual_annotations: Dict[int, List[ObjectAnnotation]] = {}  
        self.current_frame_id = 0  
        self.total_frames = 0  
        self.next_object_id = 1
        self.multi_frame_objects = {}  # オブジェクトIDごとの複数フレーム情報
          
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
          
        return annotations  
      
    def process_automatic_tracking(self, start_frame_id: int, end_frame_id: int = None) -> Dict[int, List[ObjectAnnotation]]:  
        """複数フレーム情報を活用した追跡処理"""  
        if end_frame_id is None:  
            end_frame_id = self.total_frames - 1  
          
        # 初期化  
        if not self.tracker.initialized:  
            self.tracker.initialize()  
          
        # 開始フレームの手動アノテーションを取得  
        if start_frame_id not in self.manual_annotations:  
            print(f"No manual annotations found for frame {start_frame_id}")  
            return {}  
          
        manual_objects = self.manual_annotations[start_frame_id]  
          
        # テキストプロンプトを生成（ラベルから）  
        unique_labels = list(set([obj.label for obj in manual_objects]))  
        text_prompt = " . ".join(unique_labels) if unique_labels else None  
          
        results = {}  
          
        # フレームごとに追跡処理  
        for frame_id in range(start_frame_id, min(end_frame_id + 1, self.total_frames)):  
            frame = self.get_frame(frame_id)  
            if frame is None:  
                continue  
              
            try:  
                # 追跡実行（memo_tracklet_framesとmemo_momentumを活用）
                tracked_annotations = self.tracker.track_objects(  
                    frame=frame,  
                    frame_id=frame_id,  
                    initial_annotations=manual_objects if frame_id == start_frame_id else None,  
                    texts=text_prompt  
                )  
                  
                # 結果を保存  
                results[frame_id] = tracked_annotations  
                  
                # フレームアノテーションを更新  
                if frame_id not in self.frame_annotations:  
                    self.frame_annotations[frame_id] = FrameAnnotation(frame_id=frame_id)  
                  
                # 手動アノテーションと自動追跡結果をマージ  
                all_annotations = []  
                if frame_id in self.manual_annotations:  
                    all_annotations.extend(self.manual_annotations[frame_id])  
                all_annotations.extend(tracked_annotations)  
                  
                self.frame_annotations[frame_id].objects = all_annotations  
                  
                print(f"Frame {frame_id}: {len(tracked_annotations)} objects tracked")  
                  
            except Exception as e:  
                print(f"Error tracking frame {frame_id}: {e}")  
                continue  
          
        return results
