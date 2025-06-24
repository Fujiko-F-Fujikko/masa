# Class Diaglam

## MASAAnnotationApp

```mermaid
classDiagram
    %% エントリーポイント
    class MASAAnnotationApp {
        +main_widget: MASAAnnotationWidget
        +args: argparse.Namespace
        +__init__(argv)
        +parse_args(argv)
        +run_gui_application()
    }

    %% メインウィジェット
    class MASAAnnotationWidget {
        +menu_panel: MenuPanel
        +video_preview: VideoPreviewWidget
        +video_control: VideoControlPanel
        +video_manager: VideoAnnotationManager
        +playback_controller: VideoPlaybackController
        +temp_bboxes_for_batch_add: List
        +setup_ui()
        +connect_signals()
        +load_video()
        +on_bbox_created()
        +start_tracking()
        +export_annotations()
    }

    %% UIコンポーネント
    class MenuPanel {
        +tab_widget: QTabWidget
        +edit_mode_btn: QPushButton
        +label_combo: QComboBox
        +current_selected_annotation: ObjectAnnotation
        +setup_basic_tab()
        +setup_annotation_tab()
        +update_selected_annotation_info()
    }

    class VideoPreviewWidget {
        +bbox_editor: BoundingBoxEditor
        +visualizer: AnnotationVisualizer
        +video_manager: VideoAnnotationManager
        +annotation_mode: bool
        +edit_mode: bool
        +batch_add_annotation_mode: bool
        +set_video_manager()
        +update_frame_display()
        +mousePressEvent()
    }

    class VideoControlPanel {
        +range_slider: RangeSlider
        +frame_slider: QSlider
        +total_frames: int
        +current_frame: int
        +set_total_frames()
        +set_current_frame()
        +get_selected_range()
    }

    class RangeSlider {
        +minimum: int
        +maximum: int
        +start_value: int
        +end_value: int
        +set_range()
        +set_values()
        +get_values()
    }

    %% 編集・可視化
    class BoundingBoxEditor {
        +selected_annotation: ObjectAnnotation
        +is_editing: bool
        +dragging_bbox: bool
        +resizing_bbox: bool
        +select_annotation_at_position()
        +start_drag_operation()
        +draw_selection_overlay()
    }

    class AnnotationVisualizer {
        +colors: List[Tuple]
        +_generate_colors()
        +draw_annotations()
        +create_annotation_video()
    }

    %% データ管理
    class VideoAnnotationManager {
        +video_path: str
        +config: MASAConfig
        +tracker: ObjectTracker
        +frame_annotations: Dict[int, FrameAnnotation]
        +manual_annotations: Dict[int, List[ObjectAnnotation]]
        +load_video()
        +get_frame()
        +add_manual_annotation()
        +export_annotations()
        +load_json_annotations()
    }

    class ObjectTracker {
        +config: MASAConfig
        +masa_model: nn.Module
        +det_model: nn.Module
        +initialized: bool
        +initialize()
        +track_objects()
        +_convert_track_result_to_annotations()
    }

    class JSONLoader {
        +loaded_data: dict
        +video_name: str
        +label_mapping: dict
        +load_json_annotations()
        +get_video_name()
        +get_label_mapping()
    }

    %% 非同期処理
    class TrackingWorker {
        +video_manager: VideoAnnotationManager
        +object_tracker: ObjectTracker
        +start_frame: int
        +end_frame: int
        +assigned_track_id: int
        +run()
        +process_tracking_with_progress()
    }

    class VideoPlaybackController {
        +video_manager: VideoAnnotationManager
        +timer: QTimer
        +current_frame: int
        +is_playing: bool
        +fps: float
        +play()
        +pause()
        +next_frame()
    }

    %% データクラス
    class BoundingBox {
        +x1: float
        +y1: float
        +x2: float
        +y2: float
        +confidence: float
        +to_xyxy()
        +area()
    }

    class ObjectAnnotation {
        +object_id: int
        +label: str
        +bbox: BoundingBox
        +frame_id: int
        +is_manual: bool
        +track_confidence: float
    }

    class FrameAnnotation {
        +frame_id: int
        +frame_path: str
        +objects: List[ObjectAnnotation]
    }

    class MASAConfig {
        +masa_config_path: str
        +masa_checkpoint_path: str
        +device: str
        +score_threshold: float
        +unified_mode: bool
    }

    %% ダイアログ
    class AnnotationInputDialog {
        +bbox: BoundingBox
        +label_input: QLineEdit
        +preset_combo: QComboBox
        +get_label()
    }

    class TrackingSettingsDialog {
        +total_frames: int
        +start_frame: int
        +end_frame_spin: QSpinBox
        +get_end_frame()
    }

    %% 関係性
    MASAAnnotationApp --> MASAAnnotationWidget : contains
    
    MASAAnnotationWidget --> MenuPanel : contains
    MASAAnnotationWidget --> VideoPreviewWidget : contains
    MASAAnnotationWidget --> VideoControlPanel : contains
    MASAAnnotationWidget --> VideoAnnotationManager : uses
    MASAAnnotationWidget --> VideoPlaybackController : uses
    MASAAnnotationWidget --> TrackingWorker : creates
    MASAAnnotationWidget --> AnnotationInputDialog : creates

    VideoPreviewWidget --> BoundingBoxEditor : contains
    VideoPreviewWidget --> AnnotationVisualizer : contains
    VideoPreviewWidget --> VideoAnnotationManager : uses

    VideoControlPanel --> RangeSlider : contains

    BoundingBoxEditor --> ObjectAnnotation : manipulates
    AnnotationVisualizer --> ObjectAnnotation : visualizes

    VideoAnnotationManager --> ObjectTracker : contains
    VideoAnnotationManager --> JSONLoader : uses
    VideoAnnotationManager --> FrameAnnotation : manages
    VideoAnnotationManager --> MASAConfig : uses

    TrackingWorker --> ObjectTracker : uses
    TrackingWorker --> VideoAnnotationManager : uses

    VideoPlaybackController --> VideoAnnotationManager : uses

    ObjectTracker --> MASAConfig : uses
    ObjectTracker --> ObjectAnnotation : creates

    JSONLoader --> FrameAnnotation : creates
    JSONLoader --> ObjectAnnotation : creates

    FrameAnnotation --> ObjectAnnotation : contains
    ObjectAnnotation --> BoundingBox : contains

    MenuPanel --> AnnotationInputDialog : creates
    MenuPanel --> TrackingSettingsDialog : creates
```

## 主要な関係性の説明

### 1. アーキテクチャ階層
- **MASAAnnotationApp**: アプリケーションのエントリーポイント
- **MASAAnnotationWidget**: メインコントローラー、全UIコンポーネントを統合
- **UI Components**: MenuPanel、VideoPreviewWidget、VideoControlPanel

### 2. データフロー
- **VideoAnnotationManager**: 中央データ管理、動画とアノテーションを統合管理
- **ObjectTracker**: MASA推論エンジン、自動追跡処理
- **JSONLoader**: 外部データ読み込み

### 3. 編集・可視化
- **BoundingBoxEditor**: バウンディングボックスの直接編集
- **AnnotationVisualizer**: アノテーション結果の可視化

### 4. 非同期処理
- **TrackingWorker**: バックグラウンドでの重い追跡処理
- **VideoPlaybackController**: 動画再生制御

このアーキテクチャにより、MASAの自動追跡機能と手動アノテーション機能を統合した効率的なデータセット作成ツールが実現されています。