# MASAApplicationService.py
"""
ファサードパターンによるアプリケーションサービス層
すべてのビジネスロジックへの単一窓口を提供
"""
from typing import Optional, Dict, List, Any
from pathlib import Path

from ConfigManager import ConfigManager
from AnnotationRepository import AnnotationRepository
from CommandPattern import CommandManager, AddAnnotationCommand, DeleteAnnotationCommand, DeleteTrackCommand, UpdateLabelCommand, UpdateLabelByTrackCommand, UpdateBoundingBoxCommand
from VideoManager import VideoManager
from ExportService import ExportService
from ObjectTracker import ObjectTracker
from DataClass import ObjectAnnotation, BoundingBox, FrameAnnotation
from ErrorHandler import ErrorHandler


class MASAApplicationService:
    """アプリケーション層のファサード - すべてのビジネスロジックへの窓口"""
    
    def __init__(self):
        """サービス層の初期化"""
        self.config_manager = ConfigManager()
        self.annotation_repository = AnnotationRepository()
        self.command_manager = CommandManager()
        self.export_service = ExportService()
        
        # Optionalなサービス（遅延初期化）
        self.video_manager: Optional[VideoManager] = None
        self.object_tracker: Optional[ObjectTracker] = None
        
        # 状態管理
        self._current_label = ""
        self._current_frame_id = 0
        
    # ===== アノテーション操作 =====
    
    @ErrorHandler.handle_with_dialog("Annotation Creation Error")
    def create_annotation(self, x1: int, y1: int, x2: int, y2: int, label: str) -> bool:
        """アノテーションを作成"""
        if not label:
            ErrorHandler.show_warning_dialog("ラベルが設定されていません。", "Warning")
            return False
            
        bbox = BoundingBox(x1, y1, x2, y2)
        annotation = ObjectAnnotation(
            object_id=-1,  # 新規IDを意味
            frame_id=self._current_frame_id,
            bbox=bbox,
            label=label,
            is_manual=True,
            track_confidence=1.0,
            is_batch_added=False
        )
        
        command = AddAnnotationCommand(self.annotation_repository, annotation)
        return self.command_manager.execute_command(command) is not None
    
    @ErrorHandler.handle_with_dialog("Annotation Deletion Error")
    def delete_annotation(self, annotation: ObjectAnnotation) -> bool:
        """単一アノテーションを削除"""
        command = DeleteAnnotationCommand(self.annotation_repository, annotation)
        return self.command_manager.execute_command(command) is not None
    
    @ErrorHandler.handle_with_dialog("Track Deletion Error")
    def delete_track(self, track_id: int) -> int:
        """トラック単位でアノテーションを削除"""
        command = DeleteTrackCommand(self.annotation_repository, track_id)
        return self.command_manager.execute_command(command) or 0
    
    @ErrorHandler.handle_with_dialog("Label Update Error")
    def update_label(self, annotation: ObjectAnnotation, new_label: str) -> bool:
        """単一アノテーションのラベルを更新"""
        old_label = annotation.label
        command = UpdateLabelCommand(self.annotation_repository, annotation, old_label, new_label)
        return self.command_manager.execute_command(command) is not None
    
    @ErrorHandler.handle_with_dialog("Label Propagation Error")
    def propagate_label(self, track_id: int, new_label: str) -> int:
        """トラック単位でラベルを更新"""
        annotations = self.annotation_repository.get_annotations_by_track_id(track_id)
        if not annotations:
            return 0
            
        old_label = annotations[0].label
        command = UpdateLabelByTrackCommand(self.annotation_repository, track_id, old_label, new_label)
        return self.command_manager.execute_command(command) or 0
    
    def update_bbox_position(self, annotation: ObjectAnnotation, old_bbox: BoundingBox, new_bbox: BoundingBox) -> bool:  
        """バウンディングボックス位置を更新"""  
        from CommandPattern import UpdateBoundingBoxCommand  
        command = UpdateBoundingBoxCommand(self.annotation_repository, annotation, old_bbox, new_bbox)  
        return self.command_manager.execute_command(command)

    # ===== ファイル操作 =====
    
    @ErrorHandler.handle_with_dialog("Video Load Error")
    def load_video(self, path: str) -> bool:
        """動画ファイルを読み込み"""
        # 既存のVideoManagerがあれば解放
        if self.video_manager:
            self.video_manager.release()
            self.video_manager = None
            
        self.video_manager = VideoManager(path)
        success = self.video_manager.load_video()
        
        if success:
            self._current_frame_id = 0
            
        return success
    
    @ErrorHandler.handle_with_dialog("JSON Load Error")
    def load_json(self, path: str) -> bool:
        """JSONアノテーションファイルを読み込み"""
        loaded_annotations = self.export_service.import_json(path)
        if loaded_annotations:
            self.annotation_repository.clear()
            for frame_id, frame_ann in loaded_annotations.items():
                for obj_ann in frame_ann.objects:
                    self.annotation_repository.add_annotation(obj_ann)
            return True
        return False
    
    @ErrorHandler.handle_with_dialog("Export Error")
    def export_masa_json(self, path: str) -> bool:
        """MASA形式のJSONをエクスポート"""
        if not self.annotation_repository.frame_annotations:
            ErrorHandler.show_warning_dialog("エクスポートするアノテーションがありません。", "Warning")
            return False
            
        if not self.video_manager:
            ErrorHandler.show_warning_dialog("動画が読み込まれていません。", "Warning")
            return False
            
        try:
            self.export_service.export_masa_json(
                self.annotation_repository.frame_annotations,
                self.video_manager.video_path,
                path
            )
            return True
        except Exception as e:
            ErrorHandler.show_error_dialog(f"エクスポートに失敗しました: {str(e)}", "Export Error")
            return False
    
    @ErrorHandler.handle_with_dialog("Export Error")
    def export_coco_json(self, path: str, progress_callback=None) -> bool:
        """COCO形式のJSONをエクスポート"""
        if not self.annotation_repository.frame_annotations:
            ErrorHandler.show_warning_dialog("エクスポートするアノテーションがありません。", "Warning")
            return False
            
        if not self.video_manager:
            ErrorHandler.show_warning_dialog("動画が読み込まれていません。", "Warning")
            return False
            
        try:
            # スコア閾値でフィルタリング
            display_config = self.config_manager.get_full_config(config_type="display")
            filtered_annotations = self._filter_annotations_by_score_threshold(display_config.score_threshold)
            
            self.export_service.export_coco_with_progress(
                filtered_annotations,
                self.video_manager.video_path,
                path,
                self.video_manager,
                progress_callback
            )
            return True
        except Exception as e:
            ErrorHandler.show_error_dialog(f"エクスポートに失敗しました: {str(e)}", "Export Error")
            return False
    
    def _filter_annotations_by_score_threshold(self, score_threshold: float) -> Dict[int, FrameAnnotation]:
        """スコア閾値でアノテーションをフィルタリング"""
        filtered_frame_annotations = {}
        
        for frame_id, frame_annotation in self.annotation_repository.frame_annotations.items():
            if frame_annotation and frame_annotation.objects:
                filtered_objects = []
                for annotation in frame_annotation.objects:
                    if annotation.bbox.confidence >= score_threshold:
                        filtered_objects.append(annotation)
                
                if filtered_objects:
                    filtered_frame_annotation = FrameAnnotation(
                        frame_id=frame_annotation.frame_id,
                        frame_path=frame_annotation.frame_path,
                        objects=filtered_objects
                    )
                    filtered_frame_annotations[frame_id] = filtered_frame_annotation
        
        return filtered_frame_annotations
    
    # ===== 設定管理 =====
    
    def get_display_config(self):
        """表示設定を取得"""
        return self.config_manager.get_full_config(config_type="display")
    
    def update_display_setting(self, key: str, value: Any):
        """表示設定を更新"""
        self.config_manager.update_config(key, value, config_type="display")
    
    def get_masa_config(self):
        """MASA設定を取得"""
        return self.config_manager.get_full_config(config_type="masa")
    
    # ===== コマンド操作 =====
    
    def execute_command(self, command) -> Any:
        """コマンドを実行"""
        return self.command_manager.execute_command(command)
    
    def undo(self) -> bool:
        """操作を取り消し"""
        return self.command_manager.undo()
    
    def redo(self) -> bool:
        """操作をやり直し"""
        return self.command_manager.redo()
    
    def can_undo(self) -> bool:
        """取り消し可能かチェック"""
        return self.command_manager.can_undo()
    
    def can_redo(self) -> bool:
        """やり直し可能かチェック"""
        return self.command_manager.can_redo()
    
    def get_undo_description(self) -> str:
        """取り消し操作の説明を取得"""
        return self.command_manager.get_undo_description()
    
    def get_redo_description(self) -> str:
        """やり直し操作の説明を取得"""
        return self.command_manager.get_redo_description()
    
    # ===== 追跡操作 =====
    
    @ErrorHandler.handle_with_dialog("Tracking Error")
    def start_tracking(self, track_id: int, label: str, start_frame: int, end_frame: int, 
                      initial_annotations: List[tuple]) -> bool:
        """自動追跡を開始"""
        # ObjectTrackerの初期化（遅延初期化）
        if not self.object_tracker:
            self.object_tracker = ObjectTracker(self.get_masa_config())
            
        if not self.object_tracker.initialized:
            try:
                self.object_tracker.initialize()
            except Exception as e:
                ErrorHandler.show_error_dialog(f"MASAモデルの初期化に失敗しました: {str(e)}", "Initialization Error")
                return False
        
        if not self.video_manager:
            ErrorHandler.show_warning_dialog("動画が読み込まれていません。", "Warning")
            return False
        
        # 追跡処理は別途TrackingWorkerで実行される想定
        return True
    
    # ===== データアクセス =====
    
    def get_annotations(self, frame_id: int) -> Optional[FrameAnnotation]:
        """指定フレームのアノテーションを取得"""
        return self.annotation_repository.get_annotations(frame_id)
    
    def get_annotations_by_track_id(self, track_id: int) -> List[ObjectAnnotation]:
        """指定トラックIDのアノテーションを取得"""
        return self.annotation_repository.get_annotations_by_track_id(track_id)
    
    def get_all_labels(self) -> List[str]:
        """すべてのラベルを取得"""
        return self.annotation_repository.get_all_labels()
    
    def get_statistics(self) -> Dict[str, int]:
        """アノテーション統計を取得"""
        return self.annotation_repository.get_statistics()
    
    def get_next_object_id(self) -> int:
        """次のオブジェクトIDを取得"""
        return self.annotation_repository.get_next_object_id()
    
    # ===== 状態管理 =====
    
    def set_current_frame(self, frame_id: int):
        """現在のフレームIDを設定"""
        self._current_frame_id = frame_id
    
    def get_current_frame(self) -> int:
        """現在のフレームIDを取得"""
        return self._current_frame_id
    
    def set_current_label(self, label: str):
        """現在のラベルを設定"""
        self._current_label = label
    
    def get_current_label(self) -> str:
        """現在のラベルを取得"""
        return self._current_label
    
    # ===== ビデオ関連 =====
    
    def get_video_manager(self) -> Optional[VideoManager]:
        """VideoManagerを取得"""
        return self.video_manager
    
    def get_video_info(self) -> Dict[str, Any]:
        """動画情報を取得"""
        if not self.video_manager:
            return {}
            
        return {
            "path": self.video_manager.video_path,
            "total_frames": self.video_manager.get_total_frames(),
            "fps": self.video_manager.get_fps(),
            "width": self.video_manager.get_video_width(),
            "height": self.video_manager.get_video_height()
        }
    
    # ===== クリーンアップ =====
    
    def cleanup(self):
        """リソースのクリーンアップ"""
        if self.video_manager:
            self.video_manager.release()
            self.video_manager = None
            
        if self.object_tracker:
            # ObjectTrackerのクリーンアップが必要であれば実装
            self.object_tracker = None
