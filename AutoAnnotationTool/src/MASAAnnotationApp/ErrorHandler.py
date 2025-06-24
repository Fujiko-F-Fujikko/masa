# ErrorHandler.py  
from PyQt6.QtWidgets import QMessageBox  
from functools import wraps  
import logging  
from typing import Callable, Any  
  
class ErrorHandler:  
    """統一されたエラーハンドリング機能"""  
      
    @staticmethod  
    def setup_logging():  
        """ログ設定を初期化"""  
        logging.basicConfig(  
            level=logging.ERROR,  
            format='%(asctime)s - %(levelname)s - %(message)s',  
            handlers=[  
                logging.FileHandler('masa_annotation_errors.log'),  
                logging.StreamHandler()  
            ]  
        )  
      
    @staticmethod  
    def handle_with_dialog(title: str = "Error"):  
        """エラーをダイアログで表示するデコレータ"""  
        def decorator(func: Callable) -> Callable:  
            @wraps(func)  
            def wrapper(*args, **kwargs) -> Any:  
                try:  
                    return func(*args, **kwargs)  
                except Exception as e:  
                    ErrorHandler.log_error(e, func.__name__)  
                    ErrorHandler.show_error_dialog(str(e), title)  
                    return None  
            return wrapper  
        return decorator  
      
    @staticmethod  
    def log_error(error: Exception, context: str = ""):  
        """エラーをログに記録"""  
        error_msg = f"Error in {context}: {str(error)}"  
        logging.error(error_msg, exc_info=True)  
      
    @staticmethod  
    def show_error_dialog(message: str, title: str = "Error"):  
        """エラーダイアログを表示"""  
        QMessageBox.critical(None, title, message)  
      
    @staticmethod  
    def show_warning_dialog(message: str, title: str = "Warning"):  
        """警告ダイアログを表示"""  
        QMessageBox.warning(None, title, message)  
      
    @staticmethod  
    def show_info_dialog(message: str, title: str = "Information"):  
        """情報ダイアログを表示"""  
        QMessageBox.information(None, title, message)  