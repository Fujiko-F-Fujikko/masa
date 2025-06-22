from pathlib import Path
from typing import Dict, List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QCheckBox, QLineEdit,
    QMessageBox, QTabWidget, QComboBox, QFileDialog,
    QDoubleSpinBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

class MenuPanel(QWidget):  
    """タブベースの左側メニューパネル"""  
      
    # シグナル定義  
    load_video_requested = pyqtSignal()  
    annotation_mode_requested = pyqtSignal(bool)  
    range_selection_requested = pyqtSignal(bool)  
    edit_mode_requested = pyqtSignal(bool)  
    tracking_requested = pyqtSignal()  
    export_requested = pyqtSignal(str)  # format  
    multi_frame_mode_requested = pyqtSignal(bool, str)  # enabled, label  
    result_view_requested = pyqtSignal(bool)  # 互換性のために残す（非推奨）
    load_json_requested = pyqtSignal(str)  # json_path 
    score_threshold_changed = pyqtSignal(float)  # threshold_value
    play_requested = pyqtSignal()  
    pause_requested = pyqtSignal()  
    label_change_requested = pyqtSignal(object, str)  # annotation, new_label
    delete_single_annotation_requested = pyqtSignal(object) # ObjectAnnotation

    def __init__(self, parent=None):  
        super().__init__(parent)  
        self.current_selected_annotation_label = None
        self.setFixedWidth(300)  
        self.setStyleSheet("background-color: #f0f0f0; border-right: 1px solid #ccc;")  
        self.setup_ui()  

    def setup_ui(self):  
        layout = QVBoxLayout()  
        layout.setSpacing(10)  
        layout.setContentsMargins(10, 10, 10, 10)  
          
        # タイトル  
        title_label = QLabel("MASA Annotation Tool")  
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))  
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        layout.addWidget(title_label)  

        # タブウィジェットを作成
        self.tab_widget = QTabWidget()
        self.setup_basic_tab()      # 基本設定タブ
        self.setup_annotation_tab() # アノテーションタブ
        
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

    def setup_basic_tab(self):
        """基本設定タブの設定"""
        basic_tab = QWidget()
        layout = QVBoxLayout()

        # ファイル操作グループ
        file_group = QGroupBox("ファイル操作")
        file_layout = QVBoxLayout()

        # 動画ファイル
        video_layout = QVBoxLayout()
        self.load_video_btn = QPushButton("動画を読み込み")
        self.load_video_btn.clicked.connect(self.load_video_requested.emit)
        video_layout.addWidget(self.load_video_btn)
        self.video_info_label = QLabel("動画が読み込まれていません")
        self.video_info_label.setWordWrap(True)
        video_layout.addWidget(self.video_info_label)
        file_layout.addLayout(video_layout)

        # JSONファイル操作を更新  
        json_layout = QVBoxLayout()  
        self.load_json_btn = QPushButton("JSONを読み込み")  
        self.load_json_btn.clicked.connect(self._on_load_json_clicked)  
        json_layout.addWidget(self.load_json_btn)  
          
        # MASA JSON保存ボタンを追加  
        self.save_masa_json_btn = QPushButton("MASA JSONを保存")  
        self.save_masa_json_btn.clicked.connect(lambda: self.export_requested.emit("masa_json"))  
        self.save_masa_json_btn.setEnabled(False)  
        json_layout.addWidget(self.save_masa_json_btn)  
          
        self.save_json_btn = QPushButton("カスタムJSONを保存")  
        self.save_json_btn.clicked.connect(lambda: self.export_requested.emit("json"))  
        self.save_json_btn.setEnabled(False)  
        json_layout.addWidget(self.save_json_btn)  

        self.json_info_label = QLabel("JSONが読み込まれていません")
        self.json_info_label.setWordWrap(True)
        json_layout.addWidget(self.json_info_label)
        file_layout.addLayout(json_layout)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # 再生コントロールグループを更新  
        playback_group = QGroupBox("再生コントロール")  
        playback_layout = QVBoxLayout()  
          
        self.play_btn = QPushButton("再生")  
        self.play_btn.setEnabled(False)  
        self.play_btn.clicked.connect(self._on_play_clicked)  
        playback_layout.addWidget(self.play_btn)  
          
        self.frame_label = QLabel("フレーム: 0/0")  
        playback_layout.addWidget(self.frame_label)  
        playback_group.setLayout(playback_layout)  
        layout.addWidget(playback_group)  

        # 表示設定グループ
        display_group = QGroupBox("表示設定")
        display_layout = QVBoxLayout()

        self.show_manual_cb = QCheckBox("手動アノテーション結果表示")
        self.show_manual_cb.setChecked(True)
        display_layout.addWidget(self.show_manual_cb)

        self.show_auto_cb = QCheckBox("自動アノテーション結果表示")
        self.show_auto_cb.setChecked(True)
        display_layout.addWidget(self.show_auto_cb)

        self.show_ids_cb = QCheckBox("Track ID表示")
        self.show_ids_cb.setChecked(True)
        display_layout.addWidget(self.show_ids_cb)

        self.show_confidence_cb = QCheckBox("スコア表示")
        self.show_confidence_cb.setChecked(True)
        display_layout.addWidget(self.show_confidence_cb)

        # シンプルな緑色チェックマーク  
        simple_checkbox_style = """  
        QCheckBox::indicator:checked {  
            background-color: #4CAF50;  
            border: 1px solid #4CAF50;  
        }  
        QCheckBox::indicator:unchecked {  
            background-color: white;  
            border: 1px solid #ccc;  
        }  
        """
        # 各チェックボックスに適用  
        self.show_manual_cb.setStyleSheet(simple_checkbox_style)  
        self.show_auto_cb.setStyleSheet(simple_checkbox_style)  
        self.show_ids_cb.setStyleSheet(simple_checkbox_style)  
        self.show_confidence_cb.setStyleSheet(simple_checkbox_style)

        # スコア閾値設定を追加  
        score_threshold_layout = QHBoxLayout()  
        score_threshold_layout.addWidget(QLabel("スコア閾値:"))  

        self.score_threshold_spinbox = QDoubleSpinBox()  
        self.score_threshold_spinbox.setRange(0.0, 1.0)  
        self.score_threshold_spinbox.setSingleStep(0.1)  
        self.score_threshold_spinbox.setDecimals(2)  
        self.score_threshold_spinbox.setValue(0.2)  # デフォルト値  
        self.score_threshold_spinbox.valueChanged.connect(self.on_score_threshold_changed)  
        score_threshold_layout.addWidget(self.score_threshold_spinbox)  
          
        display_layout.addLayout(score_threshold_layout)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        layout.addStretch()
        basic_tab.setLayout(layout)
        self.tab_widget.addTab(basic_tab, "基本設定")

    def setup_annotation_tab(self):
        """アノテーションタブの設定"""
        annotation_tab = QWidget()
        layout = QVBoxLayout()

        # アノテーションモードグループ
        mode_group = QGroupBox("操作モード")
        mode_layout = QVBoxLayout()

        self.annotation_mode_btn = QPushButton("シングルフレームアノテーションモード")
        self.annotation_mode_btn.setCheckable(True)
        self.annotation_mode_btn.clicked.connect(self._on_annotation_mode_clicked)
        self.annotation_mode_btn.setEnabled(False)
        mode_layout.addWidget(self.annotation_mode_btn)

        self.multi_frame_btn = QPushButton("マルチフレームアノテーションモード")
        self.multi_frame_btn.setCheckable(True)
        self.multi_frame_btn.clicked.connect(self._on_multi_frame_clicked)
        self.multi_frame_btn.setEnabled(False)
        mode_layout.addWidget(self.multi_frame_btn)

        # ラベル入力
        self.multi_frame_label_input = QLineEdit()
        self.multi_frame_label_input.setPlaceholderText("オブジェクトラベル")
        self.multi_frame_label_input.setEnabled(False)
        mode_layout.addWidget(self.multi_frame_label_input)

        # 完了ボタン
        self.complete_multi_frame_btn = QPushButton("マルチフレームアノテーション設定完了")
        self.complete_multi_frame_btn.clicked.connect(self._on_complete_multi_frame)
        self.complete_multi_frame_btn.setEnabled(False)
        mode_layout.addWidget(self.complete_multi_frame_btn)

        # 編集モードボタンのスタイルを設定  
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

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # アノテーション情報グループ
        info_group = QGroupBox("アノテーション情報")
        info_layout = QVBoxLayout()
        self.annotation_count_label = QLabel("アノテーション数: 0")
        info_layout.addWidget(self.annotation_count_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # アノテーション編集グループ
        edit_group = QGroupBox("アノテーション編集")
        edit_layout = QVBoxLayout()

        self.edit_mode_btn = QPushButton("編集モード")
        self.edit_mode_btn.setCheckable(True)
        self.edit_mode_btn.setStyleSheet(edit_button_style)
        self.edit_mode_btn.clicked.connect(self._on_edit_mode_clicked)
        self.edit_mode_btn.setEnabled(False)
        edit_layout.addWidget(self.edit_mode_btn)

        self.label_combo = QComboBox()
        self.label_combo.setEditable(True)
        self.label_combo.setEnabled(False)
        self.label_combo.currentIndexChanged.connect(self._on_label_changed)
        edit_layout.addWidget(QLabel("ラベル:"))
        edit_layout.addWidget(self.label_combo)

        self.track_id_edit = QLineEdit()
        self.track_id_edit.setEnabled(False)
        edit_layout.addWidget(QLabel("Track ID:"))
        edit_layout.addWidget(self.track_id_edit)

        # 新しい単一アノテーション削除ボタンを追加  
        self.delete_single_annotation_btn = QPushButton("選択アノテーションを削除")  
        self.delete_single_annotation_btn.setEnabled(False)  
        self.delete_single_annotation_btn.clicked.connect(self._on_delete_single_annotation_clicked)  
        edit_layout.addWidget(self.delete_single_annotation_btn)  

        # 一括編集ボタン
        self.delete_track_btn = QPushButton("選択Track全削除")
        self.delete_track_btn.setEnabled(False)
        edit_layout.addWidget(self.delete_track_btn)

        self.propagate_label_btn = QPushButton("ラベル変更を伝播")
        self.propagate_label_btn.setEnabled(False)
        edit_layout.addWidget(self.propagate_label_btn)

        edit_group.setLayout(edit_layout)
        layout.addWidget(edit_group)

        # 自動追跡グループ
        tracking_group = QGroupBox("自動追跡")
        tracking_layout = QVBoxLayout()

        self.range_selection_btn = QPushButton("範囲選択モード")
        self.range_selection_btn.setCheckable(True)
        self.range_selection_btn.clicked.connect(self._on_range_selection_clicked)
        self.range_selection_btn.setEnabled(False)
        tracking_layout.addWidget(self.range_selection_btn)

        self.range_info_label = QLabel("範囲: 未選択")
        tracking_layout.addWidget(self.range_info_label)

        self.tracking_btn = QPushButton("追跡開始")
        self.tracking_btn.clicked.connect(self.tracking_requested.emit)
        self.tracking_btn.setEnabled(False)
        tracking_layout.addWidget(self.tracking_btn)

        self.tracking_progress_label = QLabel("")
        tracking_layout.addWidget(self.tracking_progress_label)

        tracking_group.setLayout(tracking_layout)
        layout.addWidget(tracking_group)

        layout.addStretch()
        annotation_tab.setLayout(layout)
        self.tab_widget.addTab(annotation_tab, "アノテーション")

    def _on_load_json_clicked(self):  
        """JSONファイル読み込みボタンのクリックハンドラ"""  
        file_path, _ = QFileDialog.getOpenFileName(  
            self, "Select JSON Annotation File", "",  
            "JSON Files (*.json);;All Files (*)"  
        )  
          
        if file_path:  
            self.load_json_requested.emit(file_path)  

    def update_json_info(self, json_path: str, annotation_count: int):  
        """JSON情報を更新"""  
        filename = Path(json_path).name  
        self.json_info_label.setText(f"{filename}\n{annotation_count} annotations loaded")
    
    def _on_annotation_mode_clicked(self, checked):  
        if checked:  
            self.range_selection_btn.setChecked(False)  
            self.multi_frame_btn.setChecked(False)
            self.edit_mode_btn.setChecked(False)
        self.annotation_mode_requested.emit(checked)  
      
    def _on_range_selection_clicked(self, checked):  
        if checked:  
            self.annotation_mode_btn.setChecked(False)  
            self.multi_frame_btn.setChecked(False)
            self.edit_mode_btn.setChecked(False)
        self.range_selection_requested.emit(checked)  
      
    def _on_edit_mode_clicked(self, checked):  
        if checked:  
            self.annotation_mode_btn.setChecked(False)  
            self.range_selection_btn.setChecked(False)
            self.multi_frame_btn.setChecked(False)
            # 編集用コントロールを有効化
            self.label_combo.setEnabled(True)
            self.track_id_edit.setEnabled(True)
            self.delete_track_btn.setEnabled(True)
            self.propagate_label_btn.setEnabled(True)
        else:
            # 編集用コントロールを無効化
            self.label_combo.setEnabled(False)
            self.track_id_edit.setEnabled(False)
            self.delete_track_btn.setEnabled(False)
            self.propagate_label_btn.setEnabled(False)
        self.edit_mode_requested.emit(checked)  
      
    def update_video_info(self, video_path: str, total_frames: int):    
        """動画情報を更新"""    
        filename = Path(video_path).name    
        self.video_info_label.setText(f"{filename}\n{total_frames} frames")    
          
        # フレーム表示も更新  
        self.frame_label.setText(f"フレーム: 0/{total_frames - 1}")  
            
        # ボタンを有効化    
        self.annotation_mode_btn.setEnabled(True)    
        self.range_selection_btn.setEnabled(True)    
        self.multi_frame_btn.setEnabled(True)    
        self.multi_frame_label_input.setEnabled(True)  
        self.edit_mode_btn.setEnabled(True)  
        self.play_btn.setEnabled(True)
      
    def update_annotation_count(self, count: int, manual_count: int = None):  
        """アノテーション数を更新"""  
        if manual_count is not None:  
            loaded_count = count - manual_count  
            self.annotation_count_label.setText(  
                f"総アノテーション数: {count}\n"  
                f"(読み込み: {loaded_count}, 手動: {manual_count})"  
            )  
        else:  
            self.annotation_count_label.setText(f"アノテーション数: {count}")  
          
        self.tracking_btn.setEnabled(count > 0)
      
    def update_range_info(self, start_frame: int, end_frame: int):  
        """範囲情報を更新"""  
        self.range_info_label.setText(f"Range: {start_frame} - {end_frame}")  
      
    def update_tracking_progress(self, progress_text: str):  
        """追跡進捗を更新"""  
        self.tracking_progress_label.setText(progress_text)  
      
    def enable_result_view(self, enabled: bool):  
        """結果確認モードを有効化"""  
        self.save_json_btn.setEnabled(enabled)
        self.save_masa_json_btn.setEnabled(enabled)
      
    def get_display_options(self) -> Dict[str, bool]:  
        """表示オプションを取得"""  
        return {  
            'show_manual': self.show_manual_cb.isChecked(),  
            'show_auto': self.show_auto_cb.isChecked(),  
            'show_ids': self.show_ids_cb.isChecked(),  
            'show_confidence': self.show_confidence_cb.isChecked()  
        }  
      
    def _on_multi_frame_clicked(self, checked):  
        if checked:  
            label = self.multi_frame_label_input.text().strip()  
            if not label:  
                QMessageBox.warning(self, "Warning", "オブジェクトラベルを入力してください")  
                self.multi_frame_btn.setChecked(False)  
                return  
              
            # 他のモードを無効化  
            self.annotation_mode_btn.setChecked(False)  
            self.range_selection_btn.setChecked(False)  
            self.edit_mode_btn.setChecked(False)
            self.result_view_requested.emit(False)  # 結果表示モードをOFF
              
            self.multi_frame_label_input.setEnabled(False)  
            self.complete_multi_frame_btn.setEnabled(True)  
        else:  
            self.multi_frame_label_input.setEnabled(True)  
            self.complete_multi_frame_btn.setEnabled(False)  
          
        self.multi_frame_mode_requested.emit(checked, self.multi_frame_label_input.text().strip())  
      
    def _on_complete_multi_frame(self):  
        # 複数フレームアノテーション完了シグナルを発行  
        self.multi_frame_btn.setChecked(False)  
        self._on_multi_frame_clicked(False)

    def on_score_threshold_changed(self, value: float):  
        """スコア閾値変更時の処理"""  
        self.score_threshold_changed.emit(value)  
      
    def get_display_options(self) -> Dict[str, bool]:  
        """表示オプションを取得（スコア閾値を追加）"""  
        return {  
            'show_manual': self.show_manual_cb.isChecked(),  
            'show_auto': self.show_auto_cb.isChecked(),  
            'show_ids': self.show_ids_cb.isChecked(),  
            'show_confidence': self.show_confidence_cb.isChecked(),  
            'score_threshold': self.score_threshold_spinbox.value()  
        }

    def _on_play_clicked(self):  
        """再生/一時停止ボタンクリック処理"""  
        if self.play_btn.text() == "再生":  
            self.play_requested.emit()  
            self.play_btn.setText("一時停止")  
        else:  
            self.pause_requested.emit()  
            self.play_btn.setText("再生") 

    def reset_playback_button(self):  
        """再生ボタンを初期状態にリセット"""  
        self.play_btn.setText("再生")
        
    def update_frame_display(self, current_frame: int, total_frames: int):  
        """フレーム表示を更新"""  
        self.frame_label.setText(f"フレーム: {current_frame}/{total_frames - 1}")

    def _on_label_changed(self):  
        """ラベル変更時の処理"""  
        if hasattr(self, 'current_selected_annotation') and self.current_selected_annotation:  
            new_label = self.label_combo.currentText()  
              
            # ラベルが実際に変更された場合のみシグナルを発火  
            if new_label != self.current_selected_annotation_label:  
                self.label_change_requested.emit(self.current_selected_annotation, new_label)  
                # 変更が適用されたら、現在のラベルを更新  
                self.current_selected_annotation_label = new_label  
                  
                # ここで QMessageBox.information を表示  
                QMessageBox.information(  
                    self, "ラベル変更",  
                    f"アノテーションID {self.current_selected_annotation.object_id} のラベルを '{new_label}' に変更しました。"  
                )
  
    def update_selected_annotation_info(self, annotation):  
        """選択されたアノテーション情報をUIに反映"""  
        self.current_selected_annotation = annotation  
          
        # シグナルを一時的にブロック  
        print("block label_combo signals")  
        self.label_combo.blockSignals(True)  
          
        try: # try-finally ブロックで確実にシグナルブロックを解除  
            if annotation is None:  
                self.current_selected_annotation_label = None  
                self.label_combo.setCurrentText("") # ラベルコンボボックスをクリア  
                self.track_id_edit.setText("") # Track ID入力欄をクリア  
                self.delete_single_annotation_btn.setEnabled(False) # 新しいボタンを無効化  
                self.delete_track_btn.setEnabled(False)  
            else:  
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
                    # 新しいラベルの場合は追加して選択  
                    self.label_combo.addItem(annotation.label)  
                    self.label_combo.setCurrentText(annotation.label)  
                  
                # Track IDも更新  
                self.track_id_edit.setText(str(annotation.object_id))  
                self.delete_single_annotation_btn.setEnabled(True) # 新しいボタンを有効化  
                self.delete_track_btn.setEnabled(True)  
                  
        finally:  
            # シグナルブロックを解除  
            print("unblock label_combo signals")  
            self.label_combo.blockSignals(False)

    def initialize_label_combo(self, existing_labels: List[str]):  
        """既存のラベルでコンボボックスを初期化"""  
        self.label_combo.clear()  
          
        # 既存のラベルを追加  
        for label in existing_labels:  
            self.label_combo.addItem(label)  
          
        # 編集可能にして新しいラベルも入力できるようにする  
        self.label_combo.setEditable(True)  

    def _on_delete_single_annotation_clicked(self):  
        """単一アノテーション削除ボタンクリック時の処理"""  
        if hasattr(self, 'current_selected_annotation') and self.current_selected_annotation:  
            reply = QMessageBox.question(  
                self, "アノテーション削除確認",  
                f"フレーム {self.current_selected_annotation.frame_id} のアノテーション (ID: {self.current_selected_annotation.object_id}, ラベル: '{self.current_selected_annotation.label}') を削除しますか？",  
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
            )  
            if reply == QMessageBox.StandardButton.Yes:  
                self.delete_single_annotation_requested.emit(self.current_selected_annotation)  
                self.current_selected_annotation = None # 削除後、選択状態をクリア  
                self.update_selected_annotation_info(None) # UIをリセット
