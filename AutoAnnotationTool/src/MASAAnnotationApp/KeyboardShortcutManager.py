# KeyboardShortcutManager.py
"""
キーボードショートカット管理
MASAAnnotationWidgetからキーボードイベント処理を分離
"""
from typing import Dict, Callable, Optional
from PyQt6.QtWidgets import QLineEdit, QComboBox, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent

from MASAApplicationService import MASAApplicationService
from MainUIController import MainUIController

class KeyboardShortcutManager:
    """キーボードショートカットの管理とアクション実行を担当"""
    
    def __init__(self, app_service: MASAApplicationService, main_controller: MainUIController):
        """ショートカットマネージャーの初期化"""
        self.app_service = app_service
        self.main_controller = main_controller
        
        # ショートカットマッピング
        self.shortcut_mappings: Dict[str, Callable] = {}
        
        self.setup_shortcuts()
    
    def setup_shortcuts(self):
        """ショートカットマッピングを設定"""
        # Ctrl系ショートカット
        self.register_shortcut("Ctrl+O", self._load_video)
        self.register_shortcut("Ctrl+L", self._load_json)
        self.register_shortcut("Ctrl+S", self._save_masa_json)
        self.register_shortcut("Ctrl+Shift+S", self._save_coco_json)
        self.register_shortcut("Ctrl+Z", self._undo)
        self.register_shortcut("Ctrl+Y", self._redo)
        
        # 単独キー
        self.register_shortcut("Space", self._toggle_playback)
        self.register_shortcut("Left", self._prev_frame)
        self.register_shortcut("Right", self._next_frame)
        self.register_shortcut("E", self._toggle_edit_mode)
        self.register_shortcut("B", self._toggle_batch_add_mode)
        self.register_shortcut("X", self._delete_selected_annotation)
        self.register_shortcut("D", self._delete_track)
        self.register_shortcut("P", self._propagate_label)
        self.register_shortcut("R", self._execute_batch_add)
        self.register_shortcut("G", self._jump_to_frame)
        self.register_shortcut("F", self._focus_frame_input)
        self.register_shortcut("Enter", self._handle_enter_key)
    
    def register_shortcut(self, key_combo: str, action: Callable):
        """ショートカットを登録"""
        self.shortcut_mappings[key_combo] = action
    
    def handle_key_event(self, event: QKeyEvent) -> bool:
        """キーイベントを処理"""
        # テキスト入力中はショートカットを制限
        if self.is_text_input_focused():
            # Ctrl系のショートカットのみ有効にする
            if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                return self._handle_ctrl_shortcuts(event)
            elif event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
                return self._handle_enter_in_text_input(event)
            elif event.key() == Qt.Key.Key_Space:
                # テキスト入力中のSpaceキーは無効化しない
                return False
            else:
                return False
        
        # ボタンにフォーカスがある場合の特別処理
        if self._is_button_focused():
            return self._handle_button_focus(event)
        
        # 通常のショートカット処理
        key_combo = self._get_key_combination(event)
        if key_combo in self.shortcut_mappings:
            try:
                self.shortcut_mappings[key_combo]()
                return True
            except Exception as e:
                print(f"ショートカット実行エラー ({key_combo}): {e}")
                return False
        
        return False
    
    def is_text_input_focused(self) -> bool:
        """テキスト入力ウィジェットにフォーカスがあるかチェック"""
        from PyQt6.QtWidgets import QApplication
        
        focused_widget = QApplication.focusWidget()
        return isinstance(focused_widget, (QLineEdit, QComboBox))
    
    def _is_button_focused(self) -> bool:
        """ボタンにフォーカスがあるかチェック"""
        from PyQt6.QtWidgets import QApplication
        
        focused_widget = QApplication.focusWidget()
        return isinstance(focused_widget, QPushButton)
    
    def _get_key_combination(self, event: QKeyEvent) -> str:
        """キーイベントから組み合わせ文字列を生成"""
        modifiers = []
        
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            modifiers.append("Ctrl")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            modifiers.append("Shift")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier:
            modifiers.append("Alt")
        
        # キー名の変換
        key_name = self._get_key_name(event.key())
        
        if modifiers:
            return "+".join(modifiers) + "+" + key_name
        else:
            return key_name
    
    def _get_key_name(self, key: Qt.Key) -> str:
        """Qt.Keyから文字列に変換"""
        key_map = {
            Qt.Key.Key_Space: "Space",
            Qt.Key.Key_Left: "Left",
            Qt.Key.Key_Right: "Right",
            Qt.Key.Key_Return: "Enter",
            Qt.Key.Key_Enter: "Enter",
            Qt.Key.Key_O: "O",
            Qt.Key.Key_L: "L",
            Qt.Key.Key_S: "S",
            Qt.Key.Key_Z: "Z",
            Qt.Key.Key_Y: "Y",
            Qt.Key.Key_E: "E",
            Qt.Key.Key_B: "B",
            Qt.Key.Key_X: "X",
            Qt.Key.Key_D: "D",
            Qt.Key.Key_P: "P",
            Qt.Key.Key_R: "R",
            Qt.Key.Key_G: "G",
            Qt.Key.Key_F: "F",
        }
        return key_map.get(key, "Unknown")
    
    def _handle_ctrl_shortcuts(self, event: QKeyEvent) -> bool:
        """Ctrl系ショートカットの処理"""
        key_combo = self._get_key_combination(event)
        if key_combo in self.shortcut_mappings:
            try:
                self.shortcut_mappings[key_combo]()
                return True
            except Exception as e:
                print(f"Ctrlショートカット実行エラー ({key_combo}): {e}")
                return False
        return False
    
    def _handle_enter_in_text_input(self, event: QKeyEvent) -> bool:
        """テキスト入力中のEnterキー処理"""
        from PyQt6.QtWidgets import QApplication
        
        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, QComboBox):
            # ComboBoxの場合は通常のEnter処理を継続
            return False
        elif isinstance(focused_widget, QLineEdit):
            # LineEditの場合、特定の処理があれば実行
            if hasattr(focused_widget, 'returnPressed'):
                focused_widget.returnPressed.emit()
            return True
        return False
    
    def _handle_button_focus(self, event: QKeyEvent) -> bool:
        """ボタンフォーカス時の特別処理"""
        from PyQt6.QtWidgets import QApplication
        
        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, QPushButton):
            if event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
                # Enterキーでボタンをクリック
                focused_widget.click()
                return True
            elif event.key() == Qt.Key.Key_Space:
                # Spaceキーの場合は何もしない（デフォルト動作を無効化）
                return True
        return False
    
    # ===== ショートカットアクション =====
    
    def _load_video(self):
        """動画読み込み（Ctrl+O）"""
        menu_panel = self.main_controller.get_menu_panel()
        if menu_panel and hasattr(menu_panel, '_on_load_video_clicked'):
            menu_panel._on_load_video_clicked("")
    
    def _load_json(self):
        """JSON読み込み（Ctrl+L）"""
        menu_panel = self.main_controller.get_menu_panel()
        if menu_panel and hasattr(menu_panel, '_on_load_json_clicked'):
            menu_panel._on_load_json_clicked("")
    
    def _save_masa_json(self):
        """MASA JSON保存（Ctrl+S）"""
        menu_panel = self.main_controller.get_menu_panel()
        if menu_panel and hasattr(menu_panel, 'save_masa_json_btn'):
            if menu_panel.save_masa_json_btn.isEnabled():
                success = self.app_service.export_masa_json(self._get_default_filename("masa"))
                if success:
                    print("MASA JSON保存完了")
    
    def _save_coco_json(self):
        """COCO JSON保存（Ctrl+Shift+S）"""
        menu_panel = self.main_controller.get_menu_panel()
        if menu_panel and hasattr(menu_panel, 'save_coco_json_btn'):
            if menu_panel.save_coco_json_btn.isEnabled():
                success = self.app_service.export_coco_json(self._get_default_filename("coco"))
                if success:
                    print("COCO JSON保存完了")
    
    def _undo(self):
        """取り消し（Ctrl+Z）"""
        if self.app_service.undo():
            self.main_controller.refresh_display()
            print("Undo実行")
        else:
            print("取り消す操作がありません")
    
    def _redo(self):
        """やり直し（Ctrl+Y）"""
        if self.app_service.redo():
            self.main_controller.refresh_display()
            print("Redo実行")
        else:
            print("やり直す操作がありません")
    
    def _toggle_playback(self):
        """再生・一時停止切り替え（Space）"""
        # 動画再生・一時停止の処理
        if hasattr(self.main_controller.parent, 'playback_controller'):
            playback_controller = self.main_controller.parent.playback_controller
            if playback_controller and playback_controller.is_playing:
                self.main_controller.parent.pause_playback()
            else:
                self.main_controller.parent.start_playback()
    
    def _prev_frame(self):
        """前フレーム（Left）"""
        video_control = self.main_controller.get_video_control()
        if video_control:
            video_control.prev_frame()
    
    def _next_frame(self):
        """次フレーム（Right）"""
        video_control = self.main_controller.get_video_control()
        if video_control:
            video_control.next_frame()
    
    def _toggle_edit_mode(self):
        """編集モード切り替え（E）"""
        menu_panel = self.main_controller.get_menu_panel()
        if menu_panel and hasattr(menu_panel, 'edit_mode_btn'):
            if menu_panel.edit_mode_btn.isEnabled():
                current_state = menu_panel.edit_mode_btn.isChecked()
                menu_panel.edit_mode_btn.setChecked(not current_state)
                menu_panel._on_edit_mode_clicked(not current_state)
    
    def _toggle_batch_add_mode(self):
        """一括追加モード切り替え（B）"""
        menu_panel = self.main_controller.get_menu_panel()
        if menu_panel and hasattr(menu_panel, 'batch_add_annotation_btn'):
            if menu_panel.batch_add_annotation_btn.isEnabled():
                current_state = menu_panel.batch_add_annotation_btn.isChecked()
                menu_panel.batch_add_annotation_btn.setChecked(not current_state)
                menu_panel._on_batch_add_annotation_clicked(not current_state)
    
    def _delete_selected_annotation(self):
        """選択アノテーション削除（X）"""
        menu_panel = self.main_controller.get_menu_panel()
        if menu_panel and hasattr(menu_panel, 'current_selected_annotation'):
            if (menu_panel.current_selected_annotation and 
                hasattr(menu_panel, 'delete_single_annotation_btn') and
                menu_panel.delete_single_annotation_btn.isEnabled()):
                menu_panel._on_delete_single_annotation_clicked()
    
    def _delete_track(self):
        """トラック一括削除（D）"""
        menu_panel = self.main_controller.get_menu_panel()
        if menu_panel and hasattr(menu_panel, 'current_selected_annotation'):
            if (menu_panel.current_selected_annotation and 
                hasattr(menu_panel, 'delete_track_btn') and
                menu_panel.delete_track_btn.isEnabled()):
                menu_panel._on_delete_track_clicked()
    
    def _propagate_label(self):
        """一括ラベル変更（P）"""
        menu_panel = self.main_controller.get_menu_panel()
        if menu_panel and hasattr(menu_panel, 'current_selected_annotation'):
            if (menu_panel.current_selected_annotation and 
                hasattr(menu_panel, 'propagate_label_btn') and
                menu_panel.propagate_label_btn.isEnabled()):
                menu_panel._on_propagate_label_clicked()
    
    def _execute_batch_add(self):
        """実行ボタン（R）"""
        menu_panel = self.main_controller.get_menu_panel()
        if menu_panel and hasattr(menu_panel, 'execute_batch_add_btn'):
            if menu_panel.execute_batch_add_btn.isEnabled():
                menu_panel._on_complete_batch_add_clicked()
    
    def _jump_to_frame(self):
        """フレームジャンプ実行（G）"""
        video_control = self.main_controller.get_video_control()
        if video_control:
            video_control.jump_to_frame()
    
    def _focus_frame_input(self):
        """フレーム入力フィールドにフォーカス（F）"""
        video_control = self.main_controller.get_video_control()
        if video_control and hasattr(video_control, 'frame_input'):
            video_control.frame_input.setFocus()
            video_control.frame_input.selectAll()
    
    def _handle_enter_key(self):
        """Enterキー処理"""
        from PyQt6.QtWidgets import QApplication
        
        focused_widget = QApplication.focusWidget()
        if isinstance(focused_widget, QPushButton):
            focused_widget.click()
    
    # ===== ヘルパーメソッド =====
    
    def _get_default_filename(self, format: str) -> str:
        """デフォルトのファイル名を生成"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"annotations_{timestamp}.{format}"
    
    def get_shortcut_descriptions(self) -> Dict[str, str]:
        """ショートカットの説明を取得"""
        return {
            "Ctrl+O": "動画を読み込み",
            "Ctrl+L": "JSONを読み込み",
            "Ctrl+S": "MASA JSONを保存",
            "Ctrl+Shift+S": "COCO JSONを保存",
            "Ctrl+Z": "取り消し",
            "Ctrl+Y": "やり直し",
            "Space": "再生・一時停止",
            "Left": "前フレーム",
            "Right": "次フレーム",
            "E": "編集モード切り替え",
            "B": "一括追加モード切り替え",
            "X": "選択アノテーション削除",
            "D": "トラック一括削除",
            "P": "一括ラベル変更",
            "R": "一括追加実行",
            "G": "フレームジャンプ",
            "F": "フレーム入力にフォーカス",
            "Enter": "ボタンクリック（フォーカス時）"
        }
