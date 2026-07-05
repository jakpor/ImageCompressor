import os
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from abc import ABC, abstractmethod
from pathlib import Path
from definitions import FileStatus, SUPPORTED_EXTENSIONS, STRATEGY_MAPPING

_LOG_LOCK = threading.Lock()


def _log(message: str) -> None:
    with _LOG_LOCK:
        print(message, flush=True)


# ==========================================
# COMPRESSION STRATEGY INTERFACE
# ==========================================
class CompressionStrategy(ABC):
    """Abstract base class for all compression algorithms."""

    @abstractmethod
    def compress(self, source_path: Path, output_path: Path, config: dict) -> None:
        """Executes the compression for a single file."""
        pass


# ==========================================
# CONCRETE STRATEGIES (IMPLEMENTATIONS)
# ==========================================
class JpegliCompressionStrategy(CompressionStrategy):
    """Compresses images to JPEG format using ImageMagick + Jpegli via pipes."""

    def _build_resize_arg(self, config: dict) -> str:
        max_resolution = config.get("max_resolution") or "3840x2160"
        return f"{max_resolution}^>"

    def compress(self, source_path: Path, output_path: Path, config: dict) -> None:
        magick_path = config.get("magick_path")
        cjpegli_path = config.get("cjpegli_path")
        quality = config.get("quality", 90)
        strip_metadata = config.get("strip_metadata", False)
        max_resolution = self._build_resize_arg(config)

        # 1. Configure ImageMagick (processing -> stdout in PPM format)
        magick_cmd = [
            str(magick_path),
            str(source_path),
            "-resize",
            max_resolution,
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

        # 2. Configure cjpegli (stdin -> output file)
        jpegli_cmd = [str(cjpegli_path), "-", str(output_path), "-q", str(quality)]

        # 3. Connect processes via pipeline
        proc_magick = subprocess.Popen(magick_cmd, stdout=subprocess.PIPE)
        proc_jpegli = subprocess.Popen(jpegli_cmd, stdin=proc_magick.stdout, stdout=subprocess.PIPE)

        proc_magick.stdout.close()
        proc_jpegli.communicate()


class PngCompressionStrategy(CompressionStrategy):
    """Lossless compression for PNG files using ImageMagick only."""

    def _build_resize_arg(self, config: dict) -> str:
        max_resolution = config.get("max_resolution") or "3840x2160"
        return f"{max_resolution}^>"

    def compress(self, source_path: Path, output_path: Path, config: dict) -> None:
        magick_path = config.get("magick_path")
        strip_metadata = config.get("strip_metadata", False)
        max_resolution = self._build_resize_arg(config)

        magick_cmd = [
            str(magick_path),
            str(source_path),
            "-resize",
            max_resolution,
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
            "png:compression-level=9",
            "-define",
            "png:compression-strategy=1",
        ]
        if strip_metadata:
            magick_cmd.append("-strip")

        magick_cmd.append(str(output_path))

        # Direct execution since ImageMagick writes straight to disk
        subprocess.run(magick_cmd, check=True)


class UniversalStripMetadataStrategy(CompressionStrategy):
    """Only strips metadata if enabled; otherwise, copies the file identically as-is."""

    def compress(self, source_path: Path, output_path: Path, config: dict) -> None:
        magick_path = config.get("magick_path")

        if config.get("strip_metadata", False):
            magick_cmd = [str(magick_path), str(source_path), "-strip", str(output_path)]
            subprocess.run(magick_cmd, check=True)
        else:
            shutil.copy2(source_path, output_path)


class GifCompressionStrategy(CompressionStrategy):
    """Compresses animated GIFs by optimizing animation layers and reducing file size."""

    def _build_resize_arg(self, config: dict) -> str:
        max_resolution = config.get("max_resolution") or "3840x2160"
        return f"{max_resolution}^>"

    def compress(self, source_path: Path, output_path: Path, config: dict) -> None:
        magick_path = config.get("magick_path")
        strip_metadata = config.get("strip_metadata", False)
        max_resolution = self._build_resize_arg(config)

        magick_cmd = [
            str(magick_path),
            str(source_path),
            "-coalesce",
            "-resize",
            max_resolution,
            "-filter",
            "Triangle",
            "-define",
            "filter:support=2",
            "-unsharp",
            "0.25x0.08+8.3+0.045",
            "-colorspace",
            "sRGB",
            "-clamp",
            "-layers",
            "Optimize",
        ]

        if strip_metadata:
            magick_cmd.append("-strip")

        magick_cmd.append(str(output_path))

        subprocess.run(magick_cmd, check=True)


# ==========================================
# MAIN COMPRESSOR CONTEXT (MANAGER)
# ==========================================
class ImageCompressor:
    """Main manager responsible for scanning directories and executing strategies."""

    def __init__(self):
        # Map registering file extensions to their corresponding strategy
        self._strategies = {}
        self.magick_path = Path(os.getcwd()) / "imageMagick" / "magick.exe"
        self.cjpegli_path = Path(os.getcwd()) / "jpegli" / "cjpegli.exe"

    def register_strategy(self, extension: str, strategy: CompressionStrategy) -> None:
        """Dynamically registers a compression strategy for a specific extension."""
        self._strategies[extension.lower()] = strategy

    def _get_strategy_for_file(self, file_path: Path) -> CompressionStrategy:
        """Resolves the correct strategy, including handling weird extensions."""
        ext = file_path.suffix.lower()
        return self._strategies.get(ext)

    def compress_directory(self, source_dir: str, output_dir: str, config: dict) -> None:
        """Scans the source directory, builds a structured file list, and processes it internally."""
        src_path = Path(source_dir)
        out_path = Path(output_dir)

        if not src_path.exists():
            print(f"Source directory does not exist: {source_dir}")
            return

        generated_files_list = []

        for file_path in src_path.iterdir():
            if not file_path.is_file():
                continue

            ext_lower = file_path.suffix.lower()

            # 1. Determine the status
            if ext_lower in SUPPORTED_EXTENSIONS:
                initial_status = FileStatus.PENDING
                target_ext = SUPPORTED_EXTENSIONS[ext_lower]
                output_name = file_path.with_suffix(target_ext).name
            else:
                initial_status = FileStatus.UNCONVERTIBLE
                output_name = file_path.name

            destination_path = out_path / output_name

            # 2. Check if the output file already exists to map to your Enum states
            if destination_path.exists():
                if initial_status == FileStatus.PENDING:
                    initial_status = FileStatus.EXISTING_PENDING
                else:
                    initial_status = FileStatus.EXISTING_UNCONVERTIBLE

            # 3. Append built layout item to match your master list dictionary template
            generated_files_list.append(
                {
                    "source_path": str(file_path),
                    "destination": str(destination_path),
                    "filename": file_path.name,
                    "status": initial_status,
                }
            )

        # Forward the temporary list directly into the execution engine
        self.compress_files_list(generated_files_list, config)

    def _should_fallback_to_copy(self, source_path: Path, output_path: Path, config: dict) -> bool:
        if config.get("strip_metadata", False):
            return False
        if not output_path.exists():
            return False
        try:
            source_size = source_path.stat().st_size
            output_size = output_path.stat().st_size
            return output_size >= source_size
        except OSError:
            return False

    def compress_files_list(self, files_list: list, config: dict, progress_callback=None, stop_event=None) -> None:
        """Processes a master list layout row items using registered strategy configurations."""
        copy_uncompressible = config.get("copy_uncompressible", False)
        override_files = config.get("override_files", False)
        worker_count = max(1, int(config.get("worker_count", 4)))

        def process_file(file_info: dict):
            if stop_event and stop_event.is_set():
                return

            current_status = file_info.get("status")

            if current_status == FileStatus.DONE:
                return

            if not override_files and current_status in {
                FileStatus.EXISTING_PENDING,
                FileStatus.EXISTING_UNCONVERTIBLE,
            }:
                _log(f"Skipping existing file (overwrite disabled): {file_info['filename']}")
                return

            source_path = Path(file_info["source_path"])
            output_path = Path(file_info["destination"])
            output_path.parent.mkdir(parents=True, exist_ok=True)
            strategy = self._get_strategy_for_file(source_path)

            if stop_event and stop_event.is_set():
                return

            if strategy:
                _log(f"Executing {strategy.__class__.__name__}: {source_path.name} -> {output_path.name}")
                try:
                    strategy.compress(source_path, output_path, config)
                    if stop_event and stop_event.is_set():
                        return
                    if self._should_fallback_to_copy(source_path, output_path, config):
                        _log(f"Output larger than source for {source_path.name}; copying original instead")
                        shutil.copy2(source_path, output_path)
                    if progress_callback:
                        progress_callback(source_path, FileStatus.DONE)
                    _log(f"Completed: {source_path.name} -> {output_path.name}")
                except Exception as e:
                    _log(f"Error compressing file {source_path.name}: {e}")
                    if progress_callback:
                        progress_callback(source_path, FileStatus.ERROR_COMPRESSION)
            else:
                if copy_uncompressible:
                    _log(f"Copying uncompressible file: {source_path.name}")
                    try:
                        if stop_event and stop_event.is_set():
                            return
                        shutil.copy2(source_path, output_path)
                        if stop_event and stop_event.is_set():
                            return
                        if progress_callback:
                            progress_callback(source_path, FileStatus.DONE)
                    except Exception as e:
                        _log(f"Error copying file {source_path.name}: {e}")
                        if progress_callback:
                            progress_callback(source_path, FileStatus.ERROR_COPY)
                else:
                    _log(f"Skipping uncompressible file (copy disabled): {source_path.name}")
                    if progress_callback:
                        progress_callback(source_path, FileStatus.UNCONVERTIBLE)

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [executor.submit(process_file, file_info) for file_info in files_list]
            for future in futures:
                if stop_event and stop_event.is_set():
                    break
                future.result()


def create_configured_compressor():
    compressor = ImageCompressor()

    jpeg_strategy = JpegliCompressionStrategy()
    png_strategy = PngCompressionStrategy()
    gif_strategy = GifCompressionStrategy()
    stripper_strategy = UniversalStripMetadataStrategy()

    for ext in SUPPORTED_EXTENSIONS.keys():
        if ext in STRATEGY_MAPPING["jpeg_strategy"]:
            compressor.register_strategy(ext, jpeg_strategy)
        elif ext in STRATEGY_MAPPING["png_strategy"]:
            compressor.register_strategy(ext, png_strategy)
        elif ext in STRATEGY_MAPPING["gif_strategy"]:
            compressor.register_strategy(ext, gif_strategy)
        else:
            compressor.register_strategy(ext, stripper_strategy)

    return compressor


# ==========================================
# EXAMPLE USAGE
# ==========================================
if __name__ == "__main__":
    # Initialize the main compressor orchestrator
    compressor = create_configured_compressor()

    # Execute processing loop
    source = R"C:\Users\lapci\Pictures\magick_tests\test"
    output = R"C:\Users\lapci\Pictures\magick_tests\test_comp_oop"

    script_dir = Path(__file__).parent.resolve()
    magick_path = script_dir / "imageMagick" / "magick.exe"
    cjpegli_path = script_dir / "jpegli" / "cjpegli.exe"
    config = {
        "magick_path": magick_path,
        "cjpegli_path": cjpegli_path,
        "quality": 90,
        "strip_metadata": True,
        "copy_uncompressible": True,
        "override_files": True,
    }

    compressor.compress_directory(source, output, config)
