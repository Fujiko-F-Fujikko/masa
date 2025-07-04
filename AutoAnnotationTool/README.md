# README of MASAAnnotationApp

## 環境構築

### python

3.11.2

### コマンド手順

```cmd
python -m venv venv
# In windows
source venv/Scripts/activate 
# In Linux
source venv/bin/activate 

python -m pip install --upgrade pip
pip install numpy==1.26.4
pip install torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118

# Skip this command in Linux
pip install msvc-runtime # https://qiita.com/koshitan17/items/20144b79c8905fb19e88 

cd ../mmdetection # ここからcloneしてくる⇒https://github.com/open-mmlab/mmdetection/tree/v3.3.0
pip install wheel # https://github.com/open-mmlab/mmdetection/issues/10665#issuecomment-1757209752
pip install -e .

sh install_dependencies.sh
```

#### nltkダウンロード

```cmd
#Resource punkt_tab not found.
#Please use the NLTK Downloader to obtain the resource:
```

というのが出たら、

```cmd
python (仮想環境上で)
>>> import nltk
>>> nltk.download('punkt_tab', download_dir='./venv/nltk_data')
>>> nltk.download('averaged_perceptron_tagger_eng', download_dir='./venv/nltk_data')
```
If you get `False` from the above command. try removing the `download_dir` option, run the command below instead.
```cmd
python (仮想環境上で)
>>> import nltk
>>> nltk.download('punkt_tab')
>>> nltk.download('averaged_perceptron_tagger_eng')
```

### モデルファイルのダウンロード

[README](../README.md#preparation)の手順でモデルファイルをダウンロード

## 実行方法


### 1. 動画に対して自動検出実行

```cmd

python -m venv venv # 環境構築した仮想環境に入る
source venv/Scripts/activate

python demo/video_demo_with_text.py <動画ファイルのpath> --out <検出結果確認用の動画出力先のpath> --masa_config configs/masa-gdino/masa_gdino_swinb_inference.py --masa_checkpoint saved_models/masa_models/gdino_masa.pth --score-thr 0.2 --unified --show_fps --texts "camera rear casing . cotton swab . tweesers . bottle . rubber gloves . barcode label sticker" --json_out <検出結果のjsonファイル出力先のpath(GUIアプリで使用します)>
```

* --score-thr: 動画で出力するアノテーションの信頼度の閾値(0.0~1.0)
* --texts: 検出したい物体を任意の自然言語で指定。 区切り文字は"." (例: --texts "camera rear casing . cotton swab . tweesers . bottle . rubber gloves . barcode label sticker")
* ※詳しい説明はスクリプトを読んでください

### 2. GUIアプリで自動検出結果を編集

```cmd
python -m venv venv # 環境構築した仮想環境に入る
source venv/Scripts/activate
python AutoAnnotationTool/src/MASAAnnotationApp/MASAAnnotationApp.py
python AutoAnnotationTool/src/MASAAnnotationApp/MASAAnnotationApp.py --video AutoAnnotationTool/sample/H1125060570339_2025-06-05_10-52-51_2.mp4 --json AutoAnnotationTool/sample/H1125060570339_2025-06-05_10-52-51_2_outputs.json # 引数指定で起動時読み込み可
```
