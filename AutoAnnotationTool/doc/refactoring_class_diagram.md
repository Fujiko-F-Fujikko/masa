# MASAAnnotationTool リファクタリング計画 - クラス図（ファサードパターン版）

## 概要
MASAAnnotationWidget.py（895行）とMenuPanel.py（733行）の肥大化を解決するためのリファクタリング計画のクラス図です。
ファサードパターンを採用し、依存関係を整理して可読性を向上させます。

## 現在の問題
- **MASAAnnotationWidget.py**: 895行（UI、イベント処理、ビジネスロジック、状態管理、ファイル操作が混在）
- **MenuPanel.py**: 733行（複数タブのUI、設定管理、ボタンアクション、状態同期が混在）
- **依存関係の複雑化**: MASAAnnotationWidgetが多くのクラスを直接参照

## リファクタリング後のクラス構成

### 1. ファサード層（新規追加）

```mermaid
classDiagram
    class MASAApplicationService {
        -config_manager: ConfigManager
        -annotation_repository: AnnotationRepository
        -command_manager: CommandManager
        -video_manager: VideoManager
        -export_service: ExportService
        -object_tracker: ObjectTracker
        +__init__()
        +create_annotation(x1, y1, x2, y2, label): bool
        +delete_annotation(annotation): bool
        +delete_track(track_id): int
        +update_label(annotation, new_label): bool
        +propagate_label(track_id, new_label): int
        +load_video(path): bool
        +load_json(path): bool
        +export_masa_json(path): bool
        +export_coco_json(path): bool
        +get_display_config(): DisplayConfig
        +update_display_setting(key, value)
        +execute_command(command): Any
        +undo(): bool
        +redo(): bool
        +start_tracking(track_id, label, start_frame, end_frame): bool
    }
    
    class MASAAnnotationWidget {
        -app_service: MASAApplicationService
        -main_ui_controller: MainUIController
        -keyboard_shortcut_manager: KeyboardShortcutManager
        +__init__()
        +setup_connections()
        +on_bbox_created(x1, y1, x2, y2)
        +on_delete_annotation_requested(annotation)
        +on_tracking_requested(track_id, label)
        +on_config_changed(key, value)
    }
    
    MASAAnnotationWidget --> MASAApplicationService
    MASAAnnotationWidget --> MainUIController
    MASAAnnotationWidget --> KeyboardShortcutManager
```

### 2. UI管理層

```mermaid
classDiagram
    class MainUIController {
        -app_service: MASAApplicationService
        -menu_panel: MenuPanel
        -video_preview: VideoPreviewWidget
        -video_control: VideoControlPanel
        -splitter: QSplitter
        +__init__(parent, app_service)
        +setup_main_layout()
        +setup_splitter()
        +connect_components()
        +refresh_display()
        +get_menu_panel(): MenuPanel
        +get_video_preview(): VideoPreviewWidget
    }
    
    class KeyboardShortcutManager {
        -app_service: MASAApplicationService
        -main_controller: MainUIController
        -shortcut_mappings: Dict[str, Callable]
        +__init__(app_service, main_controller)
        +setup_shortcuts()
        +handle_key_event(event: QKeyEvent)
        +register_shortcut(key_combo: str, action: Callable)
        +is_text_input_focused(): bool
    }
    
    MainUIController --> MASAApplicationService
    KeyboardShortcutManager --> MASAApplicationService
    KeyboardShortcutManager --> MainUIController
```

### 3. メニューパネル層

```mermaid
classDiagram
    class MenuPanel {
        -config_manager: ConfigManager
        -tab_widget: QTabWidget
        -basic_settings_tab: BasicSettingsTabManager
        -annotation_edit_tab: AnnotationEditTabManager
        -object_list_tab: ObjectListTabManager
        -info_sync_manager: AnnotationInfoSyncManager
        +__init__(config_manager)
        +setup_tab_widget()
        +connect_tab_signals()
        +get_basic_settings_tab(): BasicSettingsTabManager
        +get_annotation_edit_tab(): AnnotationEditTabManager
        +get_object_list_tab(): ObjectListTabManager
    }
    
    class BasicSettingsTabManager {
        -config_manager: ConfigManager
        -file_group: QGroupBox
        -playback_group: QGroupBox
        -display_group: QGroupBox
        +__init__(config_manager, parent)
        +setup_file_operations()
        +setup_playback_controls()
        +setup_display_options()
        +update_video_info(path, frames)
        +update_json_info(path, count)
        +get_display_options(): Dict
    }
    
    class AnnotationEditTabManager {
        -annotation_repository: AnnotationRepository
        -edit_controls: Dict[str, QWidget]
        +__init__(parent)
        +setup_annotation_info()
        +setup_edit_controls()
        +setup_undo_redo()
        +setup_tracking_controls()
        +update_edit_controls_state(enabled: bool)
        +update_undo_redo_buttons(command_manager)
    }
    
    class ObjectListTabManager {
        -current_frame_id: int
        -current_annotations: List[ObjectAnnotation]
        -score_threshold: float
        -table: QTableWidget
        -filters: Dict[str, QWidget]
        +__init__(parent)
        +setup_ui()
        +setup_table()
        +update_frame_data(frame_id, frame_annotation)
        +apply_filters()
        +select_annotation(annotation)
        +get_selected_annotation(): ObjectAnnotation
    }
    
    MenuPanel --> BasicSettingsTabManager
    MenuPanel --> AnnotationEditTabManager  
    MenuPanel --> ObjectListTabManager
```

### 4. 情報同期管理層

```mermaid
classDiagram
    class AnnotationInfoSyncManager {
        -current_selected_annotation: ObjectAnnotation
        -label_combo: QComboBox
        -track_id_edit: QLineEdit
        -annotation_count_label: QLabel
        +__init__(parent)
        +update_selected_annotation_info(annotation)
        +update_annotation_count(total, manual)
        +initialize_label_combo(labels)
        +sync_object_list_selection(annotation)
        +sync_ui_elements()
    }
    
    MenuPanel --> AnnotationInfoSyncManager
    AnnotationInfoSyncManager --> ObjectListTabManager
```

### 5. 既存クラス（拡張）

```mermaid
classDiagram
    class ExportService {
        +export_coco_with_progress()
        +export_masa_json()
        +import_json()
        +load_video_file(path): bool
        +load_json_file(path): Dict
        +set_progress_callback(callback)
        +get_export_progress(): float
    }
    
    class ConfigManager {
        +update_config(key, value, config_type)
        +get_config(key, config_type)
        +get_full_config(config_type)
        +add_observer(observer)
        +notify_observers(key, value, config_type)
    }
```

## 全体クラス図

### ファサードパターンによる全体アーキテクチャ

```mermaid
classDiagram
    %% ファサード層
    class MASAApplicationService {
        -config_manager: ConfigManager
        -annotation_repository: AnnotationRepository
        -command_manager: CommandManager
        -video_manager: VideoManager
        -export_service: ExportService
        -object_tracker: ObjectTracker
        +create_annotation()
        +delete_annotation()
        +load_video()
        +export_json()
        +execute_command()
        +undo()
        +redo()
    }
    
    %% メイン統合クラス（依存関係を大幅削減）
    class MASAAnnotationWidget {
        -app_service: MASAApplicationService
        -main_ui_controller: MainUIController
        -keyboard_shortcut_manager: KeyboardShortcutManager
        +__init__()
        +setup_connections()
        +on_bbox_created()
        +on_delete_annotation_requested()
    }
    
    %% UIコントローラ
    class MainUIController {
        -app_service: MASAApplicationService
        -menu_panel: MenuPanel
        -video_preview: VideoPreviewWidget
        -video_control: VideoControlPanel
        -splitter: QSplitter
        +setup_main_layout()
        +refresh_display()
    }
    
    %% ショートカット管理
    class KeyboardShortcutManager {
        -app_service: MASAApplicationService
        -main_controller: MainUIController
        -shortcut_mappings: Dict
        +setup_shortcuts()
        +handle_key_event()
    }
    
    %% メニューパネル統合
    class MenuPanel {
        -app_service: MASAApplicationService
        -tab_widget: QTabWidget
        -basic_settings_tab: BasicSettingsTabManager
        -annotation_edit_tab: AnnotationEditTabManager
        -object_list_tab: ObjectListTabManager
        -info_sync_manager: AnnotationInfoSyncManager
        +setup_tab_widget()
        +connect_tab_signals()
    }
    
    %% タブマネージャー群
    class BasicSettingsTabManager {
        -app_service: MASAApplicationService
        +setup_file_operations()
        +setup_playback_controls()
        +setup_display_options()
    }
    
    class AnnotationEditTabManager {
        -app_service: MASAApplicationService
        +setup_annotation_info()
        +setup_edit_controls()
        +setup_undo_redo()
        +setup_tracking_controls()
    }
    
    class ObjectListTabManager {
        -app_service: MASAApplicationService
        -table: QTableWidget
        -filters: Dict
        +update_frame_data()
        +apply_filters()
        +select_annotation()
    }
    
    %% 情報同期管理
    class AnnotationInfoSyncManager {
        -app_service: MASAApplicationService
        -current_selected_annotation: ObjectAnnotation
        +update_selected_annotation_info()
        +sync_object_list_selection()
    }
    
    %% 既存クラス（変更なし）
    class ConfigManager {
        +update_config()
        +get_config()
        +add_observer()
    }
    
    class AnnotationRepository {
        +add_annotation()
        +delete_annotation()
        +get_annotations()
    }
    
    class CommandManager {
        +execute_command()
        +undo()
        +redo()
    }
    
    class ExportService {
        +export_coco_with_progress()
        +export_masa_json()
        +import_json()
        +load_video_file()
        +load_json_file()
    }
    
    class VideoManager {
        +load_video()
        +get_frame()
        +get_total_frames()
    }
    
    class ObjectTracker {
        +initialize()
        +track_objects()
    }
    
    class VideoPreviewWidget {
        +set_frame()
        +update_frame_display()
    }
    
    class VideoControlPanel {
        +set_current_frame()
        +get_selected_range()
    }
    
    class BoundingBoxEditor {
        +set_editing_mode()
        +draw_selection_overlay()
    }
    
    class ErrorHandler {
        +show_error_dialog()
        +handle_with_dialog()
    }
    
    %% 依存関係（大幅に削減・整理）
    MASAAnnotationWidget --> MASAApplicationService
    MASAAnnotationWidget --> MainUIController
    MASAAnnotationWidget --> KeyboardShortcutManager
    
    MainUIController --> MASAApplicationService
    MainUIController --> MenuPanel
    MainUIController --> VideoPreviewWidget
    MainUIController --> VideoControlPanel
    
    KeyboardShortcutManager --> MASAApplicationService
    
    MenuPanel --> MASAApplicationService
    MenuPanel --> BasicSettingsTabManager
    MenuPanel --> AnnotationEditTabManager
    MenuPanel --> ObjectListTabManager
    MenuPanel --> AnnotationInfoSyncManager
    
    BasicSettingsTabManager --> MASAApplicationService
    AnnotationEditTabManager --> MASAApplicationService
    ObjectListTabManager --> MASAApplicationService
    AnnotationInfoSyncManager --> MASAApplicationService
    
    %% ファサードがすべてのサービスを管理
    MASAApplicationService --> ConfigManager
    MASAApplicationService --> AnnotationRepository
    MASAApplicationService --> CommandManager
    MASAApplicationService --> ExportService
    MASAApplicationService --> VideoManager
    MASAApplicationService --> ObjectTracker
    
    VideoPreviewWidget --> BoundingBoxEditor
    
    %% すべてのクラスがErrorHandlerを使用
    MASAApplicationService --> ErrorHandler
    BasicSettingsTabManager --> ErrorHandler
    AnnotationEditTabManager --> ErrorHandler
    ObjectListTabManager --> ErrorHandler
```

## シグナル/スロット接続図（ファサードパターン版）

```mermaid
sequenceDiagram
    participant MW as MASAAnnotationWidget
    participant AS as MASAApplicationService
    participant MC as MainUIController
    participant MP as MenuPanel
    participant BST as BasicSettingsTabManager
    participant AET as AnnotationEditTabManager
    participant OLT as ObjectListTabManager
    participant AIS as AnnotationInfoSyncManager
    
    Note over MW,AS: 初期化フェーズ
    MW->>AS: create MASAApplicationService()
    MW->>MC: create MainUIController(app_service)
    MC->>MP: create MenuPanel(app_service)
    MP->>BST: create BasicSettingsTabManager(app_service)
    MP->>AET: create AnnotationEditTabManager(app_service)
    MP->>OLT: create ObjectListTabManager(app_service)
    MP->>AIS: create AnnotationInfoSyncManager(app_service)
    
    Note over MW,AS: 動画読み込みフロー
    BST->>MW: load_video_requested(path)
    MW->>AS: load_video(path)
    AS->>AS: delegate to VideoManager
    AS-->>MW: success/failure
    MW->>MC: refresh_display()
    
    Note over MW,AS: アノテーション作成フロー
    MW->>AS: create_annotation(x1, y1, x2, y2, label)
    AS->>AS: delegate to AnnotationRepository & CommandManager
    AS-->>MW: success/failure
    MW->>MC: refresh_display()
    
    Note over MW,AS: オブジェクト選択フロー
    OLT->>AIS: object_selected(annotation)
    AIS->>MW: annotation_selected(annotation)
    MW->>AS: update_selection(annotation)
    AS-->>MW: selection_updated
    MW->>MC: refresh_display()
```

## ファイル構成（ファサードパターン版）

### リファクタリング後のファイル一覧

```
AutoAnnotationTool/src/MASAAnnotationApp/
├── MASAApplicationService.py            # 200行程度（ファサード層）
├── MASAAnnotationWidget.py              # 200行程度（メイン統合・大幅縮小）
├── MainUIController.py                  # 200行程度（UIレイアウト）
├── KeyboardShortcutManager.py           # 150行程度（ショートカット）
├── MenuPanel.py                         # 150行程度（タブ統合・縮小）
├── BasicSettingsTabManager.py           # 200行程度（基本設定タブ）
├── AnnotationEditTabManager.py          # 200行程度（編集タブ）
├── ObjectListTabManager.py              # 350行程度（オブジェクト一覧タブ）
├── AnnotationInfoSyncManager.py         # 150行程度（情報同期）
└── ExportService.py                     # 200行程度（拡張済み）
```

### 既存ファイル（変更なし）
```
├── AnnotationRepository.py              # データ管理
├── CommandPattern.py                    # コマンドパターン
├── ConfigManager.py                     # 設定管理
├── VideoPreviewWidget.py                # 動画表示
├── BoundingBoxEditor.py                 # 編集機能
├── ErrorHandler.py                      # エラー処理
└── その他のユーティリティクラス
```

## ファサードパターンによるリファクタリングの利点

### 1. 依存関係の大幅削減 ⭐
- **Before**: MASAAnnotationWidgetが6つのクラスを直接参照
- **After**: MASAApplicationServiceのみを参照（83%の依存関係削減）
- 新しいサービス追加時にメインクラスを変更不要

### 2. 可読性の向上 ⭐⭐
- メソッド名が直感的（`app.create_annotation()`, `app.load_video()`）
- 処理の流れが追いやすい
- IDEの補完機能が効果的に働く

### 3. 単一責任原則の実現
- **MASAAnnotationWidget**: UI統合とイベント処理のみ
- **MASAApplicationService**: ビジネスロジックの窓口
- **各TabManager**: 特定タブの責任のみ

### 4. テスタビリティの向上
- `MASAApplicationService`をモック化すれば全体テスト可能
- 各Managerの独立テストが容易
- 依存関係がシンプルでテストケース作成が簡単

### 5. 保守性の向上
- ファイルサイズが適切（150-350行）
- 機能の所在が明確
- デバッグ時の問題箇所特定が容易

### 6. 拡張性の向上
- 新機能は`MASAApplicationService`にメソッド追加のみ
- 新しいタブ追加が標準化されたパターンで可能
- UIとビジネスロジックが完全分離

## 従来案との比較

| 項目 | 従来案 | ファサードパターン |
|------|--------|------------------|
| 依存関係数 | 6個 | 1個 |
| MASAAnnotationWidget行数 | 300行 | 200行 |
| 可読性 | 中 | 高 |
| テスト容易さ | 低 | 高 |
| 学習コスト | 中 | 低 |

## 実装順序（ファサードパターン版）

### フェーズ1: ファサード層の構築
1. **MASAApplicationService**の作成
   - 既存サービスクラスの統合
   - 直感的なメソッド名でのAPI設計
   - エラーハンドリングの統一

### フェーズ2: UI層のリファクタリング
2. **MainUIController**の作成
   - UIレイアウト管理の分離
   - app_serviceとの連携
3. **KeyboardShortcutManager**の作成
   - ショートカット処理の分離
   - app_serviceとの連携

### フェーズ3: MenuPanel層の分離
4. **基本タブマネージャー**の作成
   - BasicSettingsTabManager
   - AnnotationEditTabManager  
   - ObjectListTabManager（CurrentFrameObjectListWidgetの改名）
5. **AnnotationInfoSyncManager**の作成
   - 情報同期処理の分離

### フェーズ4: 統合とテスト
6. **MASAAnnotationWidgetのリファクタリング**
   - 既存機能の各Managerへの移行
   - シグナル/スロット接続の整理
7. **MenuPanelのリファクタリング**
   - タブ管理のみに責任を限定
8. **統合テスト**
   - 機能テスト
   - パフォーマンステスト

## 移行戦略

### 段階的移行
1. **並行開発**: 既存コードを動作させながら新クラスを作成
2. **機能単位移行**: 1つの機能ずつ新アーキテクチャに移行
3. **テスト駆動**: 各段階でテストを実行して品質確保

### リスク軽減
- 既存インターフェースの保持
- バックアップとロールバック計画
- 段階的リリースとフィードバック収集

この設計により、**可読性**、**保守性**、**拡張性**の高いアーキテクチャを実現し、将来の機能追加や変更に柔軟に対応できるようになります。
