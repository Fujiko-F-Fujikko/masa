from typing import Dict, Callable  

from PyQt6.QtCore import Qt  
from PyQt6.QtGui import QKeyEvent  
from PyQt6.QtWidgets import QLineEdit, QComboBox, QPushButton  

from ErrorHandler import ErrorHandler  

  
class KeyboardShortcutHandler:  
    """キーボードショートカット処理専用クラス"""  
      
    def __init__(self, main_widget):  
        """  
        Args:  
            main_widget: MASAAnnotationWidgetのインスタンス  
        """  
        self.main_widget = main_widget  
        self.menu_panel = main_widget.menu_panel  
        self.video_control = main_widget.video_control  
        self.video_preview = main_widget.video_preview  
        self.command_manager = main_widget.command_manager  
          
        # ショートカットハンドラーのマッピングを定義  
        self._ctrl_handlers: Dict[int, Callable] = {  
            Qt.Key.Key_O: self._handle_load_video,  
            Qt.Key.Key_L: self._handle_load_json,  
            Qt.Key.Key_S: self._handle_save_masa,  
            Qt.Key.Key_Z: self._handle_undo,  
            Qt.Key.Key_Y: self._handle_redo,  
            Qt.Key.Key_C: self._handle_copy_annotation,  
            Qt.Key.Key_V: self._handle_paste_annotation,  
        }  
          
        self._ctrl_shift_handlers: Dict[int, Callable] = {  
            Qt.Key.Key_S: self._handle_save_coco,  
        }  
          
        self._single_key_handlers: Dict[int, Callable] = {  
            Qt.Key.Key_Space: self._handle_playback_toggle,  
            Qt.Key.Key_Left: self._handle_prev_frame,  
            Qt.Key.Key_Right: self._handle_next_frame,  
            Qt.Key.Key_E: self._handle_edit_mode_toggle,  
            Qt.Key.Key_T: self._handle_tracking_mode_toggle,  
            Qt.Key.Key_C: self._handle_copy_mode_toggle,  
            Qt.Key.Key_X: self._handle_delete_single_annotation,  
            Qt.Key.Key_D: self._handle_delete_track,  
            Qt.Key.Key_P: self._handle_propagate_label,  
            Qt.Key.Key_R: self._handle_execute_tracking,  
            Qt.Key.Key_G: self._handle_jump_to_frame,  
            Qt.Key.Key_F: self._handle_focus_frame_input,  
            Qt.Key.Key_A: self._handle_align_track_ids,  
            Qt.Key.Key_F: self._handle_propagate_confidence
        }  
      
    def handle_key_press(self, event: QKeyEvent) -> bool:  
        """  
        キーイベントを処理し、処理したかどうかを返す  
          
        Args:  
            event: QKeyEvent  
              
        Returns:  
            bool: イベントが処理された場合True  
        """  
        # フォーカス制御チェック  
        if self._should_ignore_shortcut(event):  
            return False  
              
        # Ctrl系ショートカット  
        if self._handle_ctrl_shortcuts(event):  
            return True  
              
        # Ctrl+Shift系ショートカット    
        if self._handle_ctrl_shift_shortcuts(event):  
            return True  
              
        # 単独キーショートカット  
        if self._handle_single_key_shortcuts(event):  
            return True  
              
        return False  
      
    def _should_ignore_shortcut(self, event: QKeyEvent) -> bool:  
        """ショートカットを無視すべきかチェック"""  
        focused_widget = self.main_widget.focusWidget()  
          
        # テキスト入力中はCtrl系以外を無効化  
        if isinstance(focused_widget, (QLineEdit, QComboBox)):  
            if event.modifiers() != Qt.KeyboardModifier.ControlModifier:  
                return True  
                  
        # ボタンフォーカス時の特別処理  
        if isinstance(focused_widget, QPushButton):  
            if event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:  
                focused_widget.click()  
                event.accept()  
                return True  
            elif event.key() == Qt.Key.Key_Space:  
                # Spaceキーのデフォルト動作を無効化  
                event.accept()  
                return True  
                  
        return False  
      
    def _handle_ctrl_shortcuts(self, event: QKeyEvent) -> bool:  
        """Ctrl系ショートカットの処理"""  
        if event.modifiers() != Qt.KeyboardModifier.ControlModifier:  
            return False  
              
        handler = self._ctrl_handlers.get(event.key())  
        if handler:  
            handler()  
            event.accept()  
            return True  
              
        return False  
      
    def _handle_ctrl_shift_shortcuts(self, event: QKeyEvent) -> bool:  
        """Ctrl+Shift系ショートカットの処理"""  
        if event.modifiers() != (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):  
            return False  
              
        handler = self._ctrl_shift_handlers.get(event.key())  
        if handler:  
            handler()  
            event.accept()  
            return True  
              
        return False  
      
    def _handle_single_key_shortcuts(self, event: QKeyEvent) -> bool:  
        """単独キーショートカットの処理"""  
        if event.modifiers() != Qt.KeyboardModifier.NoModifier:  
            return False  
              
        handler = self._single_key_handlers.get(event.key())  
        if handler:  
            handler()  
            event.accept()  
            return True  
              
        return False  
      
    # === Ctrl系ショートカットハンドラー ===  
      
    def _handle_load_video(self):  
        """Ctrl+O: 動画を読み込み"""  
        if hasattr(self.menu_panel, 'basic_tab'):  
            self.menu_panel.basic_tab._on_load_video_clicked("")  
      
    def _handle_load_json(self):  
        """Ctrl+L: JSONを読み込み"""  
        if hasattr(self.menu_panel, 'basic_tab'):  
            self.menu_panel.basic_tab._on_load_json_clicked("")  
      
    def _handle_save_masa(self):  
        """Ctrl+S: MASA JSONを保存"""  
        if (hasattr(self.menu_panel, 'basic_tab') and   
            self.menu_panel.basic_tab.save_masa_json_btn.isEnabled()):  
            self.menu_panel.basic_tab._on_export_masa_clicked()  
      
    def _handle_undo(self):  
        """Ctrl+Z: Undo"""  
        if self.command_manager.undo():  
            if hasattr(self.main_widget, 'update_annotation_count'):  
                self.main_widget.update_annotation_count()  
            self.video_preview.update_frame_display()  
            # 選択状態をクリア  
            if hasattr(self.video_preview, 'bbox_editor'):  
                self.video_preview.bbox_editor.selected_annotation = None  
                self.video_preview.bbox_editor.selection_changed.emit(None)  
            print("--- Undo ---")  
        else:  
            ErrorHandler.show_info_dialog("There are no actions to undo.", "Undo")  
      
    def _handle_redo(self):  
        """Ctrl+Y: Redo"""  
        if self.command_manager.redo():  
            if hasattr(self.main_widget, 'update_annotation_count'):  
                self.main_widget.update_annotation_count()  
            self.video_preview.update_frame_display()  
            # 選択状態をクリア  
            if hasattr(self.video_preview, 'bbox_editor'):  
                self.video_preview.bbox_editor.selected_annotation = None  
                self.video_preview.bbox_editor.selection_changed.emit(None)  
            print("--- Redo ---")  
        else:  
            ErrorHandler.show_info_dialog("There are no actions to redo.", "Redo")  
      
    def _handle_copy_annotation(self):  
        """Ctrl+C: アノテーションをコピー"""  
        if (hasattr(self.menu_panel, 'annotation_tab') and   
            self.menu_panel.annotation_tab.current_selected_annotation and  
            self.menu_panel.annotation_tab.edit_mode_btn.isChecked() and  
            self.menu_panel.annotation_tab.copy_annotation_btn.isEnabled()):  
            print("--- Copy ---")  
            self.menu_panel.annotation_tab._on_copy_annotation_clicked()  
      
    def _handle_paste_annotation(self):  
        """Ctrl+V: アノテーションをペースト"""  
        if (hasattr(self.menu_panel, 'annotation_tab') and  
            self.menu_panel.annotation_tab.edit_mode_btn.isChecked() and  
            self.menu_panel.annotation_tab.paste_annotation_btn.isEnabled()):  
            print("--- Paste ---")  
            self.menu_panel.annotation_tab._on_paste_annotation_clicked()  
      
    # === Ctrl+Shift系ショートカットハンドラー ===  
      
    def _handle_save_coco(self):  
        """Ctrl+Shift+S: COCO JSONを保存"""  
        if (hasattr(self.menu_panel, 'basic_tab') and   
            self.menu_panel.basic_tab.save_coco_json_btn.isEnabled()):  
            self.menu_panel.basic_tab._on_export_coco_clicked()  
      
    # === 単独キーショートカットハンドラー ===  
      
    def _handle_playback_toggle(self):  
        """Space: 動画再生・一時停止の処理"""  
        if hasattr(self.main_widget, 'playback_controller') and self.main_widget.playback_controller:  
            if self.main_widget.playback_controller.is_playing:  
                self.main_widget.pause_playback()  
            else:  
                self.main_widget.start_playback()  
      
    def _handle_prev_frame(self):  
        """Left: 前のフレーム"""  
        self.video_control.prev_frame()  
      
    def _handle_next_frame(self):  
        """Right: 次のフレーム"""  
        self.video_control.next_frame()  
      
    def _handle_edit_mode_toggle(self):  
        """E: 編集モード切り替え"""  
        if (hasattr(self.menu_panel, 'annotation_tab') and   
            self.menu_panel.annotation_tab.edit_mode_btn.isEnabled()):  
            current_state = self.menu_panel.annotation_tab.edit_mode_btn.isChecked()  
            self.menu_panel.annotation_tab.edit_mode_btn.setChecked(not current_state)  
            self.menu_panel.annotation_tab._on_edit_mode_clicked(not current_state)  
      
    def _handle_tracking_mode_toggle(self):  
        """T: トラッキングモード切り替え"""  
        if (hasattr(self.menu_panel, 'annotation_tab') and   
            self.menu_panel.annotation_tab.tracking_annotation_btn.isEnabled()):  
            current_state = self.menu_panel.annotation_tab.tracking_annotation_btn.isChecked()  
            self.menu_panel.annotation_tab.tracking_annotation_btn.setChecked(not current_state)  
            self.menu_panel.annotation_tab._on_tracking_annotation_clicked(not current_state)  
      
    def _handle_copy_mode_toggle(self):  
        """C: コピーモード切り替え"""  
        if (hasattr(self.menu_panel, 'annotation_tab') and   
            self.menu_panel.annotation_tab.copy_annotations_btn.isEnabled()):  
            current_state = self.menu_panel.annotation_tab.copy_annotations_btn.isChecked()  
            self.menu_panel.annotation_tab.copy_annotations_btn.setChecked(not current_state)  
            self.menu_panel.annotation_tab._on_copy_annotations_clicked(not current_state)  
      
    def _handle_delete_single_annotation(self):  
        """X: 選択アノテーションを削除"""  
        if (hasattr(self.menu_panel, 'annotation_tab') and  
            self.menu_panel.annotation_tab.current_selected_annotation and  
            self.menu_panel.annotation_tab.delete_single_annotation_btn.isEnabled()):  
            self.menu_panel.annotation_tab._on_delete_single_annotation_clicked()  
      
    def _handle_delete_track(self):  
        """D: トラック一括削除"""  
        if (hasattr(self.menu_panel, 'annotation_tab') and  
            self.menu_panel.annotation_tab.current_selected_annotation and  
            self.menu_panel.annotation_tab.delete_track_btn.isEnabled()):  
            self.menu_panel.annotation_tab._on_delete_track_clicked()  
      
    def _handle_propagate_label(self):  
        """P: 一括ラベル変更"""  
        if (hasattr(self.menu_panel, 'annotation_tab') and  
            self.menu_panel.annotation_tab.current_selected_annotation and  
            self.menu_panel.annotation_tab.propagate_label_btn.isEnabled()):  
            self.menu_panel.annotation_tab._on_propagate_label_clicked()  
      
    def _handle_execute_tracking(self):  
        """R: 実行ボタン"""  
        if (hasattr(self.menu_panel, 'annotation_tab') and   
            self.menu_panel.annotation_tab.execute_add_btn.isEnabled()):  
            self.menu_panel.annotation_tab._on_complete_tracking_clicked()  
      
    def _handle_jump_to_frame(self):  
        """G: フレームジャンプ実行"""  
        self.video_control.jump_to_frame()  
      
    def _handle_focus_frame_input(self):  
        """F: フレーム入力フィールドにフォーカス移動"""  
        self.video_control.frame_input.setFocus()  
        self.video_control.frame_input.selectAll()  
      
    def _handle_align_track_ids(self):  
        """A: Track ID統一"""  
        if (hasattr(self.menu_panel, 'annotation_tab') and  
            self.menu_panel.annotation_tab.current_selected_annotation and  
            self.menu_panel.annotation_tab.align_track_ids_btn.isEnabled()):  
            self.menu_panel.annotation_tab._on_align_track_ids_clicked()

    def _handle_propagate_confidence(self):  
        """F: 一括信頼度変更"""  
        if (hasattr(self.menu_panel, 'annotation_tab') and  
            self.menu_panel.annotation_tab.current_selected_annotation and  
            self.menu_panel.annotation_tab.propagate_confidence_btn.isEnabled()):  
            self.menu_panel.annotation_tab._on_propagate_confidence_clicked()  
