# ObjectListTabManager.py  
"""  
オブジェクト一覧タブの管理を担当（旧CurrentFrameObjectListWidget）  
MenuPanelからオブジェクト一覧関連のUIと処理を分離  
"""  
from typing import Optional, List, Dict  
from PyQt6.QtWidgets import (  
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,  
    QHeaderView, QLabel, QSlider, QDoubleSpinBox, QCheckBox, QGroupBox,  
    QAbstractItemView, QPushButton  
)  
from PyQt6.QtCore import pyqtSignal, Qt  
from PyQt6.QtGui import QColor  
  
from MASAApplicationService import MASAApplicationService  
from DataClass import ObjectAnnotation, FrameAnnotation  
from ErrorHandler import ErrorHandler  
  
class ObjectListTabManager(QWidget):  
    """オブジェクト一覧タブのUI管理とフィルタリング機能"""  
      
    # シグナル定義  
    object_selected = pyqtSignal(object)  # ObjectAnnotation  
    object_double_clicked = pyqtSignal(object)  # ObjectAnnotation  
    config_changed = pyqtSignal(str, object, str)  # key, value, config_type  
      
    def __init__(self, app_service: MASAApplicationService, parent=None):  
        super().__init__(parent)  
        self.app_service = app_service  
          
        # 現在のフレーム情報  
        self.current_frame_id: int = 0  
        self.current_annotations: List[ObjectAnnotation] = []  
          
        # フィルタリング設定  
        self.score_threshold: float = 0.5  
        self.show_manual: bool = True  
        self.show_auto: bool = True  
        self.selected_annotation: Optional[ObjectAnnotation] = None  
          
        # UI要素  
        self.frame_info_label: Optional[QLabel] = None  
        self.table: Optional[QTableWidget] = None  
        self.score_threshold_slider: Optional[QSlider] = None  
        self.score_threshold_spinbox: Optional[QDoubleSpinBox] = None  
        self.show_manual_checkbox: Optional[QCheckBox] = None  
        self.show_auto_checkbox: Optional[QCheckBox] = None  
        self.refresh_btn: Optional[QPushButton] = None  
          
        self.setup_ui()  
        self.connect_signals()
    def setup_ui(self):  
        """UIを構築"""  
        layout = QVBoxLayout()  
        layout.setContentsMargins(5, 5, 5, 5)  
          
        # フレーム情報表示  
        self.setup_frame_info(layout)  
          
        # フィルタ設定  
        self.setup_filters(layout)  
          
        # オブジェクト一覧テーブル  
        self.setup_table(layout)  
          
        self.setLayout(layout)  
          
    def setup_frame_info(self, parent_layout):  
        """フレーム情報UIを構築"""  
        info_group = QGroupBox("Current Frame")  
        info_layout = QVBoxLayout()  
          
        self.frame_info_label = QLabel("Frame: 0 / 0")  
        self.frame_info_label.setStyleSheet("font-weight: bold; color: #2E7D32;")  
        info_layout.addWidget(self.frame_info_label)  
          
        self.refresh_btn = QPushButton("Refresh")  
        self.refresh_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 4px;")  
        info_layout.addWidget(self.refresh_btn)  
          
        info_group.setLayout(info_layout)  
        parent_layout.addWidget(info_group)  
          
    def setup_filters(self, parent_layout):  
        """フィルタUIを構築"""  
        filter_group = QGroupBox("Display Filters")  
        filter_layout = QVBoxLayout()  
          
        # スコア閾値設定  
        score_layout = QVBoxLayout()  
        score_layout.addWidget(QLabel("Score Threshold:"))  
          
        threshold_control_layout = QHBoxLayout()  
        self.score_threshold_slider = QSlider(Qt.Orientation.Horizontal)  
        self.score_threshold_slider.setMinimum(0)  
        self.score_threshold_slider.setMaximum(100)  
        self.score_threshold_slider.setValue(50)  # 0.5 * 100  
        threshold_control_layout.addWidget(self.score_threshold_slider)  
          
        self.score_threshold_spinbox = QDoubleSpinBox()  
        self.score_threshold_spinbox.setMinimum(0.0)  
        self.score_threshold_spinbox.setMaximum(1.0)  
        self.score_threshold_spinbox.setSingleStep(0.01)  
        self.score_threshold_spinbox.setValue(0.5)  
        self.score_threshold_spinbox.setDecimals(2)  
        threshold_control_layout.addWidget(self.score_threshold_spinbox)  
          
        score_layout.addLayout(threshold_control_layout)  
        filter_layout.addLayout(score_layout)  
          
        # 表示オプション  
        option_layout = QVBoxLayout()  
        self.show_manual_checkbox = QCheckBox("Show Manual Annotations")  
        self.show_manual_checkbox.setChecked(True)  
        option_layout.addWidget(self.show_manual_checkbox)  
          
        self.show_auto_checkbox = QCheckBox("Show Auto Annotations")  
        self.show_auto_checkbox.setChecked(True)  
        option_layout.addWidget(self.show_auto_checkbox)  
          
        filter_layout.addLayout(option_layout)  
          
        filter_group.setLayout(filter_layout)  
        parent_layout.addWidget(filter_group)
    def setup_table(self, parent_layout):  
        """オブジェクト一覧テーブルを構築"""  
        table_group = QGroupBox("Objects in Current Frame")  
        table_layout = QVBoxLayout()  
          
        self.table = QTableWidget()  
        self.table.setColumnCount(6)  
        self.table.setHorizontalHeaderLabels([  
            "ID", "Label", "Confidence", "Manual", "Position", "Size"  
        ])  
          
        # テーブル設定  
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)  
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)  
        self.table.setAlternatingRowColors(True)  
        self.table.setSortingEnabled(True)  
          
        # ヘッダー設定  
        header = self.table.horizontalHeader()  
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # ID  
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Label  
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Confidence  
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Manual  
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Position  
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Size  
          
        table_layout.addWidget(self.table)  
        table_group.setLayout(table_layout)  
        parent_layout.addWidget(table_group)  
          
    def connect_signals(self):  
        """シグナル接続を設定"""  
        # フィルタ設定  
        self.score_threshold_slider.valueChanged.connect(self._on_slider_changed)  
        self.score_threshold_spinbox.valueChanged.connect(self._on_spinbox_changed)  
        self.show_manual_checkbox.toggled.connect(self._on_filter_changed)  
        self.show_auto_checkbox.toggled.connect(self._on_filter_changed)  
          
        # テーブル操作  
        self.table.itemSelectionChanged.connect(self._on_selection_changed)  
        self.table.itemDoubleClicked.connect(self._on_item_double_clicked)  
          
        # リフレッシュボタン  
        self.refresh_btn.clicked.connect(self._on_refresh_clicked)
    # ===== イベントハンドラ =====  
      
    def _on_slider_changed(self, value: int):  
        """スライダー変更時の処理"""  
        threshold = value / 100.0  
        self.score_threshold_spinbox.setValue(threshold)  
        self._update_score_threshold(threshold)  
          
    def _on_spinbox_changed(self, value: float):  
        """スピンボックス変更時の処理"""  
        slider_value = int(value * 100)  
        self.score_threshold_slider.setValue(slider_value)  
        self._update_score_threshold(value)  
          
    def _update_score_threshold(self, threshold: float):  
        """スコア閾値を更新"""  
        self.score_threshold = threshold  
        self.config_changed.emit("score_threshold", threshold, "display")  
        self.apply_filters()  
          
    def _on_filter_changed(self):  
        """フィルタ設定変更時の処理"""  
        self.show_manual = self.show_manual_checkbox.isChecked()  
        self.show_auto = self.show_auto_checkbox.isChecked()  
          
        self.config_changed.emit("show_manual_annotations", self.show_manual, "display")  
        self.config_changed.emit("show_auto_annotations", self.show_auto, "display")  
          
        self.apply_filters()  
          
    def _on_selection_changed(self):  
        """テーブル選択変更時の処理"""  
        selected_items = self.table.selectedItems()  
        if selected_items:  
            row = selected_items[0].row()  
            if 0 <= row < len(self.current_annotations):  
                annotation = self.current_annotations[row]  
                self.selected_annotation = annotation  
                self.object_selected.emit(annotation)  
        else:  
            self.selected_annotation = None  
            self.object_selected.emit(None)  
              
    def _on_item_double_clicked(self, item):  
        """テーブルアイテムダブルクリック時の処理"""  
        row = item.row()  
        if 0 <= row < len(self.current_annotations):  
            annotation = self.current_annotations[row]  
            self.object_double_clicked.emit(annotation)  
              
    def _on_refresh_clicked(self):  
        """リフレッシュボタンクリック時の処理"""  
        # 現在のフレームアノテーションを再取得  
        frame_annotation = self.app_service.annotation_repository.get_annotations(self.current_frame_id)  
        self.update_frame_data(self.current_frame_id, frame_annotation)
    # ===== 公開メソッド =====  
      
    def update_frame_data(self, frame_id: int, frame_annotation: Optional[FrameAnnotation]):  
        """フレームデータを更新"""  
        self.current_frame_id = frame_id  
          
        # フレーム情報を更新（修正版 - MASAApplicationService経由でアクセス）  
        if self.frame_info_label:  
            # VideoManagerが存在する場合のみ総フレーム数を取得  
            total_frames = 0  
            if hasattr(self.app_service, 'video_manager') and self.app_service.video_manager:  
                total_frames = self.app_service.video_manager.get_total_frames()  
            self.frame_info_label.setText(f"Frame: {frame_id} / {total_frames}")  
          
        # アノテーションリストを更新  
        if frame_annotation and frame_annotation.objects:  
            self.current_annotations = frame_annotation.objects.copy()  
        else:  
            self.current_annotations = []  
              
        # フィルタを適用してテーブルを更新  
        self.apply_filters()  
          
    def apply_filters(self):  
        """フィルタを適用してテーブルを更新"""  
        if not self.table:  
            return  
              
        # フィルタリング  
        filtered_annotations = []  
        for annotation in self.current_annotations:  
            # スコア閾値チェック  
            if annotation.bbox.confidence < self.score_threshold:  
                continue  
                  
            # マニュアル/自動フィルタチェック  
            if annotation.is_manual and not self.show_manual:  
                continue  
            if not annotation.is_manual and not self.show_auto:  
                continue  
                  
            filtered_annotations.append(annotation)  
              
        # テーブル更新  
        self._update_table(filtered_annotations)  
          
    def _update_table(self, annotations: List[ObjectAnnotation]):  
        """テーブルを更新"""  
        self.table.setRowCount(len(annotations))  
          
        for row, annotation in enumerate(annotations):  
            # ID  
            id_item = QTableWidgetItem(str(annotation.object_id))  
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  
            self.table.setItem(row, 0, id_item)  
              
            # Label  
            label_item = QTableWidgetItem(annotation.label)  
            if annotation.is_manual:  
                label_item.setBackground(QColor("#E8F5E8"))  # 薄い緑  
            else:  
                label_item.setBackground(QColor("#E3F2FD"))  # 薄い青  
            self.table.setItem(row, 1, label_item)  
              
            # Confidence  
            conf_item = QTableWidgetItem(f"{annotation.bbox.confidence:.3f}")  
            conf_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  
            if annotation.bbox.confidence < 0.5:  
                conf_item.setForeground(QColor("#F44336"))  # 赤  
            elif annotation.bbox.confidence < 0.8:  
                conf_item.setForeground(QColor("#FF9800"))  # オレンジ  
            else:  
                conf_item.setForeground(QColor("#4CAF50"))  # 緑  
            self.table.setItem(row, 2, conf_item)  
              
            # Manual  
            manual_item = QTableWidgetItem("Yes" if annotation.is_manual else "No")  
            manual_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  
            if annotation.is_manual:  
                manual_item.setForeground(QColor("#4CAF50"))  
            else:  
                manual_item.setForeground(QColor("#2196F3"))  
            self.table.setItem(row, 3, manual_item)  
              
            # Position  
            bbox = annotation.bbox  
            pos_text = f"({bbox.x1},{bbox.y1})"  
            pos_item = QTableWidgetItem(pos_text)  
            pos_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  
            self.table.setItem(row, 4, pos_item)  
              
            # Size  
            width = bbox.x2 - bbox.x1  
            height = bbox.y2 - bbox.y1  
            size_text = f"{width}×{height}"  
            size_item = QTableWidgetItem(size_text)  
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  
            self.table.setItem(row, 5, size_item)  
              
        # 現在の選択を維持  
        if self.selected_annotation:  
            self.select_annotation(self.selected_annotation)
    def select_annotation(self, annotation: Optional[ObjectAnnotation]):  
        """指定されたアノテーションを選択"""  
        if not annotation or not self.table:  
            return  
              
        # テーブル内で該当する行を探す  
        for row in range(self.table.rowCount()):  
            id_item = self.table.item(row, 0)  
            if id_item and int(id_item.text()) == annotation.object_id:  
                # 該当する行の最初のフレームのアノテーションIDが一致するかチェック  
                if row < len(self.current_annotations):  
                    table_annotation = self.current_annotations[row]  
                    if (table_annotation.object_id == annotation.object_id and   
                        table_annotation.frame_id == annotation.frame_id):  
                        self.table.selectRow(row)  
                        self.selected_annotation = annotation  
                        break  
                          
    def get_selected_annotation(self) -> Optional[ObjectAnnotation]:  
        """選択中のアノテーションを取得"""  
        return self.selected_annotation  
          
    def set_score_threshold(self, threshold: float):  
        """外部からスコア閾値を設定"""  
        self.score_threshold = threshold  
        if self.score_threshold_slider:  
            self.score_threshold_slider.setValue(int(threshold * 100))  
        if self.score_threshold_spinbox:  
            self.score_threshold_spinbox.setValue(threshold)  
        self.apply_filters()  
          
    def set_display_options(self, show_manual: bool, show_auto: bool):  
        """外部から表示オプションを設定"""  
        self.show_manual = show_manual  
        self.show_auto = show_auto  
          
        if self.show_manual_checkbox:  
            self.show_manual_checkbox.setChecked(show_manual)  
        if self.show_auto_checkbox:  
            self.show_auto_checkbox.setChecked(show_auto)  
              
        self.apply_filters()  
          
    def clear_selection(self):  
        """選択をクリア"""  
        if self.table:  
            self.table.clearSelection()  
        self.selected_annotation = None  
          
    def get_annotation_count(self) -> Dict[str, int]:  
        """現在表示中のアノテーション数を取得"""  
        return {  
            "total": len(self.current_annotations),  
            "filtered": self.table.rowCount() if self.table else 0,  
            "manual": sum(1 for ann in self.current_annotations if ann.is_manual),  
            "auto": sum(1 for ann in self.current_annotations if not ann.is_manual)  
        }  
          
    def update_object_list_selection(self, annotation: Optional[ObjectAnnotation]):  
        """外部からの選択更新（双方向同期用）"""  
        if annotation != self.selected_annotation:  
            self.selected_annotation = annotation  
            self.select_annotation(annotation)