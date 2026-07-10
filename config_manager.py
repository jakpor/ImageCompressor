import os
import configparser


class ConfigManager:
    def __init__(self, filename="config.ini"):
        self.filename = os.path.abspath(filename)
        self.config = configparser.ConfigParser()

    def load_settings(self) -> dict:
        """Reads config file and returns a dictionary of settings with safe defaults."""
        defaults = {
            "source_dir": "",
            "output_dir": "",
            "strategy": "nie skanuj podfolderów",
            "quality": "90",
            "resolution_preset": "4K:3840x2560",
            "custom_w": "3840",
            "custom_h": "2560",
            "copy_uncompressible": "True",
            "overwrite_files": "False",
            "show_convertible": "True",
            "show_non_convertible": "True",
            "show_converted": "True",
            "show_errors": "True",
            "remove_metadata": "False",
            "worker_count": "4",
            "page_size": "50",
        }

        if not os.path.exists(self.filename):
            return defaults

        try:
            self.config.read(self.filename, encoding="utf-8")
            if "Settings" in self.config:
                for key in defaults.keys():
                    if key in self.config["Settings"]:
                        defaults[key] = self.config["Settings"][key]
        except Exception as e:
            print(f"Error loading config: {e}")

        return defaults

    def save_settings(self, settings_dict: dict) -> None:
        """Saves the provided settings dictionary to the config file."""
        self.config["Settings"] = {str(k): str(v) for k, v in settings_dict.items()}
        try:
            with open(self.filename, "w", encoding="utf-8") as configfile:
                self.config.write(configfile)
        except Exception as e:
            print(f"Error saving config: {e}")
