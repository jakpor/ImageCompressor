from enum import Enum


class FileStatus(Enum):
    PENDING = "Oczekuje"
    DONE = "Przekonwertowany"
    UNCONVERTIBLE = "Niekonwertowalny"
    EXISTING_PENDING = "Plik istnieje (konwertowalny)"
    EXISTING_UNCONVERTIBLE = "Plik istnieje (niekonwertowalny)"
    ERROR_COMPRESSION = "Błąd kompresji"
    ERROR_COPY = "Błąd kopiowania"


SUPPORTED_EXTENSIONS = {
    ".jpg": ".jpg",
    ".jpg_large": ".jpg",
    ".jpeg": ".jpg",
    ".jpeg_large": ".jpg",
    ".jfif": ".jpg",
    ".jpe": ".jpg",
    ".jif": ".jpg",
    ".tiff": ".jpg",
    ".tif": ".jpg",
    ".bmp": ".jpg",
    ".dib": ".jpg",
    ".png": ".png",
    ".png_large": ".png",
    ".gif": ".gif",
    # Just for metadata stripping
    ".webp": ".webp",
    ".heic": ".heic",
    ".heif": ".heif",
    ".svg": ".svg",
    ".ico": ".ico",
    ".psd": ".psd",
}

STRATEGY_MAPPING = {
    "jpeg_strategy": [
        ".jpg",
        ".jpg_large",
        ".jpeg",
        ".jpeg_large",
        ".jfif",
        ".jpe",
        ".jif",
        ".tiff",
        ".tif",
        ".bmp",
        ".dib",
    ],
    "png_strategy": [".png", ".png_large"],
    "gif_strategy": [".gif"],
}
