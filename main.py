import signal
import tkinter as tk
from tkinter import StringVar, IntVar
import customtkinter
import threading
from file_manager import FileManager
from config_manager import ConfigManager
from file_table import FileProcessingTable

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("green")


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


class App(customtkinter.CTk):
    WIDTH = 900
    HEIGHT = 700

    def __init__(self):
        super().__init__()
        self.threads = []

        self.file_manager = FileManager()
        self.load_file_config = {}

        # 1. Initialize config manager and load stored settings
        self.config_manager = ConfigManager()
        stored_settings = self.config_manager.load_settings()

        self.title("Image compressor")
        self.geometry(f"{App.WIDTH}x{App.HEIGHT}")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        signal.signal(signal.SIGINT, lambda sig, frame: self.on_closing())

        # Try loading icon safely
        try:
            self.iconbitmap("press.ico")
        except Exception:
            pass

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
        self.combo_strat.pack(side="left", padx=(0, 20))

        # --- Quality Settings inside the same horizontal pack layout ---
        self.label_quality = customtkinter.CTkLabel(
            self.strat_quality_container, text="Jakość [1-100]:", font=("Roboto", 14)
        )
        self.label_quality.pack(side="left", padx=(0, 5))

        # Hooked: Init from config + strict range trace that automatically invokes save_config
        self.quality = IntVar(value=int(stored_settings["quality"]))
        self.quality.trace_add("write", lambda *args: self.validate_quality())

        self.slider_quality = customtkinter.CTkSlider(
            self.strat_quality_container, from_=1, to=100, variable=self.quality, width=150
        )
        self.slider_quality.pack(side="left", padx=5)

        self.entry_quality = customtkinter.CTkEntry(self.strat_quality_container, width=50, textvariable=self.quality)
        self.entry_quality.pack(side="left", padx=(5, 0))

        # === 5. OUTPUT RESOLUTION (Shifted to Row 3) ===

        self.label_res = customtkinter.CTkLabel(self.frame_top, text="Rozdzielczość maksymalna:", font=("Roboto", 14))
        self.label_res.grid(row=3, column=0, pady=8, padx=15, sticky="w")

        # Container frame to align dropdown, custom inputs and checkbox horizontally
        self.res_container = customtkinter.CTkFrame(self.frame_top, fg_color="transparent")
        self.res_container.grid(row=3, column=1, columnspan=2, pady=8, padx=10, sticky="w")

        # Hooked: Init from config + redirection command
        self.res_option_var = StringVar(value=stored_settings.get("resolution_preset", "4K:3840x2560"))
        self.combo_res = customtkinter.CTkComboBox(
            self.res_container,
            values=["4K:3840x2560", "2K:2160x1440", "1080x720", "Własna (Szer x Wys)"],
            variable=self.res_option_var,
            command=self.on_resolution_changed,
            width=180,
        )
        self.combo_res.pack(side="left")

        # Custom Resolution Input frame (inside the horizontal container)
        self.custom_res_frame = customtkinter.CTkFrame(self.res_container, fg_color="transparent")
        self.custom_res_frame.pack(side="left", padx=15)

        # Hooked: Width text field + auto-save trace
        self.custom_w_var = StringVar(value=stored_settings.get("custom_w", "1920"))
        self.custom_w_var.trace_add("write", lambda *args: self.save_config())
        self.custom_w = customtkinter.CTkEntry(
            self.custom_res_frame, width=60, placeholder_text="W", textvariable=self.custom_w_var
        )
        self.custom_w.pack(side="left", padx=2)

        self.label_x = customtkinter.CTkLabel(self.custom_res_frame, text="x")
        self.label_x.pack(side="left", padx=2)

        # Hooked: Height text field + auto-save trace
        self.custom_h_var = StringVar(value=stored_settings.get("custom_h", "1080"))
        self.custom_h_var.trace_add("write", lambda *args: self.save_config())
        self.custom_h = customtkinter.CTkEntry(
            self.custom_res_frame, width=60, placeholder_text="H", textvariable=self.custom_h_var
        )
        self.custom_h.pack(side="left", padx=2)

        # Hooked: Run visibility update on startup based on loaded preferences
        self.toggle_custom_res(self.res_option_var.get())

        # ================= Options Checkboxes Container =================
        self.frame_checkboxes = customtkinter.CTkFrame(self.frame_top, fg_color="transparent")
        self.frame_checkboxes.grid(row=5, column=1, columnspan=2, pady=(4, 8), padx=10, sticky="w")

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
        self.cb_copy_uncompressible.pack(side="left", padx=(0, 25))
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
        self.cb_overwrite_files.pack(side="left", padx=0)
        CTkTooltip(self.cb_overwrite_files, "Zaznacz by nadpisać już skompresowane pliki w folderze wyjściowym")

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
            command=self.compress_images_btn,
        )
        self.btn_start_comp.grid(row=0, column=1, pady=5, padx=(10, 0), sticky="ew")

        # ================= FILE SELECTION FILTER ROW (Row 2) =================
        # Placed after control frame, directly before the file frame
        self.frame_filter = customtkinter.CTkFrame(master=self, corner_radius=8)
        self.frame_filter.grid(row=2, column=0, sticky="ew", padx=15, pady=(5, 10))

        # Enforce exact label column alignment to match top settings margins
        self.frame_filter.grid_columnconfigure(0, weight=0, minsize=180)
        self.frame_filter.grid_columnconfigure(1, weight=1)

        self.label_filter = customtkinter.CTkLabel(self.frame_filter, text="Wyświetl pliki:", font=("Roboto", 14))
        self.label_filter.grid(row=0, column=0, pady=10, padx=15, sticky="w")

        # Container framework to map checkboxes inline horizontally
        self.filter_container = customtkinter.CTkFrame(self.frame_filter, fg_color="transparent")
        self.filter_container.grid(row=0, column=1, pady=10, padx=10, sticky="w")

        # State tracking configurations for functional table view hooks
        initial_show_convertible = stored_settings.get("show_convertible", "False") == "True"
        initial_show_non_convertible = stored_settings.get("show_non_convertible", "False") == "True"
        initial_show_converted = stored_settings.get("show_converted", "False") == "True"
        self.show_convertible = customtkinter.BooleanVar(value=initial_show_convertible)
        self.show_non_convertible = customtkinter.BooleanVar(value=initial_show_non_convertible)
        self.show_converted = customtkinter.BooleanVar(value=initial_show_converted)

        self.chk_convertible = customtkinter.CTkCheckBox(
            self.filter_container, text="konwertowalne", variable=self.show_convertible, command=self.on_filter_changed
        )
        self.chk_convertible.pack(side="left", padx=(0, 15))

        self.chk_non_convertible = customtkinter.CTkCheckBox(
            self.filter_container,
            text="niekonwertowalne",
            variable=self.show_non_convertible,
            command=self.on_filter_changed,
        )
        self.chk_non_convertible.pack(side="left", padx=15)

        self.chk_converted = customtkinter.CTkCheckBox(
            self.filter_container, text="skonwertowane", variable=self.show_converted, command=self.on_filter_changed
        )
        self.chk_converted.pack(side="left", padx=15)

        # ================= MIDDLE FRAME: File Table =================
        # Row layout configuration update: row 3 is now the table
        self.grid_rowconfigure(3, weight=1)

        self.frame_middle = customtkinter.CTkFrame(master=self, corner_radius=8)
        self.frame_middle.grid(row=3, column=0, sticky="nsew", padx=15, pady=0)
        self.frame_middle.grid_rowconfigure(0, weight=1)
        self.frame_middle.grid_columnconfigure(0, weight=1)

        # Inicjalizacja nowej tabeli wewnątrz środkowej ramki
        self.table = FileProcessingTable(master=self.frame_middle)
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

        # Status Label acting as Status Bar
        self.status_var = StringVar(value="Gotowy")
        self.status_bar = customtkinter.CTkLabel(
            self.frame_bottom, textvariable=self.status_var, font=("Roboto", 11), text_color="gray"
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

    def validate_quality(self):
        try:
            val = self.quality.get()
            if val < 1:
                self.quality.set(1)
            elif val > 100:
                self.quality.set(100)
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
        # Read current checkbox states (True/False)
        show_conv = self.show_convertible.get()
        show_non_conv = self.show_non_convertible.get()
        show_converted = self.show_converted.get()

        filtered_ui_data = self.file_manager.get_ui_table_data(
            show_conv=show_conv, show_non_conv=show_non_conv, show_done=show_converted
        )

        self.table.populate_data(filtered_ui_data)

        self.status_var.set(self.file_manager.get_statistics_summary())

    def save_config(self):
        try:
            current_settings = {
                "source_dir": self.source_dir.get(),
                "output_dir": self.output_dir.get(),
                "strategy": self.strategy_var.get(),
                "quality": str(self.quality.get()),
                "resolution_preset": self.res_option_var.get(),
                "custom_w": self.custom_w_var.get(),
                "custom_h": self.custom_h_var.get(),
                "copy_uncompressible": str(self.copy_uncompressible_var.get()),
                "overwrite_files": str(self.overwrite_files_var.get()),
                "show_convertible": str(self.show_convertible.get()),
                "show_non_convertible": str(self.show_non_convertible.get()),
                "show_converted": str(self.show_converted.get()),
            }
            self.config_manager.save_settings(current_settings)
        except (tk.TclError, AttributeError):
            pass

    def load_files_btn(self):
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

        self.status_var.set("Skanowanie katalogu...")

        # Run filesystem scanning on a background thread so UI stays fluid
        def async_scan():
            self.file_manager.scan_directory(src, strat, dest)

            # Update UI components safely back on the main loop thread
            self.after(
                0,
                lambda: self.table.populate_data(
                    self.file_manager.get_ui_table_data(
                        show_conv=self.show_convertible.get(),
                        show_non_conv=self.show_non_convertible.get(),
                        show_done=self.show_converted.get(),
                    )
                ),
            )

            self.after(0, lambda: self.status_var.set(self.status_var.set(self.file_manager.get_statistics_summary())))

        threading.Thread(target=async_scan, daemon=True).start()

    def compress_images_btn(self):
        if (
            self.load_file_config.get("source_dir") != self.source_dir.get()
            or self.load_file_config.get("output_dir") != self.output_dir.get()
            or self.load_file_config.get("strategy") != self.strategy_var.get()
        ):
            self.load_files_btn()  # Refresh file list if directories or strategy changed

        self.status_var.set("Trwa kompresowanie...")

    def on_closing(self):
        self.save_config()  # Final save execution guard
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
