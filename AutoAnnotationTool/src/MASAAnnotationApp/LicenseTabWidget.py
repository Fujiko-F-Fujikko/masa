# LicenseTabWidget.py  
from typing import Dict, List, Any, Optional  
from pathlib import Path  
from PyQt6.QtWidgets import (  
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,  
    QComboBox, QTextEdit  
)  
from PyQt6.QtCore import Qt, pyqtSignal  
from PyQt6.QtGui import QFont  
  
from ConfigManager import ConfigManager  
from ErrorHandler import ErrorHandler  
  
class LicenseTabWidget(QWidget):  
    """ライセンス表示タブウィジェット（ライブラリライセンス表示機能）"""  
      
    def __init__(self, config_manager: ConfigManager, annotation_repository, command_manager, main_widget, parent=None):  
        super().__init__(parent)  
        self.config_manager = config_manager  
        self.annotation_repository = annotation_repository  
        self.command_manager = command_manager  
        self.main_widget = main_widget  # MASAAnnotationWidgetへの参照  
        self.parent_menu_panel = parent  # MenuPanelへの参照  
          
        self.setup_ui()  
      
    def setup_ui(self):  
        """UIセットアップ（MenuPanelから移動）"""  
        layout = QVBoxLayout()  
        layout.setContentsMargins(5, 5, 5, 5)  
          
        # ライブラリ選択用のコンボボックス  
        library_layout = QHBoxLayout()  
        library_layout.addWidget(QLabel("Library:"))  
          
        self.license_combo = QComboBox()  
        self.license_combo.addItems([  
            "masa", "mmcv", "mmdet", "numpy",  
            "opencv-python", "PyQt6", "torch"  
        ])  
        self.license_combo.currentTextChanged.connect(self._on_license_selection_changed)  
        library_layout.addWidget(self.license_combo)  
        library_layout.addStretch()  
          
        layout.addLayout(library_layout)  
          
        # ライセンス内容表示用のテキストエリア  
        self.license_text = QTextEdit()  
        self.license_text.setReadOnly(True)  
        self.license_text.setFont(QFont("Courier", 9))  # 等幅フォント  
        self.license_text.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)  
        self.license_text.setAcceptRichText(False)  # プレーンテキストのみ受け入れ  
        layout.addWidget(self.license_text)  
          
        self.setLayout(layout)  
          
        # 初期表示（最初のライブラリのライセンスを表示）  
        if self.license_combo.count() > 0:  
            self._load_license_content(self.license_combo.itemText(0))  
      
    def _on_license_selection_changed(self, library_name: str):  
        """ライブラリ選択変更時の処理（MenuPanelから移動）"""  
        self._load_license_content(library_name)  
      
    def _load_license_content(self, library_name: str):  
        """指定されたライブラリのライセンス内容を読み込み（MenuPanelから移動・複数ファイル対応）"""  
        try:  
            # ライセンスディレクトリのパスを構築  
            license_dir = Path(__file__).parent.parent.parent / "licenses" / library_name  
  
            if not license_dir.exists():  
                self.license_text.setPlainText(  
                    f"License directory for {library_name} not found.\n"  
                    f"Path: {license_dir}"  
                )  
                return  
              
            # ディレクトリ内のすべてのファイルを取得してソート  
            license_files = sorted(license_dir.glob("*"))  
              
            if not license_files:  
                self.license_text.setPlainText(  
                    f"No license files found for {library_name}."  
                )  
                return  
              
            # 複数ファイルの内容を連結  
            combined_content = []  
            for file_path in license_files:  
                if file_path.is_file():  # ファイルのみを対象  
                    try:  
                        with open(file_path, 'r', encoding='utf-8') as f:  
                            file_content = f.read().strip()  
                          
                        # ファイル名をヘッダーとして追加  
                        combined_content.append(f"=== {file_path.name} ===")  
                        combined_content.append(file_content)  
                        combined_content.append("")  # 空行で区切り  
                          
                    except UnicodeDecodeError:  
                        # UTF-8で読めない場合は別のエンコーディングを試す  
                        try:  
                            with open(file_path, 'r', encoding='latin-1') as f:  
                                file_content = f.read().strip()  
                            combined_content.append(f"=== {file_path.name} ===")  
                            combined_content.append(file_content)  
                            combined_content.append("")  
                        except Exception as e:  
                            combined_content.append(f"=== {file_path.name} (load error) ===")  
                            combined_content.append(f"Error: {str(e)}")  
                            combined_content.append("")  
              
            # 連結した内容を表示  
            final_content = '\n\n'.join(combined_content)  
              
            # QTextEditに設定  
            self.license_text.clear()  # 既存の内容をクリア  
            self.license_text.setPlainText(final_content)  
              
        except Exception as e:  
            error_message = f"An error occurred while loading the license for {library_name}:\n{str(e)}"  
            print(f"Error: {error_message}")  
            self.license_text.setPlainText(error_message)  
      
    # 外部インターフェース用メソッド（MenuPanelとの互換性維持）  
    def get_license_combo(self):  
        """ライセンスコンボボックスを取得"""  
        return self.license_combo  
      
    def get_license_text_widget(self):  
        """ライセンステキストウィジェットを取得"""  
        return self.license_text  
      
    def refresh_license_display(self):  
        """現在選択されているライブラリのライセンスを再読み込み"""  
        current_library = self.license_combo.currentText()  
        if current_library:  
            self._load_license_content(current_library)