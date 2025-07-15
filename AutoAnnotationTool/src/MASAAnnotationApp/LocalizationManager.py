# LocalizationManager.py  
import os  
import json  
from typing import List, Callable, Optional  
from PyQt6.QtCore import QTranslator, QLocale, QCoreApplication  
from PyQt6.QtWidgets import QApplication  
  
class LocalizationManager:  
    """多言語対応を管理するクラス"""  
      
    # サポートする言語  
    SUPPORTED_LANGUAGES = {  
        'ja_JP': '日本語',  
        'en_US': 'English'  
    }  
      
    def __init__(self):  
        self._observers: List[Callable] = []  
        self._current_language = 'ja_JP'  # デフォルトは日本語  
        self._translator: Optional[QTranslator] = None  
        self._config_file = 'localization_config.json'  
          
        # 設定ファイルから言語設定を読み込み  
        self._load_language_config()  
          
        # 翻訳ファイルのベースパス  
        self._translations_path = os.path.join(os.path.dirname(__file__), 'i18n')  
          
        # 初期言語を設定  
        self.set_language(self._current_language)  
      
    def get_current_language(self) -> str:  
        """現在の言語を取得"""  
        return self._current_language  
      
    def get_supported_languages(self) -> dict:  
        """サポートされている言語一覧を取得"""  
        return self.SUPPORTED_LANGUAGES.copy()  
      
    def set_language(self, language_code: str) -> bool:  
        """言語を設定"""  
        if language_code not in self.SUPPORTED_LANGUAGES:  
            print(f"Unsupported language: {language_code}")  
            return False  
          
        # 既存のトランスレータを削除  
        if self._translator:  
            QCoreApplication.removeTranslator(self._translator)  
            self._translator = None  
          
        # 新しいトランスレータを作成  
        self._translator = QTranslator()  
          
        # 翻訳ファイルのパスを構築  
        translation_file = os.path.join(self._translations_path, f"{language_code}.qm")  
          
        # 翻訳ファイルが存在しない場合は作成（開発時用）  
        if not os.path.exists(translation_file):  
            self._create_default_translation_file(language_code)  
          
        # 翻訳ファイルを読み込み  
        if self._translator.load(translation_file):  
            QCoreApplication.installTranslator(self._translator)  
            self._current_language = language_code  
              
            # 設定を保存  
            self._save_language_config()  
              
            # オブザーバーに通知  
            self._notify_observers(language_code)  
              
            return True  
        else:  
            print(f"Failed to load translation file: {translation_file}")  
            return False  
      
    def add_observer(self, observer: Callable[[str], None]):  
        """言語変更のオブザーバーを追加"""  
        if observer not in self._observers:  
            self._observers.append(observer)  
      
    def remove_observer(self, observer: Callable[[str], None]):  
        """オブザーバーを削除"""  
        if observer in self._observers:  
            self._observers.remove(observer)  
      
    def _notify_observers(self, language_code: str):  
        """全オブザーバーに言語変更を通知"""  
        for observer in self._observers:  
            try:  
                observer(language_code)  
            except Exception as e:  
                print(f"Error notifying localization observer: {e}")  
      
    def _load_language_config(self):  
        """設定ファイルから言語設定を読み込み"""  
        try:  
            if os.path.exists(self._config_file):  
                with open(self._config_file, 'r', encoding='utf-8') as f:  
                    config = json.load(f)  
                    self._current_language = config.get('language', 'ja_JP')  
        except Exception as e:  
            print(f"Error loading language config: {e}")  
            self._current_language = 'ja_JP'  
      
    def _save_language_config(self):  
        """言語設定を設定ファイルに保存"""  
        try:  
            config = {'language': self._current_language}  
            with open(self._config_file, 'w', encoding='utf-8') as f:  
                json.dump(config, f, ensure_ascii=False, indent=2)  
        except Exception as e:  
            print(f"Error saving language config: {e}")  
      
    def _create_default_translation_file(self, language_code: str):  
        """デフォルトの翻訳ファイルを作成（開発時用）"""  
        # i18nディレクトリが存在しない場合は作成  
        os.makedirs(self._translations_path, exist_ok=True)  
          
        # .tsファイルのパス  
        ts_file = os.path.join(self._translations_path, f"{language_code}.ts")  
          
        # デフォルトの.tsファイル内容  
        default_ts_content = f'''<?xml version="1.0" encoding="utf-8"?>  
<!DOCTYPE TS>  
<TS version="2.1" language="{language_code}">  
<context>  
    <name>Title</name>  
    <message>  
        <source>MASA Object Annotation Tool</source>  
        <translation>{"MASA 物体アノテーションツール" if language_code == "ja_JP" else "MASA Object Annotation Tool"}</translation>  
    </message>
</context>
<context>  
    <name>MenuPanel</name>  
    <message>  
        <source>Load Video (Ctrl+O)</source>  
        <translation>{"動画を読み込み (Ctrl+O)" if language_code == "ja_JP" else "Load Video (Ctrl+O)"}</translation>  
    </message>  
    <message>  
        <source>File Operations</source>  
        <translation>{"ファイル操作" if language_code == "ja_JP" else "File Operations"}</translation>  
    </message>  
    <message>  
        <source>Basic Settings</source>  
        <translation>{"基本設定" if language_code == "ja_JP" else "Basic Settings"}</translation>  
    </message>  
    <message>  
        <source>Display Settings</source>  
        <translation>{"表示設定" if language_code == "ja_JP" else "Display Settings"}</translation>  
    </message>  
    <message>  
        <source>Show Manual Annotations</source>  
        <translation>{"手動アノテーション結果表示" if language_code == "ja_JP" else "Show Manual Annotations"}</translation>  
    </message>  
    <message>  
        <source>Show Auto Annotations</source>  
        <translation>{"自動アノテーション結果表示" if language_code == "ja_JP" else "Show Auto Annotations"}</translation>  
    </message>  
    <message>  
        <source>Show Track IDs</source>  
        <translation>{"Track ID表示" if language_code == "ja_JP" else "Show Track IDs"}</translation>  
    </message>  
    <message>  
        <source>Show Confidence Scores</source>  
        <translation>{"スコア表示" if language_code == "ja_JP" else "Show Confidence Scores"}</translation>  
    </message>  
    <message>  
        <source>Score Threshold:</source>  
        <translation>{"スコア閾値:" if language_code == "ja_JP" else "Score Threshold:"}</translation>  
    </message>  
    <message>  
        <source>Language:</source>  
        <translation>{"言語:" if language_code == "ja_JP" else "Language:"}</translation>  
    </message>  
</context>  
<context>  
    <name>AnnotationInputDialog</name>  
    <message>  
        <source>Add Annotation</source>  
        <translation>{"アノテーション追加" if language_code == "ja_JP" else "Add Annotation"}</translation>  
    </message>  
</context>  
<context>  
    <name>ErrorHandler</name>  
    <message>  
        <source>Error</source>  
        <translation>{"エラー" if language_code == "ja_JP" else "Error"}</translation>  
    </message>  
    <message>  
        <source>Warning</source>  
        <translation>{"警告" if language_code == "ja_JP" else "Warning"}</translation>  
    </message>  
    <message>  
        <source>Information</source>  
        <translation>{"情報" if language_code == "ja_JP" else "Information"}</translation>  
    </message>  
</context>  
</TS>'''  
          
        # .tsファイルを作成  
        try:  
            with open(ts_file, 'w', encoding='utf-8') as f:  
                f.write(default_ts_content)  
            print(f"Created default translation file: {ts_file}")  
              
            # .qmファイルにコンパイル（実際の運用では外部ツールを使用）  
            self._compile_ts_to_qm(ts_file)  
              
        except Exception as e:  
            print(f"Error creating translation file: {e}")  
      
    def _compile_ts_to_qm(self, ts_file: str):  
        """TSファイルをQMファイルにコンパイル（lreleaseコマンド使用）"""  
        import subprocess  
        import shutil  
        
        qm_file = ts_file.replace('.ts', '.qm')  
        
        try:  
            # lreleaseコマンドが利用可能かチェック  
            lrelease_cmd = None  
            
            # 一般的なlreleaseコマンド名を試す  
            possible_commands = ['lrelease', 'lrelease-qt6', 'lrelease-qt5']  
            
            for cmd in possible_commands:  
                if shutil.which(cmd):  
                    lrelease_cmd = cmd  
                    break  
            
            if lrelease_cmd is None:  
                print("Warning: lrelease command not found. Please install Qt Linguist tools.")  
                print("Falling back to placeholder QM file creation.")  
                self._create_placeholder_qm(qm_file)  
                return  
            
            # lreleaseコマンドを実行  
            result = subprocess.run(  
                [lrelease_cmd, ts_file, '-qm', qm_file],  
                capture_output=True,  
                text=True,  
                timeout=30  
            )  
            
            if result.returncode == 0:  
                print(f"Successfully compiled translation file: {qm_file}")  
            else:  
                print(f"lrelease failed with return code {result.returncode}")  
                print(f"stderr: {result.stderr}")  
                print("Falling back to placeholder QM file creation.")  
                self._create_placeholder_qm(qm_file)  
                
        except subprocess.TimeoutExpired:  
            print("lrelease command timed out. Falling back to placeholder QM file creation.")  
            self._create_placeholder_qm(qm_file)  
        except Exception as e:  
            print(f"Error running lrelease command: {e}")  
            print("Falling back to placeholder QM file creation.")  
            self._create_placeholder_qm(qm_file)  
    
    def _create_placeholder_qm(self, qm_file: str):  
        """プレースホルダーのQMファイルを作成（lreleaseが利用できない場合のフォールバック）"""  
        try:  
            # 最小限のQMファイルヘッダーを作成  
            with open(qm_file, 'wb') as f:  
                # Qt Message File format header  
                f.write(b'\\x3c\\xb8\\x64\\x18\\x00\\x00\\x00\\x00')  
            
            print(f"Created placeholder QM file: {qm_file}")  
            print("Note: For proper translation support, install Qt Linguist tools and use lrelease.")  
            
        except Exception as e:  
            print(f"Error creating placeholder QM file: {e}")




# シングルトンインスタンス  
_localization_manager_instance = None  
  
def get_localization_manager() -> LocalizationManager:  
    """LocalizationManagerのシングルトンインスタンスを取得"""  
    global _localization_manager_instance  
    if _localization_manager_instance is None:  
        _localization_manager_instance = LocalizationManager()  
    return _localization_manager_instance