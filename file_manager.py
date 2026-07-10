import os
from definitions import FileStatus
from definitions import SUPPORTED_EXTENSIONS


class FileManager:
    def __init__(self):
        # Kept the original variable name as requested
        # Master list stores dicts: { "source_path": ..., "relative_path": ..., "filename": ..., "size_kb": ..., "status": ..., "output_size_kb": ... }
        self.files = []

    @staticmethod
    def _normalize_path(path) -> str | None:
        if path is None:
            return None
        try:
            return os.path.normcase(os.path.abspath(str(path)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _get_output_size_kb(destination: str | None) -> float | None:
        if not destination or not os.path.isfile(destination):
            return None
        return round(os.path.getsize(destination) / 1024, 1)

    def _get_matching_entry_and_index(self, source_path):
        """Helper to find both the dictionary entry and its global index location."""
        target_path = self._normalize_path(source_path)
        for idx, f in enumerate(self.files):
            if self._normalize_path(f.get("source_path")) == target_path:
                return f, idx

        fallback_name = os.path.basename(str(source_path)) if source_path is not None else None
        if fallback_name:
            for idx, f in enumerate(self.files):
                if f.get("filename") == fallback_name or f.get("relative_path") == str(source_path):
                    return f, idx
        return None, -1

    def scan_directory(
        self,
        source_dir: str,
        strategy: str,
        output_dir: str,
    ) -> list:
        self.files.clear()
        if not source_dir or not os.path.exists(source_dir):
            return []

        scan_recursively = strategy in ("zachowaj strukturę podfolderów", "spłaszcz podfoldery")

        if scan_recursively:
            stack = [source_dir]
            while stack:
                current_dir = stack.pop()
                try:
                    with os.scandir(current_dir) as entries:
                        for entry in entries:
                            if entry.is_dir(follow_symlinks=False):
                                stack.append(entry.path)
                            elif entry.is_file(follow_symlinks=False):
                                file_entry = self._build_file_entry(entry, source_dir, output_dir, strategy)
                                self.files.append(file_entry)
                except PermissionError:
                    continue
        else:
            try:
                with os.scandir(source_dir) as entries:
                    for entry in entries:
                        if entry.is_file(follow_symlinks=False):
                            file_entry = self._build_file_entry(entry, source_dir, output_dir, strategy)
                            self.files.append(file_entry)
            except PermissionError:
                pass

        return self.files

    def _build_file_entry(self, entry, source_dir: str, output_dir: str, strategy: str) -> dict:
        filename = entry.name
        full_path = entry.path
        rel_path = os.path.relpath(full_path, source_dir)
        size_kb = round(entry.stat().st_size / 1024, 1)
        destination = self._build_destination_path(output_dir, strategy, rel_path, filename)
        status = self._resolve_status(filename, destination)

        return {
            "source_path": full_path,
            "relative_path": rel_path,
            "filename": filename,
            "size_kb": size_kb,
            "status": status,
            "destination": destination,
            "output_size_kb": self._get_output_size_kb(destination),
        }

    def _build_destination_path(self, output_dir: str, strategy: str, rel_path: str, filename: str) -> str:
        if strategy == "zachowaj strukturę podfolderów":
            dest_path = os.path.join(output_dir, rel_path)
        elif strategy == "spłaszcz podfoldery":
            flattened_filename = rel_path.replace("/", "_").replace("\\", "_")
            dest_path = os.path.join(output_dir, flattened_filename)
        else:
            dest_path = os.path.join(output_dir, filename)

        base_path, ext = os.path.splitext(dest_path)
        ext_lower = ext.lower()
        if ext_lower in SUPPORTED_EXTENSIONS:
            dest_path = base_path + SUPPORTED_EXTENSIONS[ext_lower]
        return dest_path

    def _resolve_status(self, filename: str, destination: str) -> FileStatus:
        ext = os.path.splitext(filename)[1].lower()
        if ext in SUPPORTED_EXTENSIONS:
            status = FileStatus.PENDING
        else:
            status = FileStatus.UNCONVERTIBLE

        if os.path.isfile(destination):
            return FileStatus.EXISTING_PENDING if status == FileStatus.PENDING else FileStatus.EXISTING_UNCONVERTIBLE
        return status

    def get_files_for_compressor(self) -> list:
        return self.files

    def update_file_status(self, source_path, new_status: FileStatus) -> int:
        """Updates status, size, and returns the global index of the file for targeted UI sync."""
        entry, global_idx = self._get_matching_entry_and_index(source_path)
        if global_idx == -1:
            return -1

        entry["status"] = new_status
        entry["output_size_kb"] = self._get_output_size_kb(entry.get("destination"))
        return global_idx

    def get_file_entry(self, source_path) -> dict | None:
        entry, _ = self._get_matching_entry_and_index(source_path)
        return entry

    def get_statistics(self) -> dict:
        """Returns metadata about the scanned set for the status bar."""
        total_count = len(self.files)
        pending_count = sum(1 for f in self.files if f["status"] == FileStatus.PENDING)
        converted_count = sum(1 for f in self.files if f["status"] == FileStatus.DONE)
        unconvertible_count = sum(1 for f in self.files if f["status"] == FileStatus.UNCONVERTIBLE)
        error_count = sum(1 for f in self.files if f["status"] in {FileStatus.ERROR_COMPRESSION, FileStatus.ERROR_COPY})
        pending_size = sum(f["size_kb"] for f in self.files if f["status"] == FileStatus.PENDING)
        unconvertible_size = sum(f["size_kb"] for f in self.files if f["status"] == FileStatus.UNCONVERTIBLE)

        return {
            "total_count": total_count,
            "pending_count": pending_count,
            "converted_count": converted_count,
            "unconvertible_count": unconvertible_count,
            "error_count": error_count,
            "pending_size_mb": round(pending_size / 1024, 2),
            "unconvertible_size_mb": round(unconvertible_size / 1024, 2),
        }

    def get_statistics_summary(self) -> str:
        """Returns a concise summary string for the status bar."""
        stats = self.get_statistics()
        return (
            f"Wszystkich plików: {stats['total_count']} | "
            f"Do przetworzenia: {stats['pending_count']} ({stats['pending_size_mb']} MB) | "
            f"Niekonwertowalne: {stats['unconvertible_count']} ({stats['unconvertible_size_mb']} MB) | "
            f"Przekonwertowane: {stats['converted_count']} | "
            f"Błędy: {stats['error_count']}"
        )
