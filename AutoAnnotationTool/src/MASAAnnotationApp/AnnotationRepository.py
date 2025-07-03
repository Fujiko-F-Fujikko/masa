# AnnotationRepository.py  
from typing import Dict, List, Optional  
from DataClass import FrameAnnotation, ObjectAnnotation  
from ErrorHandler import ErrorHandler  
  
class AnnotationRepository:  
    """アノテーションデータの管理専用クラス"""  
      
    def __init__(self):  
        self.frame_annotations: Dict[int, FrameAnnotation] = {}  
        self.manual_annotations: Dict[int, List[ObjectAnnotation]] = {}  
        self.next_object_id = 1  
          
        # ラベルキャッシュ  
        self._all_labels_cache = set()  
        self._is_labels_cache_dirty = True  
      
    def add_annotation(self, annotation: ObjectAnnotation) -> ObjectAnnotation:  
        """アノテーションを追加"""  
        frame_id = annotation.frame_id  
          
        # フレームアノテーションが存在しない場合は作成  
        if frame_id not in self.frame_annotations:  
            self.frame_annotations[frame_id] = FrameAnnotation(  
                frame_id=frame_id, objects=[]  
            )  
          
        # オブジェクトIDが未設定の場合は新しいIDを生成  
        if annotation.object_id <= 0:  
            annotation.object_id = self.get_next_object_id()  
          
        # アノテーションを追加  
        self.frame_annotations[frame_id].objects.append(annotation)  
          
        # 手動アノテーションの場合は別途管理  
        if annotation.is_manual:  
            if frame_id not in self.manual_annotations:  
                self.manual_annotations[frame_id] = []  
            self.manual_annotations[frame_id].append(annotation)  
          
        self._is_labels_cache_dirty = True  
        return annotation  
      
    def get_annotations(self, frame_id: int) -> Optional[FrameAnnotation]:  
        """指定フレームのアノテーションを取得"""  
        return self.frame_annotations.get(frame_id)  
      
    def update_annotation(self, annotation: ObjectAnnotation) -> bool:  
        """アノテーションを更新"""  
        frame_id = annotation.frame_id  
        if frame_id not in self.frame_annotations:  
            return False  
          
        # 該当するアノテーションを検索して更新  
        for i, existing_ann in enumerate(self.frame_annotations[frame_id].objects):  
            if existing_ann.object_id == annotation.object_id:  
                self.frame_annotations[frame_id].objects[i] = annotation  
                self._is_labels_cache_dirty = True  
                return True  
          
        return False  
      
    def delete_annotation(self, object_id: int, frame_id: int) -> bool:  
        """指定されたアノテーションを削除"""  
        if frame_id not in self.frame_annotations:  
            return False  
          
        initial_count = len(self.frame_annotations[frame_id].objects)  
        self.frame_annotations[frame_id].objects = [  
            obj for obj in self.frame_annotations[frame_id].objects  
            if not (obj.object_id == object_id and obj.frame_id == frame_id)  
        ]  
          
        # 手動アノテーションからも削除  
        if frame_id in self.manual_annotations:  
            self.manual_annotations[frame_id] = [  
                obj for obj in self.manual_annotations[frame_id]  
                if not (obj.object_id == object_id and obj.frame_id == frame_id)  
            ]  
          
        success = len(self.frame_annotations[frame_id].objects) < initial_count  
        if success:  
            self._is_labels_cache_dirty = True  
          
        return success  
      
    def delete_by_track_id(self, track_id: int) -> int:  
        """指定されたTrack IDを持つすべてのアノテーションを削除"""  
        deleted_count = 0  
          
        # frame_annotationsから削除  
        for frame_id, frame_annotation in list(self.frame_annotations.items()):  
            initial_count = len(frame_annotation.objects)  
            frame_annotation.objects = [  
                obj for obj in frame_annotation.objects   
                if obj.object_id != track_id  
            ]  
            deleted_count += (initial_count - len(frame_annotation.objects))  
              
            # フレームにアノテーションが残っていなければ、フレーム自体を削除  
            if not frame_annotation.objects:  
                del self.frame_annotations[frame_id]  
          
        # manual_annotationsからも削除  
        for frame_id, manual_anns in list(self.manual_annotations.items()):  
            initial_count = len(manual_anns)  
            self.manual_annotations[frame_id] = [  
                obj for obj in manual_anns if obj.object_id != track_id  
            ]  
            if len(self.manual_annotations[frame_id]) < initial_count:  
                # フレームにアノテーションが残っていなければ、フレーム自体を削除  
                if not self.manual_annotations[frame_id]:  
                    del self.manual_annotations[frame_id]  
          
        if deleted_count > 0:  
            self._is_labels_cache_dirty = True  
          
        return deleted_count  
      
    def update_label_by_track_id(self, track_id: int, new_label: str) -> int:  
        """指定されたTrack IDを持つすべてのアノテーションのラベルを更新"""  
        updated_count = 0  
          
        for frame_annotation in self.frame_annotations.values():  
            for obj in frame_annotation.objects:  
                if obj.object_id == track_id:  
                    obj.label = new_label  
                    updated_count += 1  
          
        # manual_annotationsも更新  
        for manual_anns in self.manual_annotations.values():  
            for obj in manual_anns:  
                if obj.object_id == track_id:  
                    obj.label = new_label  
          
        if updated_count > 0:  
            self._is_labels_cache_dirty = True  
          
        return updated_count  
      
    def get_all_labels(self) -> List[str]:  
        """全ラベルを取得（キャッシュ対応）"""  
        if not self._is_labels_cache_dirty:  
            return sorted(list(self._all_labels_cache))  
          
        self._all_labels_cache.clear()  
        for frame_annotation in self.frame_annotations.values():  
            for obj in frame_annotation.objects:  
                self._all_labels_cache.add(obj.label)  
          
        self._is_labels_cache_dirty = False  
        return sorted(list(self._all_labels_cache))  
      
    def get_statistics(self) -> Dict[str, int]:  
        """アノテーション統計を取得"""  
        total = 0  
        manual = 0  
          
        for frame_annotation in self.frame_annotations.values():  
            for obj in frame_annotation.objects:  
                total += 1  
                if obj.is_manual:  
                    manual += 1  
          
        return {  
            "total": total,  
            "manual": manual,  
            "loaded": total - manual  
        }  
      
    def get_next_object_id(self) -> int:  
        """次に利用可能なオブジェクトIDを取得"""  
        next_id = self.next_object_id  
        self.next_object_id += 1  
        return next_id  
      
    def clear(self):  
        """全アノテーションをクリア"""  
        self.frame_annotations.clear()  
        self.manual_annotations.clear()  
        self._all_labels_cache.clear()  
        self._is_labels_cache_dirty = True  

    def get_annotations_by_track_id(self, track_id: int) -> List[ObjectAnnotation]:  
        """指定されたトラックIDのアノテーションを全て取得"""  
        annotations = []  
        for frame_annotation in self.frame_annotations.values():  
            if frame_annotation and frame_annotation.objects:  
                for annotation in frame_annotation.objects:  
                    if annotation.object_id == track_id:  
                        annotations.append(annotation)  
        return annotations