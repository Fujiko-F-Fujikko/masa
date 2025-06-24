# SignalConnector.py  
from PyQt6.QtCore import QObject, pyqtSignal  
from typing import Dict, Any  
  
class SignalConnector:  
    """シグナル接続を自動化するユーティリティクラス"""  
      
    @staticmethod  
    def auto_connect(source: QObject, target: QObject,   
                    signal_mapping: Dict[str, str] = None):  
        """命名規則に基づく自動シグナル接続"""  
        if signal_mapping is None:  
            signal_mapping = {}  
          
        # ソースのシグナルを取得  
        source_signals = [attr for attr in dir(source)   
                         if isinstance(getattr(source, attr), pyqtSignal)]  
          
        for signal_name in source_signals:  
            # デフォルトの命名規則: signal_name -> on_signal_name  
            slot_name = signal_mapping.get(signal_name, f"on_{signal_name}")  
              
            if hasattr(target, slot_name):  
                signal = getattr(source, signal_name)  
                slot = getattr(target, slot_name)  
                signal.connect(slot)  
      
    @staticmethod  
    def connect_by_convention(widget: QObject, parent: QObject):  
        """規約に基づいてウィジェットのシグナルを親に接続"""  
        widget_name = widget.objectName()  
        if not widget_name:  
            return  
          
        # ウィジェット名からシグナル名を推測  
        common_signals = ['clicked', 'valueChanged', 'textChanged', 'stateChanged']  
          
        for signal_name in common_signals:  
            if hasattr(widget, signal_name):  
                slot_name = f"on_{widget_name}_{signal_name}"  
                if hasattr(parent, slot_name):  
                    signal = getattr(widget, signal_name)  
                    slot = getattr(parent, slot_name)  
                    signal.connect(slot)  
      
    @staticmethod  
    def disconnect_all(widget: QObject):  
        """ウィジェットの全シグナル接続を切断"""  
        for attr_name in dir(widget):  
            attr = getattr(widget, attr_name)  
            if isinstance(attr, pyqtSignal):  
                attr.disconnect()  