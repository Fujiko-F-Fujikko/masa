# ObjectListTabWidget.py  
from typing import List, Optional  
from PyQt6.QtWidgets import (  
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,  
    QTableWidget, QTableWidgetItem, QHeaderView,  
    QComboBox, QCheckBox, QGroupBox  
)  
from PyQt6.QtCore import Qt, pyqtSignal  
from PyQt6.QtGui import QFont  
  
from ConfigManager import ConfigManager  
from ErrorHandler import ErrorHandler  
from DataClass import ObjectAnnotation, FrameAnnotation  
  
class ObjectListTabWidget(QWidget):  
    """オブジェクト一覧タブウィジェット（CurrentFrameObjectListWidget統合版）"""  
      
    # シグナル定義  
    object_selected = pyqtSignal(object)  # ObjectAnnotation  
      
    def __init__(self, config_manager: ConfigManager, annotation_repository, command_manager, main_widget, parent=None):  
        super().__init__(parent)  
        self.config_manager = config_manager  
        self.annotation_repository = annotation_repository  
        self.command_manager = command_manager  
        self.main_widget = main_widget  # MASAAnnotationWidgetへの参照  
        self.parent_menu_panel = parent  # MenuPanelへの参照  
          
        # CurrentFrameObjectListWidgetから統合された状態変数  
        self.current_frame_id = 0  
        self.current_annotations: List[ObjectAnnotation] = []  
        self.selected_annotation: Optional[ObjectAnnotation] = None  
        self.score_threshold = 0.2  # デフォルトのスコア閾値  
          
        self.setup_ui()  
        self._connect_signals()  
      
    def setup_ui(self):  
        """UIセットアップ（CurrentFrameObjectListWidgetから統合）"""  
        layout = QVBoxLayout()  
        layout.setSpacing(5)  
        layout.setContentsMargins(5, 5, 5, 5)  
          
        # ヘッダー情報  
        header_layout = QHBoxLayout()  
        self.frame_info_label = QLabel("Frame: 0")  
        self.frame_info_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))  
        header_layout.addWidget(self.frame_info_label)  
          
        self.object_count_label = QLabel("Objects: 0")  
        header_layout.addWidget(self.object_count_label)  
        header_layout.addStretch()  
          
        layout.addLayout(header_layout)  
          
        # フィルタリングオプション  
        filter_group = QGroupBox("Filter")  
        filter_layout = QVBoxLayout()  
          
        # ラベルフィルタ  
        label_filter_layout = QHBoxLayout()  
        label_filter_layout.addWidget(QLabel("Label:"))  
        self.label_filter_combo = QComboBox()  
        self.label_filter_combo.addItem("All")  
        self.label_filter_combo.setEditable(False)  
        label_filter_layout.addWidget(self.label_filter_combo)  
        filter_layout.addLayout(label_filter_layout)  
          
        # 表示オプション  
        options_layout = QHBoxLayout()  
        self.show_manual_cb = QCheckBox("Manual Annotation")  
        self.show_manual_cb.setChecked(True)  
        self.show_auto_cb = QCheckBox("Auto Annotation")  
        self.show_auto_cb.setChecked(True)  
          
        simple_checkbox_style = """    
        QCheckBox::indicator:checked {    
            background-color: white;    
            border: 2px solid #4CAF50;    
            background-image: url(file:///../AutoAnnotationTool/resources/checkmark_green_thick.svg);  
            background-repeat: no-repeat;    
            background-position: center;    
        }    
        QCheckBox::indicator:unchecked {      
            background-color: white;      
            border: 2px solid #ccc;      
        }  
        """  
        self.show_manual_cb.setStyleSheet(simple_checkbox_style)  
        self.show_auto_cb.setStyleSheet(simple_checkbox_style)  
          
        options_layout.addWidget(self.show_manual_cb)  
        options_layout.addWidget(self.show_auto_cb)  
        filter_layout.addLayout(options_layout)  
          
        filter_group.setLayout(filter_layout)  
        layout.addWidget(filter_group)  
          
        # オブジェクト一覧テーブル  
        self.table = QTableWidget()  
        self.setup_table()  
        layout.addWidget(self.table)  
          
        self.setLayout(layout)  
      
    def setup_table(self):  
        """テーブルの初期設定（CurrentFrameObjectListWidgetから統合）"""  
        columns = ["Track ID", "Label", "Coordinates (x1,y1,x2,y2)", "Confidence", "Type"]  
        self.table.setColumnCount(len(columns))  
        self.table.setHorizontalHeaderLabels(columns)  
          
        # 列幅の調整（ユーザーがマウスで調整可能）  
        header = self.table.horizontalHeader()  
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)  # Track ID  
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # ラベル  
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # 座標  
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)  # 信頼度  
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Interactive)  # 種別  
          
        # デフォルトの列幅を設定（ユーザーが調整可能）  
        header.resizeSection(0, 40)   # Track ID: 40px  
        header.resizeSection(1, 60)   # ラベル: 60px  
        header.resizeSection(2, 100)  # 座標: 100px  
        header.resizeSection(3, 50)   # 信頼度: 50px  
        header.resizeSection(4, 40)   # 種別: 40px  
          
        # 最小列幅を設定  
        header.setMinimumSectionSize(20)  # 最小20px  
          
        # テーブルの設定  
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)  
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)  
        self.table.setAlternatingRowColors(True)  
        self.table.setSortingEnabled(True)  
          
        # スタイル設定  
        self.table.setStyleSheet("""  
            QTableWidget {  
                gridline-color: #d0d0d0;  
                background-color: white;  
            }  
            QTableWidget::item:selected {  
                background-color: #4CAF50;  
                color: white;  
            }  
            QTableWidget::item:hover {  
                background-color: #e8f5e8;  
            }  
            QHeaderView::section {  
                background-color: #f0f0f0;  
                border: 1px solid #d0d0d0;  
                padding: 4px;  
                font-weight: bold;  
            }  
        """)  
      
    def _connect_signals(self):  
        """シグナル接続（CurrentFrameObjectListWidgetから統合）"""  
        self.table.itemSelectionChanged.connect(self._on_selection_changed)  
        self.label_filter_combo.currentTextChanged.connect(self._apply_filters)  
        self.show_manual_cb.stateChanged.connect(self._apply_filters)  
        self.show_auto_cb.stateChanged.connect(self._apply_filters)  
      
    def update_frame_data(self, frame_id: int, frame_annotation: Optional[FrameAnnotation]):  
        """フレームデータを更新（CurrentFrameObjectListWidgetから統合）"""  
        self.current_frame_id = frame_id  
        self.frame_info_label.setText(f"Frame: {frame_id}")  
          
        if frame_annotation and frame_annotation.objects:  
            self.current_annotations = frame_annotation.objects  
        else:  
            self.current_annotations = []  
              
        self._update_label_filter()  
        self._populate_table()  
        self._update_object_count()  
      
    def _update_label_filter(self):  
        """ラベルフィルタコンボボックスを更新（CurrentFrameObjectListWidgetから統合）"""  
        current_selection = self.label_filter_combo.currentText()  
        self.label_filter_combo.blockSignals(True)  
          
        self.label_filter_combo.clear()  
        self.label_filter_combo.addItem("All")  
          
        # 現在のフレームのラベルを取得  
        labels = set()  
        for annotation in self.current_annotations:  
            labels.add(annotation.label)  
              
        for label in sorted(labels):  
            self.label_filter_combo.addItem(label)  
              
        # 以前の選択を復元  
        index = self.label_filter_combo.findText(current_selection)  
        if index >= 0:  
            self.label_filter_combo.setCurrentIndex(index)  
        else:  
            self.label_filter_combo.setCurrentIndex(0)  
              
        self.label_filter_combo.blockSignals(False)  
      
    def _populate_table(self):  
        """テーブルにデータを設定（CurrentFrameObjectListWidgetから統合）"""  
        # フィルタリング適用  
        filtered_annotations = self._get_filtered_annotations()  
          
        self.table.setRowCount(len(filtered_annotations))  
        self.table.setSortingEnabled(False)  # ソートを一時無効化  
          
        for row, annotation in enumerate(filtered_annotations):  
            # Track ID  
            track_id_item = QTableWidgetItem(str(annotation.object_id))  
            track_id_item.setData(Qt.ItemDataRole.UserRole, annotation)  
            track_id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  
            track_id_item.setFlags(track_id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # 編集不可  
            self.table.setItem(row, 0, track_id_item)  
              
            # ラベル  
            label_item = QTableWidgetItem(annotation.label)  
            label_item.setData(Qt.ItemDataRole.UserRole, annotation)  
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # 編集不可  
            self.table.setItem(row, 1, label_item)  
              
            # 座標  
            bbox = annotation.bbox  
            coord_text = f"({bbox.x1:.0f},{bbox.y1:.0f},{bbox.x2:.0f},{bbox.y2:.0f})"  
            coord_item = QTableWidgetItem(coord_text)  
            coord_item.setData(Qt.ItemDataRole.UserRole, annotation)  
            coord_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  
            coord_item.setFlags(coord_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # 編集不可  
            self.table.setItem(row, 2, coord_item)  
              
            # 信頼度  
            confidence_text = f"{annotation.bbox.confidence:.3f}"  
            confidence_item = QTableWidgetItem(confidence_text)  
            confidence_item.setData(Qt.ItemDataRole.UserRole, annotation)  
            confidence_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  
            confidence_item.setFlags(confidence_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # 編集不可  
            self.table.setItem(row, 3, confidence_item)  
              
            # 種別  
            type_text = "Manual" if annotation.is_manual else "Auto"  
            type_item = QTableWidgetItem(type_text)  
            type_item.setData(Qt.ItemDataRole.UserRole, annotation)  
            type_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)  
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # 編集不可  
            self.table.setItem(row, 4, type_item)  
              
        self.table.setSortingEnabled(True)  # ソートを再有効化  
      
    def _get_filtered_annotations(self) -> List[ObjectAnnotation]:  
        """フィルタリング適用されたアノテーションリストを取得（CurrentFrameObjectListWidgetから統合）"""  
        filtered = []  
          
        selected_label = self.label_filter_combo.currentText()  
        show_manual = self.show_manual_cb.isChecked()  
        show_auto = self.show_auto_cb.isChecked()  
          
        for annotation in self.current_annotations:  
            # スコア閾値フィルタ  
            if annotation.bbox.confidence < self.score_threshold:  
                continue  
            if selected_label != "All" and annotation.label != selected_label:  
                continue  
                  
            # 種別フィルタ  
            if annotation.is_manual and not show_manual:  
                continue  
            if not annotation.is_manual and not show_auto:  
                continue  
                  
            filtered.append(annotation)  
              
        return filtered  
      
    def _apply_filters(self):  
        """フィルタを適用してテーブルを更新（CurrentFrameObjectListWidgetから統合）"""  
        self._populate_table()  
        self._update_object_count()  
      
    def _update_object_count(self):  
        """オブジェクト数表示を更新（CurrentFrameObjectListWidgetから統合）"""  
        filtered_count = len(self._get_filtered_annotations())  
        total_count = len(self.current_annotations)  
          
        if filtered_count == total_count:  
            self.object_count_label.setText(f"Objects: {total_count}")  
        else:  
            self.object_count_label.setText(f"Objects: {filtered_count}/{total_count}")  

    def _on_selection_changed(self):    
        """テーブル選択変更時の処理（CurrentFrameObjectListWidgetから統合）"""    
        # 循環呼び出し防止    
        if hasattr(self, '_updating_selection') and self._updating_selection:    
            return    
                
        selected_items = self.table.selectedItems()    
            
        if selected_items:    
            # 最初の選択されたアイテムからアノテーションを取得    
            annotation = selected_items[0].data(Qt.ItemDataRole.UserRole)    
                
            # object_idベースで比較（オブジェクト参照ではなく）    
            if (annotation is None or self.selected_annotation is None or     
                annotation.object_id != self.selected_annotation.object_id):    
                self.selected_annotation = annotation    
                self.object_selected.emit(annotation)    
                
                # シングルクリックでフォーカス処理も実行  
                self.on_object_focus_requested(annotation)  
        else:    
            self.selected_annotation = None    
            self.object_selected.emit(None) 
                            
    def select_annotation(self, annotation: Optional[ObjectAnnotation]):  
        """外部からのアノテーション選択（CurrentFrameObjectListWidgetから統合）"""  
        # _updating_selectionフラグを設定してシグナルをブロック  
        self._updating_selection = True  
        try:  
            self.table.clearSelection()  
              
            if annotation is None:  
                self.selected_annotation = None  
                return  
                  
            # テーブル内で該当するアノテーションを検索して選択  
            for row in range(self.table.rowCount()):  
                item = self.table.item(row, 0)  # Track ID列  
                if item:  
                    item_annotation = item.data(Qt.ItemDataRole.UserRole)  
                    if item_annotation and item_annotation.object_id == annotation.object_id:  
                        self.table.selectRow(row)  
                        self.table.scrollToItem(item)  
                        self.selected_annotation = annotation  
                        return  
        finally:  
            self._updating_selection = False  
                  
    def get_selected_annotation(self) -> Optional[ObjectAnnotation]:  
        """選択中のアノテーションを取得（CurrentFrameObjectListWidgetから統合）"""  
        return self.selected_annotation  
          
    def clear_selection(self):  
        """選択をクリア（CurrentFrameObjectListWidgetから統合）"""  
        self.table.clearSelection()  
        self.selected_annotation = None  
          
    def set_score_threshold(self, threshold: float):  
        """スコア閾値を設定（CurrentFrameObjectListWidgetから統合）"""  
        self.score_threshold = threshold  
        self._apply_filters()  # 閾値変更時にフィルタを再適用  
  
    # 移動された関数（MASAAnnotationWidgetから移動）  
    def on_object_focus_requested(self, annotation: Optional[ObjectAnnotation]):  
        """オブジェクトフォーカス要求時の処理"""  
        # ビデオプレビューでオブジェクトにフォーカス  
        self.main_widget.video_preview.select_and_focus_annotation(annotation)  

    # 外部インターフェース用メソッド（MenuPanelとの互換性維持）  
    def update_current_frame_objects(self, frame_id: int, frame_annotation: Optional[FrameAnnotation] = None):  
        """現在フレームのオブジェクト一覧を更新"""  
        self.update_frame_data(frame_id, frame_annotation)  
      
    def set_object_list_score_threshold(self, threshold: float):  
        """オブジェクト一覧のスコア閾値を設定"""  
        self.set_score_threshold(threshold)  
      
    def update_object_list_selection(self, annotation: Optional[ObjectAnnotation]):  
        """オブジェクト一覧の選択状態を更新"""  
        self.select_annotation(annotation)  
      
    def get_object_list_widget(self):  
        """オブジェクト一覧ウィジェットを取得（自分自身を返す）"""  
        return self

    def update_display_settings(self, show_manual: bool, show_auto: bool, score_threshold: float):  
        """Display settingからの設定更新"""  
        self.show_manual_cb.setChecked(show_manual)  
        self.show_auto_cb.setChecked(show_auto)  
        self.score_threshold = score_threshold  
        self._apply_filters()