# README of MASAAnnotationApp

## Environment Setup for MASA

### python

3.11.2

### Command Steps

```cmd
python -m venv venv-masa
# In windows
source venv-masa/Scripts/activate 
# In Linux
source venv-masa/bin/activate 

python -m pip install --upgrade pip
pip install torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118

# Skip this command in Linux
pip install msvc-runtime # https://qiita.com/koshitan17/items/20144b79c8905fb19e88 

cd ../mmdetection # clone from here⇒https://github.com/open-mmlab/mmdetection/tree/v3.3.0
pip install wheel # https://github.com/open-mmlab/mmdetection/issues/10665#issuecomment-1757209752
pip install -e .

sh install_dependencies.sh

# specify numpy version
pip install numpy==1.26.4
```

#### nltk Download

```cmd
#Resource punkt_tab not found.
#Please use the NLTK Downloader to obtain the resource:
```

follow next step if you encount above message.

```cmd
python (on venv)
>>> import nltk
>>> nltk.download('punkt_tab', download_dir='./venv-masa/nltk_data')
>>> nltk.download('averaged_perceptron_tagger_eng', download_dir='./venv-masa/nltk_data')
```
If you get `False` from the above command. try removing the `download_dir` option, run the command below instead.
```cmd
python (仮想環境上で)
>>> import nltk
>>> nltk.download('punkt_tab')
>>> nltk.download('averaged_perceptron_tagger_eng')
```

### Download Model Files

Download the model files by following the steps in [README](../README.md#preparation).

## How to Run

### 1. Run Automatic Detection on Video

```cmd

source venv-masa/Scripts/activate # Enter the created virtual environment

python demo/video_demo_with_text.py <path to video file> --out <path to output video for checking detection results> --masa_config configs/masa-gdino/masa_gdino_swinb_inference.py --masa_checkpoint saved_models/masa_models/gdino_masa.pth --score-thr 0.2 --unified --show_fps --texts "camera rear casing . cotton swab . tweesers . bottle . rubber gloves . barcode label sticker" --json_out <path to output json file for detection results (used in GUI app)>
```

* --score-thr: Confidence threshold for annotations output in the video (0.0~1.0)
* --texts: Specify the objects to detect in natural language. Use "." as the delimiter. (Example: --texts "camera rear casing . cotton swab . tweesers . bottle . rubber gloves . barcode label sticker")
* For more details, please read the script.

## Embironment Setup for SAMURAI

### Command Steps

```cmd
python -m venv venv-samurai
# In windows
source venv-samurai/Scripts/activate 
# In Linux
source venv-samurai/bin/activate 

python -m pip install --upgrade pip
pip install torch==2.3.1+cu118 torchvision==0.18.1+cu118 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cu118

cd sam2
pip install -e .

pip install matplotlib==3.7 tikzplotlib jpeg4py opencv-python lmdb pandas scipy loguru

pip install decord PyQt6
pip install numpy==1.26.4
```

### How to Run


#### 2. Edit Automatic Detection Results with GUI App

```cmd
python -m venv venv # Enter the created virtual environment
source venv/Scripts/activate
python AutoAnnotationTool/src/MASAAnnotationApp/MASAAnnotationApp.py
python AutoAnnotationTool/src/MASAAnnotationApp/MASAAnnotationApp.py --video AutoAnnotationTool/sample/H1125060570339_2025-06-05_10-52-51_2.mp4 --json AutoAnnotationTool/sample/H1125060570339_2025-06-05_10-52-51_2_outputs.json # You can load files at startup by specifying arguments
