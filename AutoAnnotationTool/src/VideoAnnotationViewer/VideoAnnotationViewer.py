import sys  
import argparse  
from PyQt6.QtWidgets import QApplication

from VideoAnnotationViewerWindow import VideoAnnotationViewerWindow


def parse_args():
    """コマンドライン引数を解析"""
    parser = argparse.ArgumentParser(description='MASA Video Annotation Viewer with Editor')
    parser.add_argument('--video', type=str, help='Video file path')
    parser.add_argument('--json', type=str, help='JSON annotation file path')
    return parser.parse_args()

def main():  
    app = QApplication(sys.argv)  
    
    # コマンド引数を解析
    args = parse_args()
    
    viewer = VideoAnnotationViewerWindow()
    
    # コマンド引数でファイルが指定されている場合は自動読み込み
    if args.video:
        viewer.load_video_file(args.video)
    
    if args.json:
        viewer.load_json_file(args.json)
    
    viewer.show()  
    sys.exit(app.exec())  
  
if __name__ == '__main__':  
    main()
