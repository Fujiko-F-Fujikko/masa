リファクタリング後のクラス図を以下に示します：

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

    %% メインウィジェット（簡素化）
    class MASAAnnotationWidget {
        +menu_panel: MenuPanel
        +video_preview: VideoPreviewWidget
        +video_control: VideoControlPanel
        +video_manager: VideoManager
        +annotation_repository: AnnotationRepository
        +playback_controller: VideoPlaybackController
        +mode_manager: ModeManager
        +signal_connector: SignalConnector
        +setup_ui()
        +load_video()
        +export_annotations()
    }

    %% 新しいユーティリティクラス
    class CoordinateTransform {
        +scale_x: float
        +scale_y: float
        +offset_x: int
        +offset_y: int
        +image_width: int
        +image_height: int
        +widget_to_image(pos)
        +image_to_widget(x, y)
        +clip_to_bounds(x, y)
    }

    class ConfigManager {
        -_observers: List
        -_config: MASAConfig
        +update_config(key, value)
        +get_config(key)
        +add_observer(observer)
        +_notify_observers(key, value)
    }

    class SignalConnector {
        +auto_connect(source, target)
        +connect_by_convention(widget)
        +disconnect_all(widget)
    }

    class ErrorHandler {
        +handle_with_dialog(func)
        +log_error(error, context)
        +show_error_dialog(message)
    }

    %% モード管理（状態パターン）
    class ModeManager {
        +current_mode: AnnotationMode
        +set_mode(mode_type)
        +handle_mouse_event(event)
        +get_cursor_shape()
    }

    class AnnotationMode {
        <<abstract>>
        +handle_mouse_press(event)*
        +handle_mouse_move(event)*
        +handle_mouse_release(event)*
        +get_cursor_shape()*
        +enter_mode()*
        +exit_mode()*
    }

    class EditMode {
        +handle_mouse_press(event)
        +handle_mouse_move(event)
        +handle_mouse_release(event)
        +get_cursor_shape()
    }

    class BatchAddMode {
        +handle_mouse_press(event)
        +handle_mouse_move(event)
        +handle_mouse_release(event)
        +get_cursor_shape()
    }

    class ViewMode {
        +handle_mouse_press(event)
        +handle_mouse_move(event)
        +handle_mouse_release(event)
        +get_cursor_shape()
    }

    %% 責務分離されたデータ管理
    class VideoManager {
        +video_path: str
        +video_reader: cv2.VideoCapture
        +total_frames: int
        +load_video(path)
        +get_frame(frame_id)
        +get_fps()
    }

    class AnnotationRepository {
        +frame_annotations: Dict
        +manual_annotations: Dict
        +next_object_id: int
        +add_annotation(annotation)
        +get_annotations(frame_id)
        +update_annotation(annotation)
        +delete_annotation(object_id, frame_id)
        +delete_by_track_id(track_id)
        +get_statistics()
    }

    class ExportService {
        +export_json(annotations, path)
        +export_coco(annotations, path)
        +export_masa_json(annotations, path)
        +import_json(path)
    }

    %% 改善されたUIコンポーネント
    class VideoPreviewWidget {
        +bbox_editor: BoundingBoxEditor
        +visualizer: AnnotationVisualizer
        +coordinate_transform: CoordinateTransform
        +mode_manager: ModeManager
        +set_video_manager()
        +update_frame_display()
        +handle_mouse_event(event)
    }

    class BoundingBoxEditor {
        +coordinate_transform: CoordinateTransform
        +selected_annotation: ObjectAnnotation
        +select_annotation_at_position()
        +start_drag_operation()
        +draw_selection_overlay()
    }

    class MenuPanel {
        +config_manager: ConfigManager
        +tab_widget: QTabWidget
        +current_selected_annotation: ObjectAnnotation
        +setup_basic_tab()
        +setup_annotation_tab()
        +update_selected_annotation_info()
    }

    class VideoControlPanel {
        +range_slider: RangeSlider
        +coordinate_transform: CoordinateTransform
        +set_total_frames()
        +set_current_frame()
        +get_selected_range()
    }

    %% 改善されたデータクラス（バリデーション付き）
    class BoundingBox {
        +x1: float
        +y1: float
        +x2: float
        +y2: float
        +confidence: float
        +__post_init__()
        +validate()
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
        +__post_init__()
        +validate()
    }

    class FrameAnnotation {
        +frame_id: int
        +frame_path: str
        +objects: List[ObjectAnnotation]
        +__post_init__()
        +validate()
    }

    %% その他のクラス（変更なし）
    class ObjectTracker {
        +config: MASAConfig
        +masa_model: nn.Module
        +initialize()
        +track_objects()
    }

    class TrackingWorker {
        +annotation_repository: AnnotationRepository
        +object_tracker: ObjectTracker
        +run()
        +process_tracking_with_progress()
    }

    class AnnotationVisualizer {
        +colors: List[Tuple]
        +draw_annotations()
        +create_annotation_video()
    }

    class VideoPlaybackController {
        +video_manager: VideoManager
        +timer: QTimer
        +play()
        +pause()
        +next_frame()
    }

    %% 関係性（リファクタリング後）
    MASAAnnotationApp --> MASAAnnotationWidget : contains
    
    MASAAnnotationWidget --> MenuPanel : contains
    MASAAnnotationWidget --> VideoPreviewWidget : contains
    MASAAnnotationWidget --> VideoControlPanel : contains
    MASAAnnotationWidget --> VideoManager : uses
    MASAAnnotationWidget --> AnnotationRepository : uses
    MASAAnnotationWidget --> ExportService : uses
    MASAAnnotationWidget --> ModeManager : uses
    MASAAnnotationWidget --> SignalConnector : uses
    MASAAnnotationWidget --> ConfigManager : uses

    VideoPreviewWidget --> BoundingBoxEditor : contains
    VideoPreviewWidget --> AnnotationVisualizer : contains
    VideoPreviewWidget --> CoordinateTransform : uses
    VideoPreviewWidget --> ModeManager : uses

    BoundingBoxEditor --> CoordinateTransform : uses
    VideoControlPanel --> CoordinateTransform : uses

    ModeManager --> AnnotationMode : manages
    AnnotationMode <|-- EditMode
    AnnotationMode <|-- BatchAddMode
    AnnotationMode <|-- ViewMode

    AnnotationRepository --> FrameAnnotation : manages
    AnnotationRepository --> ObjectAnnotation : manages

    ExportService --> AnnotationRepository : uses

    MenuPanel --> ConfigManager : uses
    ConfigManager --> MASAConfig : manages

    TrackingWorker --> AnnotationRepository : uses
    TrackingWorker --> ObjectTracker : uses

    VideoPlaybackController --> VideoManager : uses

    FrameAnnotation --> ObjectAnnotation : contains
    ObjectAnnotation --> BoundingBox : contains

    %% エラーハンドリング（全体に適用）
    ErrorHandler ..> MASAAnnotationWidget : decorates
    ErrorHandler ..> VideoManager : decorates
    ErrorHandler ..> AnnotationRepository : decorates
    ErrorHandler ..> ExportService : decorates
```

## 主要な改善点

### 1. **責務の明確化**
- `VideoAnnotationManager` → `VideoManager` + `AnnotationRepository` + `ExportService`
- 各クラスが単一責任を持つように分離

### 2. **共通機能の統合**
- `CoordinateTransform`: 座標変換ロジックの一元化
- `ConfigManager`: 設定管理の統合
- `ErrorHandler`: エラーハンドリングの統一

### 3. **状態管理の改善**
- `ModeManager` + `AnnotationMode`: 状態パターンによるモード管理
- 複数のモードフラグを統一的に管理

### 4. **シグナル接続の簡素化**
- `SignalConnector`: 命名規則に基づく自動接続
- 冗長なシグナル接続コードを削減

### 5. **データ検証の強化**
- 全データクラスに `validate()` メソッドを追加
- `__post_init__()` での自動検証

この改善により、コードの可読性、保守性、拡張性が大幅に向上し、重複コードが削減されます。