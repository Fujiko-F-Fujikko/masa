# 改善されたVideoPreviewWidget.py  
import cv2  
import numpy as np  
from typing import Any, List
from PyQt6.QtWidgets import QLabel, QSizePolicy  
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QRect  
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor  
  
from AnnotationVisualizer import AnnotationVisualizer  
from BoundingBoxEditor import BoundingBoxEditor  
from CoordinateTransform import CoordinateTransform  
from ModeManager import ModeManager  
from ConfigManager import ConfigManager
from DataClass import ObjectAnnotation

class VideoPreviewWidget(QLabel):  
    """統合された動画プレビューウィジェット（改善版）"""  
      
    # シグナル定義  
    bbox_created = pyqtSignal(int, int, int, int)  # x1, y1, x2, y2  
    frame_changed = pyqtSignal(int)  # frame_id  
    annotation_selected = pyqtSignal(object)  # ObjectAnnotation  
    annotation_updated = pyqtSignal(object)  # ObjectAnnotation  
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.parent_ma_widget = parent
        self.setMinimumSize(640, 480) # 適切なデフォルトサイズ  
        self.setStyleSheet("border: 2px solid gray; background-color: black;")  
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  
          
        self.video_manager = None  
        self.annotation_repository = None # AnnotationRepositoryを使用  
        self.current_frame_id = 0  
        self.current_frame = None  
        self.original_width = 0  
        self.original_height = 0
          
        self.visualizer = AnnotationVisualizer()  
        self.bbox_editor = BoundingBoxEditor(self)  
        self.coordinate_transform = CoordinateTransform() # CoordinateTransformを使用  
        self.mode_manager = ModeManager(self) # ModeManagerを使用  
        self.bbox_editor = BoundingBoxEditor(self) # BoundingBoxEditorのインスタンス  
        self.bbox_editor.set_editing_mode(False) # 初期状態は編集モードOFF 

        self.config_manager = None # ConfigManagerへの参照を追加  
          
        # 表示オプションはConfigManagerから取得するように変更  
        self.show_manual_annotations = True  
        self.show_auto_annotations = True  
        self.show_ids = True  
        self.show_confidence = True  
        self.score_threshold = 0.2   
        
        self._updating_frame = False # 再帰防止フラグ  
        
        self.temp_batch_annotations: List[ObjectAnnotation] = []

        self._connect_signals()  
          
    def _connect_signals(self):  
        """内部シグナル接続"""  
        self.bbox_editor.annotation_updated.connect(self.on_annotation_updated)  
        self.bbox_editor.selection_changed.connect(self.on_selection_changed)  
        self.bbox_editor.new_bbox_drawing_completed.connect(self._on_new_bbox_drawing_completed)  
          
    def set_video_manager(self, video_manager):  
        """VideoManagerを設定"""  
        self.video_manager = video_manager  
        if video_manager:  
            self.current_frame_id = 0  
            self.update_frame_display()  

    def set_config_manager(self, config_manager: ConfigManager):  
        """ConfigManagerを設定"""  
        self.config_manager = config_manager  
        # 初期表示オプションをConfigManagerから取得  
        display_config = self.config_manager.get_full_config(config_type="display")  
        self.set_display_options(  
            display_config.show_manual_annotations,  
            display_config.show_auto_annotations,  
            display_config.show_ids,  
            display_config.show_confidence,  
            display_config.score_threshold  
        )  
        # ConfigManagerの変更を監視  
        self.config_manager.add_observer(self._on_config_changed)  

    def set_annotation_repository(self, annotation_repository):  
        """AnnotationRepositoryを設定"""  
        self.annotation_repository = annotation_repository  
  
    def set_mode(self, mode_name: str):  
        """モードを設定"""  
        if self.mode_manager:  
            self.mode_manager.set_mode(mode_name)  
            self.update_frame_display() # モード変更時に表示を更新  


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
                          
        elif current_mode == 'batch_add':  
            # BatchAddMode: 一時的なバッチアノテーションのみ表示  
            annotations_to_show.extend([  
                ann for ann in self.temp_batch_annotations if ann.frame_id == self.current_frame_id  
            ])  
          
        # アノテーションを描画  
        if annotations_to_show:  
            self.current_frame = self.visualizer.draw_annotations(  
                self.current_frame, annotations_to_show,  
                show_ids=self.show_ids,  
                show_confidence=self.show_confidence,  
                selected_annotation=self.bbox_editor.selected_annotation  
            )  
          
        # 編集モードまたはBatchAddModeの場合、選択オーバーレイを描画  
        current_mode = self.mode_manager.current_mode_name  
        if current_mode in ['edit', 'batch_add']:  
            self.current_frame = self.bbox_editor.draw_selection_overlay(self.current_frame)  
              
        self._display_frame_on_widget(self.current_frame)
          
    def _display_frame_on_widget(self, frame: np.ndarray):  
        """フレームをウィジェットに表示"""  
        self.original_height, self.original_width = frame.shape[:2]  
          
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  
        h, w, ch = rgb_frame.shape  
        bytes_per_line = ch * w  
          
        # PyQt6対応: データをbytes形式に変換
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
        self.update() # paintEventをトリガー  
          
    def mouseMoveEvent(self, event):  
        """マウス移動イベント"""  
        self.mode_manager.handle_mouse_event('move', event)  
        self.setCursor(self.mode_manager.get_cursor_shape())  
        self.update() # paintEventをトリガー  
          
    def mouseReleaseEvent(self, event):  
        """マウス離上イベント"""  
        self.mode_manager.handle_mouse_event('release', event)  
        self.setCursor(self.mode_manager.get_cursor_shape())  
        self.update() # paintEventをトリガー  
          
    def paintEvent(self, event):  
        """描画イベント"""  
        super().paintEvent(event)  
        painter = QPainter(self)  
          
        # BoundingBoxEditorに新規描画中の矩形を描画させる  
        self.bbox_editor.draw_new_bbox_overlay(painter)  
          
    def on_annotation_updated(self, annotation):  
        """アノテーション更新時の処理"""  
        self.annotation_repository.update_annotation(annotation) # リポジトリを更新  
        self.update_frame_display()  
        self.annotation_updated.emit(annotation)  
          
    def on_selection_changed(self, annotation):  
        """選択変更時の処理""" 
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
            self.update_frame_display() # 表示設定変更時にフレームを再描画
    
    def _on_new_bbox_drawing_completed(self, x1, y1, x2, y2):  
        """新規バウンディングボックス描画完了時の処理"""  
        self.bbox_created.emit(x1, y1, x2, y2)  
        self.update_frame_display() # 新規BBox追加後に表示を更新  
          
    def resizeEvent(self, event):  
        """ウィンドウサイズ変更時の処理"""  
        super().resizeEvent(event)  
        if self.current_frame is not None:  
            self.update_frame_display()  

    def clear_temp_batch_annotations(self):  
        """一時的なバッチ追加アノテーションを設定"""  
        self.temp_batch_annotations.clear()  
        self.update_frame_display() # 更新を反映

    def add_temp_batch_annotation(self, annotation: ObjectAnnotation):  
        """一時的なバッチ追加アノテーションを設定"""  
        self.temp_batch_annotations.append(annotation)  
        self.update_frame_display() # 更新を反映
