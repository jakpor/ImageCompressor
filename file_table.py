import customtkinter
from file_status import FileStatus


class FileProcessingTable(customtkinter.CTkScrollableFrame):
    # Change 'parent' to 'master' right here
    def __init__(self, master, file_list=None, **kwargs):
        # Pass 'master' down to the super init
        super().__init__(master, label_text="", **kwargs)
        self.file_list = file_list if file_list is not None else []
        self.row_widgets = []

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
            # Resolve the raw string status value into the target FileStatus Enum object
            try:
                status_enum = FileStatus(status_val)
            except ValueError:
                # Fallback safeguard in case a raw unexpected string passes through
                status_enum = FileStatus.PENDING

            # Define unique text colors and container backgrounds based on the active state
            if status_enum == FileStatus.PENDING:
                bg_color = ("#EAEAEA", "#2D2D2D")  # Soft neutral gray for waiting status
                text_color = ("#000000", "#FFFFFF")
            elif (
                status_enum == FileStatus.DONE
                or status_enum == FileStatus.EXISTING_PENDING
                or status_enum == FileStatus.EXISTING_UNCONVERTIBLE
            ):
                bg_color = ("#D4EDDA", "#1E4620")  # Muted green tint matching success states
                text_color = ("#155724", "#A3E2A5")
            elif status_enum == FileStatus.UNCONVERTIBLE:
                bg_color = ("#FFF3CD", "#4A3B18")  # Warm amber yellow for skipped files
                text_color = ("#856404", "#FAD87F")

            # 1. Status Column: Replaced the obsolete checkbox widget with a strict text Label representation
            status_lbl = customtkinter.CTkLabel(
                self,
                text=status_enum.value,
                anchor="w",
                font=("Roboto", 12, "bold"),
                fg_color=bg_color,
                text_color=text_color,
            )
            status_lbl.grid(row=idx, column=0, padx=(20, 5), pady=3, sticky="ew")

            # 2. Filename Column: Injected matching line backgrounds for grid visual coherence
            name_lbl = customtkinter.CTkLabel(
                self,
                text=filename,
                anchor="w",
                font=("Roboto", 12),
                fg_color=bg_color,
                text_color=text_color[1] if isinstance(text_color, tuple) else None,  # Keeps regular text adaptive
            )
            name_lbl.grid(row=idx, column=1, padx=5, pady=3, sticky="ew")

            # 3. Size Column: Enforced matching strip color grids across the entire processing matrix row
            size_lbl = customtkinter.CTkLabel(
                self,
                text=f"{size_kb} KB",
                anchor="e",
                font=("Roboto", 12),
                fg_color=bg_color,
                text_color=text_color[1] if isinstance(text_color, tuple) else None,
            )
            size_lbl.grid(row=idx, column=2, padx=(5, 20), pady=3, sticky="ew")

            self.row_widgets.extend([status_lbl, name_lbl, size_lbl])

    def clear_table(self):
        for widget in self.row_widgets:
            widget.destroy()
        self.row_widgets.clear()
        self.file_list = []
