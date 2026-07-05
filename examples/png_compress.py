import subprocess
from pathlib import Path
import os


def compress_single_png(file_path: str, output_dir: str, magick_path: str, strip_metadata: bool):
    """Przetwarza i kompresuje bezstratnie pojedynczy plik PNG za pomocą ImageMagick."""
    file_path = Path(file_path)
    output_file = Path(output_dir) / file_path.name

    print(f"Przetwarzam i kompresuję bezstratnie: {file_path.name}")

    # Konfiguracja ImageMagick (obróbka graficzna + maksymalna optymalizacja PNG)
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
        "-colorspace",
        "sRGB",
        "-clamp",
        "-define",
        "png:compression-level=9",  # Maksymalna, bezstratna kompresja (0-9)
        "-define",
        "png:compression-strategy=1",  # Strategia zoptymalizowana pod rysunki/grafiki
    ]
    if strip_metadata:
        magick_cmd.append("-strip")

    magick_cmd.append(str(output_file))

    subprocess.run(magick_cmd, check=True)


def compress_png_images(source_dir, output_dir, strip_metadata: bool):
    # Ścieżka relatywna do folderu, w którym znajduje się ten skrypt .py
    magick_path = Path(os.getcwd()) / "imageMagick" / "magick.exe"

    # Walidacja obecności pliku wykonywalnego
    if not magick_path.exists():
        raise FileNotFoundError(f"Nie znaleziono ImageMagick pod ścieżką: {magick_path}")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Pętla przeszukująca pliki z rozszerzeniem .png
    for file_path in Path(source_dir).glob("*.[pP][nN][gG]"):
        compress_single_png(
            file_path=file_path, output_dir=out_path, magick_path=magick_path, strip_metadata=strip_metadata
        )


if __name__ == "__main__":
    source_dir = R"C:\Users\lapci\Pictures\magick_tests\test"
    output_dir = R"C:\Users\lapci\Pictures\magick_tests\test_comp_png"

    compress_png_images(source_dir=source_dir, output_dir=output_dir, strip_metadata=True)
