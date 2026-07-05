import os
from file_status import FileStatus


class FileManager:
    def __init__(self):
        # Master list stores dicts: { "source_path": ..., "relative_path": ..., "filename": ..., "size_kb": ..., "is_processed": ... }
        self.files = []
        self.supported_extensions = (".jpg", ".jpeg", ".png")

    def scan_directory(self, source_dir: str, strategy: str, output_dir: str) -> list:
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
                                filename = entry.name
                                full_path = entry.path
                                rel_path = os.path.relpath(full_path, source_dir)
                                size_kb = round(entry.stat().st_size / 1024, 1)
                                self.files.append(
                                    {
                                        "source_path": full_path,
                                        "relative_path": rel_path,
                                        "filename": filename,
                                        "size_kb": size_kb,
                                    }
                                )
                except PermissionError:
                    continue
        else:
            try:
                with os.scandir(source_dir) as entries:
                    for entry in entries:
                        if entry.is_file(follow_symlinks=False):
                            filename = entry.name
                            size_kb = round(entry.stat().st_size / 1024, 1)

                            self.files.append(
                                {
                                    "source_path": entry.path,
                                    "relative_path": filename,
                                    "filename": filename,
                                    "size_kb": size_kb,
                                }
                            )
            except PermissionError:
                pass
        self._update_status_metadata()
        self._update_output_path(output_dir, strategy)
        self._update_status_existing()
        return

    def _update_status_metadata(self):
        for f in self.files:
            # Initialize status using the official FileStatus Enum objects instead of raw strings
            if "status" not in f:
                ext = os.path.splitext(f["filename"])[1].lower()
                if ext in self.supported_extensions:
                    f["status"] = FileStatus.PENDING
                else:
                    f["status"] = FileStatus.UNCONVERTIBLE

    def _update_output_path(self, output_dir: str, strategy: str):
        for f in self.files:
            # Determine destination path based on subfolder layout preferences
            if strategy == "zachowaj strukturę podfolderów":
                dest_path = os.path.join(output_dir, f["relative_path"])
            elif strategy == "spłaszcz podfoldery":
                # Replace both forward and backward slashes in relative path with underscores
                flattened_filename = f["relative_path"].replace("/", "_").replace("\\", "_")
                dest_path = os.path.join(output_dir, flattened_filename)
            else:
                # "nie skanuj podfolderów" drops files directly in the output root using their original filename
                dest_path = os.path.join(output_dir, f["filename"])

            # Directly store the calculated destination path inside the master dictionary item
            f["destination"] = dest_path

    def _update_status_existing(self) -> None:
        for f in self.files:
            if "destination" not in f or f["status"] not in (FileStatus.PENDING, FileStatus.UNCONVERTIBLE):
                continue

            if os.path.isfile(f["destination"]):
                if f["status"] == FileStatus.PENDING:
                    f["status"] = FileStatus.EXISTING_PENDING
                else:
                    f["status"] = FileStatus.EXISTING_UNCONVERTIBLE

    def get_ui_table_data(self, show_conv: bool = True, show_non_conv: bool = True, show_done: bool = True) -> list:
        filtered_view = []
        for f in self.files:
            current_status = f["status"]
            if current_status == FileStatus.DONE and not show_done:
                continue
            if current_status == FileStatus.PENDING and not show_conv:
                continue
            if current_status == FileStatus.UNCONVERTIBLE and not show_non_conv:
                continue

            filtered_view.append((f["status"], f["relative_path"], f["size_kb"]))

        return filtered_view

    def get_queue_for_compressor(self) -> list:
        """
        Generates a clean execution list for the compression engine.
        Returns a list of dicts containing accurate input paths and pre-calculated output destinations.
        """
        queue = []
        for f in self.files:
            if not f["status"] == FileStatus.PENDING:
                continue

            # Determine destination path based on subfolder layout preferences
            if strategy == "zachowaj strukturę podfolderów":
                dest_path = os.path.join(output_dir, f["relative_path"])
            else:
                # "spłaszcz podfoldery" or "nie skanuj podfolderów" both drop files directly in the output root
                dest_path = os.path.join(output_dir, f["filename"])

            queue.append({"source": f["source_path"], "destination": dest_path})
        return queue

    def get_statistics(self) -> dict:
        """Returns metadata about the scanned set for the status bar."""
        total_count = len(self.files)
        pending_count = sum(1 for f in self.files if f["status"] == FileStatus.PENDING)
        unconvertible_count = sum(1 for f in self.files if f["status"] == FileStatus.UNCONVERTIBLE)
        pending_size = sum(f["size_kb"] for f in self.files if f["status"] == FileStatus.PENDING)
        unconvertible_size = sum(f["size_kb"] for f in self.files if f["status"] == FileStatus.UNCONVERTIBLE)

        return {
            "total_count": total_count,
            "pending_count": pending_count,
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
            f"Niekonwertowalne: {stats['unconvertible_count']} ({stats['unconvertible_size_mb']} MB)"
        )
