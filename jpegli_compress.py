import os
import subprocess
from pathlib import Path

def compress_images_with_jpegli(source_dir, output_dir, quality=90):
    magick_path = Path(os.getcwd()) / "imageMagick" / "magick.exe"
    cjpegli_path = Path(os.getcwd()) / "jpegli" / "cjpegli.exe"
    
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Przetwarzamy pliki pojedynczo w pętli (zamiast gwiazdki '*')
    # Jpegli obsługuje rozszerzenia .jpg oraz .jpeg
    for file_path in Path(source_dir).glob("*.[jJ][pP][gG]"):
        output_file = out_path / file_path.name
        print(f"Przetwarzam i kompresuję za pomocą Jpegli: {file_path.name}")
        
        # 1. Konfiguracja ImageMagick (tylko obróbka graficzna, brak kompresji)
        # Zamiast zapisu pliku, na końcu wymuszamy zrzut do RAM: 'ppm:-'
        magick_cmd = [
            str(magick_path),
            str(file_path),
            "-resize", "3840x2160^>",
            "-filter", "Triangle",
            "-define", "filter:support=2",
            "-unsharp", "0.25x0.08+8.3+0.045",
            "-dither", "None",
            "-define", "jpeg:fancy-upsampling=off",
            "-colorspace", "sRGB",
            "-clamp",
            "ppm:-"  # Przekaż czysty obraz do standardowego wyjścia (stdout)
        ]
        
        # 2. Konfiguracja cjpegli od Google
        # Kreska '-' na początku oznacza: przyjmij dane z pamięci RAM (stdin)
        jpegli_cmd = [
            str(cjpegli_path),
            "-", 
            str(output_file),
            # "-d", str(distance) # Odległość percepcyjna (przelicznik 0.5->~95, 1.0->~90, 1.5->~82-85)
            "-q", str(quality)  # Jakość wyjściowa
        ]
        
        # 3. Bezpieczne łączenie procesów w Pythonie (Odpowiednik systemowej pionowej kreski '|')
        proc_magick = subprocess.Popen(magick_cmd, stdout=subprocess.PIPE)
        proc_jpegli = subprocess.Popen(jpegli_cmd, stdin=proc_magick.stdout, stdout=subprocess.PIPE)
        
        # Pozwalamy na asynchroniczny przepływ danych i zwalnianie pamięci podręcznej
        proc_magick.stdout.close()
        proc_jpegli.communicate()


if __name__ == "__main__":
    source_dir = R"C:\Users\lapci\Pictures\magick_tests\test"
    output_dir = R"C:\Users\lapci\Pictures\magick_tests\test_comp"
    compress_images_with_jpegli(
        source_dir=source_dir,
        output_dir=output_dir,
        quality=90
    )