import numpy as np
import torch
from typing import List
from DataClass import MASAConfig, ObjectAnnotation, BoundingBox

# MM関連のインポート（実際の使用時に調整が必要）  
from mmcv.transforms import Compose  
from mmdet.apis import init_detector  
from mmcv.ops.nms import batched_nms  

# MASAの機能をインポート（デモコードを参考）  
import masa  
from masa.apis import inference_masa, init_masa, init_detector, inference_detector, build_test_pipeline  
from masa.models.sam import SamPredictor, sam_model_registry  


class ObjectTracker:  
    """MASA を使用した物体追跡クラス"""  
      
    def __init__(self, config: MASAConfig):  
        self.config = config  
        self.masa_model = None  
        self.det_model = None  
        self.sam_predictor = None  
        self.test_pipeline = None  
        self.masa_test_pipeline = None  
        self.initialized = False  
          
    def initialize(self):  
        """MASAモデルの初期化"""  
        if masa is None:  
            raise ImportError("MASA is not installed")  
              
        try:  
            # MASAモデルの初期化（デモコードを参考）  
            if self.config.unified_mode:  
                self.masa_model = init_masa(  
                    self.config.masa_config_path,   
                    self.config.masa_checkpoint_path,   
                    device=self.config.device  
                )  
            else:  
                # 非統合モードの場合は別途検出器も初期化  
                self.det_model = init_detector(  
                    self.config.det_config_path,   
                    self.config.det_checkpoint_path,   
                    palette='random',   
                    device=self.config.device  
                )  
                self.masa_model = init_masa(  
                    self.config.masa_config_path,   
                    self.config.masa_checkpoint_path,   
                    device=self.config.device  
                )  
                  
                # テストパイプラインの構築  
                self.det_model.cfg.test_dataloader.dataset.pipeline[0].type = 'mmdet.LoadImageFromNDArray'  
                self.test_pipeline = Compose(self.det_model.cfg.test_dataloader.dataset.pipeline)  
              
            # MASAテストパイプラインの構築  
            self.masa_test_pipeline = build_test_pipeline(self.masa_model.cfg)  
              
            # SAMの初期化（必要に応じて）  
            if self.config.sam_mask:  
                sam_model = sam_model_registry[self.config.sam_type](self.config.sam_path)  
                self.sam_predictor = SamPredictor(sam_model.to(self.config.device))  
              
            self.initialized = True  
              
        except Exception as e:  
            print(f"Failed to initialize MASA: {e}")  
            raise  
      
    def track_objects(self, frame: np.ndarray, frame_id: int,   
                    initial_annotations: List[ObjectAnnotation] = None,  
                    texts: str = None) -> List[ObjectAnnotation]:  
        """  
        フレーム内の物体を追跡  
        """  
        if not self.initialized:  
            self.initialize()  
          
        try:  
            # MASAテストパイプラインの再構築（テキストプロンプト対応）  
            if texts is not None:  
                # テキストプロンプト用のパイプラインを構築  
                self.masa_test_pipeline = build_test_pipeline(  
                    self.masa_model.cfg,   
                    with_text=True,  # テキスト対応を有効化  
                    detector_type=self.config.detector_type  
                )  
              
            # MASAによる推論実行  
            if self.config.unified_mode:  
                track_result = inference_masa(  
                    self.masa_model,   
                    frame,  
                    frame_id=frame_id,  
                    video_len=1000,  
                    test_pipeline=self.masa_test_pipeline,  
                    text_prompt=texts,  
                    custom_entities=True if texts else False,  # カスタムエンティティフラグを設定  
                    fp16=self.config.fp16,  
                    detector_type=self.config.detector_type,  
                    show_fps=False  
                )  
            else:  
                # 非統合モードの場合  
                if self.config.detector_type == 'mmdet':  
                    result = inference_detector(  
                        self.det_model,   
                        frame,  
                        text_prompt=texts,  
                        test_pipeline=self.test_pipeline,  
                        fp16=self.config.fp16  
                    )  
                  
                # NMS処理  
                det_bboxes, keep_idx = batched_nms(  
                    boxes=result.pred_instances.bboxes,  
                    scores=result.pred_instances.scores,  
                    idxs=result.pred_instances.labels,  
                    class_agnostic=True,  
                    nms_cfg=dict(type='nms', iou_threshold=0.5, class_agnostic=True, split_thr=100000)  
                )  
                  
                det_bboxes = torch.cat([  
                    det_bboxes,  
                    result.pred_instances.scores[keep_idx].unsqueeze(1)  
                ], dim=1)  
                det_labels = result.pred_instances.labels[keep_idx]  
                  
                track_result = inference_masa(  
                    self.masa_model,   
                    frame,   
                    frame_id=frame_id,  
                    video_len=1000,  
                    test_pipeline=self.masa_test_pipeline,  
                    det_bboxes=det_bboxes,  
                    det_labels=det_labels,  
                    fp16=self.config.fp16,  
                    show_fps=False  
                )  
              
            # 結果をObjectAnnotationに変換  
            annotations = self._convert_track_result_to_annotations(  
                track_result, frame_id, texts  
            )  
              
            return annotations  
              
        except Exception as e:  
            print(f"Error in object tracking: {e}")  
            return []  
      
    def _convert_track_result_to_annotations(self, track_result, frame_id: int,   
                                           texts: str = None) -> List[ObjectAnnotation]:  
        """追跡結果をObjectAnnotationに変換"""  
        annotations = []  
          
        if not track_result or len(track_result) == 0:  
            return annotations  
          
        pred_instances = track_result[0].pred_track_instances  
          
        for i in range(len(pred_instances.bboxes)):  
            bbox_tensor = pred_instances.bboxes[i]  
            bbox = BoundingBox(  
                x1=float(bbox_tensor[0]),  
                y1=float(bbox_tensor[1]),  
                x2=float(bbox_tensor[2]),  
                y2=float(bbox_tensor[3]),  
                confidence=float(pred_instances.scores[i])  
            )  
              
            # ラベルの取得  
            if hasattr(pred_instances, 'labels') and i < len(pred_instances.labels):  
                label_idx = int(pred_instances.labels[i])  
                # テキストプロンプトまたはクラス名からラベルを取得  
                if texts:  
                    label_names = texts.split(' . ')  
                    label = label_names[label_idx] if label_idx < len(label_names) else f"class_{label_idx}"  
                else:  
                    label = f"class_{label_idx}"  
            else:  
                label = "unknown"  
              
            # インスタンスIDの取得  
            object_id = int(pred_instances.instances_id[i]) if hasattr(pred_instances, 'instances_id') else i  
              
            annotation = ObjectAnnotation(  
                object_id=object_id,  
                label=label,  
                bbox=bbox,  
                frame_id=frame_id,  
                is_manual=False,  
                track_confidence=float(pred_instances.scores[i])  
            )  
              
            # 信頼度スコアでフィルタリング  
            if annotation.bbox.confidence >= self.config.score_threshold:  
                annotations.append(annotation)  
          
        return annotations
