from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QListWidget, QLineEdit, QHBoxLayout, QCheckBox, QDialogButtonBox, QMessageBox
from PySide6.QtCore import Qt

class SettingsWindow(QDialog):
    def __init__(self, config_manager, process_monitor, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.process_monitor = process_monitor # To update its list if changed

        self.setWindowTitle("Settings - Screen Capture Protector")
        self.setMinimumWidth(400) # Set a minimum width for better layout

        layout = QVBoxLayout(self)

        # Section: Disallowed Processes
        layout.addWidget(QLabel("Disallowed Processes:"))
        self.process_list_widget = QListWidget()
        self._populate_process_list()
        layout.addWidget(self.process_list_widget)

        # Add/Remove buttons for processes
        process_button_layout = QHBoxLayout()
        self.new_process_entry = QLineEdit()
        self.new_process_entry.setPlaceholderText("Enter process name (e.g., snippingtool.exe)")
        process_button_layout.addWidget(self.new_process_entry)

        add_button = QPushButton("Add")
        add_button.clicked.connect(self.add_process)
        process_button_layout.addWidget(add_button)

        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self.remove_process)
        process_button_layout.addWidget(remove_button)
        layout.addLayout(process_button_layout)

        # Section: Application Settings
        layout.addWidget(QLabel("\nApplication Settings:"))

        self.auto_start_checkbox = QCheckBox("Auto-start protection when application launches")
        self.auto_start_checkbox.setChecked(self.config_manager.get_setting("auto_start_protection", False))
        layout.addWidget(self.auto_start_checkbox)

        self.minimize_on_startup_checkbox = QCheckBox("Minimize to tray on application startup")
        self.minimize_on_startup_checkbox.setChecked(self.config_manager.get_setting("minimize_to_tray_on_startup", False))
        layout.addWidget(self.minimize_on_startup_checkbox)

        # Add more settings checkboxes or inputs as needed

        # Save/Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.save_settings)
        button_box.rejected.connect(self.reject) # Closes the dialog
        layout.addWidget(button_box)

        self.setLayout(layout)

    def _populate_process_list(self):
        self.process_list_widget.clear()
        processes = self.config_manager.get_disallowed_processes()
        for proc_name in processes:
            self.process_list_widget.addItem(proc_name)

    def add_process(self):
        new_process = self.new_process_entry.text().strip()
        if not new_process:
            QMessageBox.warning(self, "Empty Process Name", "Process name cannot be empty.")
            return

        current_processes = [self.process_list_widget.item(i).text() for i in range(self.process_list_widget.count())]
        if new_process.lower() in [p.lower() for p in current_processes]:
            QMessageBox.information(self, "Duplicate Process", f"'{new_process}' is already in the list.")
            return

        self.process_list_widget.addItem(new_process)
        self.new_process_entry.clear()

    def remove_process(self):
        selected_items = self.process_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a process to remove.")
            return
        for item in selected_items:
            self.process_list_widget.takeItem(self.process_list_widget.row(item))

    def save_settings(self):
        # Save disallowed processes
        updated_processes = [self.process_list_widget.item(i).text() for i in range(self.process_list_widget.count())]
        self.config_manager.update_disallowed_processes(updated_processes)
        if self.process_monitor: # Update the live process monitor instance
            self.process_monitor.update_disallowed_list(updated_processes)

        # Save application settings
        self.config_manager.update_setting("auto_start_protection", self.auto_start_checkbox.isChecked())
        self.config_manager.update_setting("minimize_to_tray_on_startup", self.minimize_on_startup_checkbox.isChecked())

        QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
        self.accept() # Closes the dialog

class UIManager:
    def __init__(self, config_manager, process_monitor, main_window_instance=None):
        self.config_manager = config_manager
        self.process_monitor = process_monitor
        self.main_window = main_window_instance # Reference to the main window if needed for context
        self.settings_window_instance = None # To ensure only one settings window is open

    def show_settings_dialog(self):
        if self.settings_window_instance is None or not self.settings_window_instance.isVisible():
            self.settings_window_instance = SettingsWindow(self.config_manager, self.process_monitor, parent=self.main_window)
            self.settings_window_instance.show()
        else:
            self.settings_window_instance.activateWindow() # Bring to front if already open

# Example usage (for testing this module directly)
if __name__ == '__main__':
    from PySide6.QtWidgets import QApplication
    import sys
    # Dummy ConfigManager and ProcessMonitor for testing
    class DummyConfigManager:
        def get_disallowed_processes(self): return ["test.exe", "example.exe"]
        def update_disallowed_processes(self, l): print(f"Config: Disallowed processes updated to: {l}")
        def get_setting(self, key, default): return False # Dummy implementation
        def update_setting(self, key, value): print(f"Config: Setting '{key}' updated to: {value}")

    class DummyProcessMonitor:
        def update_disallowed_list(self, l): print(f"Monitor: Disallowed list updated to: {l}")

    app = QApplication(sys.argv)

    config_mgr = DummyConfigManager()
    proc_monitor = DummyProcessMonitor()

    ui_mgr = UIManager(config_mgr, proc_monitor)
    ui_mgr.show_settings_dialog() # Show the settings window

    sys.exit(app.exec())
