import customtkinter
from definitions import FileStatus
from dataclasses import dataclass


@dataclass
class FilterConfig:
    show_conv: bool = True
    show_non_conv: bool = True
    show_done: bool = True
    show_errors: bool = True
    page_size: int = 100  # Maximum number of rows to display in the UI table
    page_number: int = 1  # Current page number for pagination (1-based index)


class FileProcessingTable(customtkinter.CTkScrollableFrame):
    def __init__(self, master, manager, displayed_indices=None, **kwargs):
        super().__init__(master, label_text="", **kwargs)
        self.manager = manager

        self.filter_config = None  # Will be set when populate_from_manager is called
        # If no custom slice/filter is provided, default to displaying all files from the manager
        self.displayed_indices = displayed_indices if displayed_indices is not None else list(range(len(manager.files)))

        self.row_widgets = []
        self.row_lookup = {}  # Maps unique file keys (paths/filenames) to their respective UI labels

        # Configure columns (0: L.p., 1: Status, 2: Filename, 3: Source size, 4: Compressed size)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)
        self.grid_columnconfigure(3, weight=0)
        self.grid_columnconfigure(4, weight=0)

        # Create static table header
        self._create_headers()

        # Build table based on the provided index list
        if self.displayed_indices:
            self.populate_from_manager(self.displayed_indices)

    def _create_headers(self):
        lbl_idx = customtkinter.CTkLabel(self, text="L.p.", font=("Roboto", 12, "bold"), width=40, anchor="center")
        lbl_idx.grid(row=0, column=0, padx=(10, 5), pady=(5, 10), sticky="w")

        lbl_status = customtkinter.CTkLabel(self, text=" Status", font=("Roboto", 12, "bold"), width=70, anchor="w")
        lbl_status.grid(row=0, column=1, padx=5, pady=(5, 10), sticky="w")

        lbl_name = customtkinter.CTkLabel(self, text="Nazwa pliku", font=("Roboto", 12, "bold"), anchor="w")
        lbl_name.grid(row=0, column=2, padx=5, pady=(5, 10), sticky="ew")

        lbl_size = customtkinter.CTkLabel(
            self, text="Źródłowy (KB)", font=("Roboto", 12, "bold"), width=100, anchor="e"
        )
        lbl_size.grid(row=0, column=3, padx=(5, 10), pady=(5, 10), sticky="e")

        lbl_compressed_size = customtkinter.CTkLabel(
            self, text="Skompresowany (KB)", font=("Roboto", 12, "bold"), width=125, anchor="e"
        )
        lbl_compressed_size.grid(row=0, column=4, padx=(5, 15), pady=(5, 10), sticky="e")

    @staticmethod
    def _normalize_row(row_data):
        if isinstance(row_data, dict):
            return (
                row_data.get("status"),
                row_data.get("relative_path") or row_data.get("filename"),
                row_data.get("size_kb"),
                row_data.get("output_size_kb"),
            )
        if len(row_data) >= 4:
            return row_data[0], row_data[1], row_data[2], row_data[3]
        return row_data[0], row_data[1], row_data[2], None

    @staticmethod
    def _format_size(size_kb):
        if size_kb is None:
            return "—"
        return f"{size_kb:.1f} KB"

    def populate_from_manager(self, filter_config: FilterConfig = None, force_refresh=False):
        """Redraws the table completely for the given list of global manager indices."""
        if self.filter_config == filter_config and not force_refresh:
            return
        self.clear_table()
        self.filter_config = filter_config
        self.displayed_indices = self._get_ui_table_indices(filter_config)

        for global_idx in self.displayed_indices:
            row_data = self.manager.files[global_idx]
            status_val, filename, size_kb, output_size_kb = self._normalize_row(row_data)

            key = row_data.get("relative_path") or row_data.get("filename") or filename
            self._create_or_update_row(global_idx + 1, status_val, filename, size_kb, output_size_kb, key=key)

    def update_single_index(self, global_idx):
        """Updates or adds a single file based on its global manager index."""
        if global_idx not in self.displayed_indices:
            # If the file updated in the background but is filtered out from the current view, do nothing
            return

        row_data = self.manager.files[global_idx]
        status_val, filename, size_kb, output_size_kb = self._normalize_row(row_data)
        key = row_data.get("relative_path") or row_data.get("filename") or filename

        # Calculate visual grid position based on the position inside the filtered list
        self._create_or_update_row(global_idx, status_val, filename, size_kb, output_size_kb, key=key)

    def _create_or_update_row(self, row_idx, status_val, filename, size_kb, output_size_kb, key=None):
        if key is None:
            key = filename

        try:
            status_enum = FileStatus(status_val)
        except (ValueError, TypeError):
            status_enum = FileStatus.PENDING

        # UI Color schemes based on file processing status
        if status_enum == FileStatus.PENDING:
            bg_color = ("#EAEAEA", "#2D2D2D")
            text_color = ("#000000", "#FFFFFF")
        elif status_enum in {FileStatus.DONE, FileStatus.EXISTING_PENDING, FileStatus.EXISTING_UNCONVERTIBLE}:
            bg_color = ("#D4EDDA", "#1E4620")
            text_color = ("#155724", "#A3E2A5")
        elif status_enum == FileStatus.UNCONVERTIBLE:
            bg_color = ("#FFF3CD", "#4A3B18")
            text_color = ("#856404", "#FAD87F")
        elif status_enum in {FileStatus.ERROR_COMPRESSION, FileStatus.ERROR_COPY}:
            bg_color = ("#F8D7DA", "#4C1D1F")
            text_color = ("#721C24", "#F5C6CB")
        else:
            bg_color = ("#F8D7DA", "#4E1D24")
            text_color = ("#721C24", "#F5B7C1")

        # UPDATE EXISTING ROW
        if key in self.row_lookup:
            idx_lbl, status_lbl, name_lbl, size_lbl, compressed_size_lbl = self.row_lookup[key]
            idx_lbl.configure(fg_color=bg_color, text_color=text_color if isinstance(text_color, tuple) else None)
            status_lbl.configure(text=status_enum.value, fg_color=bg_color, text_color=text_color)
            name_lbl.configure(
                text=filename, fg_color=bg_color, text_color=text_color if isinstance(text_color, tuple) else None
            )
            size_lbl.configure(
                text=self._format_size(size_kb),
                fg_color=bg_color,
                text_color=text_color if isinstance(text_color, tuple) else None,
            )
            compressed_size_lbl.configure(
                text=self._format_size(output_size_kb),
                fg_color=bg_color,
                text_color=text_color if isinstance(text_color, tuple) else None,
            )
            return

        # CREATE NEW ROW
        # Column 0: Row Index (L.p.)
        idx_lbl = customtkinter.CTkLabel(
            self,
            text=str(row_idx),
            anchor="center",
            width=40,
            font=("Roboto", 12),
            fg_color=bg_color,
            text_color=text_color if isinstance(text_color, tuple) else None,
        )
        idx_lbl.grid(row=row_idx, column=0, padx=(10, 5), pady=3, sticky="ew")

        # Column 1: Status
        status_lbl = customtkinter.CTkLabel(
            self,
            text=status_enum.value,
            anchor="w",
            font=("Roboto", 12, "bold"),
            fg_color=bg_color,
            text_color=text_color,
        )
        status_lbl.grid(row=row_idx, column=1, padx=5, pady=3, sticky="ew")

        # Column 2: Filename
        name_lbl = customtkinter.CTkLabel(
            self,
            text=filename,
            anchor="w",
            font=("Roboto", 12),
            fg_color=bg_color,
            text_color=text_color if isinstance(text_color, tuple) else None,
        )
        name_lbl.grid(row=row_idx, column=2, padx=5, pady=3, sticky="ew")

        # Column 3: Source Size
        size_lbl = customtkinter.CTkLabel(
            self,
            text=self._format_size(size_kb),
            anchor="e",
            font=("Roboto", 12),
            fg_color=bg_color,
            text_color=text_color if isinstance(text_color, tuple) else None,
        )
        size_lbl.grid(row=row_idx, column=3, padx=(5, 10), pady=3, sticky="ew")

        # Column 4: Compressed Size
        compressed_size_lbl = customtkinter.CTkLabel(
            self,
            text=self._format_size(output_size_kb),
            anchor="e",
            font=("Roboto", 12),
            fg_color=bg_color,
            text_color=text_color if isinstance(text_color, tuple) else None,
        )
        compressed_size_lbl.grid(row=row_idx, column=4, padx=(5, 20), pady=3, sticky="ew")

        self.row_widgets.extend([idx_lbl, status_lbl, name_lbl, size_lbl, compressed_size_lbl])
        self.row_lookup[key] = (idx_lbl, status_lbl, name_lbl, size_lbl, compressed_size_lbl)

    def _get_ui_table_indices(self, filter_config: FilterConfig = None) -> list:
        """Returns a list of global integer indices representing a raw slice of files filtered by status."""
        if filter_config is None:
            filter_config = FilterConfig()

        start_raw_idx = (filter_config.page_number - 1) * filter_config.page_size
        end_raw_idx = start_raw_idx + filter_config.page_size

        total_files = len(self.manager.files)
        if end_raw_idx > total_files:
            end_raw_idx = total_files

        filtered_indices = []

        for idx in range(start_raw_idx, end_raw_idx):
            f = self.manager.files[idx]
            current_status = f["status"]

            if current_status == FileStatus.DONE and not filter_config.show_done:
                continue  # Converted
            if (
                current_status == FileStatus.PENDING or current_status == FileStatus.EXISTING_PENDING
            ) and not filter_config.show_conv:
                continue  # Pending
            if (
                current_status == FileStatus.UNCONVERTIBLE or current_status == FileStatus.EXISTING_UNCONVERTIBLE
            ) and not filter_config.show_non_conv:
                continue  # Unconvertible
            if (
                current_status == FileStatus.ERROR_COMPRESSION or current_status == FileStatus.ERROR_COPY
            ) and not filter_config.show_errors:
                continue  # Errors

            filtered_indices.append(idx)

        return filtered_indices

    def clear_table(self):
        for widget in self.row_widgets:
            widget.destroy()
        self.row_widgets.clear()
        self.row_lookup.clear()
        self.displayed_indices = []
