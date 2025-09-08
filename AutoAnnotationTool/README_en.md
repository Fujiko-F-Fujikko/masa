# README of MASAAnnotationApp


# README of MASAAnnotationApp

## Environment Setup for MASA

### Python Version

3.11.2

### Setup Commands

```cmd
python -m venv venv-masa
# In Windows
source venv-masa/Scripts/activate 
# In Linux
source venv-masa/bin/activate 

python -m pip install --upgrade pip
pip install torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118

# Skip this command in Linux
pip install msvc-runtime # https://qiita.com/koshitan17/items/20144b79c8905fb19e88 

cd ../mmdetection # Clone from here ⇒ https://github.com/open-mmlab/mmdetection/tree/v3.3.0
pip install wheel # https://github.com/open-mmlab/mmdetection/issues/10665#issuecomment-1757209752
pip install -e .

sh install_dependencies.sh

# Set numpy to this version
pip install numpy==1.26.4
```

#### NLTK Download

If you see:

```cmd
#Resource punkt_tab not found.
#Please use the NLTK Downloader to obtain the resource:
```

Run the following in your virtual environment:

```cmd
python
>>> import nltk
>>> nltk.download('punkt_tab', download_dir='./venv-masa/nltk_data')
>>> nltk.download('averaged_perceptron_tagger_eng', download_dir='./venv-masa/nltk_data')
```
If you get `False` from the above command, try removing the `download_dir` option and run:
```cmd
python
>>> import nltk
>>> nltk.download('punkt_tab')
>>> nltk.download('averaged_perceptron_tagger_eng')
```

#### Download Model Files

Download model files following the steps in [README-MASA](../README-MASA.md#preparation).


## Environment Setup for SAMURAI

### Setup Commands

```cmd
python -m venv venv-samurai
# In Windows
source venv-samurai/Scripts/activate 
# In Linux
source venv-samurai/bin/activate 

python -m pip install --upgrade pip
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
cd sam2
pip install -e .
 
pip install matplotlib tikzplotlib jpeg4py opencv-python lmdb pandas scipy loguru
 
pip install decord PyQt6
```
### Download Checkpoints

[from this step](../sam2/README.md#getting-started),

First, we need to download a model checkpoint. All the model checkpoints can be downloaded by running:

```bash
cd checkpoints && \
./download_ckpts.sh && \
cd ..
```


## How to Run Automatic Detection with MASA

```cmd
source venv-masa/Scripts/activate # Enter the virtual environment you set up

python demo/video_demo_with_text.py <path_to_video_file> --out <path_to_output_video> --masa_config configs/masa-gdino/masa_gdino_swinb_inference.py --masa_checkpoint saved_models/masa_models/gdino_masa.pth --score-thr 0.2 --unified --show_fps --texts "camera rear casing . cotton swab . tweesers . bottle . rubber gloves . barcode label sticker" --json_out <path_to_json_output>
```

* --score-thr: Confidence threshold for annotation output in video (0.0~1.0)
* --texts: Specify objects to detect in natural language. Use "." as a separator (e.g., --texts "camera rear casing . cotton swab . tweesers . bottle . rubber gloves . barcode label sticker")
* For details, please read the script.

## How to Run the GUI Tool

#### 1. Launch from Batch File

```cmd
run_object_annotation_app.bat
```

* Alternatively, you can double-click the bat file to launch.

#### 2. Launch from Python Script

```cmd
source venv-samurai/Scripts/activate # Enter the virtual environment you set up
python AutoAnnotationTool/src/MASAAnnotationApp/MASAAnnotationApp.py
python AutoAnnotationTool/src/MASAAnnotationApp/MASAAnnotationApp.py --video <path_to_video> # Launch with a video file
python AutoAnnotationTool/src/MASAAnnotationApp/MASAAnnotationApp.py --video <path_to_video> --json <path_to_json_out> # Load results detected by MASA
```
