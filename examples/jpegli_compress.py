import os
import subprocess
from pathlib import Path


def compress_single_image(source_path, output_path, magick_path, cjpegli_path, quality=90, strip_metadata=False):
    file_path = Path(source_path)
    output_file = Path(output_path)

    # 1. Konfiguracja ImageMagick (obróbka graficzna -> stdout)
    magick_cmd = [
        str(magick_path),
        str(file_path),
        "-resize",
        "3840x2160^>",
        "-filter",
        "Triangle",
        "-define",
        "filter:support=2",
        "-unsharp",
        "0.25x0.08+8.3+0.045",
        "-dither",
        "None",
        "-define",
        "jpeg:fancy-upsampling=off",
        "-colorspace",
        "sRGB",
        "-clamp",
    ]

    if strip_metadata:
        magick_cmd.append("-strip")

    magick_cmd.append("ppm:-")

    # 2. Konfiguracja cjpegli (stdin -> plik wyjściowy)
    jpegli_cmd = [str(cjpegli_path), "-", str(output_file), "-q", str(quality)]

    # 3. Łączenie procesów potokiem (pipe)
    proc_magick = subprocess.Popen(magick_cmd, stdout=subprocess.PIPE)
    proc_jpegli = subprocess.Popen(jpegli_cmd, stdin=proc_magick.stdout, stdout=subprocess.PIPE)

    # Zamknięcie strumienia w procesie nadrzędnym i oczekiwanie na zakończenie
    proc_magick.stdout.close()
    proc_jpegli.communicate()


def compress_images_with_jpegli(source_dir, output_dir, quality=90, strip_metadata=False):
    magick_path = Path(os.getcwd()) / "imageMagick" / "magick.exe"
    cjpegli_path = Path(os.getcwd()) / "jpegli" / "cjpegli.exe"

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Pętla wywołująca wydzieloną funkcję dla każdego pliku
    for file_path in Path(source_dir).glob("*.[jJ][pP][gG]"):
        compress_single_image(
            source_path=file_path,
            output_path=out_path / file_path.name,
            magick_path=magick_path,
            cjpegli_path=cjpegli_path,
            quality=quality,
        )


if __name__ == "__main__":
    source_dir = R"C:\Users\lapci\Pictures\magick_tests\test"
    output_dir = R"C:\Users\lapci\Pictures\magick_tests\test_comp"
    compress_images_with_jpegli(source_dir=source_dir, output_dir=output_dir, quality=90, strip_metadata=False)
