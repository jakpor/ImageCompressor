# ImageCompressor

ImageCompressor is a small Windows desktop tool for batch image compression. It scans a source folder, shows the discovered files in a table, and compresses them into an output folder while keeping the workflow responsive.

The app UI language is Polish

## What it does
- compresses JPEG, PNG and GIF files
- supports folder structure options: keep subfolders, flatten them, or skip subfolders
- lets you set image quality, maximum resolution and thread count
- can remove metadata, overwrite existing output files, and copy files that cannot be compressed
- shows progress and a summary of saved space after processing

## Requirements
- Windows
- Python 3.10+
- package: customtkinter
- local executables (included in the repo):
  - imageMagick/magick.exe
  - jpegli/cjpegli.exe

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install customtkinter
   ```
3. Make sure the required executables are present in the project folders.

## Running
```bash
python main.py
```

## Building executable
```bash
pyinstaller main.spec
# pyinstaller --noconfirm --onefile --windowed main.py
```
*Requires `python -m pip install pyinstaller`

## Usage
1. Choose an input folder and an output folder.
2. Set the desired compression options.
3. Click "Wczytaj pliki" to scan the source directory.
4. Click "Kompresuj" to start processing.
5. You can stop compression at any time.

## Notes
- JPEG files are processed with ImageMagick and JPEGLI.
- PNG and GIF use optimized ImageMagick pipelines.
- If a compressed output becomes larger than the source and metadata stripping is disabled, the app can fall back to copying the original file.


## Sources
Resize image process is taken from: https://www.smashingmagazine.com/2015/06/efficient-image-resizing-with-imagemagick/

Compression is happening mostly by degrading the quality of the image using ImageMagick and JPEGLI encoders. 

JPEGLI: https://opensource.googleblog.com/2024/04/introducing-jpegli-new-jpeg-coding-library.html

Binary taken from release v0.12.0: https://github.com/libjxl/libjxl/releases/tag/v0.12.0