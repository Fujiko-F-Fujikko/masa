import sys  
import json  
import cv2  
import numpy as np  
import argparse  
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,   
                            QWidget, QPushButton, QLabel, QSlider, QFileDialog,   
                            QMessageBox, QComboBox, QSpinBox, QCheckBox, QLineEdit,  
                            QGroupBox, QFormLayout)  
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint  
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont, QKeySequence, QShortcut  
import os  
  
class VideoAnnotationViewer(QMainWindow):  
    def __init__(self):  
        super().__init__()  
        self.setWindowTitle("MASA Video Annotation Viewer with Editor")  
        self.setGeometry(100, 100, 1400, 900)  
          
        # データ管理  
        self.video_path = None  
        self.json_data = []  
        self.label_mapping = {}  
        self.video_name = ""  
        self.current_frame = 0  
        self.total_frames = 0  
        self.cap = None  
        self.timer = QTimer()  
        self.timer.timeout.connect(self.update_frame)  
        self.is_playing = False
        self.original_bbox = None  # リサイズ時の元のbbox保存用
          
        # 表示設定  
        self.show_track_ids = True  
        self.show_scores = True  
        self.score_threshold = 0.2  
        self.line_width = 3
        self.resize_handle_size = 10  # リサイズハンドルの大きさ
          
        # 編集機能  
        self.editing_mode = False  
        self.selected_annotation = None  
        self.drag_start = None  
        self.resize_handle = None  
        self.is_dragging = False  
          
        self.init_ui()  
        self.setup_shortcuts()  
          
    def init_ui(self):  
        central_widget = QWidget()  
        self.setCentralWidget(central_widget)  
          
        # メインレイアウト  
        main_layout = QHBoxLayout(central_widget)  
          
        # 左側パネル（コントロール）  
        left_panel = QWidget()  
        left_panel.setMaximumWidth(350)  
        left_layout = QVBoxLayout(left_panel)  
          
        # ファイル読み込みグループ  
        file_group = QGroupBox("ファイル読み込み")  
        file_layout = QVBoxLayout(file_group)  
          
        self.load_video_btn = QPushButton("動画を読み込み")  
        self.load_video_btn.clicked.connect(self.load_video)  
        file_layout.addWidget(self.load_video_btn)  
          
        self.load_json_btn = QPushButton("JSONを読み込み")  
        self.load_json_btn.clicked.connect(self.load_json)  
        file_layout.addWidget(self.load_json_btn)  
          
        left_layout.addWidget(file_group)  
          
        # 再生コントロールグループ  
        playback_group = QGroupBox("再生コントロール")  
        playback_layout = QVBoxLayout(playback_group)  
          
        playback_controls = QHBoxLayout()  
        self.play_btn = QPushButton("再生")  
        self.play_btn.clicked.connect(self.toggle_play)  
        self.play_btn.setEnabled(False)  
        playback_controls.addWidget(self.play_btn)  
          
        self.frame_label = QLabel("フレーム: 0/0")  
        playback_controls.addWidget(self.frame_label)  
        playback_layout.addLayout(playback_controls)  
          
        left_layout.addWidget(playback_group)  
          
        # 表示設定グループ  
        display_group = QGroupBox("表示設定")  
        display_layout = QFormLayout(display_group)  
          
        self.track_id_cb = QCheckBox()  
        self.track_id_cb.setChecked(True)  
        self.track_id_cb.stateChanged.connect(self.update_display_settings)  
        display_layout.addRow("Track ID表示:", self.track_id_cb)  
          
        self.score_cb = QCheckBox()  
        self.score_cb.setChecked(True)  
        self.score_cb.stateChanged.connect(self.update_display_settings)  
        display_layout.addRow("スコア表示:", self.score_cb)  
          
        self.score_threshold_spin = QSpinBox()  
        self.score_threshold_spin.setRange(0, 100)  
        self.score_threshold_spin.setValue(20)  
        self.score_threshold_spin.setSuffix("%")  
        self.score_threshold_spin.valueChanged.connect(self.update_display_settings)  
        display_layout.addRow("スコア閾値:", self.score_threshold_spin)  
          
        self.line_width_spin = QSpinBox()  
        self.line_width_spin.setRange(1, 10)  
        self.line_width_spin.setValue(3)  
        self.line_width_spin.valueChanged.connect(self.update_display_settings)  
        display_layout.addRow("線の太さ:", self.line_width_spin)  
        
        self.resize_handle_size_spin = QSpinBox()
        self.resize_handle_size_spin.setRange(5, 20)
        self.resize_handle_size_spin.setValue(10)
        self.resize_handle_size_spin.setSuffix("px")
        self.resize_handle_size_spin.valueChanged.connect(self.update_display_settings)
        display_layout.addRow("ハンドルサイズ:", self.resize_handle_size_spin)
          
        left_layout.addWidget(display_group)  
          
        # 編集機能グループ  
        edit_group = QGroupBox("編集機能")  
        edit_layout = QFormLayout(edit_group)  
          
        self.edit_mode_cb = QCheckBox()  
        self.edit_mode_cb.stateChanged.connect(self.toggle_edit_mode)  
        edit_layout.addRow("編集モード:", self.edit_mode_cb)  
          
        self.label_combo = QComboBox()  
        self.label_combo.setEnabled(False)  
        self.label_combo.currentTextChanged.connect(self.change_selected_label)  
        edit_layout.addRow("ラベル:", self.label_combo)  
          
        self.track_id_edit = QLineEdit()  
        self.track_id_edit.setEnabled(False)  
        self.track_id_edit.returnPressed.connect(self.change_track_id)  
        edit_layout.addRow("Track ID:", self.track_id_edit)  
          
        # 編集ボタン  
        edit_buttons = QVBoxLayout()  
          
        self.add_annotation_btn = QPushButton("アノテーション追加 (N)")  
        self.add_annotation_btn.clicked.connect(self.add_new_annotation)  
        self.add_annotation_btn.setEnabled(False)  
        edit_buttons.addWidget(self.add_annotation_btn)  
          
        self.delete_annotation_btn = QPushButton("選択削除 (Del)")  
        self.delete_annotation_btn.clicked.connect(self.delete_selected_annotation)  
        self.delete_annotation_btn.setEnabled(False)  
        edit_buttons.addWidget(self.delete_annotation_btn)  
          
        edit_layout.addRow("操作:", edit_buttons)  
          
        left_layout.addWidget(edit_group)  
          
        # 保存グループ  
        save_group = QGroupBox("保存")  
        save_layout = QVBoxLayout(save_group)  
          
        self.save_btn = QPushButton("修正結果を保存")  
        self.save_btn.clicked.connect(self.save_modifications)  
        self.save_btn.setEnabled(False)  
        save_layout.addWidget(self.save_btn)  
          
        left_layout.addWidget(save_group)  
          
        left_layout.addStretch()  
        main_layout.addWidget(left_panel)
        # 右側パネル（動画表示）  
        right_panel = QWidget()  
        right_layout = QVBoxLayout(right_panel)  
          
        # 動画表示エリア  
        self.video_label = QLabel()  
        self.video_label.setMinimumSize(800, 600)  
        self.video_label.setStyleSheet("border: 2px solid black; background-color: #f0f0f0;")  
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        self.video_label.setText("動画とJSONファイルを読み込んでください")  
        self.video_label.setScaledContents(False)  
        right_layout.addWidget(self.video_label)  
          
        # フレームスライダー  
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)  
        self.frame_slider.setEnabled(False)  
        self.frame_slider.valueChanged.connect(self.seek_frame)  
        right_layout.addWidget(self.frame_slider)  
          
        # 選択情報表示  
        self.selection_info = QLabel("選択: なし")  
        self.selection_info.setStyleSheet("padding: 5px; background-color: #e0e0e0;")  
        right_layout.addWidget(self.selection_info)  
          
        main_layout.addWidget(right_panel)  
          
    def setup_shortcuts(self):  
        """キーボードショートカットを設定"""  
        delete_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)  
        delete_shortcut.activated.connect(self.delete_selected_annotation)  
          
        add_shortcut = QShortcut(QKeySequence(Qt.Key.Key_N), self)  
        add_shortcut.activated.connect(self.add_new_annotation)  
          
        play_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Space), self)  
        play_shortcut.activated.connect(self.toggle_play)  
          
    def load_video_file(self, file_path):
        """指定されたパスの動画ファイルを読み込み"""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "エラー", f"動画ファイルが見つかりません: {file_path}")
            return False

        self.video_path = file_path
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(file_path)

        if not self.cap.isOpened():
            QMessageBox.warning(self, "エラー", "動画ファイルを開けませんでした")
            return False

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_slider.setMaximum(self.total_frames - 1)
        self.frame_slider.setEnabled(True)
        self.play_btn.setEnabled(True)

        self.current_frame = 0
        self.update_frame_display()
        return True

    def load_video(self):
        """動画ファイルを読み込み"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "動画ファイルを選択", "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.wmv)"
        )

        if file_path:
            self.load_video_file(file_path)
              
    def load_json_file(self, file_path):
        """指定されたパスのJSONファイルを読み込み"""
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "エラー", f"JSONファイルが見つかりません: {file_path}")
            return False

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if isinstance(data, dict) and 'annotations' in data:
                self.json_data = data['annotations']
                self.label_mapping = data.get('label_mapping', {})
                self.video_name = data.get('video_name', "")
            else:
                self.json_data = data
                self.label_mapping = {}
                self.video_name = ""

            self.update_label_combo()
            self.save_btn.setEnabled(True)
            print(f"JSONファイルを読み込みました: {len(self.json_data)}件のアノテーション")
            self.update_frame_display()
            return True
        except Exception as e:
            QMessageBox.warning(self, "エラー", f"JSONファイルの読み込みに失敗しました: {str(e)}")
            return False

    def load_json(self):
        """JSONファイルを読み込み"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "JSONファイルを選択", "",
            "JSON Files (*.json)"
        )

        if file_path:
            if self.load_json_file(file_path):
                QMessageBox.information(self, "成功", f"{len(self.json_data)}件のアノテーションを読み込みました")
      
    def update_display_settings(self):  
        """表示設定を更新"""  
        self.show_track_ids = self.track_id_cb.isChecked()  
        self.show_scores = self.score_cb.isChecked()  
        self.score_threshold = self.score_threshold_spin.value() / 100.0  
        self.line_width = self.line_width_spin.value()
        self.resize_handle_size = self.resize_handle_size_spin.value()
        self.update_frame_display()  
      
    def toggle_edit_mode(self, state):  
        """編集モードの切り替え"""  
        self.editing_mode = state == Qt.CheckState.Checked.value  
        self.label_combo.setEnabled(self.editing_mode)  
        self.track_id_edit.setEnabled(self.editing_mode)  
        self.add_annotation_btn.setEnabled(self.editing_mode)  
        self.delete_annotation_btn.setEnabled(self.editing_mode and self.selected_annotation is not None)  
          
        if not self.editing_mode:  
            self.selected_annotation = None  
            self.update_selection_info()  
            self.update_frame_display()  
      
    def update_label_combo(self):  
        """ラベルコンボボックスを更新"""  
        self.label_combo.clear()  
        if self.label_mapping:  
            for label_id, label_name in self.label_mapping.items():  
                self.label_combo.addItem(label_name, int(label_id))  
        else:  
            default_labels = ["person", "car", "truck", "bus", "motorcycle", "bicycle"]  
            for i, label in enumerate(default_labels):  
                self.label_combo.addItem(label, i)  
      
    def get_frame_annotations(self, frame_id):  
        """指定フレームのアノテーションを取得"""  
        annotations = []  
        for item in self.json_data:  
            if item.get('frame_id') == frame_id:  
                if item.get('score', 0) >= self.score_threshold:  
                    annotations.append(item)  
          
        # デバッグ用出力  
        print(f"フレーム {frame_id} のアノテーション数: {len(annotations)}")  
        for ann in annotations:  
            print(f"  Track ID: {ann.get('track_id')}, bbox: {ann.get('bbox')}")  
          
        return annotations
      
    def draw_annotations(self, frame, annotations):  
        """フレームにアノテーションを描画"""  
        if not annotations:  
            return frame  
              
        def get_track_color(track_id):  
            np.random.seed(track_id)  
            return tuple(np.random.randint(0, 255, 3).tolist())  
          
        for ann in annotations:  
            track_id = ann.get('track_id', 0)  
            bbox = ann.get('bbox', [])  
            score = ann.get('score', 0)  
            label_id = ann.get('label', 0)  
            label_name = ann.get('label_name', None)  
              
            if len(bbox) != 4:  
                continue  
                  
            # xywh形式として解釈
            x, y, w, h = bbox  
            x1, y1 = int(x), int(y)  
            x2, y2 = int(x + w), int(y + h)  
            
            color = get_track_color(track_id)  
              
            # 選択されたアノテーションは太い線で描画  
            line_width = self.line_width * 2 if ann == self.selected_annotation else self.line_width  
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, line_width)  
            if ann == self.selected_annotation:
                # 外側に太い枠線を追加  
                offset = line_width * 2
                cv2.rectangle(frame, (x1-offset, y1-offset), (x2+offset, y2+offset), (0, 255, 255), line_width * 2)  # 黄色の外枠
                
                # リサイズハンドルを描画
                handles = [
                    (x1, y1),      # top_left
                    (x2, y1),      # top_right
                    (x1, y2),      # bottom_left
                    (x2, y2)       # bottom_right
                ]
                
                for hx, hy in handles:
                    # 白い四角を描画
                    cv2.rectangle(frame, 
                                (int(hx - self.resize_handle_size), int(hy - self.resize_handle_size)),
                                (int(hx + self.resize_handle_size), int(hy + self.resize_handle_size)),
                                (255, 255, 255), -1)
                    # 黒い枠線を描画
                    cv2.rectangle(frame,
                                (int(hx - self.resize_handle_size), int(hy - self.resize_handle_size)),
                                (int(hx + self.resize_handle_size), int(hy + self.resize_handle_size)),
                                (0, 0, 0), 1)
            
            # ラベルテキストを構築  
            if label_name:  
                label_text = label_name  
            elif hasattr(self, 'label_mapping') and str(label_id) in self.label_mapping:  
                label_text = self.label_mapping[str(label_id)]  
            else:  
                label_text = f"class {label_id}"  
                  
            if self.show_track_ids:  
                label_text += f" | {track_id}"  
            if self.show_scores:  
                label_text += f": {score:.1%}"  
              
            # テキスト背景を描画  
            font = cv2.FONT_HERSHEY_SIMPLEX  
            font_scale = 0.6  
            thickness = 2  
            (text_width, text_height), baseline = cv2.getTextSize(  
                label_text, font, font_scale, thickness  
            )  
              
            text_x = x1  
            text_y = y1 - text_height - 5  
            if text_y < 0:  
                text_y = y1 + text_height + 5  
                  
            cv2.rectangle(  
                frame,   
                (text_x, text_y - text_height - 5),   
                (text_x + text_width, text_y + 5),   
                color,   
                -1  
            )  
              
            cv2.putText(  
                frame, label_text, (text_x, text_y),   
                font, font_scale, (0, 0, 0), thickness  
            )  
          
        return frame
    def update_frame_display(self):  
        """現在のフレームを表示"""  
        if not self.cap:  
            return  
              
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame)  
        ret, frame = self.cap.read()  
          
        if not ret:  
            return  
              
        annotations = self.get_frame_annotations(self.current_frame)  
        frame_with_annotations = self.draw_annotations(frame.copy(), annotations)  
          
        rgb_frame = cv2.cvtColor(frame_with_annotations, cv2.COLOR_BGR2RGB)  
        h, w, ch = rgb_frame.shape  
        bytes_per_line = ch * w  
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)  
          
        label_size = self.video_label.size()  
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(  
            label_size, Qt.AspectRatioMode.KeepAspectRatio,   
            Qt.TransformationMode.SmoothTransformation  
        )  
          
        self.video_label.setPixmap(scaled_pixmap)  
          
        self.frame_label.setText(f"フレーム: {self.current_frame + 1}/{self.total_frames}")  
        self.frame_slider.setValue(self.current_frame)  
      
    def seek_frame(self, frame_number):  
        """指定フレームにシーク"""  
        self.current_frame = frame_number  
        self.update_frame_display()  
      
    def toggle_play(self):  
        """再生/停止を切り替え"""  
        if self.is_playing:  
            self.timer.stop()  
            self.play_btn.setText("再生")  
            self.is_playing = False  
        else:  
            self.timer.start(33)  # 約30fps  
            self.play_btn.setText("停止")  
            self.is_playing = True  
      
    def update_frame(self):  
        """タイマーによるフレーム更新"""  
        if self.current_frame < self.total_frames - 1:  
            self.current_frame += 1  
            self.update_frame_display()  
        else:  
            self.toggle_play()  # 最後のフレームで停止  
      
    def get_resize_handle(self, bbox, click_x, click_y):
        """クリック位置がリサイズハンドルにあるかを判定"""
        x, y, w, h = bbox
        x1, y1 = x, y
        x2, y2 = x + w, y + h
        
        handles = {
            'top_left': (x1, y1),
            'top_right': (x2, y1),
            'bottom_left': (x1, y2),
            'bottom_right': (x2, y2)
        }
        
        for handle_name, (hx, hy) in handles.items():
            if (hx - self.resize_handle_size <= click_x <= hx + self.resize_handle_size and 
                hy - self.resize_handle_size <= click_y <= hy + self.resize_handle_size):
                return handle_name
        
        return None

    def mousePressEvent(self, event):  
        """マウスクリックイベントの処理"""  
        if not self.editing_mode:  
            return  
              
        pos = self.video_label.mapFromGlobal(event.globalPosition().toPoint())  
        frame_annotations = self.get_frame_annotations(self.current_frame)  
          
        if not self.cap or not frame_annotations:  
            return  
          
        # 実際のフレームサイズを取得  
        frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))  
        frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  
          
        # 表示されているピクスマップのサイズを取得  
        pixmap = self.video_label.pixmap()  
        if not pixmap:  
            return  
              
        pixmap_size = pixmap.size()  
        label_size = self.video_label.size()  
          
        # スケール計算（アスペクト比を考慮）  
        scale_x = frame_width / pixmap_size.width()  
        scale_y = frame_height / pixmap_size.height()  
          
        # ラベル内でのピクスマップの位置を計算  
        offset_x = (label_size.width() - pixmap_size.width()) // 2  
        offset_y = (label_size.height() - pixmap_size.height()) // 2  
          
        # クリック位置をピクスマップ座標に変換  
        pixmap_x = pos.x() - offset_x  
        pixmap_y = pos.y() - offset_y  
          
        # 範囲チェック  
        if pixmap_x < 0 or pixmap_y < 0 or pixmap_x >= pixmap_size.width() or pixmap_y >= pixmap_size.height():  
            return  
          
        # 実際のフレーム座標に変換  
        actual_x = pixmap_x * scale_x  
        actual_y = pixmap_y * scale_y  
          
        print(f"実際の座標: {actual_x}, {actual_y}")  
          
        # クリックされたアノテーションを検索  
        for ann in frame_annotations:  
            bbox = ann.get('bbox', [])  
            if len(bbox) != 4:  
                continue  
                  
            # xywh形式として解釈（JSONで変換済み）  
            x, y, w, h = bbox  
            x1, y1 = x, y  
            x2, y2 = x + w, y + h  
              
            print(f"チェック中のbbox: {x1}, {y1}, {x2}, {y2}")  
              
            if x1 <= actual_x <= x2 and y1 <= actual_y <= y2:  
                self.selected_annotation = ann
                
                # リサイズハンドルの判定
                self.resize_handle = self.get_resize_handle(bbox, actual_x, actual_y)
                
                if self.resize_handle:
                    # リサイズモード
                    self.drag_start = QPoint(int(actual_x), int(actual_y))
                    self.original_bbox = bbox.copy()  # 元のbboxを保存
                else:
                    # 移動モード
                    self.drag_start = QPoint(int(actual_x), int(actual_y))
                
                self.update_selection_info()  
                self.update_frame_display()  
                print(f"アノテーション選択: Track ID {ann.get('track_id')}")  
                return  
          
        # 何も選択されなかった場合  
        self.selected_annotation = None  
        self.update_selection_info()  
        self.update_frame_display()  
        print("アノテーションが選択されませんでした")
      
    def resize_bbox(self, current_x, current_y):
        """バウンディングボックスのリサイズ処理"""
        if not self.resize_handle or not hasattr(self, 'original_bbox'):
            return
        
        bbox = self.selected_annotation['bbox']
        orig_x, orig_y, orig_w, orig_h = self.original_bbox
        
        if self.resize_handle == 'top_left':
            # 左上角のリサイズ
            dx = current_x - orig_x
            dy = current_y - orig_y
            new_w = orig_w - dx
            new_h = orig_h - dy
            if new_w > 10 and new_h > 10:  # 最小サイズ制限
                bbox[0] = current_x
                bbox[1] = current_y
                bbox[2] = new_w
                bbox[3] = new_h
            
        elif self.resize_handle == 'top_right':
            # 右上角のリサイズ
            dy = current_y - orig_y
            new_w = current_x - orig_x
            new_h = orig_h - dy
            if new_w > 10 and new_h > 10:
                bbox[1] = current_y
                bbox[2] = new_w
                bbox[3] = new_h
            
        elif self.resize_handle == 'bottom_left':
            # 左下角のリサイズ
            dx = current_x - orig_x
            new_w = orig_w - dx
            new_h = current_y - orig_y
            if new_w > 10 and new_h > 10:
                bbox[0] = current_x
                bbox[2] = new_w
                bbox[3] = new_h
            
        elif self.resize_handle == 'bottom_right':
            # 右下角のリサイズ
            new_w = current_x - orig_x
            new_h = current_y - orig_y
            if new_w > 10 and new_h > 10:
                bbox[2] = new_w
                bbox[3] = new_h

    def mouseMoveEvent(self, event):  
        """マウス移動イベントの処理"""  
        if not self.editing_mode or not self.selected_annotation or not self.drag_start:  
            return  
              
        pos = self.video_label.mapFromGlobal(event.globalPosition().toPoint())  
          
        if self.cap:  
            frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))  
            frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))  
            
            pixmap = self.video_label.pixmap()
            if not pixmap:
                return
                
            pixmap_size = pixmap.size()
            label_size = self.video_label.size()  
              
            scale_x = frame_width / pixmap_size.width()  
            scale_y = frame_height / pixmap_size.height()  
            
            offset_x = (label_size.width() - pixmap_size.width()) // 2
            offset_y = (label_size.height() - pixmap_size.height()) // 2
            
            pixmap_x = pos.x() - offset_x
            pixmap_y = pos.y() - offset_y
            
            if pixmap_x < 0 or pixmap_y < 0 or pixmap_x >= pixmap_size.width() or pixmap_y >= pixmap_size.height():
                return
            
            actual_x = pixmap_x * scale_x
            actual_y = pixmap_y * scale_y
              
            if self.resize_handle:
                # リサイズモード
                self.resize_bbox(actual_x, actual_y)
            else:
                # 移動モード
                dx = actual_x - self.drag_start.x()  
                dy = actual_y - self.drag_start.y()  
                  
                bbox = self.selected_annotation['bbox']  
                bbox[0] += dx  
                bbox[1] += dy  
              
            self.drag_start = QPoint(int(actual_x), int(actual_y))  
            self.update_frame_display()
      
    def update_selection_info(self):  
        """選択情報を更新"""  
        if self.selected_annotation:  
            track_id = self.selected_annotation.get('track_id', 0)  
            label_name = self.selected_annotation.get('label_name', 'unknown')  
            score = self.selected_annotation.get('score', 0)  
            self.selection_info.setText(f"選択: Track ID {track_id}, {label_name}, Score: {score:.2f}")  
              
            # Track ID編集フィールドを更新  
            self.track_id_edit.setText(str(track_id))  
              
            # ラベルコンボボックスを更新  
            label_id = self.selected_annotation.get('label', 0)  
            index = self.label_combo.findData(label_id)  
            if index >= 0:  
                self.label_combo.setCurrentIndex(index)  
                  
            self.delete_annotation_btn.setEnabled(True)  
        else:  
            self.selection_info.setText("選択: なし")  
            self.track_id_edit.clear()  
            self.delete_annotation_btn.setEnabled(False)  
      
    def change_selected_label(self):  
        """選択されたアノテーションのラベルを変更"""  
        if not self.selected_annotation:  
            return  
              
        new_label_id = self.label_combo.currentData()  
        new_label_name = self.label_combo.currentText()  
          
        # デバッグ用出力  
        print(f"ラベル変更: ID={new_label_id}, Name={new_label_name}")  
          
        # アノテーションのラベルを更新  
        if new_label_id is not None:  
            self.selected_annotation['label'] = new_label_id  
            self.selected_annotation['label_name'] = new_label_name  
            self.update_selection_info()  
            self.update_frame_display()  
      
    def change_track_id(self):  
        """Track IDを変更"""  
        if not self.selected_annotation:  
            return  
              
        try:  
            new_track_id = int(self.track_id_edit.text())  
            self.selected_annotation['track_id'] = new_track_id  
            self.update_selection_info()  
            self.update_frame_display()  
        except ValueError:  
            QMessageBox.warning(self, "エラー", "有効な数値を入力してください")
    def manage_track_ids(self):  
        """Track IDの管理と一貫性保持"""  
        all_track_ids = set()  
        for ann in self.json_data:  
            all_track_ids.add(ann.get('track_id', 0))  
          
        return max(all_track_ids) + 1 if all_track_ids else 1  
      
    def add_new_annotation(self):  
        """新しいアノテーションを追加"""  
        if not self.editing_mode:  
            return  
              
        # 現在選択されているラベルを取得
        current_label_id = self.label_combo.currentData() if self.label_combo.currentData() is not None else 0
        current_label_name = self.label_combo.currentText() if self.label_combo.currentText() else "new_object"
        
        new_annotation = {  
            "frame_id": self.current_frame,  
            "track_id": self.manage_track_ids(),  
            "bbox": [100, 100, 300, 300],  # デフォルトサイズ（xyxy形式）  
            "score": 1.0,  
            "label": current_label_id,  # 現在選択されているラベルを使用
            "label_name": current_label_name  # 現在選択されているラベル名を使用
        }  
        self.json_data.append(new_annotation)  
        self.selected_annotation = new_annotation  
        self.update_selection_info()  
        self.update_frame_display()  
      
    def delete_selected_annotation(self):  
        """選択されたアノテーションを削除"""  
        if not self.selected_annotation:  
            return  
              
        if self.selected_annotation in self.json_data:  
            self.json_data.remove(self.selected_annotation)  
            self.selected_annotation = None  
            self.update_selection_info()  
            self.update_frame_display()  
      
    def save_modifications(self):  
        """修正結果をJSONファイルに保存"""  
        if not self.json_data:  
            QMessageBox.warning(self, "エラー", "保存するデータがありません")  
            return  
          
        file_path, _ = QFileDialog.getSaveFileName(  
            self, "修正結果を保存", "", "JSON Files (*.json)"  
        )  
          
        if file_path:  
            try:  
                # MASA形式との互換性を維持  
                result_data = {  
                    "annotations": self.json_data,  
                    "label_mapping": self.label_mapping,  
                    "video_name": self.video_name  
                }  
                  
                with open(file_path, 'w', encoding='utf-8') as f:  
                    json.dump(result_data, f, indent=2, ensure_ascii=False)  
                      
                QMessageBox.information(self, "成功", f"修正結果を保存しました: {file_path}")  
            except Exception as e:  
                QMessageBox.warning(self, "エラー", f"保存に失敗しました: {str(e)}")  
      
    def assign_new_track_id(self, annotation):  
        """新しいtrack_idを割り当て"""  
        new_id = self.manage_track_ids()  
        annotation['track_id'] = new_id  
        return new_id  
      
    def mouseReleaseEvent(self, event):
        """マウスボタンリリースイベントの処理"""
        if self.editing_mode and self.resize_handle:
            # リサイズ完了時の処理
            self.resize_handle = None
            if hasattr(self, 'original_bbox'):
                delattr(self, 'original_bbox')
            self.update_frame_display()

    def merge_track_ids(self, source_id, target_id):  
        """Track IDをマージ"""  
        for ann in self.json_data:  
            if ann.get('track_id') == source_id:  
                ann['track_id'] = target_id  
      
    def closeEvent(self, event):  
        """アプリケーション終了時の処理"""  
        if self.cap:  
            self.cap.release()  
        event.accept()  
  
def parse_args():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(description='MASA Video Annotation Viewer with Editor')
    parser.add_argument('--video', type=str, help='Video file path')
    parser.add_argument('--json', type=str, help='JSON annotation file path')
    return parser.parse_args()

def main():  
    app = QApplication(sys.argv)  
    
    # コマンド引数を解析
    args = parse_args()
    
    viewer = VideoAnnotationViewer()
    
    # コマンド引数でファイルが指定されている場合は自動読み込み
    if args.video:
        viewer.load_video_file(args.video)
    
    if args.json:
        viewer.load_json_file(args.json)
    
    viewer.show()  
    sys.exit(app.exec())  
  
if __name__ == '__main__':  
    main()
