import os
from definitions import FileStatus
from definitions import SUPPORTED_EXTENSIONS


class FileManager:
    def __init__(self):
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

    def _get_matching_entry(self, source_path):
        target_path = self._normalize_path(source_path)
        for f in self.files:
            if self._normalize_path(f.get("source_path")) == target_path:
                return f

        fallback_name = os.path.basename(str(source_path)) if source_path is not None else None
        if fallback_name:
            for f in self.files:
                if f.get("filename") == fallback_name or f.get("relative_path") == str(source_path):
                    return f
        return None

    def scan_directory(
        self,
        source_dir: str,
        strategy: str,
        output_dir: str,
        progress_callback=None,
        batch_size: int = 50,
    ) -> list:
        self.files.clear()
        if not source_dir or not os.path.exists(source_dir):
            return []

        scan_recursively = strategy in ("zachowaj strukturę podfolderów", "spłaszcz podfoldery")
        batch = []

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
                                batch.append(file_entry)
                except PermissionError:
                    continue
        else:
            try:
                with os.scandir(source_dir) as entries:
                    for entry in entries:
                        if entry.is_file(follow_symlinks=False):
                            file_entry = self._build_file_entry(entry, source_dir, output_dir, strategy)
                            self.files.append(file_entry)
                            batch.append(file_entry)
            except PermissionError:
                pass

        if batch:
            self._emit_progress(progress_callback, batch)
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

    def _emit_progress(self, progress_callback, batch: list) -> None:
        if progress_callback:
            progress_callback(batch)

    def get_ui_table_data(self, show_conv: bool = True, show_non_conv: bool = True, show_done: bool = True) -> list:
        MAX_ROWS = 100
        filtered_view = []
        current_row = 0
        for f in self.files:
            current_status = f["status"]
            if current_status == FileStatus.DONE and not show_done:
                continue
            if (
                current_status == FileStatus.PENDING or current_status == FileStatus.EXISTING_PENDING
            ) and not show_conv:
                continue
            if (
                current_status == FileStatus.UNCONVERTIBLE or current_status == FileStatus.EXISTING_UNCONVERTIBLE
            ) and not show_non_conv:
                continue

            filtered_view.append((f["status"], f["relative_path"], f["size_kb"], f.get("output_size_kb")))
            current_row += 1
            if current_row >= MAX_ROWS:
                break

        return filtered_view

    def get_files_for_compressor(self) -> list:
        return self.files

    def update_file_status(self, source_path, new_status: FileStatus) -> None:
        entry = self._get_matching_entry(source_path)
        if entry is None:
            return
        entry["status"] = new_status
        self.refresh_output_size_for_source(source_path)

    def refresh_output_size_for_source(self, source_path) -> None:
        entry = self._get_matching_entry(source_path)
        if entry is None:
            return
        entry["output_size_kb"] = self._get_output_size_kb(entry.get("destination"))

    def get_file_entry(self, source_path) -> dict | None:
        return self._get_matching_entry(source_path)

    def get_statistics(self) -> dict:
        """Returns metadata about the scanned set for the status bar."""
        total_count = len(self.files)
        pending_count = sum(1 for f in self.files if f["status"] == FileStatus.PENDING)
        converted_count = sum(1 for f in self.files if f["status"] == FileStatus.DONE)
        unconvertible_count = sum(1 for f in self.files if f["status"] == FileStatus.UNCONVERTIBLE)
        pending_size = sum(f["size_kb"] for f in self.files if f["status"] == FileStatus.PENDING)
        unconvertible_size = sum(f["size_kb"] for f in self.files if f["status"] == FileStatus.UNCONVERTIBLE)

        return {
            "total_count": total_count,
            "pending_count": pending_count,
            "converted_count": converted_count,
            "unconvertible_count": unconvertible_count,
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
            f"Przekonwertowane: {stats['converted_count']}"
        )
