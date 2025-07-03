# 改善されたAnnotationVisualizer.py  
import cv2  
import numpy as np  
import colorsys  
from typing import List, Tuple  
from DataClass import ObjectAnnotation  
  
class AnnotationVisualizer:  
    """アノテーション可視化クラス（改善版）"""  
      
    def __init__(self):  
        self.colors = self._generate_colors(100)  
          
    def _generate_colors(self, num_colors: int) -> List[Tuple[int, int, int]]:  
        """オブジェクトID用のカラーパレットを生成"""  
        colors = []  
        for i in range(num_colors):  
            hue = (i * 137.508) % 360  # Golden angle approximation  
            saturation = 0.7  
            value = 0.9  
              
            r, g, b = colorsys.hsv_to_rgb(hue/360, saturation, value)  
            colors.append((int(r*255), int(g*255), int(b*255)))  
          
        return colors  
      
    def draw_annotations(self, frame: np.ndarray, annotations: List[ObjectAnnotation],   
                        show_ids: bool = True, show_confidence: bool = True,  
                        selected_annotation: ObjectAnnotation = None) -> np.ndarray:  
        """フレームにアノテーションを描画（選択表示対応）"""  
        result_frame = frame.copy()  
          
        for annotation in annotations:  
            color = self.colors[annotation.object_id % len(self.colors)]  
              
            if selected_annotation and annotation.object_id == selected_annotation.object_id:  
                color = (255, 165, 0)  # 青色でハイライト  
                thickness = 6  
            elif annotation.is_batch_added:  
                color = (0, 0, 255)  # バッチ追加されたアノテーションの特別な色  
                thickness = 4
            else:  
                color = self.colors[annotation.object_id % len(self.colors)]  
                thickness = 4 if annotation.is_manual else 2  # 手動アノテーションは太い線、それ以外は細い線
              
            # バウンディングボックス座標を整数に変換（四捨五入）  
            pt1 = (int(round(annotation.bbox.x1)), int(round(annotation.bbox.y1)))  
            pt2 = (int(round(annotation.bbox.x2)), int(round(annotation.bbox.y2)))  
              
            # 画像境界内にクリップ  
            h, w = frame.shape[:2]  
            pt1 = (max(0, min(pt1[0], w-1)), max(0, min(pt1[1], h-1)))  
            pt2 = (max(0, min(pt2[0], w-1)), max(0, min(pt2[1], h-1)))  
              
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
      
    def create_annotation_video(self, video_manager, annotation_repository,   
                              output_path: str, fps: int = 30):  
        """アノテーション付き動画を作成"""  
        if not annotation_repository.frame_annotations:  
            print("No annotations to visualize")  
            return  
          
        first_frame = video_manager.get_frame(0)  
        if first_frame is None:  
            print("Cannot read first frame")  
            return  
          
        height, width = first_frame.shape[:2]  
          
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')  
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))  
          
        try:  
            for frame_id in range(video_manager.get_total_frames()):  
                frame = video_manager.get_frame(frame_id)  
                if frame is None:  
                    continue  
                  
                frame_annotation = annotation_repository.get_annotations(frame_id)  
                if frame_annotation and frame_annotation.objects:  
                    annotated_frame = self.draw_annotations(frame, frame_annotation.objects)  
                else:  
                    annotated_frame = frame  
                  
                out.write(annotated_frame)  
                  
                if frame_id % 100 == 0:  
                    print(f"Processed frame {frame_id}/{video_manager.get_total_frames()}")  
              
            print(f"Annotated video saved to {output_path}")  
              
        finally:  
            out.release()  