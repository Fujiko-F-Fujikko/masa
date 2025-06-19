from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,   
                            QLabel, QSlider, QFileDialog, QInputDialog,   
                            QMessageBox, QFrame, QLineEdit, QComboBox,   
                            QCheckBox, QTextEdit, QSpinBox, QDialog,   
                            QFormLayout, QDialogButtonBox, QSplitter,  
                            QListWidget, QListWidgetItem, QGroupBox,  
                            QProgressBar, QApplication)  
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QPoint, QThread  
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont, QBrush  
import sys  


import cv2  
import numpy as np  
import sys  
from typing import List, Dict, Optional, Tuple
from pathlib import Path  
import json  

from AutoAnnotation import (BoundingBox, ObjectAnnotation, FrameAnnotation, ObjectTracker, MASAConfig)

class VideoAnnotationManager:  
    """動画アノテーション管理クラス"""  
      
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
      
    def process_automatic_tracking(self, start_frame_id: int, end_frame_id: int = None) -> Dict[int, List[ObjectAnnotation]]:  
        """自動追跡処理を実行"""  
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
                # 追跡実行  
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
  
class AnnotationVisualizer:  
    """アノテーション可視化クラス"""  
      
    def __init__(self):  
        self.colors = self._generate_colors(100)  
      
    def _generate_colors(self, num_colors: int) -> List[Tuple[int, int, int]]:  
        """オブジェクトID用のカラーパレットを生成"""  
        colors = []  
        for i in range(num_colors):  
            hue = (i * 137.508) % 360  # Golden angle approximation  
            saturation = 0.7  
            value = 0.9  
              
            # HSVからRGBに変換  
            import colorsys  
            r, g, b = colorsys.hsv_to_rgb(hue/360, saturation, value)  
            colors.append((int(r*255), int(g*255), int(b*255)))  
          
        return colors  
      
    def draw_annotations(self, frame: np.ndarray, annotations: List[ObjectAnnotation],   
                        show_ids: bool = True, show_confidence: bool = True) -> np.ndarray:  
        """フレームにアノテーションを描画（座標精度を向上）"""  
        result_frame = frame.copy()  
          
        for annotation in annotations:  
            color = self.colors[annotation.object_id % len(self.colors)]  
              
            # バウンディングボックス座標を整数に変換（四捨五入）  
            pt1 = (int(round(annotation.bbox.x1)), int(round(annotation.bbox.y1)))  
            pt2 = (int(round(annotation.bbox.x2)), int(round(annotation.bbox.y2)))  
              
            # 画像境界内にクリップ  
            h, w = frame.shape[:2]  
            pt1 = (max(0, min(pt1[0], w-1)), max(0, min(pt1[1], h-1)))  
            pt2 = (max(0, min(pt2[0], w-1)), max(0, min(pt2[1], h-1)))  
              
            # 手動アノテーションは太い線、自動は細い線  
            thickness = 3 if annotation.is_manual else 2  
            cv2.rectangle(result_frame, pt1, pt2, color, thickness)  
              
            # ラベルとIDを描画  
            label_text = annotation.label  
            if show_ids:  
                label_text += f" ID:{annotation.object_id}"  
            if show_confidence:  
                label_text += f" ({annotation.bbox.confidence:.2f})"
              
            # テキスト背景  
            (text_width, text_height), _ = cv2.getTextSize(  
                label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2  
            )  
              
            cv2.rectangle(  
                result_frame,  
                (pt1[0], pt1[1] - text_height - 10),  
                (pt1[0] + text_width, pt1[1]),  
                color,  
                -1  
            )  
              
            # テキスト描画  
            cv2.putText(  
                result_frame,  
                label_text,  
                (pt1[0], pt1[1] - 5),  
                cv2.FONT_HERSHEY_SIMPLEX,  
                0.6,  
                (255, 255, 255),  
                2  
            )  
          
        return result_frame  
      
    def create_annotation_video(self, video_manager: VideoAnnotationManager,   
                              output_path: str, fps: int = 30):  
        """アノテーション付き動画を作成"""  
        if not video_manager.frame_annotations:  
            print("No annotations to visualize")  
            return  
          
        # 最初のフレームで動画サイズを取得  
        first_frame = video_manager.get_frame(0)  
        if first_frame is None:  
            print("Cannot read first frame")  
            return  
          
        height, width = first_frame.shape[:2]  
          
        # 動画ライターを初期化  
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))  
          
        try:  
            for frame_id in range(video_manager.total_frames):  
                frame = video_manager.get_frame(frame_id)  
                if frame is None:  
                    continue  
                  
                # アノテーションを取得して描画  
                frame_annotation = video_manager.get_frame_annotations(frame_id)  
                if frame_annotation and frame_annotation.objects:  
                    annotated_frame = self.draw_annotations(frame, frame_annotation.objects)  
                else:  
                    annotated_frame = frame  
                  
                out.write(annotated_frame)  
                  
                if frame_id % 100 == 0:  
                    print(f"Processed frame {frame_id}/{video_manager.total_frames}")  
              
            print(f"Annotated video saved to {output_path}")  
              
        finally:  
            out.release()

class UnifiedVideoPreviewWidget(QLabel):  
    """統合された動画プレビューウィジェット"""  
      
    # シグナル定義  
    bbox_created = pyqtSignal(int, int, int, int)  # x1, y1, x2, y2  
    frame_changed = pyqtSignal(int)  # frame_id  
    range_selection_changed = pyqtSignal(int, int)  # start_frame, end_frame  
    multi_frame_bbox_created = pyqtSignal(int, int, int, int, int)  # x1, y1, x2, y2, frame_id 
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.setMinimumSize(800, 600)  
        self.setStyleSheet("border: 2px solid gray; background-color: black;")  
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)  
          
        # 動画関連  
        self.video_manager = None  
        self.current_frame_id = 0  
        self.current_frame = None  
          
        # 描画関連  
        self.drawing = False  
        self.start_point = QPoint()  
        self.end_point = QPoint()  
        self.current_rect = QRect()  
        self.scale_x = 1.0  
        self.scale_y = 1.0  
        self.offset_x = 0  
        self.offset_y = 0  
        self.original_width = 0  
        self.original_height = 0  
          
        # 表示モード  
        self.annotation_mode = False  # アノテーション作成モード  
        self.range_selection_mode = False  # 範囲選択モード  
        self.result_view_mode = False  # 結果確認モード  
          
        # 範囲選択関連  
        self.range_start_frame = 0  
        self.range_end_frame = 0  
        self.range_selecting = False  
          
        # 表示オプション  
        self.show_manual_annotations = True  
        self.show_auto_annotations = True  
        self.show_ids = True  
        self.show_confidence = True  
        
        # 新しいモード追加 
        self.multi_frame_mode = False  # 複数フレームアノテーションモード  
        self.current_multi_frame_label = ""  
        self.multi_frame_annotations = []  # 現在作成中の複数フレームアノテーション  

        # 可視化  
        self.visualizer = AnnotationVisualizer()  

    def set_multi_frame_mode(self, enabled: bool, label: str = ""):  
        """複数フレームアノテーションモードの設定"""  
        self.multi_frame_mode = enabled  
        self.annotation_mode = False  
        self.range_selection_mode = False  
        self.result_view_mode = False  
        self.current_multi_frame_label = label  
          
        if enabled:  
            self.setCursor(Qt.CursorShape.CrossCursor)  
            # 既存の複数フレームアノテーションをクリア  
            self.multi_frame_annotations.clear()  
        else:  
            self.setCursor(Qt.CursorShape.ArrowCursor) 

    def set_video_manager(self, video_manager: VideoAnnotationManager):  
        """動画マネージャーを設定"""  
        self.video_manager = video_manager  
        if video_manager:  
            self.current_frame_id = 0  
            self.update_frame_display()  
      
    def set_annotation_mode(self, enabled: bool):  
        """アノテーション作成モードの設定"""  
        self.annotation_mode = enabled  
        self.range_selection_mode = False  
        self.result_view_mode = False  
        self.setCursor(Qt.CursorShape.CrossCursor if enabled else Qt.CursorShape.ArrowCursor)  
      
    def set_range_selection_mode(self, enabled: bool):  
        """範囲選択モードの設定"""  
        self.range_selection_mode = enabled  
        self.annotation_mode = False  
        self.result_view_mode = False  
        if enabled:  
            self.range_start_frame = self.current_frame_id  
            self.range_end_frame = self.current_frame_id  
      
    def set_result_view_mode(self, enabled: bool):  
        """結果確認モードの設定"""  
        self.result_view_mode = enabled  
        self.annotation_mode = False  
        self.range_selection_mode = False  
        self.update_frame_display()  
      
    def set_display_options(self, show_manual: bool, show_auto: bool,   
                           show_ids: bool, show_confidence: bool):  
        """表示オプションの設定"""  
        self.show_manual_annotations = show_manual  
        self.show_auto_annotations = show_auto  
        self.show_ids = show_ids  
        self.show_confidence = show_confidence  
        self.update_frame_display()  
      
    def set_frame(self, frame_id: int):  
        """指定フレームに移動"""  
        if not self.video_manager:  
            return  
          
        self.current_frame_id = max(0, min(frame_id, self.video_manager.total_frames - 1))  
        self.update_frame_display()  
        self.frame_changed.emit(self.current_frame_id)  
          
        # 範囲選択モードの場合  
        if self.range_selection_mode:  
            self.range_end_frame = self.current_frame_id  
            self.range_selection_changed.emit(  
                min(self.range_start_frame, self.range_end_frame),  
                max(self.range_start_frame, self.range_end_frame)  
            )  
      
    def update_frame_display(self):  
        """フレーム表示を更新"""  
        if not self.video_manager:  
            return  
          
        frame = self.video_manager.get_frame(self.current_frame_id)  
        if frame is None:  
            return  
          
        self.current_frame = frame.copy()  
      
        # 複数フレームモードの場合、作成中のアノテーションを表示  
        if self.multi_frame_mode and self.multi_frame_annotations:  
            frame = self._draw_multi_frame_annotations(frame)  
          
        # 結果確認モードの場合、アノテーションを描画  
        if self.result_view_mode:  
            frame_annotation = self.video_manager.get_frame_annotations(self.current_frame_id)  
            if frame_annotation and frame_annotation.objects:  
                annotations_to_show = []  
                  
                for annotation in frame_annotation.objects:  
                    if annotation.is_manual and self.show_manual_annotations:  
                        annotations_to_show.append(annotation)  
                    elif not annotation.is_manual and self.show_auto_annotations:  
                        annotations_to_show.append(annotation)  
                  
                if annotations_to_show:  
                    frame = self.visualizer.draw_annotations(  
                        frame, annotations_to_show,  
                        show_ids=self.show_ids,  
                        show_confidence=self.show_confidence  
                    )  
          
        # 範囲選択モードの場合、範囲を視覚的に表示  
        if self.range_selection_mode:  
            frame = self._draw_range_indicator(frame)  
          
        self._display_frame_on_widget(frame)  

    def _draw_multi_frame_annotations(self, frame: np.ndarray) -> np.ndarray:  
        """作成中の複数フレームアノテーションを描画"""  
        result_frame = frame.copy()  
          
        for annotation in self.multi_frame_annotations:  
            if annotation['frame_id'] == self.current_frame_id:  
                # 現在のフレームのアノテーションを緑色で描画  
                color = (0, 255, 0)  
                thickness = 3  
            else:  
                # 他のフレームのアノテーションを薄い緑色で描画（参考用）  
                color = (0, 200, 0)  
                thickness = 1  
              
            bbox = annotation['bbox']  
            pt1 = (int(bbox.x1), int(bbox.y1))  
            pt2 = (int(bbox.x2), int(bbox.y2))  
            cv2.rectangle(result_frame, pt1, pt2, color, thickness)  
              
            # フレーム番号を表示  
            cv2.putText(result_frame, f"F{annotation['frame_id']}",   
                       (pt1[0], pt1[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)  
          
        return result_frame
      
    def _draw_range_indicator(self, frame: np.ndarray) -> np.ndarray:  
        """範囲選択の視覚的インジケーターを描画"""  
        result_frame = frame.copy()  
          
        # 範囲内のフレームかどうかで色を変える  
        start_frame = min(self.range_start_frame, self.range_end_frame)  
        end_frame = max(self.range_start_frame, self.range_end_frame)  
          
        if start_frame <= self.current_frame_id <= end_frame:  
            # 範囲内：緑の枠  
            color = (0, 255, 0)  
            thickness = 5  
        else:  
            # 範囲外：赤の枠  
            color = (255, 0, 0)  
            thickness = 3  
          
        h, w = result_frame.shape[:2]  
        cv2.rectangle(result_frame, (10, 10), (w-10, h-10), color, thickness)  
          
        # 範囲情報をテキストで表示  
        range_text = f"Range: {start_frame} - {end_frame} (Current: {self.current_frame_id})"  
        cv2.putText(result_frame, range_text, (20, 50),   
                   cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)  
          
        return result_frame  
      
    def _display_frame_on_widget(self, frame: np.ndarray):  
        """フレームをウィジェットに表示"""  
        # 元の画像サイズを保存  
        self.original_height, self.original_width = frame.shape[:2]  
          
        # OpenCV BGR to RGB  
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  
        h, w, ch = rgb_frame.shape  
        bytes_per_line = ch * w  
          
        # QImageに変換  
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)  
          
        # ウィジェットサイズに合わせてスケール（アスペクト比を保持）  
        widget_size = self.size()  
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(  
            widget_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation  
        )  
          
        # スケール比とオフセットを計算  
        self.scale_x = self.original_width / scaled_pixmap.width()  
        self.scale_y = self.original_height / scaled_pixmap.height()  
          
        # 中央配置のためのオフセットを計算  
        self.offset_x = (widget_size.width() - scaled_pixmap.width()) // 2  
        self.offset_y = (widget_size.height() - scaled_pixmap.height()) // 2  
          
        self.setPixmap(scaled_pixmap)  
      
    def mousePressEvent(self, event):  
        """マウス押下イベント"""  
        # 複数フレームモードまたは通常のアノテーションモードの場合のみ処理  
        if (not self.annotation_mode and not self.multi_frame_mode) or event.button() != Qt.MouseButton.LeftButton:  
            return  
          
        self.drawing = True  
        self.start_point = event.position().toPoint()  
        self.current_rect = QRect()  
      
    def mouseMoveEvent(self, event):  
        """マウス移動イベント"""  
        if not self.drawing:  
            return  
          
        self.end_point = event.position().toPoint()  
        self.current_rect = QRect(self.start_point, self.end_point).normalized()  
        self.update()  
      
    def mouseReleaseEvent(self, event):  
        """マウス離上イベント"""  
        if not self.drawing or event.button() != Qt.MouseButton.LeftButton:  
            return  
          
        self.drawing = False  
        self.end_point = event.position().toPoint()  
          
        # 最終的な矩形を計算  
        rect = QRect(self.start_point, self.end_point).normalized()  
          
        # オフセットを考慮して座標を調整  
        adjusted_x1 = max(0, rect.x() - self.offset_x)  
        adjusted_y1 = max(0, rect.y() - self.offset_y)  
        adjusted_x2 = max(0, (rect.x() + rect.width()) - self.offset_x)  
        adjusted_y2 = max(0, (rect.y() + rect.height()) - self.offset_y)  
          
        # 元の画像座標系に変換  
        x1 = int(adjusted_x1 * self.scale_x)  
        y1 = int(adjusted_y1 * self.scale_y)  
        x2 = int(adjusted_x2 * self.scale_x)  
        y2 = int(adjusted_y2 * self.scale_y)  
          
        # 画像境界内にクリップ  
        x1 = max(0, min(x1, self.original_width))  
        y1 = max(0, min(y1, self.original_height))  
        x2 = max(0, min(x2, self.original_width))  
        y2 = max(0, min(y2, self.original_height))  
          
        # 有効なバウンディングボックスかチェック  
        if abs(x2 - x1) > 10 and abs(y2 - y1) > 10:  
            if self.multi_frame_mode:  
                # 複数フレームモードの場合  
                self.multi_frame_bbox_created.emit(x1, y1, x2, y2, self.current_frame_id)  
            else:  
                # 通常のアノテーションモード  
                self.bbox_created.emit(x1, y1, x2, y2)  
          
        self.current_rect = QRect()  
        self.update()
      
    def paintEvent(self, event):  
        """描画イベント"""  
        super().paintEvent(event)  
          
        if self.drawing and not self.current_rect.isEmpty():  
            painter = QPainter(self)  
            pen = QPen(QColor(255, 0, 0), 2, Qt.PenStyle.SolidLine)  
            painter.setPen(pen)  
            painter.drawRect(self.current_rect)

class MenuPanel(QWidget):  
    """左側のメニューパネル"""  
      
    # シグナル定義  
    load_video_requested = pyqtSignal()  
    annotation_mode_requested = pyqtSignal(bool)  
    range_selection_requested = pyqtSignal(bool)  
    result_view_requested = pyqtSignal(bool)  
    tracking_requested = pyqtSignal()  
    export_requested = pyqtSignal(str)  # format  
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.setFixedWidth(250)  
        self.setStyleSheet("background-color: #f0f0f0; border-right: 1px solid #ccc;")  
        self.setup_ui()  
          
    def setup_ui(self):  
        layout = QVBoxLayout()  
        layout.setSpacing(10)  
        layout.setContentsMargins(10, 10, 10, 10)  
          
        # タイトル  
        title_label = QLabel("MASA Annotation Tool")  
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))  
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        layout.addWidget(title_label)  
          
        # 動画読み込みセクション  
        video_group = QGroupBox("Video")  
        video_layout = QVBoxLayout()  
          
        self.load_video_btn = QPushButton("Load Video")  
        self.load_video_btn.clicked.connect(self.load_video_requested.emit)  
        video_layout.addWidget(self.load_video_btn)  
          
        self.video_info_label = QLabel("No video loaded")  
        self.video_info_label.setWordWrap(True)  
        self.video_info_label.setStyleSheet("color: #666; font-size: 10px;")  
        video_layout.addWidget(self.video_info_label)  
          
        video_group.setLayout(video_layout)  
        layout.addWidget(video_group)  
          
        # アノテーションセクション  
        self.annotation_group = QGroupBox("Annotation")  
        annotation_layout = QVBoxLayout()  
          
        self.annotation_mode_btn = QPushButton("Manual Annotation Mode")  
        self.annotation_mode_btn.setCheckable(True)  
        self.annotation_mode_btn.clicked.connect(self._on_annotation_mode_clicked)  
        self.annotation_mode_btn.setEnabled(False)  
        annotation_layout.addWidget(self.annotation_mode_btn)  
          
        self.annotation_count_label = QLabel("Annotations: 0")  
        self.annotation_count_label.setStyleSheet("color: #666; font-size: 10px;")  
        annotation_layout.addWidget(self.annotation_count_label)  
          
        self.annotation_group.setLayout(annotation_layout)  
        layout.addWidget(self.annotation_group)  
          
        # 範囲選択セクション  
        range_group = QGroupBox("Frame Range")  
        range_layout = QVBoxLayout()  
          
        self.range_selection_btn = QPushButton("Select Range Mode")  
        self.range_selection_btn.setCheckable(True)  
        self.range_selection_btn.clicked.connect(self._on_range_selection_clicked)  
        self.range_selection_btn.setEnabled(False)  
        range_layout.addWidget(self.range_selection_btn)  
          
        self.range_info_label = QLabel("Range: Not selected")  
        self.range_info_label.setStyleSheet("color: #666; font-size: 10px;")  
        range_layout.addWidget(self.range_info_label)  
          
        range_group.setLayout(range_layout)  
        layout.addWidget(range_group)  
          
        # 自動追跡セクション  
        tracking_group = QGroupBox("Auto Tracking")  
        tracking_layout = QVBoxLayout()  
          
        self.tracking_btn = QPushButton("Start Auto Tracking")  
        self.tracking_btn.clicked.connect(self.tracking_requested.emit)  
        self.tracking_btn.setEnabled(False)  
        tracking_layout.addWidget(self.tracking_btn)  
          
        self.tracking_progress_label = QLabel("")  
        self.tracking_progress_label.setStyleSheet("color: #666; font-size: 10px;")  
        tracking_layout.addWidget(self.tracking_progress_label)  
          
        tracking_group.setLayout(tracking_layout)  
        layout.addWidget(tracking_group)  
          
        # 結果確認セクション  
        result_group = QGroupBox("Results")  
        result_layout = QVBoxLayout()  
          
        self.result_view_btn = QPushButton("View Results Mode")  
        self.result_view_btn.setCheckable(True)  
        self.result_view_btn.clicked.connect(self._on_result_view_clicked)  
        self.result_view_btn.setEnabled(False)  
        result_layout.addWidget(self.result_view_btn)  
          
        # 表示オプション  
        self.show_manual_cb = QCheckBox("Show Manual")  
        self.show_manual_cb.setChecked(True)  
        result_layout.addWidget(self.show_manual_cb)  
          
        self.show_auto_cb = QCheckBox("Show Auto")  
        self.show_auto_cb.setChecked(True)  
        result_layout.addWidget(self.show_auto_cb)  
          
        self.show_ids_cb = QCheckBox("Show IDs")  
        self.show_ids_cb.setChecked(True)  
        result_layout.addWidget(self.show_ids_cb)  
          
        self.show_confidence_cb = QCheckBox("Show Confidence")  
        self.show_confidence_cb.setChecked(True)  
        result_layout.addWidget(self.show_confidence_cb)  
        
        checkbox_style = """  
        QCheckBox {  
            color: #333333;  
            font-weight: bold;  
        }  
        QCheckBox::indicator {  
            width: 18px;  
            height: 18px;  
        }  
        QCheckBox::indicator:unchecked {  
            background-color: #ffffff;  
            border: 2px solid #cccccc;  
            border-radius: 3px;  
        }  
        QCheckBox::indicator:checked {  
            background-color: #4CAF50;  
            border: 2px solid #45a049;  
            border-radius: 3px;  
        }  
        QCheckBox::indicator:checked:hover {  
            background-color: #45a049;  
        }  
        QCheckBox::indicator:unchecked:hover {  
            border: 2px solid #999999;  
        }  
        """  
          
        # 各チェックボックスにスタイルを適用  
        self.show_manual_cb.setStyleSheet(checkbox_style)  
        self.show_auto_cb.setStyleSheet(checkbox_style)  
        self.show_ids_cb.setStyleSheet(checkbox_style)  
        self.show_confidence_cb.setStyleSheet(checkbox_style)
          
        result_group.setLayout(result_layout)  
        layout.addWidget(result_group)  
          
        # エクスポートセクション  
        export_group = QGroupBox("Export")  
        export_layout = QVBoxLayout()  
          
        self.export_json_btn = QPushButton("Export JSON")  
        self.export_json_btn.clicked.connect(lambda: self.export_requested.emit("json"))  
        self.export_json_btn.setEnabled(False)  
        export_layout.addWidget(self.export_json_btn)  
          
        self.export_coco_btn = QPushButton("Export COCO")  
        self.export_coco_btn.clicked.connect(lambda: self.export_requested.emit("coco"))  
        self.export_coco_btn.setEnabled(False)  
        export_layout.addWidget(self.export_coco_btn)  
          
        export_group.setLayout(export_layout)  
        layout.addWidget(export_group)  
          
        # スペーサー  
        layout.addStretch()  
          
        self.setLayout(layout)  
      
    def _on_annotation_mode_clicked(self, checked):  
        if checked:  
            self.range_selection_btn.setChecked(False)  
            self.result_view_btn.setChecked(False)  
        self.annotation_mode_requested.emit(checked)  
      
    def _on_range_selection_clicked(self, checked):  
        if checked:  
            self.annotation_mode_btn.setChecked(False)  
            self.result_view_btn.setChecked(False)  
        self.range_selection_requested.emit(checked)  
      
    def _on_result_view_clicked(self, checked):  
        if checked:  
            self.annotation_mode_btn.setChecked(False)  
            self.range_selection_btn.setChecked(False)  
        self.result_view_requested.emit(checked)  
      
    def update_video_info(self, video_path: str, total_frames: int):  
        """動画情報を更新"""  
        filename = Path(video_path).name  
        self.video_info_label.setText(f"{filename}\n{total_frames} frames")  
          
        # ボタンを有効化  
        self.annotation_mode_btn.setEnabled(True)  
        self.range_selection_btn.setEnabled(True)  
      
    def update_annotation_count(self, count: int):  
        """アノテーション数を更新"""  
        self.annotation_count_label.setText(f"Annotations: {count}")  
        self.tracking_btn.setEnabled(count > 0)  
      
    def update_range_info(self, start_frame: int, end_frame: int):  
        """範囲情報を更新"""  
        self.range_info_label.setText(f"Range: {start_frame} - {end_frame}")  
      
    def update_tracking_progress(self, progress_text: str):  
        """追跡進捗を更新"""  
        self.tracking_progress_label.setText(progress_text)  
      
    def enable_result_view(self, enabled: bool):  
        """結果確認モードを有効化"""  
        self.result_view_btn.setEnabled(enabled)  
        self.export_json_btn.setEnabled(enabled)  
        self.export_coco_btn.setEnabled(enabled)  
      
    def get_display_options(self) -> Dict[str, bool]:  
        """表示オプションを取得"""  
        return {  
            'show_manual': self.show_manual_cb.isChecked(),  
            'show_auto': self.show_auto_cb.isChecked(),  
            'show_ids': self.show_ids_cb.isChecked(),  
            'show_confidence': self.show_confidence_cb.isChecked()  
        }  
  
class VideoControlPanel(QWidget):  
    """動画制御パネル"""  
      
    frame_changed = pyqtSignal(int)  
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.total_frames = 0  
        self.current_frame = 0  
        self.setup_ui()  
          
    def setup_ui(self):  
        layout = QVBoxLayout()  
        layout.setContentsMargins(5, 5, 5, 5)  
          
        # フレーム情報  
        self.frame_info_label = QLabel("Frame: 0 / 0")  
        self.frame_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        layout.addWidget(self.frame_info_label)  
          
        # フレームスライダー  
        control_layout = QHBoxLayout()  
          
        self.prev_btn = QPushButton("◀")  
        self.prev_btn.setFixedSize(30, 30)  
        self.prev_btn.clicked.connect(self.prev_frame)  
        control_layout.addWidget(self.prev_btn)  
          
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)  
        self.frame_slider.setMinimum(0)  
        self.frame_slider.valueChanged.connect(self.on_frame_changed)  
        control_layout.addWidget(self.frame_slider)  
          
        self.next_btn = QPushButton("▶")  
        self.next_btn.setFixedSize(30, 30)  
        self.next_btn.clicked.connect(self.next_frame)  
        control_layout.addWidget(self.next_btn)  
          
        layout.addLayout(control_layout)  
        self.setLayout(layout)  
      
    def set_total_frames(self, total_frames: int):  
        """総フレーム数を設定"""  
        self.total_frames = total_frames  
        self.frame_slider.setMaximum(total_frames - 1)  
        self.update_frame_info()  
      
    def set_current_frame(self, frame_id: int):  
        """現在のフレームを設定"""  
        self.current_frame = frame_id  
        self.frame_slider.setValue(frame_id)  
        self.update_frame_info()  
      
    def on_frame_changed(self, frame_id: int):  
        """フレーム変更イベント"""  
        self.current_frame = frame_id  
        self.update_frame_info()  
        self.frame_changed.emit(frame_id)  
      
    def prev_frame(self):  
        """前のフレームに移動"""  
        if self.current_frame > 0:  
            self.set_current_frame(self.current_frame - 1)  
      
    def next_frame(self):  
        """次のフレームに移動"""  
        if self.current_frame < self.total_frames - 1:  
            self.set_current_frame(self.current_frame + 1)  
      
    def update_frame_info(self):  
        """フレーム情報を更新"""  
        self.frame_info_label.setText(f"Frame: {self.current_frame} / {self.total_frames - 1}")  
  
class AnnotationInputDialog(QDialog):  
    """アノテーション入力ダイアログ"""  
      
    def __init__(self, bbox: BoundingBox, parent=None):  
        super().__init__(parent)  
        self.bbox = bbox  
        self.label = ""  
        self.setup_ui()  
          
    def setup_ui(self):  
        self.setWindowTitle("Add Annotation")  
        self.setModal(True)  
          
        layout = QVBoxLayout()  
          
        # バウンディングボックス情報  
        bbox_info = QLabel(f"Bounding Box: ({self.bbox.x1:.0f}, {self.bbox.y1:.0f}) to ({self.bbox.x2:.0f}, {self.bbox.y2:.0f})")  
        layout.addWidget(bbox_info)  
          
        # ラベル入力  
        label_layout = QHBoxLayout()  
        label_layout.addWidget(QLabel("Label:"))  
          
        self.label_input = QLineEdit()  
        self.label_input.setPlaceholderText("Enter object label (e.g., person, car)")  
        label_layout.addWidget(self.label_input)  
          
        # プリセット  
        self.preset_combo = QComboBox()  
        self.preset_combo.addItems(["", "person", "car", "bicycle", "dog", "cat", "bird"])  
        self.preset_combo.currentTextChanged.connect(self.on_preset_selected)  
        label_layout.addWidget(self.preset_combo)  
          
        layout.addLayout(label_layout)  
          
        # ボタン  
        buttons = QDialogButtonBox(  
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel  
        )  
        buttons.accepted.connect(self.accept)  
        buttons.rejected.connect(self.reject)  
        layout.addWidget(buttons)  
          
        self.setLayout(layout)  
          
        # フォーカスをラベル入力に設定  
        self.label_input.setFocus()  
      
    def on_preset_selected(self, text):  
        if text:  
            self.label_input.setText(text)  
      
    def get_label(self) -> str:  
        return self.label_input.text().strip()

class TrackingSettingsDialog(QDialog):  
    """自動追跡設定ダイアログ"""  
      
    def __init__(self, total_frames: int, start_frame: int, parent=None):  
        super().__init__(parent)  
        self.total_frames = total_frames  
        self.start_frame = start_frame  
        self.setup_ui()  
          
    def setup_ui(self):  
        self.setWindowTitle("Auto Tracking Settings")  
        self.setModal(True)  
          
        layout = QFormLayout()  
          
        # 開始フレーム表示（読み取り専用）  
        self.start_frame_label = QLabel(str(self.start_frame))  
        layout.addRow("Start Frame:", self.start_frame_label)  
          
        # 終了フレーム指定  
        self.end_frame_spin = QSpinBox()  
        self.end_frame_spin.setMinimum(self.start_frame + 1)  
        self.end_frame_spin.setMaximum(self.total_frames - 1)  
        self.end_frame_spin.setValue(min(self.start_frame + 100, self.total_frames - 1))  
        layout.addRow("End Frame:", self.end_frame_spin)  
          
        # フレーム数表示  
        self.frame_count_label = QLabel()  
        self.update_frame_count()  
        self.end_frame_spin.valueChanged.connect(self.update_frame_count)  
        layout.addRow("Total Frames to Process:", self.frame_count_label)  
          
        # 推定処理時間表示  
        self.time_estimate_label = QLabel()  
        self.update_time_estimate()  
        self.end_frame_spin.valueChanged.connect(self.update_time_estimate)  
        layout.addRow("Estimated Time:", self.time_estimate_label)  
          
        # ボタン  
        buttons = QDialogButtonBox(  
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel  
        )  
        buttons.accepted.connect(self.accept)  
        buttons.rejected.connect(self.reject)  
        layout.addRow(buttons)  
          
        self.setLayout(layout)  
      
    def update_frame_count(self):  
        frame_count = self.end_frame_spin.value() - self.start_frame + 1  
        self.frame_count_label.setText(str(frame_count))  
      
    def update_time_estimate(self):  
        frame_count = self.end_frame_spin.value() - self.start_frame + 1  
        # 1フレームあたり約0.1-0.5秒と仮定  
        estimated_seconds = frame_count * 0.3  
        if estimated_seconds < 60:  
            time_text = f"{estimated_seconds:.1f} seconds"  
        else:  
            minutes = estimated_seconds / 60  
            time_text = f"{minutes:.1f} minutes"  
        self.time_estimate_label.setText(time_text)  
      
    def get_end_frame(self):  
        return self.end_frame_spin.value()  
  
class UnifiedMASAAnnotationWidget(QWidget):  
    """統合されたMASAアノテーションメインウィジェット"""  
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.video_manager = None  
        self.pending_bbox = None  
        self.setup_ui()  
          
    def setup_ui(self):  
        self.setWindowTitle("MASA Video Annotation Tool")  
        self.setGeometry(100, 100, 1400, 900)  
          
        # メインレイアウト（水平分割）  
        main_layout = QHBoxLayout()  
          
        # 左側：メニューパネル  
        self.menu_panel = MenuPanel()  
        main_layout.addWidget(self.menu_panel)  
          
        # 右側：動画プレビューエリア  
        right_layout = QVBoxLayout()  
          
        # 動画プレビューウィジェット  
        self.video_preview = UnifiedVideoPreviewWidget()  
        right_layout.addWidget(self.video_preview)  
          
        # 動画制御パネル  
        self.video_control = VideoControlPanel()  
        right_layout.addWidget(self.video_control)  
          
        # 右側レイアウトをウィジェットに包む  
        right_widget = QWidget()  
        right_widget.setLayout(right_layout)  
        main_layout.addWidget(right_widget)  
          
        # レイアウト比率設定（左：右 = 1：3）  
        main_layout.setStretch(0, 1)  
        main_layout.setStretch(1, 3)  
          
        self.setLayout(main_layout)  
          
        # シグナル接続  
        self.connect_signals()  
      
    def connect_signals(self):  
        """シグナルとスロットを接続"""  
        # メニューパネルからのシグナル  
        self.menu_panel.load_video_requested.connect(self.load_video)  
        self.menu_panel.annotation_mode_requested.connect(self.set_annotation_mode)  
        self.menu_panel.range_selection_requested.connect(self.set_range_selection_mode)  
        self.menu_panel.result_view_requested.connect(self.set_result_view_mode)  
        self.menu_panel.tracking_requested.connect(self.start_tracking)  
        self.menu_panel.export_requested.connect(self.export_annotations)  
          
        # 動画プレビューからのシグナル  
        self.video_preview.bbox_created.connect(self.on_bbox_created)  
        self.video_preview.frame_changed.connect(self.on_frame_changed)  
        self.video_preview.range_selection_changed.connect(self.on_range_selection_changed)  
          
        # 動画制御からのシグナル  
        self.video_control.frame_changed.connect(self.video_preview.set_frame)  
          
        # 表示オプションの変更  
        for checkbox in [self.menu_panel.show_manual_cb, self.menu_panel.show_auto_cb,  
                        self.menu_panel.show_ids_cb, self.menu_panel.show_confidence_cb]:  
            checkbox.stateChanged.connect(self.update_display_options)  
      
    def load_video(self):  
        """動画ファイルを読み込み"""  
        file_path, _ = QFileDialog.getOpenFileName(  
            self, "Select Video File", "",   
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"  
        )  
          
        if file_path:  
            config = MASAConfig()  
            self.video_manager = VideoAnnotationManager(file_path, config)  
              
            if self.video_manager.load_video():  
                # 動画プレビューに設定  
                self.video_preview.set_video_manager(self.video_manager)  
                  
                # 動画制御パネルに設定  
                self.video_control.set_total_frames(self.video_manager.total_frames)  
                self.video_control.set_current_frame(0)  
                  
                # メニューパネルの情報更新  
                self.menu_panel.update_video_info(file_path, self.video_manager.total_frames)  
                  
                QMessageBox.information(self, "Success", f"Video loaded: {file_path}")  
            else:  
                QMessageBox.critical(self, "Error", "Failed to load video file")  
      
    def set_annotation_mode(self, enabled: bool):  
        """アノテーションモードの設定"""  
        self.video_preview.set_annotation_mode(enabled)  
        if enabled:  
            QMessageBox.information(  
                self, "Annotation Mode",   
                "Click and drag on the video to create bounding boxes.\n"  
                "You will be prompted to enter labels for each annotation."  
            )  
      
    def set_range_selection_mode(self, enabled: bool):  
        """範囲選択モードの設定"""  
        self.video_preview.set_range_selection_mode(enabled)  
        if enabled:  
            QMessageBox.information(  
                self, "Range Selection Mode",   
                "Use the frame slider to select the range for auto tracking.\n"  
                "The selected range will be highlighted on the video."  
            )  
      
    def set_result_view_mode(self, enabled: bool):  
        """結果確認モードの設定"""  
        self.video_preview.set_result_view_mode(enabled)  
        self.update_display_options()  
      
    def on_bbox_created(self, x1: int, y1: int, x2: int, y2: int):  
        """バウンディングボックス作成時の処理"""  
        bbox = BoundingBox(x1, y1, x2, y2)  
          
        # ラベル入力ダイアログを表示  
        dialog = AnnotationInputDialog(bbox, self)  
        if dialog.exec() == QDialog.DialogCode.Accepted:  
            label = dialog.get_label()  
            if label:  
                # アノテーションを追加  
                current_frame = self.video_control.current_frame  
                annotation = self.video_manager.add_manual_annotation(current_frame, bbox, label)  
                  
                # UI更新  
                self.update_annotation_count()  
                  
                QMessageBox.information(  
                    self, "Annotation Added",   
                    f"Added annotation: {label} at frame {current_frame}"  
                )  
      
    def on_frame_changed(self, frame_id: int):  
        """フレーム変更時の処理"""  
        self.video_control.set_current_frame(frame_id)  
      
    def on_range_selection_changed(self, start_frame: int, end_frame: int):  
        """範囲選択変更時の処理"""  
        self.menu_panel.update_range_info(start_frame, end_frame)  
      
    def update_display_options(self):  
        """表示オプションを更新"""  
        options = self.menu_panel.get_display_options()  
        self.video_preview.set_display_options(  
            options['show_manual'],  
            options['show_auto'],  
            options['show_ids'],  
            options['show_confidence']  
        )  
      
    def update_annotation_count(self):  
        """アノテーション数を更新"""  
        if not self.video_manager:  
            return  
          
        total_annotations = sum(  
            len(annotations) for annotations in self.video_manager.manual_annotations.values()  
        )  
        self.menu_panel.update_annotation_count(total_annotations)  
      
    def start_tracking(self):  
        """自動追跡を開始"""  
        if not self.video_manager or not self.video_manager.manual_annotations:  
            QMessageBox.warning(self, "Warning", "Please add manual annotations first")  
            return  
          
        # 開始フレームを取得  
        start_frame = min(self.video_manager.manual_annotations.keys())  
          
        # 設定ダイアログを表示  
        settings_dialog = TrackingSettingsDialog(  
            self.video_manager.total_frames,   
            start_frame,   
            self  
        )  
          
        if settings_dialog.exec() == QDialog.DialogCode.Accepted:  
            end_frame = settings_dialog.get_end_frame()  
              
            # 確認ダイアログ  
            frame_count = end_frame - start_frame + 1  
            reply = QMessageBox.question(  
                self, "Confirm Tracking",   
                f"Start automatic tracking from frame {start_frame} to {end_frame}?\n"  
                f"Total frames to process: {frame_count}\n"  
                f"This may take several minutes.",  
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
            )  
              
            if reply == QMessageBox.StandardButton.Yes:  
                self.menu_panel.update_tracking_progress("Tracking in progress...")  
                  
                # バックグラウンドで追跡処理を実行  
                self.tracking_worker = TrackingWorker(self.video_manager, start_frame, end_frame)  
                self.tracking_worker.tracking_completed.connect(self.on_tracking_completed)  
                self.tracking_worker.progress_updated.connect(self.on_tracking_progress)  
                self.tracking_worker.start()  
      
    def on_tracking_progress(self, current_frame: int, total_frames: int):  
        """追跡進捗更新"""  
        progress_percent = (current_frame / total_frames) * 100  
        progress_text = f"Tracking... {current_frame}/{total_frames} ({progress_percent:.1f}%)"  
        self.menu_panel.update_tracking_progress(progress_text)  
      
    def on_tracking_completed(self, results: Dict):  
        """追跡完了時の処理"""  
        self.menu_panel.update_tracking_progress(f"Completed! {len(results)} frames processed.")  
        self.menu_panel.enable_result_view(True)  
          
        QMessageBox.information(  
            self, "Tracking Complete",   
            f"Automatic tracking completed successfully!\n"  
            f"Processed {len(results)} frames.\n"  
            f"You can now view results using 'View Results Mode'."  
        )  
      
    def export_annotations(self, format: str):  
        """アノテーションをエクスポート"""  
        if not self.video_manager:  
            return  
          
        if format == "json":  
            file_path, _ = QFileDialog.getSaveFileName(  
                self, "Save JSON Annotations", "annotations.json",  
                "JSON Files (*.json);;All Files (*)"  
            )  
        else:  # COCO  
            file_path, _ = QFileDialog.getSaveFileName(  
                self, "Save COCO Annotations", "annotations_coco.json",  
                "JSON Files (*.json);;All Files (*)"  
            )  
          
        if file_path:  
            try:  
                self.video_manager.export_annotations(file_path, format=format)  
                QMessageBox.information(self, "Export Complete", f"Annotations exported to {file_path}")  
            except Exception as e:  
                QMessageBox.critical(self, "Export Error", f"Failed to export annotations: {e}")  

# UnifiedMASAAnnotationWidgetクラスの修正版  
class EnhancedUnifiedMASAAnnotationWidget(UnifiedMASAAnnotationWidget):  
    """範囲選択機能を改善したMASAアノテーションウィジェット"""  
      
    def setup_ui(self):  
        """UI設定（範囲選択機能を改善）"""  
        self.setWindowTitle("MASA Video Annotation Tool")  
        self.setGeometry(100, 100, 1400, 900)  
          
        # メインレイアウト（水平分割）  
        main_layout = QHBoxLayout()  
          
        # 左側：メニューパネル  
        self.menu_panel = MenuPanel()  
        main_layout.addWidget(self.menu_panel)  
          
        # 右側：動画プレビューエリア  
        right_layout = QVBoxLayout()  
          
        # 動画プレビューウィジェット  
        self.video_preview = UnifiedVideoPreviewWidget()  
        right_layout.addWidget(self.video_preview)  
          
        # 改善された動画制御パネル  
        self.video_control = EnhancedVideoControlPanel()  
        right_layout.addWidget(self.video_control)  
          
        # 右側レイアウトをウィジェットに包む  
        right_widget = QWidget()  
        right_widget.setLayout(right_layout)  
        main_layout.addWidget(right_widget)  
          
        # レイアウト比率設定（左：右 = 1：3）  
        main_layout.setStretch(0, 1)  
        main_layout.setStretch(1, 3)  
          
        self.setLayout(main_layout)  
          
        # シグナル接続  
        self.connect_signals()  
      
    def connect_signals(self):  
        """シグナルとスロットを接続（範囲選択機能を追加）"""  
        # 親クラスのシグナル接続  
        super().connect_signals()  
          
        # 範囲選択関連のシグナル接続  
        self.video_control.range_changed.connect(self.on_range_selection_changed)  
        self.video_control.range_frame_preview.connect(self.on_range_frame_preview)
        self.menu_panel.range_selection_requested.connect(self.set_range_selection_mode)  
      
    def set_range_selection_mode(self, enabled: bool):  
        """範囲選択モードの設定（改善版）"""  
        # 動画制御パネルの範囲選択モードを設定  
        self.video_control.toggle_range_mode(enabled)  
          
        # 動画プレビューの範囲選択モードは無効化（スライダーで制御）  
        self.video_preview.set_range_selection_mode(False)  
          
        if enabled:  
            QMessageBox.information(  
                self, "Range Selection Mode",   
                "Use the range slider below the video to select frames for auto tracking.\n"  
                "Drag the handles to adjust start and end frames.\n"  
                "You can also drag the blue range area to move the entire selection."  
            )  
    def on_range_frame_preview(self, frame_id: int):  
        """範囲選択中のフレームプレビュー処理"""  
        # 範囲選択モードの場合のみ動画を更新  
        if self.video_control.range_selection_mode:  
            self.video_preview.set_frame(frame_id)  
            # 通常のフレームスライダーも同期  
            self.video_control.set_current_frame(frame_id)

    def start_tracking(self):  
        """自動追跡を開始（範囲選択機能を改善）"""  
        if not self.video_manager or not self.video_manager.manual_annotations:  
            QMessageBox.warning(self, "Warning", "Please add manual annotations first")  
            return  
          
        # 範囲選択モードが有効な場合は、選択された範囲を使用  
        if self.video_control.range_selection_mode:  
            start_frame, end_frame = self.video_control.get_selected_range() 
        else:
          # 警告を表示
          QMessageBox.warning(self, "Warning", "Please select a frame range for auto tracking") 
          return
          
        # 確認ダイアログ  
        frame_count = end_frame - start_frame + 1  
        reply = QMessageBox.question(  
            self, "Confirm Tracking",   
            f"Start automatic tracking from frame {start_frame} to {end_frame}?\n"  
            f"Total frames to process: {frame_count}\n"  
            f"This may take several minutes.",  
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
        )  
          
        if reply == QMessageBox.StandardButton.Yes:  
            self.menu_panel.update_tracking_progress("Tracking in progress...")  
              
            # バックグラウンドで追跡処理を実行  
            self.tracking_worker = TrackingWorker(self.video_manager, start_frame, end_frame)  
            self.tracking_worker.tracking_completed.connect(self.on_tracking_completed)  
            self.tracking_worker.progress_updated.connect(self.on_tracking_progress)  
            self.tracking_worker.start()  

class FinalEnhancedMASAAnnotationWidget(EnhancedUnifiedMASAAnnotationWidget):  
    """複数フレーム機能を統合した最終版ウィジェット"""  
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.multi_frame_dialog = None  
      
    def setup_ui(self):  
        # 基本UIは親クラスと同じだが、MenuPanelを拡張版に変更  
        self.setWindowTitle("MASA Video Annotation Tool - Enhanced")  
        self.setGeometry(100, 100, 1400, 900)  
          
        main_layout = QHBoxLayout()  
          
        # 拡張メニューパネル  
        self.menu_panel = EnhancedMenuPanel()  
        main_layout.addWidget(self.menu_panel)  
          
        # 右側は既存と同じ  
        right_layout = QVBoxLayout()  
        self.video_preview = UnifiedVideoPreviewWidget()  
        right_layout.addWidget(self.video_preview)  
          
        self.video_control = EnhancedVideoControlPanel()  
        right_layout.addWidget(self.video_control)  
          
        right_widget = QWidget()  
        right_widget.setLayout(right_layout)  
        main_layout.addWidget(right_widget)  
          
        main_layout.setStretch(0, 1)  
        main_layout.setStretch(1, 3)  
          
        self.setLayout(main_layout)  
        self.connect_signals()  
      
    def load_video(self):  
        """動画読み込み（拡張版マネージャーを使用）"""  
        file_path, _ = QFileDialog.getOpenFileName(  
            self, "Select Video File", "",   
            "Video Files (*.mp4 *.avi *.mov *.mkv);;All Files (*)"  
        )  
          
        if file_path:  
            config = MASAConfig()  
            # 拡張版マネージャーを使用  
            self.video_manager = EnhancedVideoAnnotationManager(file_path, config)  
              
            if self.video_manager.load_video():  
                self.video_preview.set_video_manager(self.video_manager)  
                self.video_control.set_total_frames(self.video_manager.total_frames)  
                self.video_control.set_current_frame(0)  
                self.menu_panel.update_video_info(file_path, self.video_manager.total_frames)  
                  
                QMessageBox.information(self, "Success", f"Video loaded: {file_path}")  
            else:  
                QMessageBox.critical(self, "Error", "Failed to load video file")  
      
    def connect_signals(self):  
        super().connect_signals()  
          
        # 複数フレーム関連のシグナル接続  
        self.menu_panel.multi_frame_mode_requested.connect(self.set_multi_frame_mode)  
        self.video_preview.multi_frame_bbox_created.connect(self.on_multi_frame_bbox_created)  
        
        # Complete Multi-Frame ボタンのシグナル接続を追加  
        self.menu_panel.complete_multi_frame_btn.clicked.connect(self.on_complete_multi_frame)  
      
    def set_multi_frame_mode(self, enabled: bool, label: str):  
        """複数フレームモードの設定"""  
        self.video_preview.set_multi_frame_mode(enabled, label)  
          
        if enabled:  
            QMessageBox.information(  
                self, "Multi-Frame Mode",   
                f"Multi-frame annotation mode for '{label}' is now active.\n"  
                "Click and drag on different frames to create bounding boxes.\n"  
                "Click 'Complete Multi-Frame' when finished."  
            )  
      
    def on_multi_frame_bbox_created(self, x1: int, y1: int, x2: int, y2: int, frame_id: int):  
        """複数フレームバウンディングボックス作成時の処理"""  
        bbox = BoundingBox(x1, y1, x2, y2)  
          
        # 複数フレームアノテーションリストに追加  
        annotation_data = {  
            'frame_id': frame_id,  
            'bbox': bbox  
        }  
        self.video_preview.multi_frame_annotations.append(annotation_data)  
          
        # 表示を更新  
        self.video_preview.update_frame_display()  
          
        QMessageBox.information(  
            self, "Frame Added",   
            f"Added bounding box for frame {frame_id}.\n"  
            f"Total frames: {len(self.video_preview.multi_frame_annotations)}"  
        )

    def on_complete_multi_frame(self):  
        """複数フレームアノテーション完了時の処理"""  
        if not self.video_preview.multi_frame_annotations:  
            QMessageBox.warning(self, "Warning", "No multi-frame annotations to complete")  
            return  
          
        # 複数フレームアノテーションをビデオマネージャーに追加  
        frame_ids = [ann['frame_id'] for ann in self.video_preview.multi_frame_annotations]  
        bboxes = [ann['bbox'] for ann in self.video_preview.multi_frame_annotations]  
        label = self.video_preview.current_multi_frame_label  
          
        if self.video_manager and hasattr(self.video_manager, 'add_multi_frame_annotation'):  
            annotations = self.video_manager.add_multi_frame_annotation(frame_ids, bboxes, label)  
              
            # アノテーション数を更新（重要！）  
            self.update_annotation_count()  
              
            QMessageBox.information(  
                self, "Multi-Frame Annotation Completed",   
                f"Added {len(annotations)} annotations for '{label}' across {len(frame_ids)} frames"  
            )  
          
        # 複数フレームモードを終了  
        self.menu_panel.multi_frame_btn.setChecked(False)  
        self.menu_panel._on_multi_frame_clicked(False)  
          
        # 作成中のアノテーションをクリア  
        self.video_preview.multi_frame_annotations.clear()  
        self.video_preview.update_frame_display()

class TrackingWorker(QThread):  
    """自動追跡処理用ワーカースレッド"""  
      
    progress_updated = pyqtSignal(int, int)  # current_frame, total_frames  
    tracking_completed = pyqtSignal(dict)  
    error_occurred = pyqtSignal(str)  
      
    def __init__(self, video_manager, start_frame, end_frame):  
        super().__init__()  
        self.video_manager = video_manager  
        self.start_frame = start_frame  
        self.end_frame = end_frame  
      
    def run(self):  
        try:  
            results = self.process_tracking_with_progress()  
            self.tracking_completed.emit(results)  
        except Exception as e:  
            self.error_occurred.emit(str(e))
    def process_tracking_with_progress(self):  
        """進捗報告付きの追跡処理"""  
        # 初期化  
        if not self.video_manager.tracker.initialized:  
            self.video_manager.tracker.initialize()  
          
        # 手動アノテーションを取得  
        manual_objects = self.video_manager.manual_annotations[self.start_frame]  
        unique_labels = list(set([obj.label for obj in manual_objects]))  
        text_prompt = " . ".join(unique_labels) if unique_labels else None  
          
        results = {}  
        total_frames = self.end_frame - self.start_frame + 1  
          
        for i, frame_id in enumerate(range(self.start_frame, self.end_frame + 1)):  
            # 進捗を報告  
            self.progress_updated.emit(i + 1, total_frames)  
              
            frame = self.video_manager.get_frame(frame_id)  
            if frame is None:  
                continue  
              
            try:  
                tracked_annotations = self.video_manager.tracker.track_objects(  
                    frame=frame,  
                    frame_id=frame_id,  
                    initial_annotations=manual_objects if frame_id == self.start_frame else None,  
                    texts=text_prompt  
                )  
                  
                results[frame_id] = tracked_annotations  
                  
                # フレームアノテーションを更新  
                if frame_id not in self.video_manager.frame_annotations:  
                    self.video_manager.frame_annotations[frame_id] = FrameAnnotation(frame_id=frame_id)  
                  
                all_annotations = []  
                if frame_id in self.video_manager.manual_annotations:  
                    all_annotations.extend(self.video_manager.manual_annotations[frame_id])  
                all_annotations.extend(tracked_annotations)  
                  
                self.video_manager.frame_annotations[frame_id].objects = all_annotations  
                  
            except Exception as e:  
                print(f"Error tracking frame {frame_id}: {e}")  
                continue  
          
        return results  

class EnhancedVideoAnnotationManager(VideoAnnotationManager):  
    """複数フレーム機能を統合したアノテーション管理クラス"""  
      
    def __init__(self, video_path: str, config: MASAConfig = None):  
        super().__init__(video_path, config)  
        self.multi_frame_objects = {}  # オブジェクトIDごとの複数フレーム情報  
      
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
      
    def process_enhanced_tracking(self, start_frame_id: int, end_frame_id: int = None) -> Dict[int, List[ObjectAnnotation]]:  
        """複数フレーム情報を活用した追跡処理"""  
        if not self.tracker.initialized:  
            self.tracker.initialize()  
          
        # 複数フレーム情報を活用してより堅牢な追跡を実行  
        # MASAのmemo_tracklet_framesとmemo_momentumを活用  
        return self.process_automatic_tracking(start_frame_id, end_frame_id)

class EnhancedMenuPanel(MenuPanel):  
    """複数フレーム機能付きメニューパネル"""  
      
    multi_frame_mode_requested = pyqtSignal(bool, str)  # enabled, label  
      
    def setup_ui(self):  
        super().setup_ui()  
          
        # 親クラスで定義されたannotation_groupを使用  
        if hasattr(self, 'annotation_group'):  
            layout = self.annotation_group.layout()  
              
            self.multi_frame_btn = QPushButton("Multi-Frame Mode")  
            self.multi_frame_btn.setCheckable(True)  
            self.multi_frame_btn.clicked.connect(self._on_multi_frame_clicked)  
            self.multi_frame_btn.setEnabled(False)  
            layout.addWidget(self.multi_frame_btn)  
              
            # ラベル入力フィールド  
            self.multi_frame_label_input = QLineEdit()  
            self.multi_frame_label_input.setPlaceholderText("Object label")  
            self.multi_frame_label_input.setEnabled(False)  
            layout.addWidget(self.multi_frame_label_input)  
              
            # 完了ボタン  
            self.complete_multi_frame_btn = QPushButton("Complete Multi-Frame")  
            self.complete_multi_frame_btn.clicked.connect(self._on_complete_multi_frame)  
            self.complete_multi_frame_btn.setEnabled(False)  
            layout.addWidget(self.complete_multi_frame_btn)  
      
    def _on_multi_frame_clicked(self, checked):  
        if checked:  
            label = self.multi_frame_label_input.text().strip()  
            if not label:  
                QMessageBox.warning(self, "Warning", "Please enter an object label first")  
                self.multi_frame_btn.setChecked(False)  
                return  
              
            # 他のモードを無効化  
            self.annotation_mode_btn.setChecked(False)  
            self.range_selection_btn.setChecked(False)  
            self.result_view_btn.setChecked(False)  
              
            self.multi_frame_label_input.setEnabled(False)  
            self.complete_multi_frame_btn.setEnabled(True)  
        else:  
            self.multi_frame_label_input.setEnabled(True)  
            self.complete_multi_frame_btn.setEnabled(False)  
          
        self.multi_frame_mode_requested.emit(checked, self.multi_frame_label_input.text().strip())  
      
    def _on_complete_multi_frame(self):  
        # 複数フレームアノテーション完了シグナルを発行  
        self.multi_frame_btn.setChecked(False)  
        self._on_multi_frame_clicked(False)

    def update_video_info(self, video_path: str, total_frames: int):  
        """動画情報を更新（Multi-Frame Modeボタンも有効化）"""  
        # 親クラスのメソッドを呼び出し  
        super().update_video_info(video_path, total_frames)  
          
        # Multi-Frame Modeボタンを有効化  
        if hasattr(self, 'multi_frame_btn'):  
            self.multi_frame_btn.setEnabled(True)  
        if hasattr(self, 'multi_frame_label_input'):  
            self.multi_frame_label_input.setEnabled(True)

class RangeSlider(QWidget):  
    """範囲選択可能なスライダーウィジェット"""  
      
    range_changed = pyqtSignal(int, int)  # start_frame, end_frame  
    current_frame_changed = pyqtSignal(int)  # ドラッグ中のフレーム変更用シグナル  
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.setMinimumHeight(40)  
        self.setMinimumWidth(300)  
          
        # スライダーの設定  
        self.minimum = 0  
        self.maximum = 100  
        self.start_value = 0  
        self.end_value = 100  
          
        # ドラッグ状態  
        self.dragging_start = False  
        self.dragging_end = False  
        self.dragging_range = False  
        self.drag_offset = 0  
        self.is_dragging = False
          
        # ハンドルのサイズ  
        self.handle_width = 12  
        self.handle_height = 20  
          
        # トラックの設定  
        self.track_height = 6  
          
    def set_range(self, minimum: int, maximum: int):  
        """スライダーの範囲を設定"""  
        self.minimum = minimum  
        self.maximum = maximum  
        self.start_value = minimum  
        self.end_value = maximum  
        self.update()  
      
    def set_values(self, start: int, end: int):  
        """選択範囲を設定"""  
        self.start_value = max(self.minimum, min(start, self.maximum))  
        self.end_value = max(self.minimum, min(end, self.maximum))  
        if self.start_value > self.end_value:  
            self.start_value, self.end_value = self.end_value, self.start_value  
        self.update()  
        self.range_changed.emit(self.start_value, self.end_value)  
      
    def get_values(self) -> tuple:  
        """現在の選択範囲を取得"""  
        return (self.start_value, self.end_value)  
      
    def _value_to_pixel(self, value: int) -> int:  
        """値をピクセル位置に変換"""  
        if self.maximum == self.minimum:  
            return self.handle_width // 2  
          
        track_width = self.width() - self.handle_width  
        ratio = (value - self.minimum) / (self.maximum - self.minimum)  
        return int(self.handle_width // 2 + ratio * track_width)  
      
    def _pixel_to_value(self, pixel: int) -> int:  
        """ピクセル位置を値に変換"""  
        track_width = self.width() - self.handle_width  
        if track_width <= 0:  
            return self.minimum  
          
        ratio = (pixel - self.handle_width // 2) / track_width  
        ratio = max(0, min(1, ratio))  
        return int(self.minimum + ratio * (self.maximum - self.minimum))  
      
    def _get_start_handle_rect(self) -> QRect:  
        """開始ハンドルの矩形を取得"""  
        x = self._value_to_pixel(self.start_value) - self.handle_width // 2  
        y = (self.height() - self.handle_height) // 2  
        return QRect(x, y, self.handle_width, self.handle_height)  
      
    def _get_end_handle_rect(self) -> QRect:  
        """終了ハンドルの矩形を取得"""  
        x = self._value_to_pixel(self.end_value) - self.handle_width // 2  
        y = (self.height() - self.handle_height) // 2  
        return QRect(x, y, self.handle_width, self.handle_height)  
      
    def _get_range_rect(self) -> QRect:  
        """選択範囲の矩形を取得"""  
        start_x = self._value_to_pixel(self.start_value)  
        end_x = self._value_to_pixel(self.end_value)  
        y = (self.height() - self.track_height) // 2  
        return QRect(start_x, y, end_x - start_x, self.track_height)  
      
    def mouseMoveEvent(self, event):  
        pos = event.position().toPoint()  
          
        if self.dragging_start:  
            new_value = self._pixel_to_value(pos.x() - self.drag_offset)  
            self.start_value = max(self.minimum, min(new_value, self.end_value))  
            self.update()  
            self.range_changed.emit(self.start_value, self.end_value)  
            # ドラッグ中のフレーム更新  
            self.current_frame_changed.emit(self.start_value)  
              
        elif self.dragging_end:  
            new_value = self._pixel_to_value(pos.x() - self.drag_offset)  
            self.end_value = max(self.start_value, min(new_value, self.maximum))  
            self.update()  
            self.range_changed.emit(self.start_value, self.end_value)  
            # ドラッグ中のフレーム更新  
            self.current_frame_changed.emit(self.end_value)  
              
        elif self.dragging_range:  
            center_x = pos.x() - self.drag_offset  
            current_range = self.end_value - self.start_value  
            center_value = self._pixel_to_value(center_x)  
              
            new_start = center_value - current_range // 2  
            new_end = center_value + current_range // 2  
              
            # 範囲を境界内に調整  
            if new_start < self.minimum:  
                new_start = self.minimum  
                new_end = new_start + current_range  
            elif new_end > self.maximum:  
                new_end = self.maximum  
                new_start = new_end - current_range  
              
            self.start_value = new_start  
            self.end_value = new_end  
            self.update()  
            self.range_changed.emit(self.start_value, self.end_value)  
            # 範囲移動中は先頭フレームを表示  
            self.current_frame_changed.emit(self.start_value)  
      
    def mousePressEvent(self, event):  
        if event.button() == Qt.MouseButton.LeftButton:  
            pos = event.position().toPoint()  
              
            start_handle = self._get_start_handle_rect()  
            end_handle = self._get_end_handle_rect()  
            range_rect = self._get_range_rect()  
              
            if start_handle.contains(pos):  
                self.dragging_start = True  
                self.is_dragging = True  
                self.drag_offset = pos.x() - start_handle.center().x()  
            elif end_handle.contains(pos):  
                self.dragging_end = True  
                self.is_dragging = True  
                self.drag_offset = pos.x() - end_handle.center().x()  
            elif range_rect.contains(pos):  
                self.dragging_range = True  
                self.is_dragging = True  
                self.drag_offset = pos.x() - range_rect.center().x()  
            else:  
                # トラック上をクリックした場合の処理...  
                value = self._pixel_to_value(pos.x())  
                start_dist = abs(value - self.start_value)  
                end_dist = abs(value - self.end_value)  
                  
                if start_dist < end_dist:  
                    self.start_value = value  
                    self.current_frame_changed.emit(self.start_value)  
                else:  
                    self.end_value = value  
                    self.current_frame_changed.emit(self.end_value)  
                  
                self.update()  
                self.range_changed.emit(self.start_value, self.end_value)  
      
    def mouseReleaseEvent(self, event):  
        self.dragging_start = False  
        self.dragging_end = False  
        self.dragging_range = False  
        self.is_dragging = False  
        
    def paintEvent(self, event):  
        painter = QPainter(self)  
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)  
          
        # トラック背景を描画  
        track_rect = QRect(  
            self.handle_width // 2,  
            (self.height() - self.track_height) // 2,  
            self.width() - self.handle_width,  
            self.track_height  
        )  
        painter.fillRect(track_rect, QColor(200, 200, 200))  
          
        # 選択範囲を描画  
        range_rect = self._get_range_rect()  
        painter.fillRect(range_rect, QColor(100, 150, 255))  
          
        # ハンドルを描画  
        start_handle = self._get_start_handle_rect()  
        end_handle = self._get_end_handle_rect()  
          
        painter.setBrush(QBrush(QColor(50, 100, 200)))  
        painter.setPen(QPen(QColor(30, 70, 150), 2))  
        painter.drawRoundedRect(start_handle, 3, 3)  
        painter.drawRoundedRect(end_handle, 3, 3)  
          
        # 値を表示  
        painter.setPen(QPen(QColor(0, 0, 0)))  
        painter.drawText(10, self.height() - 5, f"Start: {self.start_value}")  
        painter.drawText(self.width() - 80, self.height() - 5, f"End: {self.end_value}") 
  
class EnhancedVideoControlPanel(QWidget):  
    """改善された動画制御パネル"""  
      
    frame_changed = pyqtSignal(int)  
    range_changed = pyqtSignal(int, int)  
    range_frame_preview = pyqtSignal(int)  # 範囲選択中のフレームプレビュー用  
      
    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.total_frames = 0  
        self.current_frame = 0  
        self.range_selection_mode = False  
        self.setup_ui()  
          
    def setup_ui(self):  
        layout = QVBoxLayout()  
        layout.setContentsMargins(5, 5, 5, 5)  
          
        # フレーム情報  
        self.frame_info_label = QLabel("Frame: 0 / 0")  
        self.frame_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        layout.addWidget(self.frame_info_label)  
          
        # 範囲選択スライダー  
        self.range_slider = RangeSlider()  
        self.range_slider.range_changed.connect(self.on_range_changed)  
        self.range_slider.current_frame_changed.connect(self.on_range_frame_preview)
        layout.addWidget(QLabel("Frame Range:"))  
        layout.addWidget(self.range_slider)  
          
        # 通常のフレーム制御  
        control_layout = QHBoxLayout()  
          
        self.prev_btn = QPushButton("◀")  
        self.prev_btn.setFixedSize(30, 30)  
        self.prev_btn.clicked.connect(self.prev_frame)  
        control_layout.addWidget(self.prev_btn)  
          
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)  
        self.frame_slider.setMinimum(0)  
        self.frame_slider.valueChanged.connect(self.on_frame_changed)  
        control_layout.addWidget(self.frame_slider)  
          
        self.next_btn = QPushButton("▶")  
        self.next_btn.setFixedSize(30, 30)  
        self.next_btn.clicked.connect(self.next_frame)  
        control_layout.addWidget(self.next_btn)  
          
        layout.addLayout(control_layout)  
          
        # 範囲選択モード切り替え  
        self.range_mode_btn = QPushButton("Range Selection Mode")  
        self.range_mode_btn.setCheckable(True)  
        self.range_mode_btn.clicked.connect(self.toggle_range_mode)  
        layout.addWidget(self.range_mode_btn)  
        
        
        self.setLayout(layout)  

    def on_range_frame_preview(self, frame_id: int):  
        """範囲選択中のフレームプレビュー"""  
        self.range_frame_preview.emit(frame_id)  
      
    def on_range_changed(self, start_frame: int, end_frame: int):  
        """範囲変更イベント"""  
        self.range_changed.emit(start_frame, end_frame)

    def set_total_frames(self, total_frames: int):  
        """総フレーム数を設定"""  
        self.total_frames = total_frames  
        self.frame_slider.setMaximum(total_frames - 1)  
        self.range_slider.set_range(0, total_frames - 1)  
        self.update_frame_info()  
      
    def set_current_frame(self, frame_id: int):  
        """現在のフレームを設定"""  
        self.current_frame = frame_id  
        self.frame_slider.setValue(frame_id)  
        self.update_frame_info()  
      
    def toggle_range_mode(self, enabled: bool):  
        """範囲選択モードの切り替え"""  
        self.range_selection_mode = enabled  
        self.range_slider.setVisible(enabled)  
          
        if enabled:  
            # 現在のフレームを中心とした範囲を初期設定  
            start = max(0, self.current_frame - 50)  
            end = min(self.total_frames - 1, self.current_frame + 50)  
            self.range_slider.set_values(start, end)  
      
    def on_frame_changed(self, frame_id: int):  
        """フレーム変更イベント"""  
        self.current_frame = frame_id  
        self.update_frame_info()  
        self.frame_changed.emit(frame_id)  
      
    def on_range_changed(self, start_frame: int, end_frame: int):  
        """範囲変更イベント"""  
        self.range_changed.emit(start_frame, end_frame)  
      
    def prev_frame(self):  
        """前のフレームに移動"""  
        if self.current_frame > 0:  
            self.set_current_frame(self.current_frame - 1)  
      
    def next_frame(self):  
        """次のフレームに移動"""  
        if self.current_frame < self.total_frames - 1:  
            self.set_current_frame(self.current_frame + 1)  
      
    def update_frame_info(self):  
        """フレーム情報を更新"""  
        self.frame_info_label.setText(f"Frame: {self.current_frame} / {self.total_frames - 1}")  
      
    def get_selected_range(self) -> tuple:  
        """選択された範囲を取得"""  
        if self.range_selection_mode:  
            return self.range_slider.get_values()  
        else:  
            return (0, self.total_frames - 1)  




# メインアプリケーション実行用のクラス（改善版）  
class EnhancedMASAAnnotationApp(QApplication):  
    """改善されたMASAアノテーションアプリケーション"""  
      
    def __init__(self, argv):  
        super().__init__(argv)  
        self.main_widget = FinalEnhancedMASAAnnotationWidget()  
        self.main_widget.show()  
  
def run_enhanced_gui_application():  
    """改善されたGUI版のアプリケーションを実行"""  
    app = EnhancedMASAAnnotationApp(sys.argv)  
    sys.exit(app.exec())  
  

  
if __name__ == "__main__":  
    run_enhanced_gui_application()  