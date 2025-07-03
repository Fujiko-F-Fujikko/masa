# CommandPattern.py  
from abc import ABC, abstractmethod  
from typing import Any, List  

from DataClass import ObjectAnnotation, BoundingBox

  
class Command(ABC):  
    """コマンドの基底クラス"""  
      
    @abstractmethod  
    def execute(self) -> Any:  
        """コマンドを実行"""  
        pass  
      
    @abstractmethod  
    def undo(self) -> Any:  
        """コマンドを取り消し"""  
        pass  
      
    @abstractmethod  
    def get_description(self) -> str:  
        """コマンドの説明を取得"""  
        pass  
  
class AddAnnotationCommand(Command):  
    """アノテーション追加コマンド"""  
      
    def __init__(self, annotation_repository, annotation: ObjectAnnotation):  
        self.annotation_repository = annotation_repository  
        self.annotation = annotation  
      
    def execute(self):  
        return self.annotation_repository.add_annotation(self.annotation)  
      
    def undo(self):  
        return self.annotation_repository.delete_annotation(  
            self.annotation.object_id, self.annotation.frame_id  
        )  
      
    def get_description(self) -> str:  
        return f"Add annotation {self.annotation.label} at frame {self.annotation.frame_id}"  
  
class DeleteAnnotationCommand(Command):  
    """アノテーション削除コマンド"""  
      
    def __init__(self, annotation_repository, annotation: ObjectAnnotation):  
        self.annotation_repository = annotation_repository  
        self.annotation = annotation  
      
    def execute(self):  
        return self.annotation_repository.delete_annotation(  
            self.annotation.object_id, self.annotation.frame_id  
        )  
      
    def undo(self):  
        return self.annotation_repository.add_annotation(self.annotation)  
      
    def get_description(self) -> str:  
        return f"Delete annotation {self.annotation.label} at frame {self.annotation.frame_id}"  
  
class DeleteTrackCommand(Command):  
    """トラック削除コマンド"""  
      
    def __init__(self, annotation_repository, track_id: int):  
        self.annotation_repository = annotation_repository  
        self.track_id = track_id  
        self.deleted_annotations = []  
      
    def execute(self):  
        # 削除前にアノテーションを保存  
        self.deleted_annotations = self.annotation_repository.get_annotations_by_track_id(self.track_id)  
        return self.annotation_repository.delete_by_track_id(self.track_id)  
      
    def undo(self):  
        # 保存されたアノテーションを復元  
        for annotation in self.deleted_annotations:  
            self.annotation_repository.add_annotation(annotation)  
        return len(self.deleted_annotations)  
      
    def get_description(self) -> str:  
        return f"Delete track {self.track_id} ({len(self.deleted_annotations)} annotations)"  
  
class UpdateLabelCommand(Command):  
    """ラベル更新コマンド"""  
      
    def __init__(self, annotation_repository, annotation: ObjectAnnotation, old_label: str, new_label: str):  
        self.annotation_repository = annotation_repository  
        self.annotation = annotation  
        self.old_label = old_label  
        self.new_label = new_label  
      
    def execute(self):  
        self.annotation.label = self.new_label  
        return self.annotation_repository.update_annotation(self.annotation)  
      
    def undo(self):  
        self.annotation.label = self.old_label  
        return self.annotation_repository.update_annotation(self.annotation)  
      
    def get_description(self) -> str:  
        return f"Update label from '{self.old_label}' to '{self.new_label}'"  
  
class UpdateLabelByTrackCommand(Command):  
    """トラック単位でのラベル更新コマンド"""  
      
    def __init__(self, annotation_repository, track_id: int, old_label: str, new_label: str):  
        self.annotation_repository = annotation_repository  
        self.track_id = track_id  
        self.old_label = old_label  
        self.new_label = new_label  
        self.affected_annotations = []  
      
    def execute(self):  
        # 影響を受けるアノテーションを記録  
        self.affected_annotations = self.annotation_repository.get_annotations_by_track_id(self.track_id)  
        return self.annotation_repository.update_label_by_track_id(self.track_id, self.new_label)  
      
    def undo(self):  
        return self.annotation_repository.update_label_by_track_id(self.track_id, self.old_label)  
      
    def get_description(self) -> str:  
        return f"Update track {self.track_id} label from '{self.old_label}' to '{self.new_label}'"  
  
class MacroCommand(Command):  
    """複数のコマンドをまとめて実行するマクロコマンド"""  
      
    def __init__(self, commands: List[Command], description: str):  
        self.commands = commands  
        self.description = description  
      
    def execute(self):  
        results = []  
        for command in self.commands:  
            results.append(command.execute())  
        return results  
      
    def undo(self):  
        results = []  
        # 逆順で実行  
        for command in reversed(self.commands):  
            results.append(command.undo())  
        return results  
      
    def get_description(self) -> str:  
        return self.description  

class UpdateBoundingBoxCommand(Command):  
    """バウンディングボックス位置・サイズ更新コマンド"""  
      
    def __init__(self, annotation_repository, annotation: ObjectAnnotation, old_bbox: BoundingBox, new_bbox: BoundingBox):  
        self.annotation_repository = annotation_repository  
        self.annotation = annotation  
        self.old_bbox = old_bbox  
        self.new_bbox = new_bbox  
      
    def execute(self):  
        self.annotation.bbox = self.new_bbox  
        return self.annotation_repository.update_annotation(self.annotation)  
      
    def undo(self):  
        self.annotation.bbox = self.old_bbox  
        return self.annotation_repository.update_annotation(self.annotation)  
      
    def get_description(self) -> str:  
        return f"Update bounding box position for {self.annotation.label} at frame {self.annotation.frame_id}"  

class CommandManager:  
    """コマンド履歴を管理するマネージャー"""  
      
    def __init__(self, max_history_size: int = 100):  
        self.undo_stack: List[Command] = []  
        self.redo_stack: List[Command] = []  
        self.max_history_size = max_history_size  
      
    def execute_command(self, command: Command):  
        """コマンドを実行し、履歴に追加"""  
        result = command.execute()  
        self.undo_stack.append(command)  
        self.redo_stack.clear()  # 新しいコマンド実行時はredo履歴をクリア  
          
        # 履歴サイズ制限  
        if len(self.undo_stack) > self.max_history_size:  
            self.undo_stack.pop(0)  
          
        return result  
      
    def undo(self):  
        """最後のコマンドを取り消し"""  
        if not self.undo_stack:  
            return False  
          
        command = self.undo_stack.pop()  
        result = command.undo()  
        self.redo_stack.append(command)  
        return result  
      
    def redo(self):  
        """取り消したコマンドを再実行"""  
        if not self.redo_stack:  
            return False  
          
        command = self.redo_stack.pop()  
        result = command.execute()  
        self.undo_stack.append(command)  
        return result  
      
    def can_undo(self) -> bool:  
        """Undoが可能かどうか"""  
        return len(self.undo_stack) > 0  
      
    def can_redo(self) -> bool:  
        """Redoが可能かどうか"""  
        return len(self.redo_stack) > 0  
      
    def get_undo_description(self) -> str:  
        """次にUndoされるコマンドの説明を取得"""  
        if self.can_undo():  
            return self.undo_stack[-1].get_description()  
        return ""  
      
    def get_redo_description(self) -> str:  
        """次にRedoされるコマンドの説明を取得"""  
        if self.can_redo():  
            return self.redo_stack[-1].get_description()  
        return ""  
      
    def clear(self):  
        """履歴をクリア"""  
        self.undo_stack.clear()  
        self.redo_stack.clear()