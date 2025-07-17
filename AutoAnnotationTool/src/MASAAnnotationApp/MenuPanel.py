# MenuPanel.py  
from typing import List, Optional  
from PyQt6.QtWidgets import (  
    QWidget, QVBoxLayout, QLabel, QTabWidget
)  
from PyQt6.QtCore import Qt, pyqtSignal  
from PyQt6.QtGui import QFont, QKeyEvent  
  
from BasicTabWidget import BasicTabWidget  
from AnnotationTabWidget import AnnotationTabWidget  
from ObjectListTabWidget import ObjectListTabWidget  
from LicenseTabWidget import LicenseTabWidget  
from ConfigManager import ConfigManager  
from DataClass import ObjectAnnotation
  
class MenuPanel(QWidget):  
    """タブベースの左側メニューパネル（分割版）"""  
      
    # シグナル定義（各タブから転送）  
    load_video_requested = pyqtSignal(str)  
    load_json_requested = pyqtSignal(str)  
    export_requested = pyqtSignal(str)  
      
    edit_mode_requested = pyqtSignal(bool)  
    tracking_mode_requested = pyqtSignal(bool)  
    copy_mode_requested = pyqtSignal(bool)  
      
    tracking_requested = pyqtSignal(int, str)  
    copy_annotations_requested = pyqtSignal(int, str)  
      
    label_change_requested = pyqtSignal(object, str)  
    delete_single_annotation_requested = pyqtSignal(object)  
    delete_track_requested = pyqtSignal(int)  
    propagate_label_requested = pyqtSignal(int, str)  
    align_track_ids_requested = pyqtSignal(str, int)  
    copy_annotation_requested = pyqtSignal()  
    paste_annotation_requested = pyqtSignal()  
            
    config_changed = pyqtSignal(str, object, str)  
      
    def __init__(self, config_manager: ConfigManager, annotation_repository, command_manager, main_widget, parent=None):  
        super().__init__(parent)  
        self.config_manager = config_manager  
        self.annotation_repository = annotation_repository  
        self.command_manager = command_manager  
        self.main_widget = main_widget  # MASAAnnotationWidgetへの参照  
        self.clipboard_annotation = None  # クリップボード機能をMenuPanelに移動  
          
        # 固定幅を削除し、最小幅のみ設定  
        self.setMinimumWidth(250)  
        self.setStyleSheet("background-color: #f0f0f0; border-right: 1px solid #ccc;")  
          
        self.setup_ui()  
        self._connect_signals()  
        self._connect_config_signals()  
      
    def setup_ui(self):  
        layout = QVBoxLayout()  
        layout.setSpacing(10)  
        layout.setContentsMargins(10, 10, 10, 10)  
          
        title_label = QLabel("MASA Annotation Tool")  
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))  
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        layout.addWidget(title_label)  
          
        # タブウィジェットを作成  
        self.tab_widget = QTabWidget()  
          
        # 各タブウィジェットを作成  
        self.basic_tab = BasicTabWidget(self.config_manager, self.annotation_repository, self.command_manager, self.main_widget, self)  
        self.annotation_tab = AnnotationTabWidget(self.config_manager, self.annotation_repository, self.command_manager, self.main_widget, self)  
        self.object_list_tab = ObjectListTabWidget(self.config_manager, self.annotation_repository, self.command_manager, self.main_widget, self)  
        self.license_tab = LicenseTabWidget(self.config_manager, self.annotation_repository, self.command_manager, self.main_widget, self)  
          
        # タブに追加  
        self.tab_widget.addTab(self.basic_tab, "⚙️ Basic Settings")  
        self.tab_widget.addTab(self.annotation_tab, "📝 Annotation")  
        self.tab_widget.addTab(self.object_list_tab, "📋 Object List")  
        self.tab_widget.addTab(self.license_tab, "📄 License")  
          
        # タブのスタイルを設定  
        tab_style = """  
            QTabWidget::pane {  
                border: 2px solid #ccc;  
                background-color: white;  
            }  
            QTabBar::tab {  
                background-color: #e0e0e0;  
                border: 1px solid #ccc;  
                padding: 8px 16px;  
                margin-right: 2px;  
                font-weight: bold;  
            }  
            QTabBar::tab:selected {  
                background-color: #4CAF50;  
                color: white;  
                border-bottom: 2px solid #4CAF50;  
            }  
            QTabBar::tab:hover {  
                background-color: #f0f0f0;  
            }  
        """  
        self.tab_widget.setStyleSheet(tab_style)  
          
        layout.addWidget(self.tab_widget)  
        self.setLayout(layout)  
      
    def _connect_signals(self):  
        """各タブからのシグナルを上位に転送"""  
        # BasicTabからのシグナル転送  
        self.basic_tab.load_video_requested.connect(self.load_video_requested)  
        self.basic_tab.load_json_requested.connect(self.load_json_requested)  
        self.basic_tab.export_requested.connect(self.export_requested)  
          
        # AnnotationTabからのシグナル転送  
        self.annotation_tab.edit_mode_requested.connect(self.edit_mode_requested)  
        self.annotation_tab.tracking_mode_requested.connect(self.tracking_mode_requested)  
        self.annotation_tab.copy_mode_requested.connect(self.copy_mode_requested)  
        self.annotation_tab.tracking_requested.connect(self.tracking_requested)  
        self.annotation_tab.copy_annotations_requested.connect(self.copy_annotations_requested)  
        self.annotation_tab.label_change_requested.connect(self.label_change_requested)  
        self.annotation_tab.delete_single_annotation_requested.connect(self.delete_single_annotation_requested)  
        self.annotation_tab.delete_track_requested.connect(self.delete_track_requested)  
        self.annotation_tab.propagate_label_requested.connect(self.propagate_label_requested)  
        self.annotation_tab.align_track_ids_requested.connect(self.align_track_ids_requested)  
        self.annotation_tab.copy_annotation_requested.connect(self.copy_annotation_requested)  
        self.annotation_tab.paste_annotation_requested.connect(self.paste_annotation_requested)  
      
        # ObjectListTabからのシグナル転送を追加  
        self.object_list_tab.config_changed.connect(self.config_changed)

    def _connect_config_signals(self):  
        """ConfigManagerからの設定変更シグナルを接続"""  
        self.config_manager.add_observer(self._on_config_changed)  
      
    def _on_config_changed(self, key: str, value: object, config_type: str):      
        """ConfigManagerからの設定変更を処理"""      
        if config_type == "display":    
            # ObjectListTabWidgetの表示設定を更新    
            display_options = self.config_manager.get_full_config(config_type="display")    
            self.update_object_list_display_settings(    
                display_options.show_manual_annotations,    
                display_options.show_auto_annotations,     
                display_options.score_threshold    
            )

    def keyPressEvent(self, event: QKeyEvent):  
        """MenuPanel関連のキーボードショートカット"""  
        # Ctrlキー組み合わせの処理  
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:  
            if event.key() == Qt.Key.Key_O:  
                self.basic_tab._on_load_video_clicked("")  
                event.accept()  
                return  
            elif event.key() == Qt.Key.Key_L:  
                self.basic_tab._on_load_json_clicked("")  
                event.accept()  
                return  
            elif event.key() == Qt.Key.Key_S:  
                if self.basic_tab.save_masa_json_btn.isEnabled():  
                    self.basic_tab._on_export_masa_clicked()  
                event.accept()  
                return  
            elif event.key() == Qt.Key.Key_Z:  
                self.annotation_tab._on_undo_clicked()  
                event.accept()  
                return  
            elif event.key() == Qt.Key.Key_Y:  
                self.annotation_tab._on_redo_clicked()  
                event.accept()  
                return  
            elif event.key() == Qt.Key.Key_C:  
                if (self.annotation_tab.current_selected_annotation and   
                    self.annotation_tab.edit_mode_btn.isChecked() and  
                    self.annotation_tab.copy_annotation_btn.isEnabled()):  
                    self.annotation_tab._on_copy_annotation_clicked()  
                event.accept()  
                return  
            elif event.key() == Qt.Key.Key_V:  
                if (self.annotation_tab.edit_mode_btn.isChecked() and  
                    self.annotation_tab.paste_annotation_btn.isEnabled()):  
                    self.annotation_tab._on_paste_annotation_clicked()  
                event.accept()  
                return  
          
        # Ctrl+Shift組み合わせの処理  
        if event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):  
            if event.key() == Qt.Key.Key_S:  
                if self.basic_tab.save_coco_json_btn.isEnabled():  
                    self.basic_tab._on_export_coco_clicked()  
                event.accept()  
                return  
          
        # 単独キーのショートカット処理  
        if event.key() == Qt.Key.Key_E:  
            if self.annotation_tab.edit_mode_btn.isEnabled():  
                current_state = self.annotation_tab.edit_mode_btn.isChecked()  
                self.annotation_tab.edit_mode_btn.setChecked(not current_state)  
                self.annotation_tab._on_edit_mode_clicked(not current_state)  
            event.accept()  
        elif event.key() == Qt.Key.Key_T:  
            if self.annotation_tab.tracking_annotation_btn.isEnabled():  
                current_state = self.annotation_tab.tracking_annotation_btn.isChecked()  
                self.annotation_tab.tracking_annotation_btn.setChecked(not current_state)  
                self.annotation_tab._on_tracking_annotation_clicked(not current_state)  
            event.accept()  
        elif event.key() == Qt.Key.Key_C:  
            if self.annotation_tab.copy_annotations_btn.isEnabled():  
                current_state = self.annotation_tab.copy_annotations_btn.isChecked()  
                self.annotation_tab.copy_annotations_btn.setChecked(not current_state)  
                self.annotation_tab._on_copy_annotations_clicked(not current_state)  
            event.accept()  
        elif event.key() == Qt.Key.Key_X:  
            if (self.annotation_tab.current_selected_annotation and   
                self.annotation_tab.delete_single_annotation_btn.isEnabled()):  
                self.annotation_tab._on_delete_single_annotation_clicked()  
            event.accept()  
        elif event.key() == Qt.Key.Key_D:  
            if (self.annotation_tab.current_selected_annotation and   
                self.annotation_tab.delete_track_btn.isEnabled()):  
                self.annotation_tab._on_delete_track_clicked()  
            event.accept()  
        elif event.key() == Qt.Key.Key_P:  
            if (self.annotation_tab.current_selected_annotation and   
                self.annotation_tab.propagate_label_btn.isEnabled()):  
                self.annotation_tab._on_propagate_label_clicked()  
            event.accept()  
        elif event.key() == Qt.Key.Key_A:  
            if (self.annotation_tab.current_selected_annotation and   
                self.annotation_tab.align_track_ids_btn.isEnabled()):  
                self.annotation_tab._on_align_track_ids_clicked()  
            event.accept()  
        elif event.key() == Qt.Key.Key_R:  
            if self.annotation_tab.execute_add_btn.isEnabled():  
                self.annotation_tab._on_complete_tracking_clicked()  
            event.accept()  
        else:  
            super().keyPressEvent(event)  
      
    # 各タブへのアクセス用プロパティ  
    @property  
    def current_selected_annotation(self):  
        return self.annotation_tab.current_selected_annotation  
      
    @current_selected_annotation.setter  
    def current_selected_annotation(self, value):  
        self.annotation_tab.current_selected_annotation = value  
            
    # 各タブのUIコンポーネントへのアクセス用プロパティ  
    @property  
    def edit_mode_btn(self):  
        return self.annotation_tab.edit_mode_btn  
      
    @property  
    def tracking_annotation_btn(self):  
        return self.annotation_tab.tracking_annotation_btn  
      
    @property  
    def copy_annotations_btn(self):  
        return self.annotation_tab.copy_annotations_btn  
      
    @property  
    def execute_add_btn(self):  
        return self.annotation_tab.execute_add_btn  
      
    @property  
    def save_masa_json_btn(self):  
        return self.basic_tab.save_masa_json_btn  
      
    @property  
    def save_coco_json_btn(self):  
        return self.basic_tab.save_coco_json_btn  
      
    @property  
    def copy_annotation_btn(self):  
        return self.annotation_tab.copy_annotation_btn  
      
    @property  
    def paste_annotation_btn(self):  
        return self.annotation_tab.paste_annotation_btn  
      
    # 各タブのメソッドへの転送  
    def update_video_info(self, video_path: str, total_frames: int):  
        self.basic_tab.update_video_info(video_path, total_frames)  
        self.annotation_tab.edit_mode_btn.setEnabled(True)  
        self.annotation_tab.tracking_annotation_btn.setEnabled(True)  
        self.annotation_tab.copy_annotations_btn.setEnabled(True)
            
    def update_export_progress(self, message: str):  
        self.basic_tab.update_export_progress(message)  
      
    def update_annotation_count(self, count: int, manual_count: int = None):  
        if manual_count is not None:  
            loaded_count = count - manual_count  
            self.annotation_tab.annotation_count_label.setText(  
                f"All Annotation count: {count}\n"  
                f"(auto: {loaded_count}, manual: {manual_count})"  
            )  
        else:  
            self.annotation_tab.annotation_count_label.setText(f"Annotation count: {count}")  
      
    def update_range_info(self, start_frame: int, end_frame: int):  
        self.annotation_tab.update_range_info(start_frame, end_frame)  
      
    def update_tracking_progress(self, progress_text: str):  
        self.annotation_tab.update_tracking_progress(progress_text)  
      
    def update_selected_annotation_info(self, annotation: Optional[ObjectAnnotation]):  
        self.annotation_tab.update_selected_annotation_info(annotation)  
      
    def initialize_label_combo(self, labels: List[str]):  
        self.annotation_tab.initialize_label_combo(labels)  
      
    def set_tracking_enabled(self, enabled: bool):  
        self.annotation_tab.set_tracking_enabled(enabled)  
      
    def update_undo_redo_buttons(self, command_manager):  
        self.annotation_tab.update_undo_redo_buttons(command_manager)  
      
    def update_current_frame_objects(self, frame_id: int, frame_annotation=None):  
        self.object_list_tab.update_current_frame_objects(frame_id, frame_annotation)  
            
    def update_object_list_selection(self, annotation):  
        self.object_list_tab.update_object_list_selection(annotation)  