import json
import os

class ConfigManager:
    def __init__(self, config_name="config.json"):
        # Determine path for config file in user's home directory or app data folder
        self.config_dir = self._get_config_directory()
        self.config_path = os.path.join(self.config_dir, config_name)
        self.default_config = {
            "disallowed_processes": [
                "obs64.exe", "obs32.exe", "SnippingTool.exe", "XboxGameBar.exe",
                "wfica32.exe", "Zoom.exe", "Teams.exe", "greenshot.exe",
                "ShareX.exe", "Lightshot.exe"
                # Platform-specific defaults could be added here too
            ],
            "settings": {
                "auto_start_protection": False,
                "minimize_to_tray_on_startup": False,
                # Add other settings as needed
            }
        }
        self.config = self.load_config()

    def _get_config_directory(self):
        """Returns the appropriate directory for storing config files."""
        if os.name == 'nt': # Windows
            app_data_path = os.getenv('APPDATA')
            if app_data_path:
                return os.path.join(app_data_path, "ScreenCaptureProtector")
        else: # macOS, Linux
            home_dir = os.path.expanduser('~')
            if home_dir:
                return os.path.join(home_dir, ".config", "ScreenCaptureProtector")

        # Fallback if appropriate directory can't be found (e.g., store in script's directory)
        # This is less ideal for installed applications.
        return os.path.dirname(os.path.abspath(__file__))


    def load_config(self):
        """Loads configuration from file, or returns default if file doesn't exist or is invalid."""
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir) # Create config directory if it doesn't exist
            except OSError as e:
                print(f"Error creating config directory {self.config_dir}: {e}")
                # Fallback to using default config if directory creation fails
                return self.default_config

        if not os.path.exists(self.config_path):
            self.save_config(self.default_config) # Create default config if none exists
            return self.default_config

        try:
            with open(self.config_path, 'r') as f:
                config_data = json.load(f)
                # Basic validation: check if top-level keys exist
                if "disallowed_processes" not in config_data or "settings" not in config_data:
                    print("Config file is missing essential keys. Using default config.")
                    self._backup_invalid_config() # Backup invalid config
                    self.save_config(self.default_config) # Save a fresh default config
                    return self.default_config
                return config_data
        except json.JSONDecodeError:
            print("Error decoding config.json. Using default configuration.")
            self._backup_invalid_config()
            self.save_config(self.default_config)
            return self.default_config
        except Exception as e: # Catch any other exceptions during loading
            print(f"An unexpected error occurred loading config: {e}. Using default config.")
            self._backup_invalid_config()
            self.save_config(self.default_config)
            return self.default_config

    def _backup_invalid_config(self):
        """Backs up an invalid config file."""
        if os.path.exists(self.config_path):
            try:
                backup_path = self.config_path + ".bak"
                # If backup already exists, remove it or create a numbered backup
                if os.path.exists(backup_path):
                    os.remove(backup_path) # Simplest approach: overwrite old backup
                os.rename(self.config_path, backup_path)
                print(f"Backed up invalid config to {backup_path}")
            except OSError as e:
                print(f"Error backing up invalid config: {e}")


    def save_config(self, config_data=None):
        """Saves the current configuration to file."""
        data_to_save = config_data if config_data is not None else self.config
        try:
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir) # Ensure directory exists before writing
            with open(self.config_path, 'w') as f:
                json.dump(data_to_save, f, indent=4)
            self.config = data_to_save # Update internal config state
        except OSError as e:
            print(f"Error creating config directory or writing to config file {self.config_path}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred saving config: {e}")


    def get_setting(self, key, default=None):
        """Retrieves a specific setting by key."""
        return self.config.get("settings", {}).get(key, default)

    def update_setting(self, key, value):
        """Updates a specific setting."""
        if "settings" not in self.config:
            self.config["settings"] = {}
        self.config["settings"][key] = value
        self.save_config()

    def get_disallowed_processes(self):
        """Retrieves the list of disallowed processes."""
        return self.config.get("disallowed_processes", [])

    def update_disallowed_processes(self, new_list):
        """Updates the list of disallowed processes."""
        self.config["disallowed_processes"] = new_list
        self.save_config()

# Example Usage (for testing module directly)
if __name__ == "__main__":
    # Create a ConfigManager instance (will create config file in user's dir if not exists)
    config_manager = ConfigManager()

    # Load and print current config
    print("Current config loaded:")
    print(json.dumps(config_manager.config, indent=4))

    # Example: Get a specific setting
    auto_start = config_manager.get_setting("auto_start_protection")
    print(f"\nAuto-start protection: {auto_start}")

    # Example: Update a setting
    print("\nUpdating 'auto_start_protection' to True...")
    config_manager.update_setting("auto_start_protection", True)
    auto_start = config_manager.get_setting("auto_start_protection")
    print(f"New auto-start protection value: {auto_start}")

    # Example: Get disallowed processes
    processes = config_manager.get_disallowed_processes()
    print(f"\nDisallowed processes: {processes}")

    # Example: Update disallowed processes
    # new_processes = processes + ["another_app.exe"]
    # print(f"\nUpdating disallowed processes to: {new_processes}")
    # config_manager.update_disallowed_processes(new_processes)
    # print(f"New disallowed processes: {config_manager.get_disallowed_processes()}")

    # To see the file, check your user's config directory:
    # Windows: %APPDATA%\ScreenCaptureProtector\config.json
    # Linux/macOS: ~/.config/ScreenCaptureProtector/config.json
    # Or the script's directory if the preferred paths are not writable/creatable.
    print(f"\nConfig file is at: {config_manager.config_path}")
