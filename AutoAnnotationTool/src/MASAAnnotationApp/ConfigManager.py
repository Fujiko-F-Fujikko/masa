# ConfigManager.py (変更)  
from typing import List, Any, Callable  
from DataClass import MASAConfig, DisplayConfig # DisplayConfigをインポート  
  
class ConfigManager:  
    """設定管理を一元化するクラス"""  
      
    def __init__(self):  
        self._observers: List[Callable] = []  
        self._masa_config = MASAConfig() # MASAモデル用設定  
        self._display_config = DisplayConfig() # 表示用設定  
      
    def update_config(self, key: str, value: Any, config_type: str = "masa"): # config_type引数を追加  
        """設定値を更新し、オブザーバーに通知"""  
        if config_type == "masa":  
            target_config = self._masa_config  
        elif config_type == "display":  
            target_config = self._display_config  
        else:  
            raise ValueError(f"Unknown config type: {config_type}")  
  
        if hasattr(target_config, key):  
            setattr(target_config, key, value)  
            self._notify_observers(key, value, config_type) # config_typeを通知に含める  
        else:  
            raise AttributeError(f"Config type '{config_type}' has no attribute '{key}'")  
      
    def get_config(self, key: str, config_type: str = "masa") -> Any: # config_type引数を追加  
        """設定値を取得"""  
        if config_type == "masa":  
            target_config = self._masa_config  
        elif config_type == "display":  
            target_config = self._display_config  
        else:  
            raise ValueError(f"Unknown config type: {config_type}")  
        return getattr(target_config, key, None)  
      
    def get_full_config(self, config_type: str = "masa") -> Any: # config_type引数を追加  
        """完全な設定オブジェクトを取得"""  
        if config_type == "masa":  
            return self._masa_config  
        elif config_type == "display":  
            return self._display_config  
        else:  
            raise ValueError(f"Unknown config type: {config_type}")  
      
    def add_observer(self, observer: Callable):  
        """設定変更のオブザーバーを追加"""  
        if observer not in self._observers:  
            self._observers.append(observer)  
      
    def remove_observer(self, observer: Callable):  
        """オブザーバーを削除"""  
        if observer in self._observers:  
            self._observers.remove(observer)  
      
    def _notify_observers(self, key: str, value: Any, config_type: str): # config_typeを通知に含める  
        """全オブザーバーに設定変更を通知"""  
        for observer in self._observers:  
            try:  
                observer(key, value, config_type) # config_typeを渡す  
            except Exception as e:  
                print(f"Error notifying observer: {e}")