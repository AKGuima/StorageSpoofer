"""
Screen Capture Protector - Main Application Module

This module contains the main application logic for the Screen Capture Protector.
It defines the main window, user interface elements, event handling,
process listing, and the core screen capture protection mechanism, which
utilizes the Windows API function SetWindowDisplayAffinity via ctypes.
The application allows users to select a running process and apply (or remove)
protection to its windows to prevent them from being screen captured.
"""
import sys
import psutil
import os # For OS-specific checks (e.g., 'nt' for Windows)
import ctypes # For calling Windows API functions

# Conditional import and setup for Windows-specific API calls
if os.name == 'nt':
    from ctypes import wintypes # For Windows specific types like HWND, DWORD, etc.

    # Attempt to load user32.dll, which contains functions for window management.
    # use_last_error=True allows to call ctypes.get_last_error() for more details on failure.
    try:
        user32 = ctypes.WinDLL('user32', use_last_error=True)
    except OSError as e:
        # This is a critical failure if on Windows. The application may not function correctly.
        # A more robust application might log this to a file or show a more user-friendly error.
        print(f"FATAL ERROR: Could not load user32.dll. Application functionality will be severely limited. Error: {e}")
        user32 = None # Ensure user32 is None so subsequent checks fail cleanly.

    # --- SetWindowDisplayAffinity Constants ---
    # These constants are used with the SetWindowDisplayAffinity function.
    # WDA_NONE (0x00000000): Default behavior. No display affinity. Window content is capturable.
    WDA_NONE = 0x00000000
    # WDA_MONITOR (0x00000001): Window content is capturable only on a monitor directly connected
    # to the machine. It appears black in captures via indirect display drivers or remote connections.
    WDA_MONITOR = 0x00000001
    # WDA_EXCLUDEFROMCAPTURE (0x00000011): The window content is entirely excluded from capture by
    # most common screen capture APIs (e.g., BitBlt, PrintWindow). This is the primary mechanism
    # used for protection in this application. Requires Windows 10 version 2004 or later.
    WDA_EXCLUDEFROMCAPTURE = 0x00000011

    # --- Windows API Function Prototypes and Type Definitions ---
    # Define EnumWindowsProc: A type definition for the callback function passed to EnumWindows.
    # This callback is invoked for each top-level window.
    # It receives the window handle (HWND) and a user-defined parameter (LPARAM).
    # It must return BOOL (True to continue enumeration, False to stop).
    EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    # Define argument types (argtypes) and return types (restype) for Windows API functions
    # to ensure correct marshalling of data between Python and the C functions in user32.dll.
    if user32: # Proceed only if user32.dll was loaded successfully.
        # HWND EnumWindows(EnumWindowsProc lpEnumFunc, LPARAM lParam)
        user32.EnumWindows.argtypes = [EnumWindowsProc, wintypes.LPARAM]
        user32.EnumWindows.restype = wintypes.BOOL # Returns non-zero if successful.

        # DWORD GetWindowThreadProcessId(HWND hWnd, LPDWORD lpdwProcessId)
        # Returns the identifier of the thread that created the window.
        # The process identifier is returned via the lpdwProcessId pointer.
        user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
        user32.GetWindowThreadProcessId.restype = wintypes.DWORD

        # BOOL IsWindowVisible(HWND hWnd)
        user32.IsWindowVisible.argtypes = [wintypes.HWND]
        user32.IsWindowVisible.restype = wintypes.BOOL

        # int GetWindowTextLengthW(HWND hWnd) - Used to determine buffer size for GetWindowTextW.
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextLengthW.restype = ctypes.c_int

        # int GetWindowTextW(HWND hWnd, LPWSTR lpString, int nMaxCount) - Unicode version.
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowTextW.restype = ctypes.c_int

        # BOOL SetWindowDisplayAffinity(HWND hWnd, DWORD dwAffinity)
        user32.SetWindowDisplayAffinity.argtypes = [wintypes.HWND, wintypes.DWORD]
        user32.SetWindowDisplayAffinity.restype = wintypes.BOOL # Returns True if successful.
else:
    # Define placeholders for non-Windows systems. This allows the application
    # to run without crashing on import, though protection features will be disabled.
    user32 = None
    WDA_NONE = None
    WDA_MONITOR = None
    WDA_EXCLUDEFROMCAPTURE = None
    EnumWindowsProc = None

# --- Qt Imports ---
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget,
                               QPushButton, QSystemTrayIcon, QMenu, QListWidget,
                               QHBoxLayout, QListWidgetItem, QSpacerItem, QSizePolicy)
from PySide6.QtGui import QIcon, QAction, QColor
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve

# --- Project Specific Imports ---
from .process_monitor import ProcessMonitor
from .config_manager import ConfigManager
from .ui_manager import UIManager

# --- Dark Theme Stylesheet ---
# (Assuming DARK_STYLE is defined as before and is sufficiently commented if complex)
DARK_STYLE = """
QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
    border: none;
}
QMainWindow {
    background-color: #2b2b2b;
}
QPushButton {
    background-color: #3c3f41;
    color: #ffffff;
    border: 1px solid #555555;
    padding: 5px 10px;
    min-height: 20px;
    border-radius: 3px;
}
QPushButton:hover {
    background-color: #4f5254;
}
QPushButton:pressed {
    background-color: #5a5e60;
}
QPushButton:disabled {
    background-color: #303030;
    color: #777777;
    border-color: #444444;
}
QLabel {
    color: #cccccc;
}
QListWidget {
    background-color: #3c3f41;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 3px;
}
QListWidget::item {
    padding: 4px;
}
QListWidget::item:selected {
    background-color: #5a5e60;
    color: #ffffff;
}
QMenu {
    background-color: #2b2b2b;
    border: 1px solid #555555;
    color: #ffffff;
}
QMenu::item {
    padding: 5px 20px 5px 20px;
}
QMenu::item:selected {
    background-color: #5a5e60;
}
QSystemTrayIcon::message {
    color: #ffffff;
    background-color: #2b2b2b;
    border: 1px solid #555555;
}
QScrollBar:vertical {
    border: 1px solid #2b2b2b;
    background: #3c3f41;
    width: 12px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #5a5e60;
    min-height: 25px;
    border-radius: 3px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
    background: none;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
"""

class ScreenCaptureProtector(QMainWindow):
    """
    Main application window for Screen Capture Protector.

    Manages the user interface, lists running processes, and applies/removes
    screen capture protection to selected processes using Windows API calls.
    It also handles system tray integration and configuration management.
    """
    def __init__(self):
        """
        Initializes the main window, sets up UI components, timers,
        and loads initial configuration.
        """
        super().__init__()
        self.setWindowTitle("Screen Capture Protector")
        self.setWindowFlags(Qt.WindowStaysOnTopHint) # Keep window on top

        self.config_manager = ConfigManager()
        self.icon_path = "ui/shield.png"

        # Attempt to set window icon, log error if it fails
        if self.icon_path and os.path.exists(self.icon_path): # Check if icon path exists
            try:
                self.setWindowIcon(QIcon(self.icon_path))
            except Exception as e:
                # Use print as logger might not be ready or visible yet
                print(f"Error setting window icon '{self.icon_path}': {e}")
        elif self.icon_path: # Path provided but does not exist
             print(f"Warning: Icon file '{self.icon_path}' not found. No application icon will be set.")

        # State variables
        self.current_protected_pid = None # PID of the process currently under protection
        self.current_protected_process_name = None # Name of the protected process
        self.overlay_windows = [] # For general screen overlay (legacy feature, may be removed)

        # Initialize ProcessMonitor with disallowed list from config (used for tray alerts)
        disallowed_list_for_alerts = self.config_manager.get_disallowed_processes()
        self.process_monitor = ProcessMonitor(disallowed_processes=disallowed_list_for_alerts)

        # UIManager handles the settings dialog
        self.ui_manager = UIManager(self.config_manager, self.process_monitor, main_window_instance=self)

        self.init_ui()
        self._add_log_message("Application interface initialized.", "info")
        self.create_tray_icon()

        # Fade-in animation for the main window
        self.opacity_animation = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_animation.setDuration(600)
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)
        self.opacity_animation.setEasingCurve(QEasingCurve.InOutCubic)

        # Timer for periodic checks (e.g., for disallowed process alerts)
        self.check_processes_timer = QTimer(self)
        self.check_processes_timer.timeout.connect(self.notify_disallowed_processes_if_detected)
        self.check_processes_timer.start(15000) # Check every 15 seconds

        self.apply_initial_settings()
        self._refresh_process_list() # Populate process list on startup

    def showEvent(self, event):
        """
        Override QWidget.showEvent to trigger fade-in animation when window is shown.
        """
        super().showEvent(event)
        if self.opacity_animation.state() != QPropertyAnimation.Running: # Avoid restarting if already running
            self.setWindowOpacity(0.0)
            self.opacity_animation.start()

    def apply_initial_settings(self):
        """
        Applies settings from the configuration when the application starts.
        Example: auto-start of general overlay protection.
        """
        # This refers to the general screen overlay, not the process-specific API protection.
        auto_start_overlay = self.config_manager.get_setting("auto_start_protection", False)
        if auto_start_overlay:
            self._toggle_overlay_protection(True)
        # Note: Minimize on startup is handled in the __main__ block.

    def _refresh_process_list(self):
        """
        Fetches all currently running processes using psutil and populates the
        process list widget in the UI. Handles errors during process iteration.
        """
        self._add_log_message("Refreshing process list...", "info")
        self.process_list_widget.clear() # Clear previous entries
        self.selected_pid = None # Reset selected PID as the list is new
        found_processes_count = 0

        try:
            # Iterate over processes, requesting only 'pid' and 'name' for efficiency.
            # Other attributes like 'exe' or 'username' could be fetched if needed.
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    pid = proc.info['pid']
                    name = proc.info['name']

                    # Skip processes with no name (common for some system processes)
                    # or very low PIDs (often kernel/system internal processes).
                    if not name or pid < 100: # Heuristic to filter out most system/idle processes
                        continue

                    display_text = f"{name} (PID: {pid})"
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, pid) # Store PID for later retrieval
                    self.process_list_widget.addItem(item)
                    found_processes_count +=1
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
                    # These exceptions are expected for some processes (e.g., if they terminate
                    # during iteration or have restricted access). Log as info/debug.
                    self._add_log_message(f"Skipping process PID {getattr(e, 'pid', 'N/A')} (Name: {getattr(e, 'name', 'N/A')}): {e.msg}", "info")
                except Exception as e:
                    # Catch any other unexpected error for a specific process during info retrieval.
                    self._add_log_message(f"Error accessing detailed info for PID {getattr(proc, 'pid', 'N/A')}: {str(e)}", "error")

            if found_processes_count > 0:
                self._add_log_message(f"Process list refreshed. Found {found_processes_count} user-accessible processes.", "success")
            else:
                self._add_log_message("No accessible user processes found or list is empty.", "info")
        except psutil.Error as e:
            # Catch general psutil errors (e.g., related to library initialization or iter errors).
            self._add_log_message(f"Failed to refresh process list due to a psutil error: {str(e)}", "error")
        except Exception as e:
            # Catch any other unexpected error during the process listing operation.
            self._add_log_message(f"An unexpected error occurred while refreshing process list: {str(e)}", "error")

        self._update_button_states() # Ensure buttons reflect current state (e.g., no selection)

    def init_ui(self):
        """
        Initializes the main UI layout and widgets.
        Sets up status label, process list, control buttons, and log view.
        """
        self.selected_pid = None # PID of the process currently selected in the list widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10) # Add some margins
        main_layout.setSpacing(8) # Spacing between widgets

        # Status Label
        self.status_label = QLabel("Status: Not Protected")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #aaa; font-weight: bold; padding: 5px;") # Adjusted color
        main_layout.addWidget(self.status_label)

        # Process List Area
        process_area_layout = QHBoxLayout()
        self.process_list_widget = QListWidget()
        self.process_list_widget.itemSelectionChanged.connect(self._on_process_selection_changed)
        process_area_layout.addWidget(self.process_list_widget)

        self.refresh_button = QPushButton("Refresh List") # Made it an instance member for clarity
        self.refresh_button.clicked.connect(self._refresh_process_list) # Connect to the new method

        process_button_vbox = QVBoxLayout()
        process_button_vbox.addWidget(self.refresh_button)
        process_button_vbox.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        process_area_layout.addLayout(process_button_vbox)
        main_layout.addLayout(process_area_layout)

        # Protection Control Buttons
        button_layout = QHBoxLayout()
        self.activate_button = QPushButton("Protect Selected Process") # More descriptive
        self.activate_button.clicked.connect(self._activate_process_protection)
        self.activate_button.setEnabled(False)
        button_layout.addWidget(self.activate_button)

        self.deactivate_button = QPushButton("Unprotect Process")
        self.deactivate_button.clicked.connect(self._deactivate_process_protection)
        self.deactivate_button.setEnabled(False)
        button_layout.addWidget(self.deactivate_button)
        main_layout.addLayout(button_layout)

        # Log View
        log_label = QLabel("Activity Log:")
        log_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        main_layout.addWidget(log_label)
        self.log_view_widget = QListWidget()
        self.log_view_widget.setFixedHeight(120) # Slightly taller log view
        self.log_view_widget.setWordWrap(True)
        # self.log_view_widget.setStyleSheet("QListWidget::item { color: #cccccc; }") # Ensure log text is light
        main_layout.addWidget(self.log_view_widget)

        self.resize(550, 450) # Adjusted size for new elements

    def _on_process_selection_changed(self):
        """
        Handles the event when a user selects a different process in the list.
        Updates `self.selected_pid` and button states accordingly.
        """
        current_item = self.process_list_widget.currentItem()
        if current_item:
            # Retrieve the PID stored with the list item
            pid_data = current_item.data(Qt.ItemDataRole.UserRole)
            if pid_data is not None: # Ensure data is not None before casting
                try:
                    self.selected_pid = int(pid_data)
                    self._add_log_message(f"Selected process with PID: {self.selected_pid}", "info")
                except ValueError:
                    self.selected_pid = None
                    self._add_log_message(f"Invalid PID data for selected item: {pid_data}", "error")
            else:
                # This case should ideally not happen if items are added correctly with setData.
                self.selected_pid = None
                self._add_log_message("Selected item has no PID data (data is None).", "warning")
        else: # No item is currently selected
            self.selected_pid = None
        self._update_button_states() # Update buttons based on new selection or lack thereof

    def _update_button_states(self):
        """
        Updates the enabled/disabled state of the 'Activate Protection' and
        'Deactivate Protection' buttons based on the current selection (`self.selected_pid`)
        and whether a process is actively being protected (`self.current_protected_pid`).
        """
        can_activate = False
        can_deactivate = False

        if self.selected_pid is not None: # An item is selected in the list
            if self.current_protected_pid == self.selected_pid:
                # The selected process is the one currently protected.
                can_deactivate = True # Allow deactivation of this selected process.
            else:
                # The selected process is not currently protected (or another process is).
                # Allow activation for the selected process.
                can_activate = True
                # If another process is protected, its deactivation must be handled by selecting it first.

        self.activate_button.setEnabled(can_activate)
        self.deactivate_button.setEnabled(can_deactivate)

    def _get_hwnds_for_pid(self, pid_to_find):
        """
        Enumerates all top-level windows and returns a list of visible window
        handles (HWNDs) that belong to the specified process ID (PID).

        Args:
            pid_to_find (int): The process ID to find windows for.

        Returns:
            list[int]: A list of HWNDs (window handles as integers).
                       Returns an empty list if on a non-Windows OS, if user32.dll
                       is not loaded, or if EnumWindows fails.
        """
        if not user32 or not EnumWindowsProc: # Check if Windows API is available/loaded
            if os.name == 'nt': # Only log error if user32 should have been available
                self._add_log_message("Window enumeration (EnumWindows) is not available due to user32.dll loading issue.", "critical")
            else: # Expected on non-Windows
                self._add_log_message("Window enumeration is a Windows-specific feature.", "info")
            return []

        hwnds_found = []
        # Define the callback function that EnumWindows will call for each window.
        # This function must be defined according to the EnumWindowsProc signature.
        def enum_windows_callback(hwnd, lparam):
            # Get the process ID of the current window.
            # We need a pointer to a DWORD to pass to GetWindowThreadProcessId.
            current_window_pid_ptr = wintypes.DWORD()
            # The function returns the thread ID, but the process ID is an output parameter.
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(current_window_pid_ptr))
            current_window_pid = current_window_pid_ptr.value

            # Check if this window's PID matches the target PID.
            if current_window_pid == pid_to_find:
                # Also check if the window is visible to avoid affecting hidden/system windows.
                if user32.IsWindowVisible(hwnd):
                    hwnds_found.append(hwnd) # Add the handle to our list
                    # Optional: Log found window details (can be verbose and slow).
                    # window_title_len = user32.GetWindowTextLengthW(hwnd) + 1
                    # window_title_buffer = ctypes.create_unicode_buffer(window_title_len)
                    # user32.GetWindowTextW(hwnd, window_title_buffer, window_title_len)
                    # self._add_log_message(f"Found visible HWND: {hwnd} Title: '{window_title_buffer.value}' for PID {pid_to_find}", "debug")
            return True # Must return True to continue enumeration for all windows.

        # Create a CFunctionType (callback pointer) from the Python function.
        c_enum_windows_callback = EnumWindowsProc(enum_windows_callback)

        # Call EnumWindows. The second parameter (lparam) can be used to pass data
        # to the callback if needed (e.g., passing `pid_to_find` directly), but here
        # we use a list (`hwnds_found`) defined in the outer scope of the callback.
        if not user32.EnumWindows(c_enum_windows_callback, 0):
            # EnumWindows returns 0 (False) on failure.
            # This usually means the callback itself returned False at some point,
            # but our callback always returns True. So, this might indicate a more
            # fundamental issue with the EnumWindows call.
            error_code = ctypes.get_last_error() if hasattr(ctypes, 'get_last_error') else 'N/A'
            self._add_log_message(f"EnumWindows call failed. Error code: {error_code}", "error")
            return [] # Return empty list on failure

        return hwnds_found

    def _activate_process_protection(self):
        """
        Applies screen capture protection to the currently selected process.
        This uses the SetWindowDisplayAffinity Windows API call to mark windows
        of the selected process as WDA_EXCLUDEFROMCAPTURE, preventing their
        content from being captured by most common screen capture methods.

        Protection Mechanism Explanation:
        - Core API Function: `SetWindowDisplayAffinity(HWND, DWORD)` from `user32.dll`.
        - `WDA_EXCLUDEFROMCAPTURE` (Value: 0x11): This flag, when applied to a window,
          instructs Windows that the content of this specific window should not be
          included in screen captures made using standard Windows APIs (e.g., BitBlt, PrintWindow).
          This is a strong form of protection, available from Windows 10 version 2004 onwards.
        - `WDA_MONITOR` (Value: 0x01): A fallback flag. If `WDA_EXCLUDEFROMCAPTURE` fails
          (e.g., due to permissions or older OS), `WDA_MONITOR` can be used. This flag typically
          causes the window to appear black in captures unless the capture is happening on the
          physical monitor itself (e.g., it may prevent capture via RDP or some virtual display drivers).
        - How it helps against detection: By making window content unavailable for capture,
          many anti-cheat or DRM systems that might perform test captures or check window properties
          related to capturability will find the window "uninteresting," non-capturable, or black.
          This can bypass detection mechanisms that flag easily capturable windows.
        - Pure Python Implementation: This protection is achieved using Python's `ctypes` library
          to call native Windows DLL functions directly. No external compiled libraries or DLL injection
          is required, making it a "pure Python" approach from the perspective of not needing C/C++ compilation.
        - Limitations:
            - Requires appropriate permissions (often administrator rights) to affect windows of other processes,
              especially those running with higher privileges. An "Access Denied" error (code 5) is common otherwise.
            - Effectiveness can vary against highly specialized or kernel-level screen capture techniques
              that might bypass standard Windows APIs.
            - New windows created by the target process *after* protection is applied are not automatically protected.
              The user would need to re-apply protection (e.g., via "Refresh List" and "Protect Selected Process").
        """
        if os.name != 'nt' or not user32: # Check for Windows and successful user32.dll load
            self._add_log_message("Screen capture protection (SetWindowDisplayAffinity) is only available on Windows or user32.dll failed to load.", "error")
            self.status_label.setText("Status: Protection API not available on this OS.")
            self.status_label.setStyleSheet("color: orange; font-weight: bold; padding: 5px;")
            return

        if self.selected_pid is None:
            self._add_log_message("Activation failed: No process selected from the list.", "error")
            return

        # Get process name from the selected list item for better logging and status messages.
        current_list_item = self.process_list_widget.currentItem()
        process_name_for_display = f"PID {self.selected_pid}" # Fallback name if item text is unusual
        if current_list_item:
            try:
                process_name_for_display = current_list_item.text().split(" (PID:")[0]
            except IndexError: # Should not happen with correct format but good to be safe
                self._add_log_message(f"Could not parse name from list item: {current_list_item.text()}", "warning")

        self._add_log_message(f"Attempting to protect {process_name_for_display} (PID: {self.selected_pid})...", "info")

        hwnds = self._get_hwnds_for_pid(self.selected_pid)
        if not hwnds:
            self._add_log_message(f"No visible windows found for {process_name_for_display} (PID: {self.selected_pid}). Cannot apply protection.", "warning")
            self.status_label.setText(f"Status: No visible windows for {process_name_for_display}.")
            self.status_label.setStyleSheet("color: orange; font-weight: bold; padding: 5px;")
            return

        success_count = 0
        error_count = 0
        is_fallback_used_successfully = False # Flag to track if WDA_MONITOR was successfully used as a fallback.

        for hwnd_val in hwnds:
            # Try applying WDA_EXCLUDEFROMCAPTURE first
            if user32.SetWindowDisplayAffinity(hwnd_val, WDA_EXCLUDEFROMCAPTURE):
                self._add_log_message(f"Applied WDA_EXCLUDEFROMCAPTURE to HWND {hwnd_val} for PID {self.selected_pid}.", "success")
                success_count += 1
            else: # WDA_EXCLUDEFROMCAPTURE failed
                error_code = ctypes.get_last_error()
                error_message_detail = f"Failed WDA_EXCLUDEFROMCAPTURE on HWND {hwnd_val} (PID: {self.selected_pid}). Error code: {error_code}"

                if error_code == 5: # ERROR_ACCESS_DENIED (common if not admin)
                    error_message_detail += " (Access Denied)."
                    self._add_log_message(f"{error_message_detail} Attempting fallback to WDA_MONITOR.", "warning")
                    # Fallback to WDA_MONITOR if WDA_EXCLUDEFROMCAPTURE is denied
                    if user32.SetWindowDisplayAffinity(hwnd_val, WDA_MONITOR):
                        self._add_log_message(f"Applied WDA_MONITOR (fallback) to HWND {hwnd_val} for PID {self.selected_pid}.", "success")
                        success_count += 1
                        is_fallback_used_successfully = True # Mark that fallback was successfully used
                    else: # Fallback WDA_MONITOR also failed
                        fallback_error_code = ctypes.get_last_error()
                        self._add_log_message(f"Fallback WDA_MONITOR also failed for HWND {hwnd_val}. Error code: {fallback_error_code}", "error")
                        error_count += 1
                else: # Other errors for WDA_EXCLUDEFROMCAPTURE (e.g., invalid HWND, older OS)
                    self._add_log_message(error_message_detail, "error")
                    error_count += 1

        # Update status based on the outcomes
        if success_count > 0:
            self.current_protected_pid = self.selected_pid
            self.current_protected_process_name = process_name_for_display # Store the name for future reference

            status_message = f"Status: Protected {process_name_for_display} (PID: {self.current_protected_pid})"
            if error_count > 0: # Some windows failed, but at least one succeeded
                status_message += " (Partial - some windows failed or required fallback)"
                self.status_label.setStyleSheet("color: #FFB300; font-weight: bold; padding: 5px;") # Orange for partial/fallback
            elif is_fallback_used_successfully: # All successes were via WDA_MONITOR fallback
                status_message += " (Fallback WDA_MONITOR only)"
                self.status_label.setStyleSheet("color: #FFB300; font-weight: bold; padding: 5px;") # Orange for fallback
            else: # All successes were WDA_EXCLUDEFROMCAPTURE
                self.status_label.setStyleSheet("color: #66BB6A; font-weight: bold; padding: 5px;") # Green
            self.status_label.setText(status_message)
            self._add_log_message(f"Protection applied to {success_count} window(s) for {process_name_for_display} (PID: {self.current_protected_pid}).", "success")
        else: # No windows were successfully protected
            self.status_label.setText(f"Status: Failed to protect {process_name_for_display} (PID: {self.selected_pid}).")
            self.status_label.setStyleSheet("color: #EF5350; font-weight: bold; padding: 5px;") # Red
            self._add_log_message(f"Failed to apply protection to any window for {process_name_for_display} (PID: {self.selected_pid}). Check logs for details.", "error")

        self._update_button_states()

    def _deactivate_process_protection(self):
        """
        Removes screen capture protection from the currently protected process
        by setting display affinity to WDA_NONE for all its windows.
        WDA_NONE reverts the window to its default capturability state.
        """
        if os.name != 'nt' or not user32: # Check for Windows and successful user32.dll load
            self._add_log_message("Screen unprotection (SetWindowDisplayAffinity) is only available on Windows or user32.dll failed to load.", "error")
            return

        if self.current_protected_pid is None: # Check if any process is marked as protected
            self._add_log_message("Deactivation failed: No process was actively protected.", "error")
            return

        # Safety check: Ensure the process to deactivate is the one stored as protected.
        # This can be an issue if UI selection changes before deactivation, though UI logic should prevent this.
        if self.selected_pid != self.current_protected_pid:
            self._add_log_message(f"Deactivation warning: Selected PID ({self.selected_pid}) does not match currently protected PID ({self.current_protected_pid}). Proceeding to unprotect stored PID: {self.current_protected_pid}.", "warning")

        pid_to_unprotect = self.current_protected_pid
        # Use stored name; if somehow not set, fallback to PID string.
        name_to_unprotect = self.current_protected_process_name or f"PID {pid_to_unprotect}"

        self._add_log_message(f"Attempting to unprotect {name_to_unprotect} (PID: {pid_to_unprotect})...", "info")

        hwnds = self._get_hwnds_for_pid(pid_to_unprotect)
        if not hwnds:
            self._add_log_message(f"No visible windows found for {name_to_unprotect} (PID: {pid_to_unprotect}) during deactivation. Process may have closed or windows are hidden.", "info")
            # Still proceed to clear protection state, as the process might have already exited.
        else: # HWNDs found, attempt to remove affinity
            success_count = 0
            error_count = 0
            for hwnd_val in hwnds:
                if user32.SetWindowDisplayAffinity(hwnd_val, WDA_NONE): # Apply WDA_NONE to remove affinity
                    self._add_log_message(f"Removed display affinity from HWND {hwnd_val} for PID {pid_to_unprotect}.", "success")
                    success_count += 1
                else: # Failed to remove affinity
                    error_code = ctypes.get_last_error()
                    # Log error but continue trying other windows. This is important as some windows might have closed.
                    self._add_log_message(f"Failed to remove display affinity from HWND {hwnd_val} (PID: {pid_to_unprotect}). Error code: {error_code}", "error")
                    error_count +=1

            # Log summary of deactivation attempt on windows
            if success_count == len(hwnds):
                self._add_log_message(f"Successfully removed protection from all {len(hwnds)} window(s) for {name_to_unprotect}.", "info")
            elif success_count > 0 : # Partial success
                self._add_log_message(f"Removed protection from {success_count}/{len(hwnds)} window(s) for {name_to_unprotect}. Some may have failed or closed.", "warning")
            elif error_count > 0: # No successes, only errors (and hwnds list was not empty)
                 self._add_log_message(f"Failed to remove protection from any window for {name_to_unprotect}. Windows may have closed or other errors occurred.", "error")
            # If hwnds was empty and success_count is 0, it's covered by the initial "No visible windows" log.

        # Clear protection state regardless of window operation outcomes, as the intent is to unprotect.
        self.current_protected_pid = None
        self.current_protected_process_name = None # Clear stored name

        self.status_label.setText("Status: Not Protected")
        self.status_label.setStyleSheet("color: #aaa; font-weight: bold; padding: 5px;") # Default gray
        self._add_log_message(f"Protection for former process {name_to_unprotect} (PID: {pid_to_unprotect}) has been marked as deactivated.", "info")
        self._update_button_states()

    def _add_log_message(self, message, level='info'):
        item = QListWidgetItem()
        icon_char = ""
        color = QColor("#cccccc") # Default log text

        if level == 'info':
            icon_char = "ℹ️" # Unicode info symbol
            color = QColor("#A9A9A9") # DarkGray for info
        elif level == 'success':
            icon_char = "✔️" # Unicode checkmark
            color = QColor("#66BB6A") # Green
        elif level == 'error':
            icon_char = "❌" # Unicode cross mark
            color = QColor("#EF5350") # Red

        item.setText(f"{icon_char} {message}")
        item.setForeground(color)

        # Animation for new item (simple fade or slide is too complex for QListWidgetItem directly)
        # We'll insert at top and ensure it's visible.
        self.log_view_widget.insertItem(0, item)
        if self.log_view_widget.count() > 100: # Limit log history
            self.log_view_widget.takeItem(self.log_view_widget.count() - 1)
        self.log_view_widget.scrollToItem(item, QListWidget.ScrollHint.EnsureVisible)


    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        if self.icon_path:
            try:
                self.tray_icon.setIcon(QIcon(self.icon_path))
            except Exception as e:
                self._add_log_message(f"Error setting tray icon: {e}", "error")
        else:
            # self.tray_icon.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ApplicationIcon))
            pass

        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_window)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.open_settings_window)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_application)

        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(settings_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def open_settings_window(self):
        self.ui_manager.show_settings_dialog()
        self._add_log_message("Settings window opened.", "info")

    def _toggle_overlay_protection(self, protect): # Renamed to avoid conflict
        """Manages the general screen-wide overlay."""
        if protect:
            self._add_log_message("Screen overlay activated (general).", "info")
            self.show_overlay()
        else:
            self._add_log_message("Screen overlay deactivated (general).", "info")
            self.hide_overlay()

    def show_overlay(self): # Original overlay logic, slightly adapted
        screens = QApplication.screens()
        if not self.overlay_windows:
            for screen_idx, screen in enumerate(screens):
                overlay = QWidget()
                overlay.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
                overlay.setAttribute(Qt.WA_TranslucentBackground)
                overlay.setGeometry(screen.geometry())
                overlay.setStyleSheet("background-color: rgba(0, 0, 0, 100);") # Slightly less opaque
                self.overlay_windows.append(overlay)

        for overlay in self.overlay_windows:
            if not overlay.isVisible():
                overlay.show()

    def hide_overlay(self):
        for overlay in self.overlay_windows:
            overlay.hide()
        # Do not clear them, just hide so they can be reshown quickly.

    def notify_disallowed_processes_if_detected(self):
        """Checks for disallowed processes (from config) and sends a tray notification."""
        # This is a general notification, not tied to the active process protection UI.
        detected_processes = self.process_monitor.find_disallowed_processes()
        if detected_processes:
            self.tray_icon.showMessage(
                "Screen Capture Protector Alert",
                f"Configured disallowed process(es) running: {', '.join(detected_processes)}.",
                QSystemTrayIcon.Warning,
                5000
            )
            self._add_log_message(f"Alert: Configured disallowed process(es) detected: {', '.join(detected_processes)}", "error")

    def show_window(self):
        self.showNormal()
        self.activateWindow() # Bring to front
        if self.opacity_animation.state() != QPropertyAnimation.Running: # Ensure not already running
            self.setWindowOpacity(0.0)
            self.opacity_animation.start()
        self._add_log_message("Main window shown.", "info")

    def quit_application(self):
        self._add_log_message("Quitting application...", "info")
        self.hide_overlay()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "Screen Capture Protector",
            "Application minimized to tray.",
            QSystemTrayIcon.Information,
            2000
        )
        self._add_log_message("Application minimized to tray.", "info")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)

    protector = ScreenCaptureProtector()

    minimize_on_startup = protector.config_manager.get_setting("minimize_to_tray_on_startup", False)
    if minimize_on_startup:
        protector.tray_icon.show()
        protector._add_log_message("Application started minimized to tray.", "info")
    else:
        protector.show()

    sys.exit(app.exec())
