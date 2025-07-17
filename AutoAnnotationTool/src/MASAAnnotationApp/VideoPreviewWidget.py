# VideoPreviewWidget.py    
from typing import Any, List, Optional  
import cv2    
import numpy as np    
  
from PyQt6.QtWidgets import QLabel, QSizePolicy, QDialog  
from PyQt6.QtCore import Qt, pyqtSignal  
from PyQt6.QtGui import QPixmap, QImage, QPainter  
  
from AnnotationVisualizer import AnnotationVisualizer    
from BoundingBoxEditor import BoundingBoxEditor    
from CoordinateTransform import CoordinateTransform    
from ModeManager import ModeManager    
from ConfigManager import ConfigManager  
from DataClass import ObjectAnnotation, BoundingBox  
from AnnotationInputDialog import AnnotationInputDialog  
from ErrorHandler import ErrorHandler  
from CommandPattern import AddAnnotationCommand, UpdateBoundingBoxCommand  
  
class VideoPreviewWidget(QLabel):    
    """統合された動画プレビューウィジェット（軽量化版）"""    
        
    # シグナル定義    
    bbox_created = pyqtSignal(int, int, int, int)  # x1, y1, x2, y2    
    frame_changed = pyqtSignal(int)  # frame_id    
    annotation_selected = pyqtSignal(object)  # ObjectAnnotation    
    annotation_updated = pyqtSignal(object)  # ObjectAnnotation    
        
    def __init__(self, main_widget, parent=None):    
        super().__init__(parent)    
        self.main_widget = main_widget  # MASAAnnotationWidgetへの参照  
        self.parent_ma_widget = main_widget  # 既存コードとの互換性のため  
          
        self.setMinimumSize(640, 480)  
        self.setStyleSheet("border: 2px solid gray; background-color: black;")    
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)    
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)    
            
        self.video_manager = None    
        self.annotation_repository = None  
        self.current_frame_id = 0    
        self.current_frame = None    
        self.original_width = 0    
        self.original_height = 0  
            
        self.visualizer = AnnotationVisualizer()    
        self.bbox_editor = BoundingBoxEditor(self)    
        self.coordinate_transform = CoordinateTransform()  
        self.mode_manager = ModeManager(self)  
        self.bbox_editor.set_editing_mode(False)  
  
        self.config_manager = None  
            
        # 表示オプション  
        self.show_manual_annotations = True    
        self.show_auto_annotations = True    
        self.show_ids = True    
        self.show_confidence = True    
        self.score_threshold = 0.2     
          
        self._updating_frame = False  
          
        self.temp_tracking_annotations: List[ObjectAnnotation] = []  
  
        self._connect_signals()    
            
    def _connect_signals(self):    
        """内部シグナル接続"""    
        self.bbox_editor.annotation_updated.connect(self.on_annotation_updated)    
        self.bbox_editor.selection_changed.connect(self.on_selection_changed)    
        self.bbox_editor.new_bbox_drawing_completed.connect(self._on_new_bbox_drawing_completed)  
        self.bbox_editor.bbox_position_updated.connect(self.on_bbox_position_updated)  
            
    def set_video_manager(self, video_manager):    
        """VideoManagerを設定"""    
        self.video_manager = video_manager    
        if video_manager:    
            self.current_frame_id = 0    
            self.update_frame_display()    
  
    def set_config_manager(self, config_manager: ConfigManager):    
        """ConfigManagerを設定"""    
        self.config_manager = config_manager    
        display_config = self.config_manager.get_full_config(config_type="display")    
        self.set_display_options(    
            display_config.show_manual_annotations,    
            display_config.show_auto_annotations,    
            display_config.show_ids,    
            display_config.show_confidence,    
            display_config.score_threshold    
        )    
        self.config_manager.add_observer(self._on_config_changed)    
  
    def set_annotation_repository(self, annotation_repository):    
        """AnnotationRepositoryを設定"""    
        self.annotation_repository = annotation_repository    
    
    def set_mode(self, mode_name: str):    
        """モードを設定"""    
        if self.mode_manager:    
            self.mode_manager.set_mode(mode_name)    
            self.update_frame_display()  
        else:    
            print("Error: ModeManager not set in VideoPreviewWidget.")  
  
    def set_display_options(self, show_manual: bool, show_auto: bool,     
                           show_ids: bool, show_confidence: bool, score_threshold: float = 0.2):    
        """表示オプションの設定"""    
        self.show_manual_annotations = show_manual    
        self.show_auto_annotations = show_auto    
        self.show_ids = show_ids    
        self.show_confidence = show_confidence    
        self.score_threshold = score_threshold    
        self.update_frame_display()    
            
    def set_frame(self, frame_id: int):    
        """指定フレームに移動"""    
        if not self.video_manager:    
            return    
            
        if self._updating_frame:    
            return    
            
        self._updating_frame = True    
        try:    
            self.current_frame_id = max(0, min(frame_id, self.video_manager.get_total_frames() - 1))    
     
            # フレーム変更時に選択状態をクリア    
            if self.bbox_editor.selected_annotation:    
                self.bbox_editor.selected_annotation = None    
                self.bbox_editor.selection_changed.emit(None)   
  
            self.update_frame_display()    
            self.frame_changed.emit(self.current_frame_id)    
        finally:    
            self._updating_frame = False    
        
    def update_frame_display(self):    
        """フレーム表示を更新"""    
        if not self.video_manager or not self.annotation_repository:    
            return    
                
        frame = self.video_manager.get_frame(self.current_frame_id)    
        if frame is None:    
            return    
                
        self.current_frame = frame.copy()    
            
        # 座標変換パラメータを更新    
        self.coordinate_transform.update_transform(    
            self.original_width / self.width(),    
            self.original_height / self.height(),    
            0, 0,    
            self.original_width, self.original_height    
        )    
            
        self.bbox_editor.set_coordinate_transform(self.coordinate_transform)    
            
        annotations_to_show = []    
            
        # モードに応じてアノテーションを選択    
        current_mode = self.mode_manager.current_mode_name    
            
        if current_mode == 'edit':    
            # EditMode: リポジトリのアノテーションのみ表示    
            frame_annotation = self.annotation_repository.get_annotations(self.current_frame_id)    
            if frame_annotation and frame_annotation.objects:    
                for annotation in frame_annotation.objects:    
                    if annotation.bbox.confidence < self.score_threshold:    
                        continue    
                    if (annotation.is_manual and self.show_manual_annotations) or \
                      (not annotation.is_manual and self.show_auto_annotations):    
                        annotations_to_show.append(annotation)    
                            
        elif current_mode == 'tracking':    
            # TrackingMode: 一時的なバッチアノテーションのみ表示    
            annotations_to_show.extend([    
                ann for ann in self.temp_tracking_annotations if ann.frame_id == self.current_frame_id    
            ])    
            
        # アノテーションを描画    
        if annotations_to_show:    
            self.current_frame = self.visualizer.draw_annotations(    
                self.current_frame, annotations_to_show,    
                show_ids=self.show_ids,    
                show_confidence=self.show_confidence,    
                selected_annotation=self.bbox_editor.selected_annotation    
            )    
            
        # 編集モードまたはTrackingModeの場合、選択オーバーレイを描画    
        current_mode = self.mode_manager.current_mode_name    
        if current_mode in ['edit', 'tracking']:    
            self.current_frame = self.bbox_editor.draw_selection_overlay(self.current_frame)    
                
        self._display_frame_on_widget(self.current_frame)  
            
    def _display_frame_on_widget(self, frame: np.ndarray):    
        """フレームをウィジェットに表示"""    
        self.original_height, self.original_width = frame.shape[:2]    
            
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)    
        h, w, ch = rgb_frame.shape    
        bytes_per_line = ch * w    
            
        qt_image = QImage(rgb_frame.data.tobytes(), w, h, bytes_per_line, QImage.Format.Format_RGB888)  
            
        widget_size = self.size()    
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(    
            widget_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation    
        )    
            
        # スケール比とオフセットを再計算し、CoordinateTransformを更新    
        self.coordinate_transform.update_transform(    
            self.original_width / scaled_pixmap.width(),    
            self.original_height / scaled_pixmap.height(),    
            (widget_size.width() - scaled_pixmap.width()) // 2,    
            (widget_size.height() - scaled_pixmap.height()) // 2,    
            self.original_width,    
            self.original_height    
        )    
            
        self.setPixmap(scaled_pixmap)    
            
    def mousePressEvent(self, event):    
        """マウス押下イベント"""    
        self.mode_manager.handle_mouse_event('press', event)    
        self.setCursor(self.mode_manager.get_cursor_shape())    
        self.update()  
            
    def mouseMoveEvent(self, event):    
        """マウス移動イベント"""    
        self.mode_manager.handle_mouse_event('move', event)    
        self.setCursor(self.mode_manager.get_cursor_shape())    
        self.update()  
            
    def mouseReleaseEvent(self, event):    
        """マウス離上イベント"""    
        self.mode_manager.handle_mouse_event('release', event)    
        self.setCursor(self.mode_manager.get_cursor_shape())    
        self.update()  
            
    def paintEvent(self, event):    
        """描画イベント"""    
        super().paintEvent(event)    
        painter = QPainter(self)    
            
        # BoundingBoxEditorに新規描画中の矩形を描画させる    
        self.bbox_editor.draw_new_bbox_overlay(painter)    
            
    # 移動された関数群  
    def on_bbox_created(self, x1: int, y1: int, x2: int, y2: int):  
        """バウンディングボックス作成時の処理（内部処理版）"""  
        bbox = BoundingBox(x1, y1, x2, y2)  
        current_frame = self.main_widget.video_control.current_frame  
          
        if self.mode_manager.current_mode_name == 'edit':  
            dialog = AnnotationInputDialog(bbox, self, existing_labels=self.annotation_repository.get_all_labels())  
            if dialog.exec() == QDialog.DialogCode.Accepted:  
                label = dialog.get_label()  
                if label:  
                    annotation = ObjectAnnotation(  
                        object_id=-1,  
                        frame_id=current_frame,  
                        bbox=bbox,  
                        label=label,  
                        is_manual=True,  
                        track_confidence=1.0,  
                        is_manual_added=True  
                    )  
                      
                    command = AddAnnotationCommand(self.annotation_repository, annotation)  
                    self.main_widget.command_manager.execute_command(command)  
                      
                    self.main_widget.update_annotation_count()  
                    ErrorHandler.show_info_dialog(f"Added annotation: {label} at frame {current_frame}", "Annotation Added")  
                      
                    self.bbox_editor.selected_annotation = annotation  
                    self.bbox_editor.selection_changed.emit(annotation)  
                    self.update_frame_display()  
                      
                    # オブジェクト一覧を更新  
                    frame_annotation = self.annotation_repository.get_annotations(current_frame)  
                    self.main_widget.menu_panel.update_current_frame_objects(current_frame, frame_annotation)  
                else:  
                    ErrorHandler.show_warning_dialog("Label cannot be empty.", "Input Error")  
        elif self.mode_manager.current_mode_name == 'tracking':  
            pass  
        else:  
            ErrorHandler.show_warning_dialog("bbox_created was called in an unknown mode.", "Warning") 
    def on_annotation_updated(self, annotation: ObjectAnnotation):  
        """アノテーション更新時の処理（内部処理版）"""  
        if hasattr(annotation, 'is_manual_added') and annotation.is_manual_added:  
            self.main_widget.update_annotation_count()  
            return  
          
        # 位置変更は別途bbox_position_updatedで処理されるため、ここでは他の更新のみ  
        if self.annotation_repository.update_annotation(annotation):  
            self.main_widget.update_annotation_count()  
        else:  
            ErrorHandler.show_warning_dialog("アノテーションの更新に失敗しました。", "Error")  
  
    def on_bbox_position_updated(self, annotation: ObjectAnnotation, old_bbox: BoundingBox, new_bbox: BoundingBox):  
        """バウンディングボックス位置更新時の処理（内部処理版）"""  
        # 位置に変更があった場合のみコマンドを実行  
        if (old_bbox.x1 != new_bbox.x1 or old_bbox.y1 != new_bbox.y1 or   
            old_bbox.x2 != new_bbox.x2 or old_bbox.y2 != new_bbox.y2):  
              
            command = UpdateBoundingBoxCommand(self.annotation_repository, annotation, old_bbox, new_bbox)  
            self.main_widget.command_manager.execute_command(command)  
              
            self.main_widget.update_annotation_count()  
            self.update_frame_display()  
              
            # オブジェクト一覧を更新  
            current_frame = self.main_widget.video_control.current_frame  
            frame_annotation = self.annotation_repository.get_annotations(current_frame)  
            self.main_widget.menu_panel.update_current_frame_objects(current_frame, frame_annotation)  
    
    def on_selection_changed(self, annotation):    
        """選択変更時の処理（内部処理版）"""   
        self.update_frame_display()   
        self.annotation_selected.emit(annotation)  
      
    def _on_config_changed(self, key: str, value: Any, config_type: str):    
        """ConfigManagerからの設定変更を処理"""    
        if config_type == "display":    
            if key == "show_manual_annotations":    
                self.show_manual_annotations = value    
            elif key == "show_auto_annotations":    
                self.show_auto_annotations = value    
            elif key == "show_ids":    
                self.show_ids = value    
            elif key == "show_confidence":    
                self.show_confidence = value    
            elif key == "score_threshold":    
                self.score_threshold = value    
            self.update_frame_display()  
      
    def _on_new_bbox_drawing_completed(self, x1, y1, x2, y2):    
        """新規バウンディングボックス描画完了時の処理"""    
        self.on_bbox_created(x1, y1, x2, y2)  
        self.update_frame_display()  
            
    def resizeEvent(self, event):    
        """ウィンドウサイズ変更時の処理"""    
        super().resizeEvent(event)    
        if self.current_frame is not None:    
            self.update_frame_display()    
  
    def clear_temp_tracking_annotations(self):    
        """一時的なバッチ追加アノテーションをクリア"""    
        self.temp_tracking_annotations.clear()    
        self.update_frame_display()  
  
    def add_temp_tracking_annotation(self, annotation: ObjectAnnotation):    
        """一時的なバッチ追加アノテーションを追加"""    
        self.temp_tracking_annotations.append(annotation)    
        self.update_frame_display()  

    def select_and_focus_annotation(self, annotation: Optional[ObjectAnnotation]):  
        """アノテーションを選択してフォーカス（統合版）"""  
        if hasattr(self, '_updating_selection') and self._updating_selection:  
            return  
        
        self._updating_selection = True  
        try:  
            if annotation:  
                # アノテーションが存在するフレームに移動（focus_on_annotationから）  
                if annotation.frame_id != self.current_frame_id:  
                    self.set_frame(annotation.frame_id)  
            
            # MenuPanelの情報を更新（on_annotation_selectedから）  
            self.main_widget.menu_panel.update_selected_annotation_info(annotation)  
            self.main_widget.menu_panel.update_object_list_selection(annotation)  
            
            # BoundingBoxEditorの選択状態を更新（両方から）  
            if hasattr(self, 'bbox_editor') and self.bbox_editor:  
                self.bbox_editor.selected_annotation = annotation  
                self.bbox_editor.selection_changed.emit(annotation)  
            
            # 表示を更新（両方から）  
            self.update_frame_display()  
            
            # Undo/Redoボタンの状態も更新（on_annotation_selectedから）  
            self.main_widget.menu_panel.update_undo_redo_buttons(self.main_widget.command_manager)  
        finally:  
            self._updating_selection = False

