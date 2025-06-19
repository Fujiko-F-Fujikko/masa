## テストコマンド

python demo/video_demo_with_text.py stt/H1125060570339_2025-06-05_10-52-51_2.mp4 --out stt_outputs/H1125060570339_2025-06-05_10-52-51_2_outputs.mp4 --masa_config configs/masa-gdino/masa_gdino_swinb_inference.py --masa_checkpoint saved_models/masa_models/gdino_masa.pth --score-thr 0.2 --unified --show_fps --texts "camera rear casing . cotton swab . tweesers . bottle . rubber gloves . barcode label sticker" --json_out stt_json_outputs/H1125060570339_2025-06-05_10-52-51_2_outputs.json

### yolo版(ボツ)
python demo/video_demo_with_text.py stt/H1125060570339_2025-06-05_10-52-51_2.mp4 --out stt_outputs/H1125060570339_2025-06-05_10-52-51_2_outputs_yolox.mp4 --det_config projects/mmdet_configs/yolox/yolox_x_8xb8-300e_coco.py --det_checkpoint saved_models/pretrain_weights/yolox_x_8x8_300e_coco_20211126_140254-1ef88d67.pth --masa_config configs/masa-one/masa_r50_plug_and_play.py --masa_checkpoint saved_models/masa_models/gdino_masa.pth --score-thr 0.3 --show_fps

#### Viewerアプリ起動

python QtViewer.py --video stt/H1125060570339_2025-06-05_10-52-51_2.mp4 --json stt_json_outputs/H1125060570339_2025-06-05_10-52-51_2_outputs.json

## 環境構築

### python

3.11.2

### コマンド手順

python -m pip install --upgrade pip
pip install numpy==1.26.4
pip install torch==2.1.2+cu118 torchvision==0.16.2+cu118 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
pip install msvc-runtime # https://qiita.com/koshitan17/items/20144b79c8905fb19e88

cd ../mmdetection # ここからcloneしてくる⇒https://github.com/open-mmlab/mmdetection/tree/v3.3.0
pip install wheel # https://github.com/open-mmlab/mmdetection/issues/10665#issuecomment-1757209752
pip install -e .

sh install_dependencies.sh

#Resource punkt_tab not found.
#Please use the NLTK Downloader to obtain the resource:
python
>>> import nltk
>>> nltk.download('punkt_tab', download_dir='./venv/nltk_data')
>>> nltk.download('averaged_perceptron_tagger_eng', download_dir='./venv/nltk_data')