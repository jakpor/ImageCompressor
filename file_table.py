import customtkinter
from definitions import FileStatus


class FileProcessingTable(customtkinter.CTkScrollableFrame):
    # Change 'parent' to 'master' right here
    def __init__(self, master, file_list=None, **kwargs):
        # Pass 'master' down to the super init
        super().__init__(master, label_text="", **kwargs)
        self.file_list = file_list if file_list is not None else []
        self.row_widgets = []
        self.row_lookup = {}

        # Configure columns (0: Checkbox, 1: Filename, 2: Size)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0)

        # Create static table header
        self._create_headers()

        if self.file_list:
            self.populate_data(self.file_list)

    def _create_headers(self):
        lbl_status = customtkinter.CTkLabel(self, text=" Status", font=("Roboto", 12, "bold"), width=70, anchor="w")
        lbl_status.grid(row=0, column=0, padx=(10, 5), pady=(5, 10), sticky="w")

        lbl_name = customtkinter.CTkLabel(self, text="Nazwa pliku", font=("Roboto", 12, "bold"), anchor="w")
        lbl_name.grid(row=0, column=1, padx=5, pady=(5, 10), sticky="ew")

        lbl_size = customtkinter.CTkLabel(self, text="Rozmiar (KB) ", font=("Roboto", 12, "bold"), width=90, anchor="e")
        lbl_size.grid(row=0, column=2, padx=(5, 15), pady=(5, 10), sticky="e")

    def populate_data(self, file_list):
        self.clear_table()
        self.file_list = file_list

        for idx, (status_val, filename, size_kb) in enumerate(self.file_list, start=1):
            self._create_or_update_row(idx, status_val, filename, size_kb)

    def update_rows_from_entries(self, entries):
        for entry in entries:
            relative_path = entry.get("relative_path") or entry.get("filename")
            if not relative_path:
                continue
            self._create_or_update_row(
                len(self.row_lookup) + 1,
                entry.get("status"),
                relative_path,
                entry.get("size_kb", 0),
                key=relative_path,
            )

    def _create_or_update_row(self, row_idx, status_val, filename, size_kb, key=None):
        if key is None:
            key = filename

        try:
            status_enum = FileStatus(status_val)
        except (ValueError, TypeError):
            status_enum = FileStatus.PENDING

        if status_enum == FileStatus.PENDING:
            bg_color = ("#EAEAEA", "#2D2D2D")
            text_color = ("#000000", "#FFFFFF")
        elif status_enum in {FileStatus.DONE, FileStatus.EXISTING_PENDING, FileStatus.EXISTING_UNCONVERTIBLE}:
            bg_color = ("#D4EDDA", "#1E4620")
            text_color = ("#155724", "#A3E2A5")
        elif status_enum == FileStatus.UNCONVERTIBLE:
            bg_color = ("#FFF3CD", "#4A3B18")
            text_color = ("#856404", "#FAD87F")
        else:
            bg_color = ("#F8D7DA", "#4E1D24")
            text_color = ("#721C24", "#F5B7C1")

        if key in self.row_lookup:
            status_lbl, name_lbl, size_lbl = self.row_lookup[key]
            status_lbl.configure(text=status_enum.value, fg_color=bg_color, text_color=text_color)
            name_lbl.configure(
                text=filename, fg_color=bg_color, text_color=text_color[1] if isinstance(text_color, tuple) else None
            )
            size_lbl.configure(
                text=f"{size_kb} KB",
                fg_color=bg_color,
                text_color=text_color[1] if isinstance(text_color, tuple) else None,
            )
            return

        status_lbl = customtkinter.CTkLabel(
            self,
            text=status_enum.value,
            anchor="w",
            font=("Roboto", 12, "bold"),
            fg_color=bg_color,
            text_color=text_color,
        )
        status_lbl.grid(row=row_idx, column=0, padx=(20, 5), pady=3, sticky="ew")

        name_lbl = customtkinter.CTkLabel(
            self,
            text=filename,
            anchor="w",
            font=("Roboto", 12),
            fg_color=bg_color,
            text_color=text_color[1] if isinstance(text_color, tuple) else None,
        )
        name_lbl.grid(row=row_idx, column=1, padx=5, pady=3, sticky="ew")

        size_lbl = customtkinter.CTkLabel(
            self,
            text=f"{size_kb} KB",
            anchor="e",
            font=("Roboto", 12),
            fg_color=bg_color,
            text_color=text_color[1] if isinstance(text_color, tuple) else None,
        )
        size_lbl.grid(row=row_idx, column=2, padx=(5, 20), pady=3, sticky="ew")

        self.row_widgets.extend([status_lbl, name_lbl, size_lbl])
        self.row_lookup[key] = (status_lbl, name_lbl, size_lbl)

    def clear_table(self):
        for widget in self.row_widgets:
            widget.destroy()
        self.row_widgets.clear()
        self.row_lookup.clear()
        self.file_list = []
