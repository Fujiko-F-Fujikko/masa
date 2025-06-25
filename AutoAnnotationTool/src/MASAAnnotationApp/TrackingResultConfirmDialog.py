import cv2  
import numpy as np  
from PyQt6.QtWidgets import (  
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,  
    QSlider, QFrame, QSizePolicy, QListWidget, QListWidgetItem, QMessageBox, QCheckBox  
)  
from PyQt6.QtCore import Qt  
from PyQt6.QtGui import QPixmap, QImage  
from typing import Dict, List, Optional  
from DataClass import ObjectAnnotation  
from AnnotationVisualizer import AnnotationVisualizer  
  
class TrackingResultConfirmDialog(QDialog):  
    """Track IDごとに選択・非選択できる追跡結果確認ダイアログ"""  
  
    def __init__(self, tracking_results: Dict[int, List[ObjectAnnotation]],  
                 video_manager, parent=None):  
        super().__init__(parent)  
        self.tracking_results = tracking_results  # {frame_id: [ObjectAnnotation]}  
        self.video_manager = video_manager  
        self.approved = False  
        self.visualizer = AnnotationVisualizer()  
        self.current_frame_id = None  
  
        # Track IDごとにグループ化  
        self.grouped_tracking_results: Dict[int, List[ObjectAnnotation]] = {}  
        for frame_id, ann_list in tracking_results.items():  
            for ann in ann_list:  
                if ann.object_id not in self.grouped_tracking_results:  
                    self.grouped_tracking_results[ann.object_id] = []  
                self.grouped_tracking_results[ann.object_id].append(ann)  
        # Track IDごとの選択状態  
        self.track_selected: Dict[int, bool] = {track_id: True for track_id in self.grouped_tracking_results.keys()}  
  
        self.setup_ui()  
        if self.grouped_tracking_results:  
            self.track_list_widget.setCurrentRow(0)  
            self.update_preview()  
  
    def setup_ui(self):  
        self.setWindowTitle("追跡結果の確認")  
        self.setModal(True)  
        self.resize(1100, 750)  
        layout = QVBoxLayout()  
  
        # Track IDリスト  
        track_group = QFrame()  
        track_group.setFrameStyle(QFrame.Shape.Box)  
        track_group.setStyleSheet("border: 2px solid #ccc; background-color: #f9f9f9;")  
        track_layout = QVBoxLayout(track_group)  
        track_title = QLabel("Track IDごとに承認するものを選択:")  
        track_title.setStyleSheet("font-weight: bold; margin: 5px;")  
        track_layout.addWidget(track_title)  
  
        self.track_list_widget = QListWidget()  
        self.track_list_widget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)  
        self.track_list_widget.itemSelectionChanged.connect(self.on_track_list_selection_changed)  
        self.track_id_to_item: Dict[int, QListWidgetItem] = {}  
        for track_id, anns in self.grouped_tracking_results.items():  
            label = anns[0].label if anns else ""  
            item_text = f"Track ID: {track_id} | {label} | {len(anns)}件"  
            item = QListWidgetItem(item_text)  
            item.setData(Qt.ItemDataRole.UserRole, track_id)  
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)  
            item.setCheckState(Qt.CheckState.Checked)  
            self.track_list_widget.addItem(item)  
            self.track_id_to_item[track_id] = item  

        self.track_list_widget.setStyleSheet("""  
        QListWidget::item {  
            padding: 4px 0px 4px 0px;  
        }  
        QListWidget::item:selected {  
            background: #e0f7fa;  
        }  
        QListWidget::indicator:checked {  
            background-color: #4CAF50;  
            border: 1px solid #388E3C;  
        }  
        QListWidget::indicator:unchecked {  
            background-color: white;  
            border: 1px solid #ccc;  
        }  
        """)

        self.track_list_widget.itemChanged.connect(self.on_track_item_check_changed)  
        track_layout.addWidget(self.track_list_widget)  
        layout.addWidget(track_group)  
  
        # プレビュー  
        preview_frame = QFrame()  
        preview_frame.setFrameStyle(QFrame.Shape.Box)  
        preview_frame.setStyleSheet("border: 2px solid #ccc; background-color: #f9f9f9;")  
        preview_layout = QVBoxLayout(preview_frame)  
        preview_title = QLabel("プレビュー:")  
        preview_title.setStyleSheet("font-weight: bold; margin: 5px;")  
        preview_layout.addWidget(preview_title)  
        self.preview_widget = QLabel()  
        self.preview_widget.setMinimumSize(600, 400)  
        self.preview_widget.setMaximumSize(800, 600)  
        self.preview_widget.setStyleSheet("border: 1px solid gray; background-color: black;")  
        self.preview_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        self.preview_widget.setScaledContents(True)  
        self.preview_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)  
        preview_layout.addWidget(self.preview_widget)  
        frame_control_layout = QHBoxLayout()  
        frame_control_layout.addWidget(QLabel("フレーム:"))  
        all_frame_ids = sorted({fid for fid in self.tracking_results})  
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)  
        if all_frame_ids:  
            self.frame_slider.setMinimum(min(all_frame_ids))  
            self.frame_slider.setMaximum(max(all_frame_ids))  
            self.frame_slider.setValue(min(all_frame_ids))  
            self.frame_slider.valueChanged.connect(self.update_preview)  
        frame_control_layout.addWidget(self.frame_slider)  
        self.frame_info_label = QLabel("Frame: 0")  
        frame_control_layout.addWidget(self.frame_info_label)  
        preview_layout.addLayout(frame_control_layout)  
        layout.addWidget(preview_frame)  
  
        # 詳細  
        self.annotation_info_label = QLabel("アノテーション情報: 選択されたTrackの詳細がここに表示されます")  
        self.annotation_info_label.setStyleSheet("margin: 10px; padding: 5px; background-color: #f0f0f0;")  
        layout.addWidget(self.annotation_info_label)  
  
        # 承認/破棄  
        bottom_btn_layout = QHBoxLayout()  
        self.approve_btn = QPushButton("選択中のアノテーションを承認して追加")  
        self.approve_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")  
        self.approve_btn.clicked.connect(self.approve_results)  
        bottom_btn_layout.addWidget(self.approve_btn)  
        self.reject_btn = QPushButton("全て破棄")  
        self.reject_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold;")  
        self.reject_btn.clicked.connect(self.reject_results)  
        bottom_btn_layout.addWidget(self.reject_btn)  
        layout.addLayout(bottom_btn_layout)  
        self.setLayout(layout)  
  
    def on_track_list_selection_changed(self):  
        self.update_preview()  
  
    def on_track_item_check_changed(self, item: QListWidgetItem):  
        track_id = item.data(Qt.ItemDataRole.UserRole)  
        checked = item.checkState() == Qt.CheckState.Checked  
        self.track_selected[track_id] = checked  
        # グレーアウト表示  
        font = item.font()  
        if checked:  
            font.setStrikeOut(False)  
            item.setForeground(Qt.GlobalColor.black)  
        else:  
            font.setStrikeOut(True)  
            item.setForeground(Qt.GlobalColor.gray)  
        item.setFont(font)  
        self.update_preview()  
  
    def get_selected_track_id(self) -> Optional[int]:  
        selected_items = self.track_list_widget.selectedItems()  
        if selected_items:  
            return selected_items[0].data(Qt.ItemDataRole.UserRole)  
        return None  
  
    def update_preview(self):  
        track_id = self.get_selected_track_id()  
        frame_id = self.frame_slider.value()  
        self.current_frame_id = frame_id  
        self.frame_info_label.setText(f"Frame: {frame_id}")  
  
        # Track IDでフィルタ  
        annotations = []  
        if track_id is not None and track_id in self.grouped_tracking_results:  
            annotations = [ann for ann in self.grouped_tracking_results[track_id] if ann.frame_id == frame_id]  
  
        # 詳細  
        if annotations:  
            info_text = f"Track ID {track_id} | フレーム {frame_id}: {len(annotations)}個\n"  
            for i, ann in enumerate(annotations):  
                bbox = ann.bbox  
                info_text += f"  {i+1}. ラベル: {ann.label}, 位置: ({bbox.x1:.0f}, {bbox.y1:.0f}) - ({bbox.x2:.0f}, {bbox.y2:.0f}), 信頼度: {bbox.confidence:.3f}\n"  
        else:  
            info_text = f"Track ID {track_id} | フレーム {frame_id}: アノテーションなし"  
        self.annotation_info_label.setText(info_text)  
  
        # プレビュー  
        frame = self.video_manager.get_frame(frame_id)  
        if frame is None:  
            self.preview_widget.setText("フレームを読み込めませんでした")  
            return  
        annotated_frame = self.visualizer.draw_annotations(  
            frame.copy(),  
            annotations,  
            show_ids=True,  
            show_confidence=True,  
            selected_annotation=None  
        )  
        self.display_frame(annotated_frame)  
  
    def display_frame(self, frame: np.ndarray):  
        try:  
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  
            height, width, channel = rgb_frame.shape  
            bytes_per_line = 3 * width  
            q_image = QImage(  
                rgb_frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888  
            )  
            pixmap = QPixmap.fromImage(q_image)  
            scaled_pixmap = pixmap.scaled(  
                self.preview_widget.size(),  
                Qt.AspectRatioMode.KeepAspectRatio,  
                Qt.TransformationMode.SmoothTransformation  
            )  
            self.preview_widget.setPixmap(scaled_pixmap)  
        except Exception as e:  
            self.preview_widget.setText(f"プレビュー表示エラー: {str(e)}")  
  
    def approve_results(self):  
        self.approved = True  
        # 選択されているTrack IDのアノテーションのみをframe_idごとに再構成  
        final_approved: Dict[int, List[ObjectAnnotation]] = {}  
        for track_id, is_selected in self.track_selected.items():  
            if is_selected:  
                for ann in self.grouped_tracking_results[track_id]:  
                    if ann.frame_id not in final_approved:  
                        final_approved[ann.frame_id] = []  
                    final_approved[ann.frame_id].append(ann)  
        self.tracking_results = final_approved  
        self.accept()  
  
    def reject_results(self):  
        self.approved = False  
        self.reject()