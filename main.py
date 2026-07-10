import signal
import sys
import os
import queue
import tkinter as tk
from tkinter import StringVar, IntVar
import customtkinter
import threading
from file_manager import FileManager
from config_manager import ConfigManager
from file_table import FileProcessingTable, FilterConfig
from compressor import create_configured_compressor
from definitions import FileStatus

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("green")

_UI_LOG_LOCK = threading.Lock()


# Tooltip class for providing hover-over information
class CTkTooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        # Bindowanie zdarzeń najechania myszką
        self.widget.bind("<Enter>", self.show_tip)
        self.widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        # Pobieranie pozycji widgetu na ekranie
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 25

        # Tworzenie małego okna bez obramowania systemowego
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")

        # Etykieta z tekstem podpowiedzi (styl dopasowany do ciemnego/jasnego motywu)
        is_dark = customtkinter.get_appearance_mode() == "Dark"
        bg_color = "#2b2b2b" if is_dark else "#e5e5e5"
        fg_color = "white" if is_dark else "black"

        label = tk.Label(
            self.tip_window,
            text=self.text,
            justify="left",
            background=bg_color,
            foreground=fg_color,
            relief="solid",
            borderwidth=1,
            font=("Roboto", 10, "italic"),
            padx=5,
            pady=3,
        )
        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class App(customtkinter.CTk):
    WIDTH = 900
    HEIGHT = 700

    def __init__(self):
        super().__init__()
        self.threads = []
        self._shutdown_event = threading.Event()
        self._compression_stop_event = threading.Event()

        self.file_manager = FileManager()
        self.load_file_config = {}

        # 1. Initialize config manager and load stored settings
        self.config_manager = ConfigManager()
        stored_settings = self.config_manager.load_settings()

        self.title("Zmniejszacz obrazów")
        self.geometry(f"{App.WIDTH}x{App.HEIGHT}")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        signal.signal(signal.SIGINT, lambda sig, frame: self.on_closing())

        self.magick_path = None
        self.cjpegli_path = None
        try:
            icon_path = get_resource_path("press.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
                self.after(10, lambda: self.wm_iconbitmap(icon_path))
            self.magick_path = get_resource_path("imageMagick/magick.exe")
            self.cjpegli_path = get_resource_path("jpegli/cjpegli.exe")
        except Exception:
            print("Error loading internal files.")
            pass

        # Initialize compressor
        self.compressor = create_configured_compressor()

        # Main Layout Configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Table takes up remaining vertical space

        # ================= TOP FRAME: Settings & Options =================
        self.frame_top = customtkinter.CTkFrame(master=self, corner_radius=8)
        self.frame_top.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)

        # Exact column layout rules that force everything to align properly
        self.frame_top.grid_columnconfigure(0, weight=0, minsize=180)
        self.frame_top.grid_columnconfigure(1, weight=1)
        self.frame_top.grid_columnconfigure(2, weight=0)

        # 1. Input Directory
        self.label_src = customtkinter.CTkLabel(self.frame_top, text="Folder wejściowy:", font=("Roboto", 14))
        self.label_src.grid(row=0, column=0, pady=8, padx=15, sticky="w")

        # Hooked: Init from config + auto-save trace
        self.source_dir = StringVar(value=stored_settings["source_dir"])
        self.source_dir.trace_add("write", lambda *args: self.save_config())
        self.entry_src = customtkinter.CTkEntry(self.frame_top, textvariable=self.source_dir)
        self.entry_src.grid(row=0, column=1, pady=8, padx=10, sticky="ew")

        self.btn_src = customtkinter.CTkButton(
            self.frame_top, text="Przeglądaj...", width=100, command=self.get_source_dir
        )
        self.btn_src.grid(row=0, column=2, pady=8, padx=15)

        # 2. Output Directory
        self.label_out = customtkinter.CTkLabel(self.frame_top, text="Folder wyjściowy:", font=("Roboto", 14))
        self.label_out.grid(row=1, column=0, pady=8, padx=15, sticky="w")

        # Hooked: Init from config + auto-save trace
        self.output_dir = StringVar(value=stored_settings["output_dir"])
        self.output_dir.trace_add("write", lambda *args: self.save_config())
        self.entry_out = customtkinter.CTkEntry(self.frame_top, textvariable=self.output_dir)
        self.entry_out.grid(row=1, column=1, pady=8, padx=10, sticky="ew")

        self.btn_out = customtkinter.CTkButton(
            self.frame_top, text="Przeglądaj...", width=100, command=self.get_output_dir
        )
        self.btn_out.grid(row=1, column=2, pady=8, padx=15)

        # === 3. SUBFOLDER STRATEGY & 4. QUALITY SETTINGS (Combined in Row 2) ===
        # Place the main label directly in column 0 of frame_top for perfect alignment
        self.label_strat = customtkinter.CTkLabel(self.frame_top, text="Struktura folderów:", font=("Roboto", 14))
        self.label_strat.grid(row=2, column=0, pady=8, padx=15, sticky="w")

        # Create a container ONLY for the interactive fields to live in column 1 and 2 spanned
        self.strat_quality_container = customtkinter.CTkFrame(self.frame_top, fg_color="transparent")
        self.strat_quality_container.grid(row=2, column=1, columnspan=2, pady=8, padx=10, sticky="w")

        # Hooked: Init from config + auto-save command callback
        self.strategy_var = StringVar(value=stored_settings["strategy"])
        self.combo_strat = customtkinter.CTkComboBox(
            self.strat_quality_container,
            values=["zachowaj strukturę podfolderów", "spłaszcz podfoldery", "nie skanuj podfolderów"],
            variable=self.strategy_var,
            width=220,
            command=lambda choice: self.save_config(),
        )
        CTkTooltip(
            self.combo_strat,
            "Wybierz jak mają być traktowane podfoldery w folderze wejściowym. 'Nie skanuj podfolderów' oznacza, że tylko pliki w głównym folderze wejściowym zostaną przetworzone.",
        )
        self.combo_strat.pack(side="left", padx=(0, 20))

        # --- Quality Settings inside the same horizontal pack layout ---
        self.label_quality = customtkinter.CTkLabel(
            self.strat_quality_container, text="Jakość [1-100]:", font=("Roboto", 14)
        )
        self.label_quality.pack(side="left", padx=(0, 5))
        CTkTooltip(
            self.label_quality,
            "Jakość kompresji. Wyższa wartość oznacza lepszą jakość obrazu, ale większy rozmiar pliku. Zalecana wartość to 85-95.",
        )

        # Hooked: Init from config + strict range trace that automatically invokes save_config
        initial_quality = int(stored_settings.get("quality", 90))
        self.quality_int = IntVar(value=initial_quality)
        self.quality_str = StringVar(value=str(initial_quality))
        self.quality_int.trace_add("write", lambda *args: self._on_slider_move())
        self.quality_str.trace_add("write", lambda *args: self._validate_quality())

        self.slider_quality = customtkinter.CTkSlider(
            self.strat_quality_container, from_=1, to=100, variable=self.quality_int, width=150
        )
        self.slider_quality.pack(side="left", padx=5)

        self.entry_quality = customtkinter.CTkEntry(
            self.strat_quality_container, width=50, textvariable=self.quality_str
        )
        self.entry_quality.pack(side="left", padx=(5, 0))

        # === 5. OUTPUT RESOLUTION (Shifted to Row 3) ===
        self.label_res = customtkinter.CTkLabel(self.frame_top, text="Rozdzielczość maksymalna:", font=("Roboto", 14))
        self.label_res.grid(row=3, column=0, pady=8, padx=15, sticky="w")

        # Container frame to align dropdown, custom inputs and checkbox horizontally
        self.res_container = customtkinter.CTkFrame(self.frame_top, fg_color="transparent")
        self.res_container.grid(row=3, column=1, columnspan=2, pady=8, padx=10, sticky="w")

        # Resolution dropdown selection
        self.res_option_var = StringVar(value=stored_settings.get("resolution_preset", "4K:3840x2560"))
        self.combo_res = customtkinter.CTkComboBox(
            self.res_container,
            values=["4K:3840x2560", "2K:2160x1440", "1080x720", "Własna (Szer x Wys)"],
            variable=self.res_option_var,
            command=self.on_resolution_changed,
            width=180,
        )
        CTkTooltip(
            self.combo_res,
            "Maksymalna rozdzielczość wyjściowa. Obrazy większe niż wybrana rozdzielczość zostaną zmniejszone proporcjonalnie.",
        )
        self.combo_res.pack(side="left")

        # Custom Resolution Input frame (inside the horizontal container)
        self.custom_res_frame = customtkinter.CTkFrame(self.res_container, fg_color="transparent")
        self.custom_res_frame.pack(side="left", padx=15)

        # Width input field
        self.custom_w_var = StringVar(value=stored_settings.get("custom_w", "1920"))
        self.custom_w_var.trace_add("write", lambda *args: self.save_config())
        self.custom_w = customtkinter.CTkEntry(
            self.custom_res_frame, width=60, placeholder_text="W", textvariable=self.custom_w_var
        )
        self.custom_w.pack(side="left", padx=2)

        self.label_x = customtkinter.CTkLabel(self.custom_res_frame, text="x")
        self.label_x.pack(side="left", padx=2)

        # Height input field
        self.custom_h_var = StringVar(value=stored_settings.get("custom_h", "1080"))
        self.custom_h_var.trace_add("write", lambda *args: self.save_config())
        self.custom_h = customtkinter.CTkEntry(
            self.custom_res_frame, width=60, placeholder_text="H", textvariable=self.custom_h_var
        )
        self.custom_h.pack(side="left", padx=2)

        # Run visibility update on startup based on loaded preferences
        self.toggle_custom_res(self.res_option_var.get())

        # --- WORKERS SECTION (Moved next to resolution container) ---
        # Label for the worker input field
        self.worker_count_label = customtkinter.CTkLabel(self.res_container, text="Wątki:", font=("Roboto", 14))
        self.worker_count_label.pack(side="left", padx=(25, 5))

        # Hooked: Worker text field + auto-save trace
        self.worker_count_var = StringVar(value=stored_settings.get("worker_count", "4"))
        self.worker_count_var.trace_add("write", lambda *args: self.save_config())
        self.worker_count_entry = customtkinter.CTkEntry(
            self.res_container, width=45, textvariable=self.worker_count_var
        )
        self.worker_count_entry.pack(side="left", padx=2)
        CTkTooltip(
            self.worker_count_entry,
            "Ile obrazów może być przetwarzanych jednocześnie. Zbyt duża liczba wątków może spowodować spowolnienie systemu.",
        )

        # ================= Options Checkboxes Container =================
        self.frame_checkboxes = customtkinter.CTkFrame(self.frame_top, fg_color="transparent")
        self.frame_checkboxes.grid(row=5, column=1, columnspan=2, pady=(4, 8), padx=10)

        # 6. Checkbox - copy all files, including uncompressible ones
        initial_cb_value = stored_settings.get("copy_uncompressible", "False") == "True"
        self.copy_uncompressible_var = tk.BooleanVar(value=initial_cb_value)
        self.cb_copy_uncompressible = customtkinter.CTkCheckBox(
            self.frame_checkboxes,
            text="Kopiuj niekompresowalne pliki",
            variable=self.copy_uncompressible_var,
            command=self.save_config,
            font=("Roboto", 12),
        )
        self.cb_copy_uncompressible.pack(side="left", padx=15, anchor="center")
        CTkTooltip(
            self.cb_copy_uncompressible,
            "Zaznacz by skopiować wszystkie pliki, nawet te, których nie można skompresować",
        )

        # 7. Checkbox - overwrite existing output files
        initial_overwrite_value = stored_settings.get("overwrite_files", "False") == "True"
        self.overwrite_files_var = tk.BooleanVar(value=initial_overwrite_value)
        self.cb_overwrite_files = customtkinter.CTkCheckBox(
            self.frame_checkboxes,
            text="Nadpisz pliki w folderze wyjściowym",
            variable=self.overwrite_files_var,
            command=self.save_config,
            font=("Roboto", 12),
        )
        self.cb_overwrite_files.pack(side="left", padx=15, anchor="center")
        CTkTooltip(self.cb_overwrite_files, "Zaznacz by nadpisać już skompresowane pliki w folderze wyjściowym")

        # 7. Checkbox - Usuń metadane
        initial_remove_metadata_value = stored_settings.get("remove_metadata", "False") == "True"
        self.remove_metadata_var = tk.BooleanVar(value=initial_remove_metadata_value)
        self.cb_remove_metadata = customtkinter.CTkCheckBox(
            self.frame_checkboxes,
            text="Usuń metadane",
            variable=self.remove_metadata_var,
            command=self.save_config,
            font=("Roboto", 12),
        )
        self.cb_remove_metadata.pack(side="left", padx=15, anchor="center")
        CTkTooltip(
            self.cb_remove_metadata, "Zaznacz by usunąć metadane plików (daty utworzenia, informacje o aparacie, etc.)"
        )

        # ================= CONTROLS FRAME =================
        self.frame_controls = customtkinter.CTkFrame(master=self, fg_color="transparent")
        self.frame_controls.grid(row=1, column=0, sticky="ew", padx=15, pady=(5, 10))
        self.frame_controls.columnconfigure((0, 1), weight=1)

        # Big, prominent action buttons
        self.btn_load = customtkinter.CTkButton(
            self.frame_controls,
            text="Wczytaj pliki",
            height=45,
            font=("Roboto", 15, "bold"),
            fg_color="green",
            hover_color="darkgreen",
            command=self.load_files_btn,
        )
        self.btn_load.grid(row=0, column=0, pady=5, padx=(0, 10), sticky="ew")

        self.btn_start_comp = customtkinter.CTkButton(
            self.frame_controls,
            text="Kompresuj",
            height=45,
            font=("Roboto", 15, "bold"),
            fg_color="green",
            hover_color="darkgreen",
            command=self.toggle_compression,
        )
        self.btn_start_comp.grid(row=0, column=1, pady=5, padx=(10, 0), sticky="ew")

        # ================= FILE SELECTION FILTER ROW (Row 2) =================
        # Placed after control frame, directly before the file frame
        self.frame_filter = customtkinter.CTkFrame(master=self, corner_radius=8)
        self.frame_filter.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 10))

        # Optimized columns for width=900 (reduced left column minsize from 180 to 130)
        self.frame_filter.grid_columnconfigure(0, weight=0, minsize=130)
        self.frame_filter.grid_columnconfigure(1, weight=1)

        self.label_filter = customtkinter.CTkLabel(self.frame_filter, text="Wyświetl pliki:", font=("Roboto", 14))
        CTkTooltip(
            self.label_filter,
            "Filtruj wyświetlane pliki w tabeli. Możesz wybrać, czy chcesz widzieć pliki konwertowalne, niekonwertowalne, skonwertowane lub błędy.\nTabela wyświetla pliki stronicami, użyj strzałek po prawej stronie, aby przełączać strony.",
        )
        self.label_filter.grid(row=0, column=0, pady=10, padx=10, sticky="w")

        # Container framework to map checkboxes and navigation inline horizontally
        self.filter_container = customtkinter.CTkFrame(self.frame_filter, fg_color="transparent")
        self.filter_container.grid(row=0, column=1, pady=10, padx=(0, 10), sticky="ew")

        # State tracking configurations for functional table view hooks
        initial_show_convertible = stored_settings.get("show_convertible", "False") == "True"
        initial_show_non_convertible = stored_settings.get("show_non_convertible", "False") == "True"
        initial_show_converted = stored_settings.get("show_converted", "False") == "True"
        initial_show_errors = stored_settings.get("show_errors", "False") == "True"
        self.page_size = int(stored_settings.get("page_size", 50))

        self.show_convertible = customtkinter.BooleanVar(value=initial_show_convertible)
        self.show_non_convertible = customtkinter.BooleanVar(value=initial_show_non_convertible)
        self.show_converted = customtkinter.BooleanVar(value=initial_show_converted)
        self.show_errors = customtkinter.BooleanVar(value=initial_show_errors)

        # Checkboxes with tighter horizontal padding (padx=8 instead of 15) to preserve space
        self.chk_convertible = customtkinter.CTkCheckBox(
            self.filter_container, text="konwertowalne", variable=self.show_convertible, command=self.on_filter_changed
        )
        self.chk_convertible.pack(side="left", padx=(0, 8))

        self.chk_non_convertible = customtkinter.CTkCheckBox(
            self.filter_container,
            text="niekonwertowalne",
            variable=self.show_non_convertible,
            command=self.on_filter_changed,
        )
        self.chk_non_convertible.pack(side="left", padx=8)

        self.chk_converted = customtkinter.CTkCheckBox(
            self.filter_container, text="skonwertowane", variable=self.show_converted, command=self.on_filter_changed
        )
        self.chk_converted.pack(side="left", padx=8)

        self.chk_errors = customtkinter.CTkCheckBox(
            self.filter_container, text="błędy", variable=self.show_errors, command=self.on_filter_changed
        )
        self.chk_errors.pack(side="left", padx=8)

        # ================= PAGINATION NAVIGATION =================
        self.current_page = 1
        self.total_pages = 1

        # Pagination sub-container placed at the far RIGHT of the bar
        self.pagination_container = customtkinter.CTkFrame(self.filter_container, fg_color="transparent")
        self.pagination_container.pack(side="right", padx=(5, 0))

        # Left arrow button to go to previous page
        self.btn_prev_page = customtkinter.CTkButton(
            self.pagination_container,
            text="←",
            width=25,  # Slightly narrower button
            height=26,
            font=("Roboto", 12, "bold"),
            command=self.on_prev_page,
        )
        self.btn_prev_page.pack(side="left", padx=2)

        # Central label displaying current position
        self.lbl_page_number = customtkinter.CTkLabel(
            self.pagination_container, text=f"Strona {self.current_page} z {self.total_pages}", font=("Roboto", 12)
        )
        self.lbl_page_number.pack(side="left", padx=6)

        # Right arrow button to go to next page
        self.btn_next_page = customtkinter.CTkButton(
            self.pagination_container,
            text="→",
            width=25,  # Slightly narrower button
            height=26,
            font=("Roboto", 12, "bold"),
            command=self.on_next_page,
        )
        self.btn_next_page.pack(side="left", padx=2)

        # ================= MIDDLE FRAME: File Table =================
        # Row layout configuration update: row 3 is now the table
        self.grid_rowconfigure(3, weight=1)

        self.frame_middle = customtkinter.CTkFrame(master=self, corner_radius=8)
        self.frame_middle.grid(row=3, column=0, sticky="nsew", padx=15, pady=0)
        self.frame_middle.grid_rowconfigure(0, weight=1)
        self.frame_middle.grid_columnconfigure(0, weight=1)

        # Inicjalizacja nowej tabeli wewnątrz środkowej ramki
        self.table = FileProcessingTable(master=self.frame_middle, manager=self.file_manager)
        self.table.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # ================= BOTTOM FRAME: Status Bar (At the very bottom) =================
        # Row layout configuration update: row 4 is the thin status bar
        self.grid_rowconfigure(4, weight=0)

        self.frame_bottom = customtkinter.CTkFrame(master=self, height=50, corner_radius=8)
        self.frame_bottom.grid(row=4, column=0, sticky="ew", padx=15, pady=15)
        self.frame_bottom.columnconfigure(0, weight=1)

        # Progress bar integrated cleanly into the status area
        self.progressbar = customtkinter.CTkProgressBar(self.frame_bottom)
        self.progressbar.grid(row=0, column=0, sticky="ew", padx=15, pady=(10, 5))
        self.progressbar.set(0)
        self.scan_in_progress = False
        self.compress_in_progress = False
        self.ui_queue = queue.Queue()
        self._ui_queue_active = False
        self._pending_refresh = False
        self._processed_file_count = 0
        self._total_files_to_process = 0
        self._compression_pending = False

        # Status Label acting as Status Bar
        self.status_var = StringVar(value="Gotowy")
        self.status_bar = customtkinter.CTkLabel(
            self.frame_bottom, textvariable=self.status_var, font=("Roboto", 12), text_color="gray"
        )
        self.status_bar.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 5))

    # ================= LOGIC & UTILITIES =================
    def get_source_dir(self):
        path = customtkinter.filedialog.askdirectory()
        if path:
            self.source_dir.set(path)

    def get_output_dir(self):
        path = customtkinter.filedialog.askdirectory()
        if path:
            self.output_dir.set(path)

    def _on_slider_move(self) -> None:
        try:
            val = self.quality_int.get()
            if self.quality_str.get() != str(val):
                self.quality_str.set(str(val))
                self.save_config()
        except tk.TclError:
            pass

    def _validate_quality(self):
        try:
            val_str = self.quality_str.get().strip()
            if val_str == "":
                return
            val_int = int(val_str)
            if val_int < 1:
                val_int = 1
            elif val_int > 100:
                val_int = 100
            if str(val_int) != val_str:
                self.quality.set(str(val_int))
            if self.quality_int.get() != val_int:
                self.quality_int.set(val_int)
        except tk.TclError:
            return  # Allow blank temporary values while typing
        self.save_config()

    def on_resolution_changed(self, choice):
        self.toggle_custom_res(choice)
        self.save_config()

    def toggle_custom_res(self, choice):
        if choice == "Własna (Szer x Wys)":
            self.custom_res_frame.pack(side="left", padx=15)
        else:
            self.custom_res_frame.pack_forget()

    def on_filter_changed(self):
        self._refresh_table_with_current_filters()

    def save_config(self):
        try:
            current_settings = {
                "source_dir": self.source_dir.get(),
                "output_dir": self.output_dir.get(),
                "strategy": self.strategy_var.get(),
                "quality": str(self.quality_int.get()),
                "resolution_preset": self.res_option_var.get(),
                "custom_w": self.custom_w_var.get(),
                "custom_h": self.custom_h_var.get(),
                "copy_uncompressible": str(self.copy_uncompressible_var.get()),
                "overwrite_files": str(self.overwrite_files_var.get()),
                "show_convertible": str(self.show_convertible.get()),
                "show_non_convertible": str(self.show_non_convertible.get()),
                "show_converted": str(self.show_converted.get()),
                "show_errors": str(self.show_errors.get()),
                "remove_metadata": str(self.remove_metadata_var.get()),
                "worker_count": self.worker_count_var.get(),
            }
            self.config_manager.save_settings(current_settings)
        except (tk.TclError, AttributeError) as error:
            print("Error saving config: Invalid value in one of the fields. {}".format(error))
            pass

    def load_files_btn(self, start_compression_after_scan: bool = False):
        src = self.source_dir.get()
        dest = self.output_dir.get()
        strat = self.strategy_var.get()

        self.load_file_config = {"source_dir": src, "output_dir": dest, "strategy": strat}

        if not src:
            self.status_var.set("Błąd: Wybierz najpierw folder wejściowy!")
            return
        if not dest:
            self.status_var.set("Błąd: Wybierz najpierw folder wyjściowy!")
            return

        self.scan_in_progress = True
        self._compression_pending = start_compression_after_scan
        self._set_progress_value(0)
        self._set_status_message("Skanowanie katalogu...")
        self._schedule_ui_drain()
        self.table.clear_table()

        def async_scan():
            try:
                if self._shutdown_event.is_set():
                    return
                self.file_manager.scan_directory(src, strat, dest)
            finally:
                if not self._shutdown_event.is_set():
                    self._queue_ui_update("scan_complete", None)

        thread = threading.Thread(target=async_scan, name="scan-worker", daemon=True)
        self.threads.append(thread)
        thread.start()

    def _refresh_table_with_current_filters(self, force_refresh=False):
        filter_config = FilterConfig(
            show_conv=self.show_convertible.get(),
            show_non_conv=self.show_non_convertible.get(),
            show_done=self.show_converted.get(),
            show_errors=self.show_errors.get(),
            page_number=self.current_page,
            page_size=self.page_size,
        )
        self.table.populate_from_manager(filter_config, force_refresh)
        self.table.update_idletasks()

    def _finalize_scan(self):
        self.scan_in_progress = False
        self._set_progress_value(1)
        self._set_status_message("Skanowanie katalogu zakończone")
        self.total_pages = max(1, (len(self.file_manager.files) + self.page_size - 1) // self.page_size)
        self.update_pagination_display()
        self._refresh_table_with_current_filters(force_refresh=True)
        if self._compression_pending:
            self._compression_pending = False
            self._start_compression_job()

    def _set_compression_button_state(self, running: bool):
        self.btn_start_comp.configure(text="Zatrzymaj kompresję" if running else "Kompresuj")

    def toggle_compression(self):
        if self.compress_in_progress:
            self.stop_compression()
        else:
            self.compress_images_btn()

    def stop_compression(self):
        if not self.compress_in_progress:
            return
        self._compression_stop_event.set()
        self._set_status_message("Zatrzymywanie kompresji...")

    def compress_images_btn(self):
        if self.compress_in_progress:
            return

        if self.scan_in_progress:
            self._compression_pending = True
            self._set_status_message("Skanowanie w toku. Kompresja rozpocznie się po zakończeniu skanowania.")
            return

        if (
            self.load_file_config.get("source_dir") != self.source_dir.get()
            or self.load_file_config.get("output_dir") != self.output_dir.get()
            or self.load_file_config.get("strategy") != self.strategy_var.get()
        ):
            self.load_files_btn(start_compression_after_scan=True)
            self._set_status_message("Wczytywanie plików... Kompresja rozpocznie się po zakończeniu skanowania.")
            return

        self._start_compression_job()

    def _start_compression_job(self):
        quality = self.quality_int.get()
        strip_metadata = self.remove_metadata_var.get()
        overwrite_files = self.overwrite_files_var.get()
        copy_uncompressible = self.copy_uncompressible_var.get()

        resolution = self._get_max_resolution_config()
        config = {
            "magick_path": self.magick_path,
            "cjpegli_path": self.cjpegli_path,
            "quality": quality,
            "strip_metadata": strip_metadata,
            "copy_uncompressible": copy_uncompressible,
            "override_files": overwrite_files,
            "worker_count": int(self.worker_count_var.get()),
            "max_resolution": resolution,
        }
        files_to_process = self.file_manager.get_files_for_compressor()
        if not files_to_process:
            self._set_status_message("Brak plików do kompresji. Najpierw wczytaj katalog.")
            return

        self._processed_file_count = 0
        self._total_files_to_process = len(files_to_process)
        self._compression_stop_event = threading.Event()
        self._set_progress_value(0)
        self.compress_in_progress = True
        self._schedule_ui_drain()
        self._set_compression_button_state(True)

        def worker():
            if self._shutdown_event.is_set():
                return
            self.compressor.compress_files_list(
                files_list=files_to_process,
                config=config,
                progress_callback=self._on_file_processed_callback,
                stop_event=self._compression_stop_event,
            )
            if self._compression_stop_event.is_set():
                self._queue_ui_update("compression_stopped", None)
            else:
                self._queue_ui_update("compression_complete", None)

        thread = threading.Thread(target=worker, name="compress-worker", daemon=True)
        self.threads.append(thread)
        thread.start()
        self._set_status_message("Trwa kompresowanie...")

    def _get_max_resolution_config(self):
        preset = self.res_option_var.get()
        if preset == "4K:3840x2560":
            return "3840x2560"
        if preset == "2K:2160x1440":
            return "2160x1440"
        if preset == "1080x720":
            return "1080x720"
        return f"{self.custom_w_var.get()}x{self.custom_h_var.get()}"

    def _format_size(self, size_kb):
        if size_kb is None:
            return "0 KB"
        if size_kb >= 1024:
            return f"{size_kb / 1024:.1f} MB"
        return f"{size_kb:.1f} KB"

    def _safe_log(self, message: str) -> None:
        with _UI_LOG_LOCK:
            print(message, flush=True)

    def _set_status_message(self, message: str) -> None:
        if threading.current_thread() is threading.main_thread():
            self.status_var.set(message)
        else:
            self._queue_ui_update("status", message)

    def _set_progress_value(self, value: float) -> None:
        if threading.current_thread() is threading.main_thread():
            self.progressbar.set(value)
        else:
            self._queue_ui_update("progress", value)

    def _build_completion_summary(self):
        total = len(self.file_manager.files)
        processed = 0
        skipped = 0
        errors = 0
        saved_kb = 0.0
        for entry in self.file_manager.files:
            status = entry.get("status")
            if status in {
                FileStatus.DONE,
                FileStatus.UNCONVERTIBLE,
                FileStatus.ERROR_COMPRESSION,
                FileStatus.ERROR_COPY,
            }:
                processed += 1
            elif status in {FileStatus.EXISTING_PENDING, FileStatus.EXISTING_UNCONVERTIBLE}:
                skipped += 1
            if status in {FileStatus.ERROR_COMPRESSION, FileStatus.ERROR_COPY}:
                errors += 1
            source_size = entry.get("size_kb") or 0
            output_size = entry.get("output_size_kb")
            if output_size is None:
                continue
            if output_size < source_size:
                saved_kb += source_size - output_size

        saved_text = self._format_size(saved_kb)
        error_suffix = f" Błędy: {errors}." if errors else ""
        if skipped:
            return (
                f"Kompresja zakończona. Przetworzono {processed}/{total} plików. "
                f"Pominięto {skipped} plików z powodu istniejących wyników."
                f"{error_suffix} Zaoszczędzono około {saved_text}."
            )
        return f"Kompresja zakończona. Przetworzono {processed}/{total} plików.{error_suffix} Zaoszczędzono około {saved_text}."

    def _on_file_processed_callback(self, source_path, status: FileStatus):
        self._queue_ui_update("file_status", (str(source_path), status))

    def _schedule_ui_drain(self):
        if self._ui_queue_active:
            return
        self._ui_queue_active = True
        self.after(0, self._drain_ui_queue)

    def _queue_ui_update(self, event_type, payload):
        self.ui_queue.put((event_type, payload))
        if threading.current_thread() is threading.main_thread():
            self._schedule_ui_drain()

    def _drain_ui_queue(self):
        self._ui_queue_active = False
        batch_events = []
        while True:
            try:
                event_type, payload = self.ui_queue.get_nowait()
            except queue.Empty:
                break
            batch_events.append((event_type, payload))

        for event_type, payload in batch_events:
            # self._safe_log("Processing UI event: {} with payload: {}".format(event_type, payload))
            if event_type == "scan_complete":
                self._finalize_scan()
                self._safe_log("Input directory scan complete for: {}".format(self.source_dir.get()))
            elif event_type == "status":
                self.status_var.set(payload)
            elif event_type == "progress":
                self.progressbar.set(payload)
            elif event_type == "file_status":
                source_path, status = payload
                global_idx = self.file_manager.update_file_status(source_path, status)
                self._processed_file_count += 1
                if self._total_files_to_process:
                    self._set_progress_value(self._processed_file_count / self._total_files_to_process)
                    self._set_status_message(self.file_manager.get_statistics_summary())
                    self.table.update_single_index(global_idx)
            elif event_type == "compression_complete":
                self.compress_in_progress = False
                self._set_compression_button_state(False)
                self._set_progress_value(1)
                self._set_status_message(self._build_completion_summary())
                self._safe_log("Compression complete. Updated table and status summary.")
            elif event_type == "compression_stopped":
                self.compress_in_progress = False
                self._set_compression_button_state(False)
                self._set_progress_value(self.progressbar.get())
                self._set_status_message("Kompresja zatrzymana.")
                self._safe_log("Compression stopped by user. Updated table and status summary.")

        if self.scan_in_progress or self.compress_in_progress:
            if not self.ui_queue.empty():
                self._schedule_ui_drain()
            else:
                self.after(50, self._drain_ui_queue)
        else:
            self._refresh_table_with_current_filters()
            self._set_status_message(self.file_manager.get_statistics_summary())

    def on_prev_page(self):
        """Navigates to the previous file table page if available."""
        if self.current_page > 1:
            self.current_page -= 1
            self._refresh_table_with_current_filters()
            self.update_pagination_display()

    def on_next_page(self):
        """Navigates to the next file table page if available."""
        if self.current_page < self.total_pages:
            self.current_page += 1
            self._refresh_table_with_current_filters()
            self.update_pagination_display()

    def update_pagination_display(self):
        """Updates the total page count and state of navigation buttons."""
        # Clamp current page if changes in filters made it out of bounds
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages

        # Update text string
        self.lbl_page_number.configure(text=f"Strona {self.current_page} z {self.total_pages}")

        # Intercept and toggle button states to prevent invalid interactions
        self.btn_prev_page.configure(state="normal" if self.current_page > 1 else "disabled")
        self.btn_next_page.configure(state="normal" if self.current_page < self.total_pages else "disabled")

    def on_closing(self):
        self._shutdown_event.set()
        self._compression_stop_event.set()
        for thread in list(self.threads):
            if thread.is_alive():
                thread.join(timeout=0.2)
        self.save_config()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
