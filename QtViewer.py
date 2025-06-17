import sys  
import json  
import cv2  
import numpy as np  
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,   
                            QWidget, QPushButton, QLabel, QSlider, QFileDialog,   
                            QMessageBox, QComboBox, QSpinBox, QCheckBox)  
from PyQt6.QtCore import Qt, QTimer, pyqtSignal  
from PyQt6.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QFont  
import os  
  
class VideoAnnotationViewer(QMainWindow):  
    def __init__(self):  
        super().__init__()  
        self.setWindowTitle("MASA Video Annotation Viewer")  
        self.setGeometry(100, 100, 1200, 800)  
          
        # データ管理  
        self.video_path = None  
        self.json_data = []  
        self.current_frame = 0  
        self.total_frames = 0  
        self.cap = None  
        self.timer = QTimer()  
        self.timer.timeout.connect(self.update_frame)  
        self.is_playing = False  
          
        # 表示設定  
        self.show_track_ids = True  
        self.show_scores = True  
        self.score_threshold = 0.2  
        self.line_width = 3  
          
        self.init_ui()  
          
    def init_ui(self):  
        central_widget = QWidget()  
        self.setCentralWidget(central_widget)  
          
        # メインレイアウト  
        main_layout = QVBoxLayout(central_widget)  
          
        # コントロールパネル  
        control_layout = QHBoxLayout()  
          
        # ファイル読み込みボタン  
        self.load_video_btn = QPushButton("動画を読み込み")  
        self.load_video_btn.clicked.connect(self.load_video)  
        control_layout.addWidget(self.load_video_btn)  
          
        self.load_json_btn = QPushButton("JSONを読み込み")  
        self.load_json_btn.clicked.connect(self.load_json)  
        control_layout.addWidget(self.load_json_btn)  
          
        # 再生コントロール  
        self.play_btn = QPushButton("再生")  
        self.play_btn.clicked.connect(self.toggle_play)  
        self.play_btn.setEnabled(False)  
        control_layout.addWidget(self.play_btn)  
          
        # フレーム情報  
        self.frame_label = QLabel("フレーム: 0/0")  
        control_layout.addWidget(self.frame_label)  
          
        control_layout.addStretch()  
        main_layout.addLayout(control_layout)  
          
        # 表示設定パネル  
        settings_layout = QHBoxLayout()  
          
        # Track ID表示チェックボックス  
        self.track_id_cb = QCheckBox("Track ID表示")  
        self.track_id_cb.setChecked(True)  
        self.track_id_cb.stateChanged.connect(self.update_display_settings)  
        settings_layout.addWidget(self.track_id_cb)  
          
        # スコア表示チェックボックス  
        self.score_cb = QCheckBox("スコア表示")  
        self.score_cb.setChecked(True)  
        self.score_cb.stateChanged.connect(self.update_display_settings)  
        settings_layout.addWidget(self.score_cb)  
          
        # スコア閾値設定  
        settings_layout.addWidget(QLabel("スコア閾値:"))  
        self.score_threshold_spin = QSpinBox()  
        self.score_threshold_spin.setRange(0, 100)  
        self.score_threshold_spin.setValue(20)  
        self.score_threshold_spin.setSuffix("%")  
        self.score_threshold_spin.valueChanged.connect(self.update_display_settings)  
        settings_layout.addWidget(self.score_threshold_spin)  
          
        # 線の太さ設定  
        settings_layout.addWidget(QLabel("線の太さ:"))  
        self.line_width_spin = QSpinBox()  
        self.line_width_spin.setRange(1, 10)  
        self.line_width_spin.setValue(3)  
        self.line_width_spin.valueChanged.connect(self.update_display_settings)  
        settings_layout.addWidget(self.line_width_spin)  
          
        settings_layout.addStretch()  
        main_layout.addLayout(settings_layout)  
          
        # 動画表示エリア  
        self.video_label = QLabel()  
        self.video_label.setMinimumSize(800, 600)  
        self.video_label.setStyleSheet("border: 1px solid black")  
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  
        self.video_label.setText("動画とJSONファイルを読み込んでください")  
        main_layout.addWidget(self.video_label)  
          
        # フレームスライダー  
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)  
        self.frame_slider.setEnabled(False)  
        self.frame_slider.valueChanged.connect(self.seek_frame)  
        main_layout.addWidget(self.frame_slider)  
          
    def load_video(self):  
        """動画ファイルを読み込み"""  
        file_path, _ = QFileDialog.getOpenFileName(  
            self, "動画ファイルを選択", "",   
            "Video Files (*.mp4 *.avi *.mov *.mkv)"  
        )  
          
        if file_path:  
            self.video_path = file_path  
            self.cap = cv2.VideoCapture(file_path)  
              
            if not self.cap.isOpened():  
                QMessageBox.warning(self, "エラー", "動画ファイルを開けませんでした")  
                return  
                  
            self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))  
            self.frame_slider.setMaximum(self.total_frames - 1)  
            self.frame_slider.setEnabled(True)  
            self.play_btn.setEnabled(True)  
              
            self.current_frame = 0  
            self.update_frame_display()  
              
    def load_json(self):  
        """JSONファイルを読み込み"""  
        file_path, _ = QFileDialog.getOpenFileName(  
            self, "JSONファイルを選択", "",   
            "JSON Files (*.json)"  
        )  
          
        if file_path:  
            try:  
                with open(file_path, 'r', encoding='utf-8') as f:  
                    self.json_data = json.load(f)  
                QMessageBox.information(self, "成功", f"{len(self.json_data)}件のアノテーションを読み込みました")  
                self.update_frame_display()  
            except Exception as e:  
                QMessageBox.warning(self, "エラー", f"JSONファイルの読み込みに失敗しました: {str(e)}")  
      
    def update_display_settings(self):  
        """表示設定を更新"""  
        self.show_track_ids = self.track_id_cb.isChecked()  
        self.show_scores = self.score_cb.isChecked()  
        self.score_threshold = self.score_threshold_spin.value() / 100.0  
        self.line_width = self.line_width_spin.value()  
        self.update_frame_display()  
      
    def get_frame_annotations(self, frame_id):  
        """指定フレームのアノテーションを取得"""  
        annotations = []  
        for item in self.json_data:  
            if item.get('frame_id') == frame_id:  
                if item.get('score', 0) >= self.score_threshold:  
                    annotations.append(item)  
        return annotations  
      
    def draw_annotations(self, frame, annotations):  
        """フレームにアノテーションを描画"""  
        if not annotations:  
            return frame  
              
        # MASAの可視化ロジックを参考にした色生成  
        def get_track_color(track_id):  
            """Track IDに基づいて色を生成"""  
            np.random.seed(track_id)  
            return tuple(np.random.randint(0, 255, 3).tolist())  
          
        height, width = frame.shape[:2]  
          
        for ann in annotations:  
            track_id = ann.get('track_id', 0)  
            bbox = ann.get('bbox', [])  
            score = ann.get('score', 0)  
            label = ann.get('label', 0)  
              
            if len(bbox) != 4:  
                continue  
                  
            # xyxy形式として解釈（修正箇所）  
            x1, y1, x2, y2 = bbox  
            x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
            # 色を取得  
            color = get_track_color(track_id)  
              
            # バウンディングボックスを描画  
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, self.line_width)  
              
            # ラベルテキストを構築  
            label_text = f"class {label}"  
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
              
            # テキスト背景の矩形  
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
              
            # テキストを描画  
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
              
        # アノテーションを取得して描画  
        annotations = self.get_frame_annotations(self.current_frame)  
        frame_with_annotations = self.draw_annotations(frame.copy(), annotations)  
          
        # フレームをQtで表示可能な形式に変換  
        rgb_frame = cv2.cvtColor(frame_with_annotations, cv2.COLOR_BGR2RGB)  
        h, w, ch = rgb_frame.shape  
        bytes_per_line = ch * w  
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)  
          
        # ラベルサイズに合わせてスケール  
        label_size = self.video_label.size()  
        scaled_pixmap = QPixmap.fromImage(qt_image).scaled(  
            label_size, Qt.AspectRatioMode.KeepAspectRatio,   
            Qt.TransformationMode.SmoothTransformation  
        )  
          
        self.video_label.setPixmap(scaled_pixmap)  
          
        # フレーム情報を更新  
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
  
def main():  
    app = QApplication(sys.argv)  
    viewer = VideoAnnotationViewer()  
    viewer.show()  
    sys.exit(app.exec())  
  
if __name__ == '__main__':  
    main()