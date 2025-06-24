import os  
import json  
import cv2  
import numpy as np  
from PyQt6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout,   
                            QWidget, QPushButton, QLabel, QSlider, QFileDialog,   
                            QMessageBox, QComboBox, QSpinBox, QCheckBox, QLineEdit,  
                            QGroupBox, QFormLayout, QSizePolicy, QListWidget, QDoubleSpinBox, QTabWidget)  
from PyQt6.QtCore import Qt, QTimer, QPoint  
from PyQt6.QtGui import QPixmap, QImage, QKeySequence, QShortcut  

class VideoAnnotationViewerWindow(QMainWindow):  
    def __init__(self):  
        super().__init__()  
        self.setWindowTitle("MASA Video Annotation Viewer with Editor")  
        self.setGeometry(100, 100, 2000, 1200) # ウィンドウサイズを拡張  
          
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
          
        # 表示設定  
        self.show_track_ids = True  
        self.show_scores = True  
        self.score_threshold = 0.2  
        self.line_width = 3  
        self.resize_handle_size = 10  
          
        # 編集機能  
        self.editing_mode = False  
        self.selected_annotation = None  
        self.drag_start = None  
        self.resize_handle = None  
        self.is_dragging = False  
  
        # カルマンフィルタパラメータ  
        self.kalman_process_noise_pos = 1.0  
        self.kalman_process_noise_vel = 5.0  
        self.kalman_observation_noise = 2.0  
        self.kalman_velocity_factor = 1.2  
        self.kalman_pos_uncertainty = 5.0  
        self.kalman_vel_uncertainty = 10.0  
          
        # 制御点管理  
        self.control_points = []  
          
        self.init_ui()  
        self.setup_shortcuts()  
          
    def init_ui(self):  
        central_widget = QWidget()  
        self.setCentralWidget(central_widget)  
          
        # メインレイアウト  
        main_layout = QHBoxLayout(central_widget)  
          
        # 左側パネル（コントロール）  
        left_panel = QWidget()  
        left_panel.setMaximumWidth(300) # 幅を拡張  
        left_layout = QVBoxLayout(left_panel)  
          
        # タブウィジェットを作成  
        tab_widget = QTabWidget()  
          
        # --- 1. 基本設定タブ ---  
        basic_settings_tab = QWidget()  
        basic_settings_layout = QVBoxLayout(basic_settings_tab)  
          
        # ファイル読み込みグループ  
        file_group = QGroupBox("ファイル読み込み")  
        file_layout = QVBoxLayout(file_group)  
        self.load_video_btn = QPushButton("動画を読み込み")  
        self.load_video_btn.clicked.connect(self.load_video)  
        file_layout.addWidget(self.load_video_btn)  
        self.load_json_btn = QPushButton("JSONを読み込み")  
        self.load_json_btn.clicked.connect(self.load_json)  
        file_layout.addWidget(self.load_json_btn)  
        basic_settings_layout.addWidget(file_group)  
          
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
        basic_settings_layout.addWidget(playback_group)  
          
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
        basic_settings_layout.addWidget(display_group)  
          
        # 保存グループ  
        save_group = QGroupBox("保存")  
        save_layout = QVBoxLayout(save_group)  
        self.save_btn = QPushButton("修正結果を保存")  
        self.save_btn.clicked.connect(self.save_modifications)  
        self.save_btn.setEnabled(False)  
        save_layout.addWidget(self.save_btn)  
        basic_settings_layout.addWidget(save_group)  
          
        basic_settings_layout.addStretch()  
        tab_widget.addTab(basic_settings_tab, "基本設定")  
          
        # --- 2. 編集機能タブ ---  
        edit_features_tab = QWidget()  
        edit_features_layout = QVBoxLayout(edit_features_tab)  
          
        # 編集機能グループ  
        edit_group = QGroupBox("編集機能")  
        edit_layout = QFormLayout(edit_group)  
        self.edit_mode_cb = QCheckBox()  
        self.edit_mode_cb.stateChanged.connect(self.toggle_edit_mode)  
        edit_layout.addRow("編集モード:", self.edit_mode_cb)  
        self.label_combo = QComboBox()  
        self.label_combo.setEnabled(False)  
        self.label_combo.currentIndexChanged.connect(self.change_selected_label) # currentIndexChangedを使用  
        edit_layout.addRow("ラベル:", self.label_combo)  
        self.track_id_edit = QLineEdit()  
        self.track_id_edit.setEnabled(False)  
        self.track_id_edit.returnPressed.connect(self.change_track_id)  
        edit_layout.addRow("Track ID:", self.track_id_edit)  
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
        edit_features_layout.addWidget(edit_group)  
          
        # 一括編集グループ  
        batch_edit_group = QGroupBox("一括編集")  
        batch_edit_layout = QFormLayout(batch_edit_group)  
        range_layout = QHBoxLayout()  
        self.start_frame_spin = QSpinBox()  
        self.start_frame_spin.setMinimum(0)  
        range_layout.addWidget(QLabel("開始:"))  
        range_layout.addWidget(self.start_frame_spin)  
        self.end_frame_spin = QSpinBox()  
        self.end_frame_spin.setMinimum(0)  
        range_layout.addWidget(QLabel("終了:"))  
        range_layout.addWidget(self.end_frame_spin)  
        batch_edit_layout.addRow("フレーム範囲:", range_layout)  
        batch_buttons = QVBoxLayout()  
        self.delete_track_btn = QPushButton("選択Track全削除")  
        self.delete_track_btn.clicked.connect(self.delete_track_globally)  
        self.delete_track_btn.setEnabled(False)  
        batch_buttons.addWidget(self.delete_track_btn)  
        self.propagate_label_btn = QPushButton("ラベル変更を伝播")  
        self.propagate_label_btn.clicked.connect(self.propagate_label_change)  
        self.propagate_label_btn.setEnabled(False)  
        batch_buttons.addWidget(self.propagate_label_btn)  
        self.add_track_range_btn = QPushButton("範囲内Track追加")  
        self.add_track_range_btn.clicked.connect(self.add_track_in_range)  
        self.add_track_range_btn.setEnabled(False)  
        batch_buttons.addWidget(self.add_track_range_btn)  
        self.interpolate_track_btn = QPushButton("補間Track追加")  
        self.interpolate_track_btn.clicked.connect(self.interpolate_track_in_range)  
        self.interpolate_track_btn.setEnabled(False)  
        batch_buttons.addWidget(self.interpolate_track_btn)  
        batch_edit_layout.addRow("操作:", batch_buttons)  
        edit_features_layout.addWidget(batch_edit_group)  
          
        edit_features_layout.addStretch()  
        tab_widget.addTab(edit_features_tab, "編集機能")  
          
        # --- 3. 高度な補間タブ ---  
        advanced_interpolation_tab = QWidget()  
        advanced_interpolation_layout = QVBoxLayout(advanced_interpolation_tab)  
          
        # 高度な補間グループ  
        advanced_group = QGroupBox("高度な補間")  
        advanced_layout = QFormLayout(advanced_group)  
        self.control_points_list = QListWidget()  
        advanced_layout.addRow("制御点:", self.control_points_list)  
        control_buttons = QHBoxLayout()  
        self.add_control_point_btn = QPushButton("現在位置を追加")  
        self.add_control_point_btn.clicked.connect(self.add_control_point)  
        control_buttons.addWidget(self.add_control_point_btn)  
        self.clear_control_points_btn = QPushButton("クリア")  
        self.clear_control_points_btn.clicked.connect(self.clear_control_points)  
        control_buttons.addWidget(self.clear_control_points_btn)  
        advanced_layout.addRow("操作:", control_buttons)  
        self.kalman_interpolate_btn = QPushButton("カルマンフィルター補間Track追加")  
        self.kalman_interpolate_btn.clicked.connect(self.create_kalman_track)  
        advanced_layout.addRow("カルマンフィルター:", self.kalman_interpolate_btn)  
        advanced_interpolation_layout.addWidget(advanced_group)  
          
        # カルマンフィルタパラメータグループ  
        kalman_group = QGroupBox("カルマンフィルタパラメータ")  
        kalman_layout = QFormLayout(kalman_group)  
        self.process_noise_pos_spin = QDoubleSpinBox()  
        self.process_noise_pos_spin.setRange(0.1, 10.0)  
        self.process_noise_pos_spin.setValue(1.0)  
        self.process_noise_pos_spin.setSingleStep(0.1)  
        self.process_noise_pos_spin.valueChanged.connect(self.update_kalman_params)  
        self.process_noise_pos_spin.setToolTip("位置の予測における不確実性の度合い。値を大きくすると、予測が観測に強く影響され、動きがよりダイナミックになります。範囲: 0.1 - 10.0") # 説明を追加
        kalman_layout.addRow("位置プロセスノイズ:", self.process_noise_pos_spin)  
        self.process_noise_vel_spin = QDoubleSpinBox()  
        self.process_noise_vel_spin.setRange(0.1, 20.0)  
        self.process_noise_vel_spin.setValue(5.0)  
        self.process_noise_vel_spin.setSingleStep(0.1)  
        self.process_noise_vel_spin.valueChanged.connect(self.update_kalman_params)  
        self.process_noise_vel_spin.setToolTip("速度の予測における不確実性の度合い。値を大きくすると、オブジェクトの速度変化がより自由に予測されます。範囲: 0.1 - 20.0") # 説明を追加
        kalman_layout.addRow("速度プロセスノイズ:", self.process_noise_vel_spin)  
        self.observation_noise_spin = QDoubleSpinBox()  
        self.observation_noise_spin.setRange(0.1, 10.0)  
        self.observation_noise_spin.setValue(2.0)  
        self.observation_noise_spin.setSingleStep(0.1)  
        self.observation_noise_spin.valueChanged.connect(self.update_kalman_params)  
        self.observation_noise_spin.setToolTip("観測データの信頼性。値を小さくすると、観測データがより信頼され、予測が観測に近づきます。範囲: 0.1 - 10.0") # 説明を追加
        kalman_layout.addRow("観測ノイズ:", self.observation_noise_spin)  
        self.velocity_factor_spin = QDoubleSpinBox()  
        self.velocity_factor_spin.setRange(0.5, 3.0)  
        self.velocity_factor_spin.setValue(1.2)  
        self.velocity_factor_spin.setSingleStep(0.1)  
        self.velocity_factor_spin.valueChanged.connect(self.update_kalman_params)  
        self.velocity_factor_spin.setToolTip("初期速度の計算に適用される係数。値を大きくすると、初期速度が強調され、より速い動きが予測されます。範囲: 0.5 - 3.0") # 説明を追加
        kalman_layout.addRow("速度係数:", self.velocity_factor_spin)  
        self.pos_uncertainty_spin = QDoubleSpinBox()  
        self.pos_uncertainty_spin.setRange(1.0, 20.0)  
        self.pos_uncertainty_spin.setValue(5.0)  
        self.pos_uncertainty_spin.setSingleStep(0.5)  
        self.pos_uncertainty_spin.valueChanged.connect(self.update_kalman_params)  
        self.pos_uncertainty_spin.setToolTip("カルマンフィルタの初期状態における位置の不確実性。値を大きくすると、初期位置の信頼度が低いと見なされます。範囲: 1.0 - 20.0") # 説明を追加
        kalman_layout.addRow("位置不確実性:", self.pos_uncertainty_spin)  
        self.vel_uncertainty_spin = QDoubleSpinBox()  
        self.vel_uncertainty_spin.setRange(1.0, 30.0)  
        self.vel_uncertainty_spin.setValue(10.0)  
        self.vel_uncertainty_spin.setSingleStep(0.5)  
        self.vel_uncertainty_spin.valueChanged.connect(self.update_kalman_params)  
        self.vel_uncertainty_spin.setToolTip("カルマンフィルタの初期状態における速度の不確実性。値を大きくすると、初期速度の信頼度が低いと見なされます。範囲: 1.0 - 30.0") # 説明を追加  
        kalman_layout.addRow("速度不確実性:", self.vel_uncertainty_spin)  
        self.reset_kalman_btn = QPushButton("デフォルトに戻す")  
        self.reset_kalman_btn.clicked.connect(self.reset_kalman_params)  
        kalman_layout.addRow("リセット:", self.reset_kalman_btn)  
        advanced_interpolation_layout.addWidget(kalman_group)  
          
        advanced_interpolation_layout.addStretch()  
        tab_widget.addTab(advanced_interpolation_tab, "高度な補間") # ここでタブを閉じる  
  
        left_layout.addWidget(tab_widget) # タブウィジェットを左側パネルに追加  
          
        left_layout.addStretch()  
        main_layout.addWidget(left_panel)  
  
        # 右側パネル（動画表示）  
        right_panel = QWidget()  
        right_layout = QVBoxLayout(right_panel)  
          
        # 動画表示エリア  
        self.video_label = QLabel()  
        self.video_label.setMinimumSize(1300, 700) # 最小サイズを調整  
        self.video_label.setSizePolicy(  
            QSizePolicy.Policy.Expanding,   
            QSizePolicy.Policy.Expanding  
        ) # 拡張可能に設定  
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
        
        # ハンドル判定のための少し大きめの範囲を設定
        handle_size = self.resize_handle_size * 1.5  # 判定範囲を1.5倍に拡大
        
        handles = {
            'top_left': (x1, y1),
            'top_right': (x2, y1),
            'bottom_left': (x1, y2),
            'bottom_right': (x2, y2)
        }
        
        # 各ハンドルの判定範囲を確認（少し余裕を持たせる）
        for handle_name, (hx, hy) in handles.items():
            # 判定範囲を楕円形に近い形状で計算
            dx = abs(click_x - hx) / handle_size
            dy = abs(click_y - hy) / handle_size
            if (dx * dx + dy * dy) <= 1.5:  # 1.5は判定の緩さを調整する係数
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
        
        # 座標変換処理
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
        
        # アノテーション選択とリサイズハンドル判定を改善
        for ann in frame_annotations:
            bbox = ann.get('bbox', [])
            if len(bbox) != 4:
                continue
                
            # まずリサイズハンドルの判定を行う
            resize_handle = self.get_resize_handle(bbox, actual_x, actual_y)
            
            # リサイズハンドルがクリックされた場合
            if resize_handle:
                self.selected_annotation = ann
                self.resize_handle = resize_handle
                self.drag_start = QPoint(int(actual_x), int(actual_y))
                self.original_bbox = bbox.copy()  # 元のbboxを保存
                self.update_selection_info()
                self.update_frame_display()
                print(f"リサイズハンドル選択: {resize_handle}, Track ID {ann.get('track_id')}")
                return
            
            # リサイズハンドルでない場合、バウンディングボックス内部かチェック
            x, y, w, h = bbox
            x1, y1 = x, y
            x2, y2 = x + w, y + h
            
            if x1 <= actual_x <= x2 and y1 <= actual_y <= y2:
                self.selected_annotation = ann
                self.resize_handle = None
                self.drag_start = QPoint(int(actual_x), int(actual_y))
                self.update_selection_info()
                self.update_frame_display()
                print(f"アノテーション選択: Track ID {ann.get('track_id')}")
                return
        
        # 何も選択されなかった場合
        self.selected_annotation = None
        self.resize_handle = None
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

            self.delete_annotation_btn.setEnabled(True)  
            # 一括編集ボタンを有効化  
            if hasattr(self, 'delete_track_btn'):  
                self.delete_track_btn.setEnabled(True)  
            if hasattr(self, 'propagate_label_btn'):  
                self.propagate_label_btn.setEnabled(True)  
        else:  
            self.selection_info.setText("選択: なし")  
            self.track_id_edit.clear()  
            self.delete_annotation_btn.setEnabled(False)  

            self.delete_annotation_btn.setEnabled(False)  
            # 一括編集ボタンを無効化  
            if hasattr(self, 'delete_track_btn'):  
                self.delete_track_btn.setEnabled(False)  
            if hasattr(self, 'propagate_label_btn'):  
                self.propagate_label_btn.setEnabled(False)
      
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

    def edit_track_across_frames(self, track_id, operation, **kwargs):  
        """指定されたtrack_idのアノテーションを全フレームで編集"""  
        modified_count = 0  
          
        if operation == 'delete':  
            # 削除の場合は逆順でイテレートするか、リストコピーを使用  
            annotations_to_remove = []  
            for ann in self.json_data:  
                if ann.get('track_id') == track_id:  
                    annotations_to_remove.append(ann)  
              
            # 収集したアノテーションを削除  
            for ann in annotations_to_remove:  
                self.json_data.remove(ann)  
                modified_count += 1  
                  
        elif operation == 'change_label':  
            for ann in self.json_data:  
                if ann.get('track_id') == track_id:  
                    ann['label'] = kwargs.get('new_label_id')  
                    ann['label_name'] = kwargs.get('new_label_name')  
                    modified_count += 1  
          
        return modified_count

    def delete_track_globally(self):  
        """選択されたtrack_idを全フレームから削除"""  
        if not self.selected_annotation:  
            return  
              
        track_id = self.selected_annotation.get('track_id')  
          
        # 削除前の件数を確認  
        before_count = sum(1 for ann in self.json_data if ann.get('track_id') == track_id)  
          
        reply = QMessageBox.question(  
            self, "確認",   
            f"Track ID {track_id} を全フレーム（{before_count}件）から削除しますか？",  
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
        )  
          
        if reply == QMessageBox.StandardButton.Yes:  
            count = self.edit_track_across_frames(track_id, 'delete')  
              
            # 削除後の確認  
            remaining_count = sum(1 for ann in self.json_data if ann.get('track_id') == track_id)  
              
            if remaining_count == 0:  
                QMessageBox.information(self, "完了", f"{count}個のアノテーションを削除しました")  
            else:  
                QMessageBox.warning(self, "警告", f"{count}個削除しましたが、{remaining_count}個が残っています")  
              
            self.selected_annotation = None  
            self.update_frame_display()

    def interpolate_missing_frames(self, track_id):  
        """指定されたtrack_idの欠損フレームを補間"""  
        track_annotations = [ann for ann in self.json_data if ann.get('track_id') == track_id]  
        track_annotations.sort(key=lambda x: x.get('frame_id'))  
          
        if len(track_annotations) < 2:  
            return  
          
        # フレーム間の補間処理  
        for i in range(len(track_annotations) - 1):  
            current_frame = track_annotations[i]['frame_id']  
            next_frame = track_annotations[i + 1]['frame_id']  
              
            # 間に欠損フレームがある場合  
            if next_frame - current_frame > 1:  
                self.interpolate_between_frames(track_annotations[i], track_annotations[i + 1])  
      
    def interpolate_between_frames(self, start_ann, end_ann):  
        """2つのアノテーション間を線形補間"""  
        start_frame = start_ann['frame_id']  
        end_frame = end_ann['frame_id']  
        start_bbox = start_ann['bbox']  
        end_bbox = end_ann['bbox']  
          
        for frame_id in range(start_frame + 1, end_frame):  
            # 線形補間でbboxを計算  
            ratio = (frame_id - start_frame) / (end_frame - start_frame)  
            interpolated_bbox = [  
                start_bbox[i] + (end_bbox[i] - start_bbox[i]) * ratio  
                for i in range(4)  
            ]  
              
            # 補間されたアノテーションを追加  
            interpolated_ann = {  
                "frame_id": frame_id,  
                "track_id": start_ann['track_id'],  
                "bbox": interpolated_bbox,  
                "score": start_ann['score'],  # スコアは開始フレームのものを使用  
                "label": start_ann['label'],  
                "label_name": start_ann['label_name']  
            }  
              
            self.json_data.append(interpolated_ann)

    def propagate_label_change(self):  
        """選択されたアノテーションのラベル変更を同一track_idの全フレームに伝播"""  
        if not self.selected_annotation:  
            QMessageBox.warning(self, "エラー", "アノテーションが選択されていません")  
            return  
              
        track_id = self.selected_annotation.get('track_id')  
        new_label_id = self.selected_annotation.get('label')  
        new_label_name = self.selected_annotation.get('label_name')  
          
        reply = QMessageBox.question(  
            self, "確認",   
            f"Track ID {track_id} のラベルを '{new_label_name}' に全フレームで変更しますか？",  
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
        )  
          
        if reply == QMessageBox.StandardButton.Yes:  
            count = self.edit_track_across_frames(  
                track_id, 'change_label',  
                new_label_id=new_label_id,  
                new_label_name=new_label_name  
            )  
            QMessageBox.information(self, "完了", f"{count}個のアノテーションのラベルを変更しました")  
            self.update_frame_display()

    def add_control_point(self):  
        """現在のアノテーションを制御点として追加"""  
        if not self.selected_annotation:  
            QMessageBox.warning(self, "エラー", "アノテーションを選択してください")  
            return  
          
        control_point = {  
            'frame': self.current_frame,  
            'bbox': self.selected_annotation['bbox'].copy()  
        }  
        self.control_points.append(control_point)  
          
        # リストに表示  
        self.control_points_list.addItem(f"フレーム {self.current_frame}: {control_point['bbox']}")  
      
    def clear_control_points(self):  
        """制御点をクリア"""  
        self.control_points.clear()  
        self.control_points_list.clear()  
      
    def create_spline_track(self):  
        """制御点を使用してスプライン補間trackを作成"""  
        if len(self.control_points) < 2:  
            QMessageBox.warning(self, "エラー", "最低2つの制御点が必要です")  
            return  
          
        if not self.selected_annotation:  
            QMessageBox.warning(self, "エラー", "ラベル情報のためにアノテーションを選択してください")  
            return  
          
        label_id = self.selected_annotation['label']  
        label_name = self.selected_annotation['label_name']  
          
        track_id, count = self.spline_interpolate_track(self.control_points, label_id, label_name)  
        if track_id:  
            QMessageBox.information(self, "完了", f"Track ID {track_id} で {count}個の補間アノテーションを追加しました")  
            self.update_frame_display()

    def kalman_filter_interpolation(self, control_points, label_id, label_name):  
        """カルマンフィルターを使用した軌跡予測（修正版）"""  
        import numpy as np  
        from scipy.linalg import inv  
          
        if len(control_points) < 2:  
            return None, 0  
          
        # 制御点をソート  
        control_points.sort(key=lambda x: x['frame'])  
          
        # システムモデル（等速度モデル）  
        dt = 1.0  
        F = np.array([[1, 0, dt, 0],  
                      [0, 1, 0, dt],  
                      [0, 0, 1, 0],  
                      [0, 0, 0, 1]])  
          
        H = np.array([[1, 0, 0, 0],  
                      [0, 1, 0, 0]])  
          
        # UIで設定されたパラメータを使用  
        Q = np.diag([self.kalman_process_noise_pos, self.kalman_process_noise_pos,   
                    self.kalman_process_noise_vel, self.kalman_process_noise_vel])  
        R = np.diag([self.kalman_observation_noise, self.kalman_observation_noise])  
          
        # 初期状態の推定  
        first_point = control_points[0]  
        initial_pos = [(first_point['bbox'][0] + first_point['bbox'][2])/2,   
                      (first_point['bbox'][1] + first_point['bbox'][3])/2]  
          
        if len(control_points) > 1:  
            second_point = control_points[1]  
            frame_diff = second_point['frame'] - first_point['frame']  
            second_pos = [(second_point['bbox'][0] + second_point['bbox'][2])/2,  
                          (second_point['bbox'][1] + second_point['bbox'][3])/2]  
              
            # UIで設定された速度係数を使用  
            initial_vel = [  
                (second_pos[0] - initial_pos[0]) / frame_diff * self.kalman_velocity_factor,  
                (second_pos[1] - initial_pos[1]) / frame_diff * self.kalman_velocity_factor  
            ]  
        else:  
            initial_vel = [0, 0]  
          
        # 初期状態ベクトル  
        x = np.array([initial_pos[0], initial_pos[1], initial_vel[0], initial_vel[1]])  
          
        # UIで設定された不確実性を使用  
        P = np.diag([self.kalman_pos_uncertainty, self.kalman_pos_uncertainty,   
                    self.kalman_vel_uncertainty, self.kalman_vel_uncertainty])            

        new_track_id = self.manage_track_ids()  
        added_count = 0  
          
        start_frame = control_points[0]['frame']  
        end_frame = control_points[-1]['frame']  
          
        for frame_id in range(start_frame, end_frame + 1):  
            # 予測ステップ  
            x_pred = F @ x  
            P_pred = F @ P @ F.T + Q  
              
            # 観測データがある場合は更新  
            observation = None  
            for cp in control_points:  
                if cp['frame'] == frame_id:  
                    observation = np.array([(cp['bbox'][0] + cp['bbox'][2])/2,   
                                          (cp['bbox'][1] + cp['bbox'][3])/2])  
                    break  
              
            if observation is not None:  
                # 更新ステップ  
                y = observation - H @ x_pred  
                S = H @ P_pred @ H.T + R  
                K = P_pred @ H.T @ inv(S)  
                x = x_pred + K @ y  
                P = (np.eye(4) - K @ H) @ P_pred  
            else:  
                x = x_pred  
                P = P_pred  
              
            # 元のbboxサイズを維持  
            ref_bbox = control_points[0]['bbox']  
            w, h = ref_bbox[2] - ref_bbox[0], ref_bbox[3] - ref_bbox[1]  
              
            # 異常値チェック  
            if abs(x[0]) > 10000 or abs(x[1]) > 10000:  
                print(f"Warning: Abnormal position detected at frame {frame_id}: ({x[0]}, {x[1]})")  
                # 最後の有効な観測値を使用  
                for cp in reversed(control_points):  
                    if cp['frame'] <= frame_id:  
                        x[0] = (cp['bbox'][0] + cp['bbox'][2])/2  
                        x[1] = (cp['bbox'][1] + cp['bbox'][3])/2  
                        break  
              
            interpolated_bbox = [  
                x[0] - w/2, x[1] - h/2,  
                x[0] + w/2, x[1] + h/2  
            ]  
              
            new_annotation = {  
                "frame_id": frame_id,  
                "track_id": new_track_id,  
                "bbox": interpolated_bbox,  
                "score": 0.9,  
                "label": label_id,  
                "label_name": label_name  
            }  
            self.json_data.append(new_annotation)  
            added_count += 1  
          
        return new_track_id, added_count
      
    def create_kalman_track(self):  
        """カルマンフィルター補間trackを作成"""  
        if len(self.control_points) < 2:  
            QMessageBox.warning(self, "エラー", "カルマンフィルター補間には最低2つの制御点が必要です")  
            return  
          
        if not self.selected_annotation:  
            return  
          
        label_id = self.selected_annotation['label']  
        label_name = self.selected_annotation['label_name']  
          
        track_id, count = self.kalman_filter_interpolation(self.control_points, label_id, label_name)  
        if track_id:  
            QMessageBox.information(self, "完了", f"カルマンフィルター補間でTrack ID {track_id}、{count}個のアノテーションを追加しました")  
            self.update_frame_display()

    def update_kalman_params(self):  
        """カルマンフィルタパラメータを更新"""  
        self.kalman_process_noise_pos = self.process_noise_pos_spin.value()  
        self.kalman_process_noise_vel = self.process_noise_vel_spin.value()  
        self.kalman_observation_noise = self.observation_noise_spin.value()  
        self.kalman_velocity_factor = self.velocity_factor_spin.value()  
        self.kalman_pos_uncertainty = self.pos_uncertainty_spin.value()  
        self.kalman_vel_uncertainty = self.vel_uncertainty_spin.value()  
      
    def reset_kalman_params(self):  
        """カルマンフィルタパラメータをデフォルト値にリセット"""  
        self.process_noise_pos_spin.setValue(1.0)  
        self.process_noise_vel_spin.setValue(5.0)  
        self.observation_noise_spin.setValue(2.0)  
        self.velocity_factor_spin.setValue(1.2)  
        self.pos_uncertainty_spin.setValue(5.0)  
        self.vel_uncertainty_spin.setValue(10.0)

    def add_track_in_range(self):  
        """フレーム範囲内に同じbboxでtrack追加"""  
        if not self.selected_annotation:  
            QMessageBox.warning(self, "エラー", "テンプレートとなるアノテーションを選択してください")  
            return  
          
        start_frame = self.start_frame_spin.value()  
        end_frame = self.end_frame_spin.value()  
          
        if start_frame > end_frame:  
            QMessageBox.warning(self, "エラー", "開始フレームは終了フレーム以下にしてください")  
            return  
          
        template_bbox = self.selected_annotation['bbox'].copy()  
        label_id = self.selected_annotation['label']  
        label_name = self.selected_annotation['label_name']  
          
        reply = QMessageBox.question(  
            self, "確認",   
            f"フレーム {start_frame} から {end_frame} まで '{label_name}' のtrackを追加しますか？",  
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
        )  
          
        if reply == QMessageBox.StandardButton.Yes:  
            track_id, count = self.add_track_across_frames(  
                start_frame, end_frame, template_bbox, label_id, label_name  
            )  
            QMessageBox.information(self, "完了", f"Track ID {track_id} で {count}個のアノテーションを追加しました")  
            self.update_frame_display()

    def add_track_across_frames(self, start_frame, end_frame, bbox_template, label_id, label_name):  
        """指定されたフレーム範囲に新しいtrack_idでアノテーションを一括追加"""  
        new_track_id = self.manage_track_ids()  
        added_count = 0  
          
        for frame_id in range(start_frame, end_frame + 1):  
            # 既に同じフレームに同じtrack_idのアノテーションがないかチェック  
            existing = any(ann.get('track_id') == new_track_id and ann.get('frame_id') == frame_id   
                          for ann in self.json_data)  
              
            if not existing:  
                new_annotation = {  
                    "frame_id": frame_id,  
                    "track_id": new_track_id,  
                    "bbox": bbox_template.copy(),  # テンプレートbboxをコピー  
                    "score": 1.0,  
                    "label": label_id,  
                    "label_name": label_name  
                }  
                self.json_data.append(new_annotation)  
                added_count += 1  
          
        return new_track_id, added_count

    def interpolate_track_in_range(self):  
        """フレーム範囲内に補間trackを追加"""  
        if not self.selected_annotation:  
            QMessageBox.warning(self, "エラー", "開始位置となるアノテーションを選択してください")  
            return  
          
        start_frame = self.start_frame_spin.value()  
        end_frame = self.end_frame_spin.value()  
          
        if start_frame > end_frame:  
            QMessageBox.warning(self, "エラー", "開始フレームは終了フレーム以下にしてください")  
            return  
          
        # 終了位置のbboxを入力で取得（簡易実装）  
        start_bbox = self.selected_annotation['bbox'].copy()  
          
        # 終了位置のbboxを現在のbboxから少しずらした位置として設定（実際の実装では別途入力UI必要）  
        end_bbox = start_bbox.copy()  
        end_bbox[0] += 50  # x座標を50ピクセル移動  
        end_bbox[2] += 50  # x2座標も移動  
          
        label_id = self.selected_annotation['label']  
        label_name = self.selected_annotation['label_name']  
          
        reply = QMessageBox.question(  
            self, "確認",   
            f"フレーム {start_frame} から {end_frame} まで補間 '{label_name}' trackを追加しますか？",  
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No  
        )  
          
        if reply == QMessageBox.StandardButton.Yes:  
            track_id, count = self.interpolate_track_across_frames(  
                start_frame, end_frame, start_bbox, end_bbox, label_id, label_name  
            )  
            QMessageBox.information(self, "完了", f"Track ID {track_id} で {count}個の補間アノテーションを追加しました")  
            self.update_frame_display()

    def interpolate_track_across_frames(self, start_frame, end_frame, start_bbox, end_bbox, label_id, label_name):  
        """指定されたフレーム範囲に補間されたアノテーションを一括追加"""  
        new_track_id = self.manage_track_ids()  
        added_count = 0  
          
        for frame_id in range(start_frame, end_frame + 1):  
            # 線形補間でbboxを計算  
            if end_frame > start_frame:  
                ratio = (frame_id - start_frame) / (end_frame - start_frame)  
                interpolated_bbox = [  
                    start_bbox[i] + (end_bbox[i] - start_bbox[i]) * ratio  
                    for i in range(4)  
                ]  
            else:  
                interpolated_bbox = start_bbox.copy()  
              
            new_annotation = {  
                "frame_id": frame_id,  
                "track_id": new_track_id,  
                "bbox": interpolated_bbox,  
                "score": 1.0,  
                "label": label_id,  
                "label_name": label_name  
            }  
            self.json_data.append(new_annotation)  
            added_count += 1  
          
        return new_track_id, added_count