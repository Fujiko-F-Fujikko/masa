# Class Diagram

## Graph

```mermaid
classDiagram
%% エントリーポイント
class MASAAnnotationApp {
+main_widget: MASAAnnotationWidget
+args: argparse.Namespace
+init(argv)
+parse_args(argv)
+run_gui_application()
}

%% メインウィジェット  
class MASAAnnotationWidget {  
    +menu_panel: MenuPanel  
    +video_preview: VideoPreviewWidget  
    +video_control: VideoControlPanel  
    +video_manager: VideoManager  
    +annotation_repository: AnnotationRepository  
    +playback_controller: VideoPlaybackController  
    +object_tracker: ObjectTracker  
    +tracking_worker: TrackingWorker  
    +export_service: ExportService  
    +command_manager: CommandManager  
    +config_manager: ConfigManager  
    +keyboard_handler: KeyboardShortcutHandler  
    +button_filter: ButtonKeyEventFilter  
    +temp_bboxes_for_tracking: List[Tuple[int, BoundingBox]]  
    +setup_ui()  
    +_connect_signals()  
    +keyPressEvent(event)  
    +set_edit_mode(enabled)  
    +start_playback()  
    +pause_playback()  
    +load_video(file_path)  
    +start_tracking(assigned_track_id, assigned_label)  
    +on_tracking_completed(results)  
    +export_annotations(format)  
}  

%% キーボードショートカットハンドラー  
class KeyboardShortcutHandler {  
    +main_widget: MASAAnnotationWidget  
    +menu_panel: MenuPanel  
    +video_control: VideoControlPanel  
    +video_preview: VideoPreviewWidget  
    +command_manager: CommandManager  
    +_ctrl_handlers: Dict[int, Callable]  
    +_ctrl_shift_handlers: Dict[int, Callable]  
    +_single_key_handlers: Dict[int, Callable]  
    +handle_key_press(event): bool  
    +_should_ignore_shortcut(event): bool  
    +_handle_ctrl_shortcuts(event): bool  
    +_handle_ctrl_shift_shortcuts(event): bool  
    +_handle_single_key_shortcuts(event): bool  
}  

%% ボタンキーイベントフィルター  
class ButtonKeyEventFilter {  
    +eventFilter(obj, event)  
}  

%% タブベースMenuPanel  
class MenuPanel {  
    +config_manager: ConfigManager  
    +annotation_repository: AnnotationRepository  
    +command_manager: CommandManager  
    +main_widget: MASAAnnotationWidget  
    +tab_widget: QTabWidget  
    +basic_tab: BasicTabWidget  
    +annotation_tab: AnnotationTabWidget  
    +object_list_tab: ObjectListTabWidget  
    +license_tab: LicenseTabWidget  
    +clipboard_annotation: ObjectAnnotation  
    +setup_ui()  
    +keyPressEvent(event)  
}  

%% タブウィジェット群  
class BasicTabWidget {  
    +config_manager: ConfigManager  
    +annotation_repository: AnnotationRepository  
    +command_manager: CommandManager  
    +main_widget: MASAAnnotationWidget  
    +export_service: ExportService  
    +export_worker: COCOExportWorker  
    +save_masa_json_btn: QPushButton  
    +save_coco_json_btn: QPushButton  
    +video_info_label: QLabel  
    +json_info_label: QLabel  
    +export_progress_label: QLabel  
    +_on_load_video_clicked(path)  
    +_on_load_json_clicked(path)  
    +_on_export_masa_clicked()  
    +_on_export_coco_clicked()  
}  

class AnnotationTabWidget {  
    +config_manager: ConfigManager  
    +annotation_repository: AnnotationRepository  
    +command_manager: CommandManager  
    +main_widget: MASAAnnotationWidget  
    +current_selected_annotation: ObjectAnnotation  
    +edit_mode_btn: QPushButton  
    +tracking_annotation_btn: QPushButton  
    +copy_annotations_btn: QPushButton  
    +execute_add_btn: QPushButton  
    +copy_annotation_btn: QPushButton  
    +paste_annotation_btn: QPushButton  
    +delete_single_annotation_btn: QPushButton  
    +delete_track_btn: QPushButton  
    +propagate_label_btn: QPushButton  
    +align_track_ids_btn: QPushButton  
    +_on_edit_mode_clicked(checked)  
    +_on_tracking_annotation_clicked(checked)  
    +_on_copy_annotations_clicked(checked)  
    +_on_complete_tracking_clicked()  
    +_on_copy_annotation_clicked()  
    +_on_paste_annotation_clicked()  
    +_on_delete_single_annotation_clicked()  
    +_on_delete_track_clicked()  
    +_on_propagate_label_clicked()  
    +_on_align_track_ids_clicked()  
    +_on_undo_clicked()  
    +_on_redo_clicked()  
}  

class ObjectListTabWidget {  
    +config_manager: ConfigManager  
    +annotation_repository: AnnotationRepository  
    +command_manager: CommandManager  
    +main_widget: MASAAnnotationWidget  
    +current_frame_id: int  
    +current_annotations: List[ObjectAnnotation]  
    +selected_annotation: ObjectAnnotation  
    +score_threshold: float  
    +object_table: QTableWidget  
    +score_threshold_spinbox: QDoubleSpinBox  
    +update_current_frame_objects(frame_id, frame_annotation)  
    +update_object_list_selection(annotation)  
    +set_object_list_score_threshold(threshold)  
}  

class LicenseTabWidget {  
    +config_manager: ConfigManager  
    +annotation_repository: AnnotationRepository  
    +command_manager: CommandManager  
    +main_widget: MASAAnnotationWidget  
    +license_text: QTextEdit  
    +setup_ui()  
}  

%% UIコンポーネント  
class VideoPreviewWidget {  
    +bbox_editor: BoundingBoxEditor  
    +visualizer: AnnotationVisualizer  
    +coordinate_transform: CoordinateTransform  
    +mode_manager: ModeManager  
    +main_widget: MASAAnnotationWidget  
    +video_manager: VideoManager  
    +annotation_repository: AnnotationRepository  
    +config_manager: ConfigManager  
    +temp_tracking_annotations: List  
    +score_threshold: float  
    +set_video_manager(video_manager)  
    +set_annotation_repository(repo)  
    +set_config_manager(config_manager)  
    +update_frame_display()  
    +set_mode(mode_name)  
    +set_editing_mode(enabled)  
    +clear_temp_tracking_annotations()  
    +mousePressEvent(event)  
    +mouseMoveEvent(event)  
    +mouseReleaseEvent(event)  
}  

class VideoControlPanel {  
    +range_slider: RangeSlider  
    +frame_slider: QSlider  
    +frame_input: QLineEdit  
    +jump_btn: QPushButton  
    +play_btn: QPushButton  
    +main_widget: MASAAnnotationWidget  
    +current_frame: int  
    +total_frames: int  
    +keyPressEvent(event)  
    +prev_frame()  
    +next_frame()  
    +jump_to_frame()  
    +set_total_frames(total)  
    +set_current_frame(frame)  
    +set_play_button_state(is_playing)  
}  

class BoundingBoxEditor {  
    +coordinate_transform: CoordinateTransform  
    +selected_annotation: ObjectAnnotation  
    +is_editing: bool  
    +is_dragging: bool  
    +drag_start_pos: QPoint  
    +selection_changed: pyqtSignal  
    +set_editing_mode(enabled)  
    +select_annotation_at_position(pos, annotations)  
    +start_drag_operation(pos)  
    +draw_selection_overlay(frame)  
    +start_new_bbox_drawing(start_point)  
}  

class RangeSlider {  
    +minimum: int  
    +maximum: int  
    +low: int  
    +high: int  
    +range_changed: pyqtSignal  
    +frame_preview: pyqtSignal  
    +setMinimum(minimum)  
    +setMaximum(maximum)  
    +setLow(low)  
    +setHigh(high)  
    +paintEvent(event)  
    +mousePressEvent(event)  
    +mouseMoveEvent(event)  
}  

%% データ管理  
class AnnotationRepository {  
    +frame_annotations: Dict[int, FrameAnnotation]  
    +manual_annotations: Dict[int, List[ObjectAnnotation]]  
    +next_object_id: int  
    +add_annotation(annotation)  
    +get_annotations(frame_id)  
    +update_annotation(annotation)  
    +delete_annotation(object_id, frame_id)  
    +delete_by_track_id(track_id)  
    +get_statistics()  
    +get_all_labels()  
    +clear()  
    +get_max_track_id()  
}  

class VideoManager {  
    +video_path: str  
    +video_reader: cv2.VideoCapture  
    +total_frames: int  
    +fps: float  
    +video_width: int  
    +video_height: int  
    +frame_lock: threading.Lock  
    +load_video(file_path)  
    +get_frame(frame_id)  
    +get_fps()  
    +get_total_frames()  
    +get_video_width()  
    +get_video_height()  
    +release()  
}  

class ExportService {  
    +export_masa_json(annotations, video_path, file_path)  
    +export_coco(annotations, video_path, file_path, video_manager)  
    +export_coco_with_progress(annotations, video_path, file_path, video_manager, progress_callback)  
    +import_json(path)  
}  

class COCOExportWorker {  
    +export_service: ExportService  
    +frame_annotations: Dict  
    +video_path: str  
    +file_path: str  
    +video_manager: VideoManager  
    +progress_updated: pyqtSignal  
    +export_completed: pyqtSignal  
    +error_occurred: pyqtSignal  
    +run()  
    +emit_progress(current, total)  
}  

class JSONLoader {  
    +load_masa_json(file_path)  
    +load_coco_json(file_path)  
    +validate_json_format(data)  
    +convert_to_internal_format(data)  
}  

%% コマンドパターン  
class CommandManager {  
    +command_history: List  
    +current_index: int  
    +execute_command(command)  
    +undo(): bool  
    +redo(): bool  
    +can_undo(): bool  
    +can_redo(): bool  
}  

%% ユーティリティクラス  
class ConfigManager {  
    -_observers: List  
    -_config: MASAConfig  
    +update_config(key, value)  
    +get_config(key)  
    +get_full_config(config_type)  
    +add_observer(observer)  
    +_notify_observers(key, value)  
}  

class ErrorHandler {  
    +handle_with_dialog(func)  
    +log_error(error, context)  
    +show_error_dialog(message)  
    +show_info_dialog(message, title)  
    +show_warning_dialog(message, title)  
}  

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
    +update_transform(widget_size, image_size)  
}  

class ModeManager {  
    +current_mode: AnnotationMode  
    +current_mode_name: str  
    +set_mode(mode_type)  
    +handle_mouse_event(event)  
    +get_cursor_shape()  
}  

class AnnotationVisualizer {  
    +colors: List[Tuple]  
    +draw_annotations(frame, annotations, show_ids, show_confidence, selected_annotation)  
    +create_annotation_video()  
    +get_color_for_track_id(track_id)  
}  

%% 処理系クラス  
class ObjectTracker {  
    +config: MASAConfig  
    +masa_model: nn.Module  
    +last_frame_id: int  
    +initialize()  
    +track_objects(frame, frame_id, initial_annotations, texts)  
    +reset_tracking_state()  
    +_convert_track_result_to_annotations(track_result, frame_id, texts)  
}  

class TrackingWorker {  
    +video_manager: VideoManager  
    +annotation_repository: AnnotationRepository  
    +object_tracker: ObjectTracker  
    +start_frame: int  
    +end_frame: int  
    +initial_annotations: List  
    +assigned_track_id: int  
    +assigned_label: str  
    +max_used_track_id: int  
    +progress_updated: pyqtSignal  
    +tracking_completed: pyqtSignal  
    +error_occurred: pyqtSignal  
    +run()  
    +process_tracking_with_progress()  
}  

class VideoPlaybackController {  
    +video_manager: VideoManager  
    +timer: QTimer  
    +current_frame: int  
    +is_playing: bool  
    +fps: float  
    +frame_updated: pyqtSignal  
    +playback_finished: pyqtSignal  
    +play(start_frame)  
    +pause()  
    +stop()  
    +next_frame()  
    +set_fps(fps)  
}  

%% ダイアログクラス  
class TrackingResultConfirmDialog {  
    +tracking_results: Dict  
    +video_manager: VideoManager  
    +approved: bool  
    +visualizer: AnnotationVisualizer  
    +current_frame_id: int  
    +grouped_tracking_results: Dict[int, List[ObjectAnnotation]]  
    +track_selected: Dict[int, bool]  
    +track_list_widget: QListWidget  
    +preview_widget: QLabel  
    +frame_slider: QSlider  
    +setup_ui()  
    +update_preview()  
    +approve_results()  
    +reject_results()  
}  

class AnnotationInputDialog {  
    +label_input: QLineEdit  
    +track_id_input: QSpinBox  
    +confidence_input: QDoubleSpinBox  
    +get_annotation_data()  
    +set_default_values(label, track_id, confidence)  
}  

%% データクラス  
class ObjectAnnotation {  
    +object_id: int  
    +label: str  
    +bbox: BoundingBox  
    +frame_id: int  
    +track_id: int  
    +is_manual: bool  
    +track_confidence: float  
    +is_batch_added: bool  
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

class BoundingBox {
+x1: float
+y1: float
+x2: float
+y2: float
+confidence: float
+post_init()
+validate()
+to_xyxy()
+area()
}

class MASAConfig {
+model_config: Dict
+tracking_config: Dict
+ui_config: Dict
+post_init()
+validate()
}

%% 関係性
MASAAnnotationApp --> MASAAnnotationWidget : contains

MASAAnnotationWidget --> MenuPanel : contains
MASAAnnotationWidget --> VideoPreviewWidget : contains
MASAAnnotationWidget --> VideoControlPanel : contains
MASAAnnotationWidget --> KeyboardShortcutHandler : contains
MASAAnnotationWidget --> ButtonKeyEventFilter : contains
MASAAnnotationWidget --> VideoManager : uses
MASAAnnotationWidget --> AnnotationRepository : uses
MASAAnnotationWidget --> ExportService : uses
MASAAnnotationWidget --> ObjectTracker : uses
MASAAnnotationWidget --> ConfigManager : uses
MASAAnnotationWidget --> CommandManager : uses
MASAAnnotationWidget --> VideoPlaybackController : uses
MASAAnnotationWidget --> TrackingWorker : uses

KeyboardShortcutHandler --> MASAAnnotationWidget : references
KeyboardShortcutHandler --> MenuPanel : delegates to
KeyboardShortcutHandler --> VideoControlPanel : delegates to
KeyboardShortcutHandler --> VideoPreviewWidget : delegates to
KeyboardShortcutHandler --> CommandManager : delegates to

MenuPanel --> BasicTabWidget : contains
MenuPanel --> AnnotationTabWidget : contains
MenuPanel --> ObjectListTabWidget : contains
MenuPanel --> LicenseTabWidget : contains
MenuPanel --> ConfigManager : uses
MenuPanel --> AnnotationRepository : uses
MenuPanel --> CommandManager : uses

BasicTabWidget --> ConfigManager : uses
BasicTabWidget --> AnnotationRepository : uses
BasicTabWidget --> CommandManager : uses
BasicTabWidget --> MASAAnnotationWidget : references
BasicTabWidget --> ExportService : uses
BasicTabWidget --> COCOExportWorker : uses
BasicTabWidget --> JSONLoader : uses

AnnotationTabWidget --> ConfigManager : uses
AnnotationTabWidget --> AnnotationRepository : uses
AnnotationTabWidget --> CommandManager : uses
AnnotationTabWidget --> MASAAnnotationWidget : references
AnnotationTabWidget --> AnnotationInputDialog : uses

ObjectListTabWidget --> ConfigManager : uses
ObjectListTabWidget --> AnnotationRepository : uses
ObjectListTabWidget --> CommandManager : uses
ObjectListTabWidget --> MASAAnnotationWidget : references

LicenseTabWidget --> ConfigManager : uses
LicenseTabWidget --> AnnotationRepository : uses
LicenseTabWidget --> CommandManager : uses
LicenseTabWidget --> MASAAnnotationWidget : references

VideoPreviewWidget --> BoundingBoxEditor : contains
VideoPreviewWidget --> AnnotationVisualizer : contains
VideoPreviewWidget --> CoordinateTransform : uses
VideoPreviewWidget --> ModeManager : uses
VideoPreviewWidget --> MASAAnnotationWidget : references
VideoPreviewWidget --> VideoManager : uses
VideoPreviewWidget --> AnnotationRepository : uses
VideoPreviewWidget --> ConfigManager : uses

VideoControlPanel --> RangeSlider : contains
VideoControlPanel --> MASAAnnotationWidget : references

BoundingBoxEditor --> CoordinateTransform : uses
BoundingBoxEditor --> AnnotationRepository : uses

RangeSlider --> VideoControlPanel : signals to

AnnotationRepository --> FrameAnnotation : manages
AnnotationRepository --> ObjectAnnotation : manages

ExportService --> AnnotationRepository : uses
ExportService --> VideoManager : uses

COCOExportWorker --> ExportService : uses
COCOExportWorker --> VideoManager : uses

JSONLoader --> AnnotationRepository : populates

CommandManager --> AnnotationRepository : operates on

ConfigManager --> MASAConfig : manages

CoordinateTransform --> VideoManager : uses dimensions from

ModeManager --> AnnotationVisualizer : uses for drawing

AnnotationVisualizer --> ObjectAnnotation : visualizes
AnnotationVisualizer --> BoundingBox : draws

ObjectTracker --> ConfigManager : uses config from
ObjectTracker --> MASAConfig : configured by

TrackingWorker --> VideoManager : uses
TrackingWorker --> AnnotationRepository : uses
TrackingWorker --> ObjectTracker : uses
TrackingWorker --> MASAAnnotationWidget : signals to

VideoPlaybackController --> VideoManager : uses
VideoPlaybackController --> VideoControlPanel : signals to

TrackingResultConfirmDialog --> VideoManager : uses
TrackingResultConfirmDialog --> AnnotationVisualizer : uses
TrackingResultConfirmDialog --> ObjectAnnotation : displays

AnnotationInputDialog --> ObjectAnnotation : creates
AnnotationInputDialog --> BoundingBox : creates

FrameAnnotation --> ObjectAnnotation : contains
ObjectAnnotation --> BoundingBox : contains

%% エラーハンドリング（全体に適用）
ErrorHandler ..> MASAAnnotationWidget : decorates
ErrorHandler ..> VideoManager : decorates
ErrorHandler ..> AnnotationRepository : decorates
ErrorHandler ..> ExportService : decorates
ErrorHandler ..> ObjectTracker : decorates
ErrorHandler ..> TrackingWorker : decorates
ErrorHandler ..> COCOExportWorker : decorates
```

## Classes

各クラスの機能説明表を以下に示します：

| クラス名                       | ファイル名                        | 主要機能                     | 責任範囲・説明                                               |
|-------------------------------|-----------------------------------|------------------------------|--------------------------------------------------------------|
| MASAAnnotationApp             | MASAAnnotationApp.py              | アプリケーションエントリーポイント | コマンドライン引数解析、GUI起動制御                          |
| MASAAnnotationWidget          | MASAAnnotationWidget.py           | メインウィジェット・オーケストレーター | UI全体の統合、コンポーネント間調整、シグナル接続             |
| KeyboardShortcutHandler       | KeyboardShortcutHandler.py         | キーボードショートカット処理 | キーイベント処理の分離、Strategyパターンによる委譲           |
| MenuPanel                     | MenuPanel.py                      | 左側メニューパネル           | タブベースUI、各タブからのシグナル転送                       |
| BasicTabWidget                | BasicTabWidget.py                 | 基本操作タブ                 | ファイル読み込み・保存、エクスポート機能                      |
| AnnotationTabWidget           | AnnotationTabWidget.py            | アノテーション編集タブ        | 編集モード、トラッキング、コピー・ペースト機能                |
| ObjectListTabWidget           | ObjectListTabWidget.py            | オブジェクト一覧タブ          | アノテーション一覧表示・管理、フィルタリング機能              |
| LicenseTabWidget              | LicenseTabWidget.py               | ライセンス情報タブ            | ライセンス表示                                               |
| VideoPreviewWidget            | VideoPreviewWidget.py             | 動画プレビュー表示            | フレーム表示、アノテーション描画、マウス操作処理              |
| VideoControlPanel             | VideoControlPanel.py              | 動画制御パネル                | フレーム操作、再生制御、範囲選択                              |
| BoundingBoxEditor             | BoundingBoxEditor.py               | バウンディングボックス編集     | アノテーション選択・編集、座標変換                            |
| AnnotationRepository          | AnnotationRepository.py            | アノテーションデータ管理       | データ永続化、CRUD操作、統計情報提供                          |
| VideoManager                  | VideoManager.py                   | 動画ファイル管理              | 動画読み込み、フレーム取得、メタデータ管理                    |
| ExportService                 | ExportService.py                  | データエクスポート             | MASA JSON・COCO形式でのデータ出力                            |
| COCOExportWorker              | COCOExportWorker.py               | COCO形式エクスポートワーカー   | バックグラウンドでのCOCO形式データ出力                        |
| CommandManager                | CommandPattern.py                 | コマンドパターン実装           | Undo/Redo機能、操作履歴管理                                   |
| ConfigManager                 | ConfigManager.py                  | 設定管理                       | Observerパターンによる設定変更通知                            |
| ErrorHandler                  | ErrorHandler.py                   | エラーハンドリング              | 例外処理、ユーザー向けエラーダイアログ表示                    |
| ObjectTracker                 | ObjectTracker.py                  | オブジェクト追跡                | MASAモデルを使用した自動追跡処理                              |
| TrackingWorker                | TrackingWorker.py                 | 追跡処理ワーカー                | バックグラウンドでの追跡処理、進捗通知                        |
| VideoPlaybackController       | VideoPlaybackController.py        | 動画再生制御                    | タイマーベースの自動再生、フレーム更新                        |
| CoordinateTransform           | CoordinateTransform.py            | 座標変換ウィジェット             | ウィジェット座標と画像座標の相互変換                          |
| ModeManager                   | ModeManager.py                    | モード管理                        | StateパターンによるUI操作モード制御                           |
| AnnotationVisualizer          | AnnotationVisualizer.py           | アノテーション描画                 | バウンディングボックスの視覚化                                |
| RangeSlider                   | RangeSlider.py                    | 範囲選択スライダー                  | フレーム範囲選択UI、カスタムスライダーウィジェット            |
| JSONLoader                    | JSONLoader.py                     | JSONファイル読み込み                  | アノテーションファイルの読み込み・解析                        |
| TrackingResultConfirmDialog   | TrackingResultConfirmDialog.py    | 追跡結果確認ダイアログ                   | 追跡結果の確認・編集UI                                       |
| AnnotationInputDialog         | AnnotationInputDialog.py          | アノテーション入力ダイアログ                  | 新規アノテーション作成時の入力UI                              |
| ObjectAnnotationDataClass     | ObjectAnnotationDataClass.py      | オブジェクトアノテーションデータクラス           | アノテーション情報の構造化データ                              |
| FrameAnnotationDataClass      | FrameAnnotationDataClass.py       | フレームアノテーションデータクラス              | フレーム単位のアノテーション管理                              |
| BoundingBoxDataClass          | BoundingBoxDataClass.py           | バウンディングボックスデータクラス               | 矩形領域の座標情報管理                                        |
| MASAConfigDataClass           | MASAConfigDataClass.py            | MASA設定データクラス                        | アプリケーション設定の構造化データ                            |


## アーキテクチャ上の特徴 

1. 責任分離 
   - UI層（Widget系）、データ層（Repository、Manager系）、処理層（Worker、Tracker系）が明確に分離
   - 各クラスが単一責任を持つ設計
2. デザインパターンの活用 
   - Strategy パターン: KeyboardShortcutHandlerでのキーイベント処理
   - Observer パターン: ConfigManagerでの設定変更通知
   - Command パターン: CommandManagerでのUndo/Redo機能
   - Repository パターン: AnnotationRepositoryでのデータ管理
3. タブベースUI 
   - MenuPanelが4つのタブウィジェットを統合
   - 機能別にタブが分離され、保守性が向上
4. 非同期処理 
   - TrackingWorkerによるバックグラウンド処理
   - UIの応答性を維持しながら重い処理を実行