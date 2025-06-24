# ObjectTracker.py  
import os
import sys
import numpy as np  
import torch  
from typing import List, Optional, Union  
from DataClass import MASAConfig, ObjectAnnotation, BoundingBox  
from ErrorHandler import ErrorHandler  
  
# MM関連のインポート  
from mmcv.transforms import Compose  
from mmdet.apis import init_detector  
from mmcv.ops.nms import batched_nms  
  
# MASAの機能をインポート  
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))  
import masa  
from masa.apis import inference_masa, init_masa, inference_detector, build_test_pipeline  
from masa.models.sam import SamPredictor, sam_model_registry  
  
class ObjectTracker:  
    """MASA を使用した物体追跡クラス（改善版）"""  
      
    def __init__(self, config: MASAConfig):  
        self.config = config  
        self.masa_model = None  
        self.det_model = None  
        self.sam_predictor = None  
        self.test_pipeline = None  
        self.masa_test_pipeline = None  
        self.initialized = False  
      
    @ErrorHandler.handle_with_dialog("MASA Initialization Error")  
    def initialize(self):  
        """MASAモデルの初期化"""  
        if masa is None:  
            raise ImportError("MASA is not installed. Please install it to use this feature.")  
          
        if self.initialized:  
            return  
          
        # MASAモデルの初期化  
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
        print("MASA models initialized successfully.")  
      
    @ErrorHandler.handle_with_dialog("Object Tracking Error")  
    def track_objects(self, frame: np.ndarray, frame_id: int,  
                    initial_annotations: List[ObjectAnnotation] = None,  
                    texts: str = None) -> List[ObjectAnnotation]:  
        """  
        フレーム内の物体を追跡  
        """  
        if not self.initialized:  
            self.initialize()  
          
        # MASAテストパイプラインの再構築（テキストプロンプト対応）  
        if texts is not None:  
            self.masa_test_pipeline = build_test_pipeline(  
                self.masa_model.cfg,  
                with_text=True,  
                detector_type=self.config.detector_type  
            )  
          
        det_bboxes_from_initial = None  
        det_labels_from_initial = None  
        if initial_annotations:  
            bboxes_list = []  
            labels_list = []  
              
            # MASAモデルの入力形式に合わせるため、ラベルを数値IDに変換する必要がある  
            # ここでは、textsが単一のラベル名であることを前提とし、そのラベルIDを0とする  
            # 実際のMASAモデルのラベルマッピングに応じて調整が必要  
            label_to_id = {texts: 0} if texts else {}  
              
            for ann in initial_annotations:  
                # bboxはxyxy形式で、スコアを結合してxyxy+scoreの5次元テンソルにする  
                bbox_tensor = torch.tensor([ann.bbox.x1, ann.bbox.y1, ann.bbox.x2, ann.bbox.y2, ann.bbox.confidence],  
                                           dtype=torch.float32, device=self.config.device)  
                bboxes_list.append(bbox_tensor)  
                labels_list.append(torch.tensor(label_to_id.get(ann.label, 0), dtype=torch.long, device=self.config.device))  
              
            if bboxes_list:  
                det_bboxes_from_initial = torch.stack(bboxes_list)  
                det_labels_from_initial = torch.stack(labels_list)  
          
        # MASAによる推論実行  
        if self.config.unified_mode:  
            track_result = inference_masa(  
                self.masa_model,  
                frame,  
                frame_id=frame_id,  
                video_len=1000,  # 仮の値、実際にはVideoManagerから取得  
                test_pipeline=self.masa_test_pipeline,  
                text_prompt=texts,  
                custom_entities=True if texts else False,  
                det_bboxes=det_bboxes_from_initial,  
                det_labels=det_labels_from_initial,  
                fp16=self.config.fp16,  
                detector_type=self.config.detector_type,  
                show_fps=False  
            )  
        else:  
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
              
            # initial_annotationsが存在する場合は、既存の検出結果と結合する  
            if det_bboxes_from_initial is not None and det_labels_from_initial is not None:  
                det_bboxes = torch.cat([det_bboxes_from_initial, det_bboxes], dim=0)  
                det_labels = torch.cat([det_labels_from_initial, det_labels], dim=0)  
              
            track_result = inference_masa(  
                self.masa_model,  
                frame,  
                frame_id=frame_id,  
                video_len=1000,  # 仮の値、実際にはVideoManagerから取得  
                test_pipeline=self.masa_test_pipeline,  
                det_bboxes=det_bboxes,  
                det_labels=det_labels,  
                fp16=self.config.fp16,  
                show_fps=False  
            )  
          
        annotations = self._convert_track_result_to_annotations(  
            track_result, frame_id, texts  
        )  
          
        return annotations  
      
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
            label = "unknown"  
            if hasattr(pred_instances, 'labels') and i < len(pred_instances.labels):  
                label_idx = int(pred_instances.labels[i])  
                if texts:  
                    label_names = texts.split(' . ')  
                    label = label_names[label_idx] if label_idx < len(label_names) else f"class_{label_idx}"  
                else:  
                    # MASAモデルのクラス名があればそれを使用  
                    if hasattr(self.masa_model, 'dataset_meta') and 'classes' in self.masa_model.dataset_meta:  
                        classes = self.masa_model.dataset_meta['classes']  
                        label = classes[label_idx] if label_idx < len(classes) else f"class_{label_idx}"  
                    else:  
                        label = f"class_{label_idx}"  
              
            # インスタンスIDの取得  
            object_id = int(pred_instances.instances_id[i]) if hasattr(pred_instances, 'instances_id') else -1 # -1は新規IDを意味  
              
            annotation = ObjectAnnotation(  
                object_id=object_id,  
                label=label,  
                bbox=bbox,  
                frame_id=frame_id,  
                is_manual=False, # 自動追跡結果  
                track_confidence=float(pred_instances.scores[i])  
            )  
              
            # 信頼度スコアでフィルタリング  
            if annotation.bbox.confidence >= self.config.score_threshold:  
                annotations.append(annotation)  
          
        return annotations