# AnnotationTabWidget.py  
from typing import Dict, List, Any, Optional  
from PyQt6.QtWidgets import (  
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,  
    QPushButton, QGroupBox, QLineEdit,  
    QMessageBox, QComboBox, QDialog,
    QInputDialog
)  
from PyQt6.QtCore import pyqtSignal  
  
from ConfigManager import ConfigManager  
from ErrorHandler import ErrorHandler  
from DataClass import ObjectAnnotation, BoundingBox  
from AnnotationInputDialog import AnnotationInputDialog  
  
class AnnotationTabWidget(QWidget):  
    """アノテーション編集タブウィジェット（編集・トラッキング・コピー機能）"""  
      
    # シグナル定義  
    edit_mode_requested = pyqtSignal(bool)  
    tracking_mode_requested = pyqtSignal(bool)  
    copy_mode_requested = pyqtSignal(bool)  
    delete_mode_requested = pyqtSignal(bool)  
      
    tracking_requested = pyqtSignal(int, str)  
    copy_annotations_requested = pyqtSignal(int, str)  
    delete_annotations_requested = pyqtSignal(int, int, int)  # track_id, start_frame, end_frame
      
    label_change_requested = pyqtSignal(object, str)  
    delete_single_annotation_requested = pyqtSignal(object)  
    delete_track_requested = pyqtSignal(int)  
    propagate_label_requested = pyqtSignal(int, str)  
    propagate_confidence_requested = pyqtSignal(int, float)
    align_track_ids_requested = pyqtSignal(str, int)  
    copy_annotation_requested = pyqtSignal()  
    paste_annotation_requested = pyqtSignal()  
      
    def __init__(self, config_manager: ConfigManager, annotation_repository, command_manager, main_widget, parent=None):  
        super().__init__(parent)  
        self.config_manager = config_manager  
        self.annotation_repository = annotation_repository  
        self.command_manager = command_manager  
        self.main_widget = main_widget  # MASAAnnotationWidgetへの参照  
        self.parent_menu_panel = parent  # MenuPanelへの参照  
          
        # アノテーション選択状態  
        self.current_selected_annotation: Optional[ObjectAnnotation] = None  
          
        self.setup_ui()  
      
    def setup_ui(self):  
        layout = QVBoxLayout()  
        layout.setContentsMargins(5, 5, 5, 5)  
          
        # アノテーション情報グループ  
        info_group = QGroupBox("Annotation Info")  
        info_layout = QVBoxLayout()  
        self.annotation_count_label = QLabel("Annotation Count: 0")  
        info_layout.addWidget(self.annotation_count_label)  
        info_group.setLayout(info_layout)  
        layout.addWidget(info_group)  
          
        # アノテーション編集グループ  
        edit_group = QGroupBox("Edit Annotation")  
        edit_layout = QVBoxLayout()  
          
        # EditModeボタン用スタイル  
        edit_button_style = """  
            QPushButton {  
                background-color: #f0f0f0;  
                border: 2px solid #ccc;  
                padding: 5px;  
            }  
            QPushButton:checked {  
                background-color: #FFD700;  
                border: 2px solid #FFA500;  
                font-weight: bold;  
            }  
        """  
          
        self.edit_mode_btn = QPushButton("Edit Mode (E)")  
        self.edit_mode_btn.setCheckable(True)  
        self.edit_mode_btn.setStyleSheet(edit_button_style)  
        self.edit_mode_btn.clicked.connect(self._on_edit_mode_clicked)  
        self.edit_mode_btn.setEnabled(False)  
        edit_layout.addWidget(self.edit_mode_btn)  
          
        self.label_combo = QComboBox()  
        self.label_combo.setEditable(True)  
        self.label_combo.setEnabled(True)  
        self.label_combo.currentIndexChanged.connect(self._on_label_changed)  
        edit_layout.addWidget(QLabel("Label:"))  
        edit_layout.addWidget(self.label_combo)  
          
        self.track_id_edit = QLineEdit()  
        self.track_id_edit.setEnabled(False)  
        self.track_id_edit.setReadOnly(True)  
        edit_layout.addWidget(QLabel("Track ID:"))  
        edit_layout.addWidget(self.track_id_edit)  
          
        self.delete_single_annotation_btn = QPushButton("Delete Selected Annotation (X)")  
        self.delete_single_annotation_btn.setEnabled(False)  
        self.delete_single_annotation_btn.clicked.connect(self._on_delete_single_annotation_clicked)  
        edit_layout.addWidget(self.delete_single_annotation_btn)  
          
        self.delete_track_btn = QPushButton("Delete All (Del)")  
        self.delete_track_btn.setEnabled(False)  
        self.delete_track_btn.clicked.connect(self._on_delete_track_clicked)  
        edit_layout.addWidget(self.delete_track_btn)  
          
        self.propagate_label_btn = QPushButton("Change Label for All (P)")  
        self.propagate_label_btn.setEnabled(False)  
        self.propagate_label_btn.clicked.connect(self._on_propagate_label_clicked)  
        edit_layout.addWidget(self.propagate_label_btn)  
        
        self.propagate_confidence_btn = QPushButton("Change Confidence for All (F)")  
        self.propagate_confidence_btn.setEnabled(False)  
        self.propagate_confidence_btn.clicked.connect(self._on_propagate_confidence_clicked)  
        edit_layout.addWidget(self.propagate_confidence_btn)
          
        self.align_track_ids_btn = QPushButton("Align Track IDs (A)")  
        self.align_track_ids_btn.setEnabled(False)  
        self.align_track_ids_btn.clicked.connect(self._on_align_track_ids_clicked)  
        edit_layout.addWidget(self.align_track_ids_btn)  
          
        # コピー・ペーストボタン  
        copy_paste_layout = QHBoxLayout()  
        self.copy_annotation_btn = QPushButton("Copy (Ctrl+C)")  
        self.copy_annotation_btn.setEnabled(False)  
        self.copy_annotation_btn.clicked.connect(self._on_copy_annotation_clicked)  
        copy_paste_layout.addWidget(self.copy_annotation_btn)  
          
        self.paste_annotation_btn = QPushButton("Paste (Ctrl+V)")  
        self.paste_annotation_btn.setEnabled(False)  
        self.paste_annotation_btn.clicked.connect(self._on_paste_annotation_clicked)  
        copy_paste_layout.addWidget(self.paste_annotation_btn)  
          
        edit_layout.addLayout(copy_paste_layout)  
          
        # Undo/Redoボタン  
        undo_redo_layout = QHBoxLayout()  
        self.undo_btn = QPushButton("Undo (Ctrl+Z)")  
        self.undo_btn.setEnabled(False)  
        self.undo_btn.clicked.connect(self._on_undo_clicked)  
        undo_redo_layout.addWidget(self.undo_btn)  
          
        self.redo_btn = QPushButton("Redo (Ctrl+Y)")  
        self.redo_btn.setEnabled(False)  
        self.redo_btn.clicked.connect(self._on_redo_clicked)  
        undo_redo_layout.addWidget(self.redo_btn)  
          
        edit_layout.addLayout(undo_redo_layout)  
          
        edit_group.setLayout(edit_layout)  
        layout.addWidget(edit_group)  
          
        # トラッキング・コピーグループ  
        batch_group = QGroupBox("Batch Operations")  
        batch_layout = QVBoxLayout()  
          
        # トラッキングボタン用スタイル  
        tracking_button_style = """  
            QPushButton {  
                background-color: #f0f0f0;  
                border: 2px solid #ccc;  
                padding: 5px;  
            }  
            QPushButton:checked {  
                background-color: #87CEEB;  
                border: 2px solid #4682B4;  
                font-weight: bold;  
            }  
        """  
          
        self.tracking_annotation_btn = QPushButton("Tracking Mode (T)")  
        self.tracking_annotation_btn.setCheckable(True)  
        self.tracking_annotation_btn.setStyleSheet(tracking_button_style)  
        self.tracking_annotation_btn.clicked.connect(self._on_tracking_annotation_clicked)  
        self.tracking_annotation_btn.setEnabled(False)  
        batch_layout.addWidget(self.tracking_annotation_btn)  
          
        # コピーボタン用スタイル  
        copy_button_style = """  
            QPushButton {  
                background-color: #f0f0f0;  
                border: 2px solid #ccc;  
                padding: 5px;  
            }  
            QPushButton:checked {  
                background-color: #FFB6C1;  
                border: 2px solid #FF69B4;  
                font-weight: bold;  
            }  
        """  
          
        self.copy_annotations_btn = QPushButton("Copy Mode (C)")  
        self.copy_annotations_btn.setCheckable(True)  
        self.copy_annotations_btn.setStyleSheet(copy_button_style)  
        self.copy_annotations_btn.clicked.connect(self._on_copy_annotations_clicked)  
        self.copy_annotations_btn.setEnabled(False)  
        batch_layout.addWidget(self.copy_annotations_btn)  
          
        # 削除ボタン用スタイル  
        delete_button_style = """  
            QPushButton {  
                background-color: #f0f0f0;  
                border: 2px solid #ccc;  
                padding: 5px;  
            }  
            QPushButton:checked {  
                background-color: #FFB6B6;  
                border: 2px solid #FF6B6B;  
                font-weight: bold;  
            }  
        """  
          
        self.delete_annotations_btn = QPushButton("Delete Mode (D)")  
        self.delete_annotations_btn.setCheckable(True)  
        self.delete_annotations_btn.setStyleSheet(delete_button_style)  
        self.delete_annotations_btn.clicked.connect(self._on_delete_annotations_clicked)  
        self.delete_annotations_btn.setEnabled(False)  
        batch_layout.addWidget(self.delete_annotations_btn)

        # 範囲情報表示  
        self.range_info_label = QLabel("Range: Not selected")  
        batch_layout.addWidget(self.range_info_label)  
          
        # 実行ボタン  
        self.execute_add_btn = QPushButton("Run (R)")  
        self.execute_add_btn.setEnabled(False)  
        self.execute_add_btn.clicked.connect(self._on_complete_tracking_clicked)  
        batch_layout.addWidget(self.execute_add_btn)  
          
        # 進捗表示  
        self.tracking_status_label = QLabel("Ready")  
        batch_layout.addWidget(self.tracking_status_label)  
          
        batch_group.setLayout(batch_layout)  
        layout.addWidget(batch_group)  
          
        layout.addStretch()  
        self.setLayout(layout)  
      
    # モード制御関数（MASAAnnotationWidgetから移動）  
    def set_tracking_mode(self, enabled: bool):  
        """一括追加モードの設定とUIの更新"""  
        if enabled:  
            if self.main_widget.menu_panel.edit_mode_btn.isChecked():  
                self.main_widget.menu_panel.edit_mode_btn.setChecked(False)  
                self.main_widget.set_edit_mode(False)  
              
            self.main_widget.video_preview.set_mode('tracking')  
            self.main_widget.video_control.range_slider.setVisible(True)  
            self.main_widget.video_preview.clear_temp_tracking_annotations()  
            ErrorHandler.show_info_dialog(  
                "Tracking mode enabled.\n"  
                "1. Draw bounding boxes on the video preview.\n"  
                "2. Specify the frame range to add.\n"  
                "3. Press the Run button.",  
                "Mode Change"  
            )  
            self.main_widget.temp_bboxes_for_tracking.clear()  
            if self.main_widget.playback_controller and self.main_widget.playback_controller.is_playing:  
                self.main_widget.playback_controller.pause()  
        else:  
            self.main_widget.video_preview.set_mode('view')  
            ErrorHandler.show_info_dialog("Tracking Mode disabled.", "Mode Change")  
            if self.main_widget.playback_controller:  
                self.main_widget.playback_controller.pause()  
          
        self.main_widget.video_preview.bbox_editor.set_editing_mode(enabled)  
        self.main_widget.video_preview.update_frame_display()  
  
    def set_copy_mode(self, enabled: bool):  
        """コピーモードの設定とUIの更新"""  
        if enabled:  
            if self.main_widget.menu_panel.edit_mode_btn.isChecked():  
                self.main_widget.menu_panel.edit_mode_btn.setChecked(False)  
                self.main_widget.set_edit_mode(False)  
            if self.main_widget.menu_panel.tracking_annotation_btn.isChecked():  
                self.main_widget.menu_panel.tracking_annotation_btn.setChecked(False)  
                self.set_tracking_mode(False)  
              
            self.main_widget.video_preview.set_mode('edit')  
            self.main_widget.video_control.range_slider.setVisible(True)  
            self.main_widget.video_preview.bbox_editor.set_editing_mode(True)  
              
            ErrorHandler.show_info_dialog(  
                "Copy mode enabled.\n"  
                "1. Select an annotation to copy.\n"  
                "2. Specify the frame range.\n"  
                "3. Press the Run button.",  
                "Mode Change"  
            )  
        else:  
            self.main_widget.video_preview.set_mode('view')  
            self.main_widget.video_control.range_slider.setVisible(False)  
            self.main_widget.video_preview.bbox_editor.set_editing_mode(False)  
            ErrorHandler.show_info_dialog("Copy mode disabled.", "Mode Change")  
          
        self.main_widget.video_preview.update_frame_display()  

    def set_delete_mode(self, enabled: bool):  
        """削除モードの設定とUIの更新"""  
        if enabled:  
            if self.main_widget.menu_panel.edit_mode_btn.isChecked():  
                self.main_widget.menu_panel.edit_mode_btn.setChecked(False)  
                self.main_widget.set_edit_mode(False)  
            if self.main_widget.menu_panel.tracking_annotation_btn.isChecked():  
                self.main_widget.menu_panel.tracking_annotation_btn.setChecked(False)  
                self.set_tracking_mode(False)  
            if self.main_widget.menu_panel.copy_annotations_btn.isChecked():  
                self.main_widget.menu_panel.copy_annotations_btn.setChecked(False)  
                self.set_copy_mode(False)  
                  
            self.main_widget.video_preview.set_mode('edit')  
            self.main_widget.video_control.range_slider.setVisible(True)  
            self.main_widget.video_preview.bbox_editor.set_editing_mode(True)  
              
            ErrorHandler.show_info_dialog(  
                "Delete mode enabled.\n"  
                "1. Select an annotation to delete.\n"  
                "2. Specify the frame range.\n"  
                "3. Press the Run button.",  
                "Mode Change"  
            )  
        else:  
            self.main_widget.video_preview.set_mode('view')  
            self.main_widget.video_control.range_slider.setVisible(False)  
            self.main_widget.video_preview.bbox_editor.set_editing_mode(False)  
            ErrorHandler.show_info_dialog("Delete mode disabled.", "Mode Change")  
              
        self.main_widget.video_preview.update_frame_display()
    
    # イベントハンドラー  
    def _on_edit_mode_clicked(self, checked: bool):  
        """編集モードボタンクリック時の処理"""  
        if checked:  
            # Edit Modeがオンの時は他のモードボタンを無効化  
            self.tracking_annotation_btn.setEnabled(False)  
            self.copy_annotations_btn.setEnabled(False)  
            self.delete_annotations_btn.setEnabled(False)
            
            # 他のモードがオンの場合はオフにする  
            if self.tracking_annotation_btn.isChecked():  
                self.tracking_annotation_btn.setChecked(False)  
                self.set_tracking_mode(False)  
            if self.copy_annotations_btn.isChecked():  
                self.copy_annotations_btn.setChecked(False)  
                self.set_copy_mode(False)  
            if self.delete_annotations_btn.isChecked():  
                self.delete_annotations_btn.setChecked(False)  
                self.set_delete_mode(False)
        else:  
            # Edit Modeがオフの時は他のモードボタンを有効化  
            self.tracking_annotation_btn.setEnabled(True)  
            self.copy_annotations_btn.setEnabled(True)  
            self.delete_annotations_btn.setEnabled(True)
        
        self.edit_mode_requested.emit(checked)  

    def _on_tracking_annotation_clicked(self, checked: bool):  
        """トラッキングモードボタンクリック時の処理"""  
        if checked:  
            # Tracking Modeがオンの時は他のモードボタンを無効化  
            self.edit_mode_btn.setEnabled(False)  
            self.copy_annotations_btn.setEnabled(False)  
            self.delete_annotations_btn.setEnabled(False)
            
            # 他のモードがオンの場合はオフにする  
            if self.edit_mode_btn.isChecked():  
                self.edit_mode_btn.setChecked(False)  
                # edit_mode_requestedシグナルを発行してedit modeを無効化  
                self.edit_mode_requested.emit(False)  
            if self.copy_annotations_btn.isChecked():  
                self.copy_annotations_btn.setChecked(False)  
                self.set_copy_mode(False)  
            if self.delete_annotations_btn.isChecked():  
                self.delete_annotations_btn.setChecked(False)  
                self.set_copy_mode(False)  

            
            self.set_tracking_mode(True)  
        else:  
            # Tracking Modeがオフの時は他のモードボタンを有効化  
            self.edit_mode_btn.setEnabled(True)  
            self.copy_annotations_btn.setEnabled(True)  
            self.delete_annotations_btn.setEnabled(True)
            self.set_tracking_mode(False)  
        
        self.tracking_mode_requested.emit(checked)
  
    def _on_copy_annotations_clicked(self, checked: bool):  
        """コピーモードボタンクリック時の処理"""  
        if checked:  
            # Copy Modeがオンの時は他のモードボタンを無効化  
            self.edit_mode_btn.setEnabled(False)  
            self.tracking_annotation_btn.setEnabled(False)  
            self.delete_annotations_btn.setEnabled(False)
            
            # 他のモードがオンの場合はオフにする  
            if self.edit_mode_btn.isChecked():  
                self.edit_mode_btn.setChecked(False)  
                # edit_mode_requestedシグナルを発行してedit modeを無効化  
                self.edit_mode_requested.emit(False)  
            if self.tracking_annotation_btn.isChecked():  
                self.tracking_annotation_btn.setChecked(False)  
                self.set_tracking_mode(False)  
            if self.delete_annotations_btn.isChecked():  
                self.delete_annotations_btn.setChecked(False)  
                self.set_copy_mode(False)  

            
            self.set_copy_mode(True)  
        else:  
            # Copy Modeがオフの時は他のモードボタンを有効化  
            self.edit_mode_btn.setEnabled(True)  
            self.tracking_annotation_btn.setEnabled(True)  
            self.delete_annotations_btn.setEnabled(True)
            self.set_copy_mode(False)  
        
        self.copy_mode_requested.emit(checked)
  
    def _on_delete_annotations_clicked(self, checked: bool):  
        """削除モードボタンクリック時の処理"""  
        if checked:  
            # Delete Modeがオンの時は他のモードボタンを無効化  
            self.edit_mode_btn.setEnabled(False)  
            self.tracking_annotation_btn.setEnabled(False)  
            self.copy_annotations_btn.setEnabled(False)  
              
            # 他のモードがオンの場合はオフにする  
            if self.edit_mode_btn.isChecked():  
                self.edit_mode_btn.setChecked(False)  
                self.edit_mode_requested.emit(False)  
            if self.tracking_annotation_btn.isChecked():  
                self.tracking_annotation_btn.setChecked(False)  
                self.set_tracking_mode(False)  
            if self.copy_annotations_btn.isChecked():  
                self.copy_annotations_btn.setChecked(False)  
                self.set_copy_mode(False)  
              
            self.set_delete_mode(True)  
        else:  
            # Delete Modeがオフの時は他のモードボタンを有効化  
            self.edit_mode_btn.setEnabled(True)  
            self.tracking_annotation_btn.setEnabled(True)  
            self.copy_annotations_btn.setEnabled(True)  
            self.set_delete_mode(False)  
          
        self.delete_mode_requested.emit(checked)

    def _on_label_changed(self, index: int):  
        """ラベル変更時の処理"""  
        if self.current_selected_annotation and index >= 0:  
            new_label = self.label_combo.currentText().strip()  
            if new_label and new_label != self.current_selected_annotation.label:  
                self.label_change_requested.emit(self.current_selected_annotation, new_label)
  
    def _on_delete_single_annotation_clicked(self):  
        """単一アノテーション削除ボタンクリック時の処理"""  
        if not self.current_selected_annotation:  
            return  
            
        reply = QMessageBox.question(  
            self, "Confirm Delete Annotation",  
            f"Do you want to delete the annotation for SELECTED frame {self.current_selected_annotation.frame_id} (ID: {self.current_selected_annotation.object_id}, label: '{self.current_selected_annotation.label}')?",  
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
        )  
        
        if reply == QMessageBox.StandardButton.Yes:  
            self.delete_single_annotation_requested.emit(self.current_selected_annotation)
  
    def _on_delete_track_clicked(self):  
        """トラック削除ボタンクリック時の処理"""  
        if not self.current_selected_annotation:  
            return  
            
        track_id_to_delete = self.current_selected_annotation.object_id  
        reply = QMessageBox.question(  
            self, "Confirm ALL Track Deletion",  
            f"Do you want to delete ALL annotations with Track ID '{track_id_to_delete}'?\n"  
            "This action cannot be undone.",  
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
        )  
        
        if reply == QMessageBox.StandardButton.Yes:  
            self.delete_track_requested.emit(track_id_to_delete)
  
    def _on_propagate_label_clicked(self):  
        """ラベル伝播ボタンクリック時の処理"""  
        if not self.current_selected_annotation:  
            return  
            
        track_id_to_change = self.current_selected_annotation.object_id  
        current_label = self.current_selected_annotation.label  
        
        # 既存のラベル一覧を取得  
        existing_labels = self.annotation_repository.get_all_labels()  
        
        # ダイアログでラベル入力  
        dialog = AnnotationInputDialog(  
            BoundingBox(0, 0, 1, 1),  
            existing_labels=existing_labels,  
            default_label=current_label  
        )  
        dialog.setWindowTitle(f"Change Label for ALL with Track ID {track_id_to_change}")  
        
        if dialog.exec() == QDialog.DialogCode.Accepted:  
            new_label = dialog.get_label()  
            if not new_label:  
                ErrorHandler.show_warning_dialog("No label selected.", "Warning")  
                return  
                
            # 確認ダイアログ  
            reply = QMessageBox.question(  
                self, "Confirm ALL Track Label Change",  
                f"Do you want to change the label of ALL annotations with Track ID '{track_id_to_change}' to '{new_label}'?",  
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
            )  
            
            if reply == QMessageBox.StandardButton.Yes:  
                self.propagate_label_requested.emit(track_id_to_change, new_label)  
        else:  
            ErrorHandler.show_info_dialog("Label selection was cancelled.", "Info")
  
    def _on_propagate_confidence_clicked(self):  
        """confidence伝播ボタンクリック時の処理"""  
        if not self.current_selected_annotation:  
            return  
              
        track_id_to_change = self.current_selected_annotation.object_id  
        current_confidence = self.current_selected_annotation.bbox.confidence  
          
        # confidence入力ダイアログ  
        confidence, ok = QInputDialog.getDouble(  
            self,   
            f"Change Confidence for ALL with Track ID {track_id_to_change}",  
            "Enter new confidence (0.0-1.0):",  
            current_confidence,  
            0.0,  
            1.0,  
            2  
        )  
          
        if ok:  
            # 確認ダイアログ  
            reply = QMessageBox.question(  
                self, "Confirm ALL Track Confidence Change",  
                f"Do you want to change the confidence of ALL annotations with Track ID '{track_id_to_change}' to '{confidence:.2f}'?",  
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
            )  
              
            if reply == QMessageBox.StandardButton.Yes:  
                self.propagate_confidence_requested.emit(track_id_to_change, confidence)

    def _on_align_track_ids_clicked(self):  
        """Track ID統一ボタンクリック時の処理"""  
        if not self.current_selected_annotation:  
            return  
            
        target_label = self.current_selected_annotation.label  
        target_track_id = self.current_selected_annotation.object_id  
        
        reply = QMessageBox.question(  
            self, "Confirm Track ID Alignment",  
            f"Do you want to align ALL annotations with label '{target_label}' to Track ID '{target_track_id}'?\n"  
            "This will change the Track ID of all annotations with the same label.",  
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
        )  
        
        if reply == QMessageBox.StandardButton.Yes:  
            self.align_track_ids_requested.emit(target_label, target_track_id)
  
    def _on_copy_annotation_clicked(self):  
        """アノテーションコピーボタンクリック時の処理"""  
        self.copy_annotation_requested.emit()  
  
    def _on_paste_annotation_clicked(self):  
        """アノテーションペーストボタンクリック時の処理"""  
        self.paste_annotation_requested.emit()  
  
    def _on_undo_clicked(self):  
        """Undoボタンクリック時の処理"""  
        if self.command_manager.undo():  
            self.main_widget.update_annotation_count()  
            self.main_widget.video_preview.update_frame_display()  
            self.main_widget.video_preview.bbox_editor.selected_annotation = None  
            self.main_widget.video_preview.bbox_editor.selection_changed.emit(None)  
            print("--- Undo ---")  
        else:  
            ErrorHandler.show_info_dialog("There are no actions to undo.", "Undo")  
  
    def _on_redo_clicked(self):  
        """Redoボタンクリック時の処理"""  
        if self.command_manager.redo():  
            self.main_widget.update_annotation_count()  
            self.main_widget.video_preview.update_frame_display()  
            self.main_widget.video_preview.bbox_editor.selected_annotation = None  
            self.main_widget.video_preview.bbox_editor.selection_changed.emit(None)  
            print("--- Redo ---")  
        else:  
            ErrorHandler.show_info_dialog("There are no actions to redo.", "Redo")  
  
    def _on_complete_tracking_clicked(self):  
        """実行ボタンクリック時の処理"""  
        # コピーモードの場合  
        if self.copy_annotations_btn.isChecked():  
            return self._handle_copy_mode_execution()  

        # 削除モードの場合  
        if self.delete_annotations_btn.isChecked():  
            return self._handle_delete_mode_execution()  
  
        # トラッキングモードの場合  
        if not self.main_widget.temp_bboxes_for_tracking:  
            ErrorHandler.show_warning_dialog("There are no annotations to add.", "Warning")  
            return  
  
        # 共通ラベル入力ダイアログを表示  
        existing_labels = self.annotation_repository.get_all_labels()  
        dialog = AnnotationInputDialog(None, existing_labels=existing_labels)  
        dialog.setWindowTitle("Select Common Label for Tracking Added Annotations")  
  
        if dialog.exec() == QDialog.DialogCode.Accepted:  
            assigned_label = dialog.get_label()  
            if not assigned_label:  
                ErrorHandler.show_warning_dialog("No label selected.", "Warning")  
                return  
  
            start_frame, end_frame = self.main_widget.video_control.get_selected_range()  
            if start_frame == -1 or end_frame == -1:  
                ErrorHandler.show_warning_dialog("No tracking range selected.", "Warning")  
                return  
  
            current_max_track_id = self.annotation_repository.next_object_id  
            self.tracking_requested.emit(current_max_track_id, assigned_label)  
        else:  
            ErrorHandler.show_info_dialog("Label selection was cancelled.", "Info")  
  
    def _handle_copy_mode_execution(self):  
        """コピーモード実行時の処理"""  
        if not self.current_selected_annotation:  
            ErrorHandler.show_warning_dialog("Please select an annotation to copy.", "Warning")  
            return  
    
        start_frame, end_frame = self.main_widget.video_control.get_selected_range()  
        if start_frame == -1 or end_frame == -1:  
            ErrorHandler.show_warning_dialog("No frame range selected.", "Warning")  
            return  
    
        existing_labels = self.annotation_repository.get_all_labels()  
        
        # コピー元のラベルをデフォルトとして設定  
        default_label = self.current_selected_annotation.label  
        
        dialog = AnnotationInputDialog(  
            None,   
            existing_labels=existing_labels,  
            default_label=default_label  
        )  
        dialog.setWindowTitle("Select Label for Copied Annotations")    
 
        if dialog.exec() == QDialog.DialogCode.Accepted:  
            assigned_label = dialog.get_label()  
            if not assigned_label:  
                ErrorHandler.show_warning_dialog("No label selected.", "Warning")  
                return  
  
            assigned_track_id = self.current_selected_annotation.object_id  
            self.copy_annotations_requested.emit(assigned_track_id, assigned_label)  
        else:  
            ErrorHandler.show_info_dialog("Label selection was cancelled.", "Info")  

    def _handle_delete_mode_execution(self):  
        """削除モード実行時の処理"""  
        if not self.current_selected_annotation:  
            ErrorHandler.show_warning_dialog("Please select an annotation to delete.", "Warning")  
            return  
      
        start_frame, end_frame = self.main_widget.video_control.get_selected_range()  
        if start_frame == -1 or end_frame == -1:  
            ErrorHandler.show_warning_dialog("No frame range selected.", "Warning")  
            return  
      
        track_id = self.current_selected_annotation.object_id  
        frame_count = end_frame - start_frame + 1  
          
        reply = QMessageBox.question(  
            self, "Confirm Range Delete",  
            f"Delete all annotations with Track ID '{track_id}' from frame {start_frame} to {end_frame}?\n"  
            f"Total frames to process: {frame_count}\n"  
            "This action cannot be undone.",  
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
        )  
          
        if reply == QMessageBox.StandardButton.Yes:  
            self.delete_annotations_requested.emit(track_id, start_frame, end_frame)  
        else:  
            ErrorHandler.show_info_dialog("Delete operation was cancelled.", "Info")
  
    # UI更新メソッド  
    def update_selected_annotation_info(self, annotation: Optional[ObjectAnnotation]):  
        """選択されたアノテーション情報を更新"""  
        self.current_selected_annotation = annotation  
        self.label_combo.blockSignals(True)  # シグナルを一時的にブロック  
        
        try:  
            if annotation:  
                self.current_selected_annotation_label = annotation.label  
                
                # 既存のラベルをコンボボックスに追加（重複チェック）  
                current_labels = [self.label_combo.itemText(i) for i in range(self.label_combo.count())]  
                if annotation.label not in current_labels:  
                    self.label_combo.addItem(annotation.label)  
                
                # 現在のラベルを選択  
                index = self.label_combo.findText(annotation.label)  
                if index >= 0:  
                    self.label_combo.setCurrentIndex(index)  
                else:  
                    self.label_combo.addItem(annotation.label)  
                    self.label_combo.setCurrentText(annotation.label)  
                
                self.track_id_edit.setText(str(annotation.object_id))  
                
                # ボタンの有効化  
                self.delete_single_annotation_btn.setEnabled(True)  
                self.delete_track_btn.setEnabled(True)  
                self.propagate_label_btn.setEnabled(True)  
                self.propagate_confidence_btn.setEnabled(True) 
                self.align_track_ids_btn.setEnabled(True)  
                self.copy_annotation_btn.setEnabled(True)  
            else:  
                self.current_selected_annotation_label = None  
                self.label_combo.setCurrentText("")  
                self.track_id_edit.setText("")  
                
                # ボタンの無効化  
                self.delete_single_annotation_btn.setEnabled(False)  
                self.delete_track_btn.setEnabled(False)  
                self.propagate_label_btn.setEnabled(False)  
                self.propagate_confidence_btn.setEnabled(False)
                self.align_track_ids_btn.setEnabled(False)  
                self.copy_annotation_btn.setEnabled(False)  
        finally:  
            self.label_combo.blockSignals(False)  # シグナルブロックを解除
  
    def initialize_label_combo(self, labels: List[str]):  
        """ラベルコンボボックスを初期化"""  
        # 現在選択されているラベルを一時的に保持  
        current_selected_label = self.label_combo.currentText()  
        
        self.label_combo.blockSignals(True)  # シグナルを一時的にブロック  
        self.label_combo.clear()  # 既存のアイテムをクリア  
        
        # 新しいラベルを追加  
        for label in sorted(list(set(labels))):  # 重複を排除しソート  
            self.label_combo.addItem(label)  
        
        # 以前選択されていたラベルを再設定  
        if current_selected_label and self.label_combo.findText(current_selected_label) >= 0:  
            self.label_combo.setCurrentText(current_selected_label)  
        elif self.current_selected_annotation:  # 現在選択中のアノテーションのラベルを優先  
            index = self.label_combo.findText(self.current_selected_annotation.label)  
            if index >= 0:  
                self.label_combo.setCurrentIndex(index)  
            else:  
                # もし現在のラベルがリストにない場合は追加して選択  
                self.label_combo.addItem(self.current_selected_annotation.label)  
                self.label_combo.setCurrentText(self.current_selected_annotation.label)  
        elif self.label_combo.count() > 0:  
            self.label_combo.setCurrentIndex(0)  # リストが空でなければ最初の要素を選択  
            
        self.label_combo.blockSignals(False)  # シグナルブロックを解除
  
    def update_range_info(self, start_frame: int, end_frame: int):  
        """範囲情報を更新"""  
        if start_frame != -1 and end_frame != -1:  
            self.range_info_label.setText(f"Range: {start_frame} - {end_frame}")  
            self.execute_add_btn.setEnabled(True)  
        else:  
            self.range_info_label.setText("Range: Not selected")  
            self.execute_add_btn.setEnabled(False)  
  
    def update_tracking_progress(self, progress_text: str):  
        """トラッキング進捗を更新"""  
        self.tracking_status_label.setText(progress_text)  
  
    def set_tracking_enabled(self, enabled: bool):  
        """トラッキング機能の有効/無効を設定"""  
        self.tracking_annotation_btn.setEnabled(enabled)  
  
    def update_undo_redo_buttons(self, command_manager):  
        """Undo/Redoボタンの状態を更新"""  
        self.undo_btn.setEnabled(command_manager.can_undo())  
        self.redo_btn.setEnabled(command_manager.can_redo())