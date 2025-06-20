# Screen Capture Protector - Tutorial

## 1. Introduction

Welcome to Screen Capture Protector! This application helps prevent other programs on your Windows computer from detecting that you are taking a screen capture of their windows. It does this without injecting any code (DLLs) into the target application, relying instead on a standard Windows feature to make the target window's content uncapturable by most common methods.

This can be useful in scenarios where an application might restrict its functionality or alert a remote server if it detects a screen capture attempt.

## 2. System Requirements

- **Operating System:** Windows (specifically tested on Windows 10 and later). The core protection feature relies on Windows-specific APIs.
- **Python:** Python 3.7+
- **Dependencies:** `PySide6` (for the graphical interface) and `psutil` (for listing processes).

## 3. Setup

1.  **Download/Clone the Repository:**
    Obtain the application files. If you have Git, you can clone it:
    ```bash
    git clone <repository_url> # Replace <repository_url> with the actual URL
    cd screen_capture_protector
    ```
    Otherwise, download the source code as a ZIP and extract it.

2.  **Install Dependencies:**
    Open a command prompt or PowerShell, navigate to the `screen_capture_protector` directory (where `requirements.txt` is located), and run:
    ```bash
    pip install -r requirements.txt
    ```

## 4. Running the Application

1.  **Navigate to the Source Directory:**
    Ensure your command prompt/PowerShell is in the `screen_capture_protector` directory.

2.  **Run the Main Script:**
    Execute the following command:
    ```bash
    python -m src.main
    ```
    This runs the application as a module, which is important for correct relative imports within the `src` package.

3.  **IMPORTANT: Run as Administrator!**
    For the screen protection to work effectively on windows belonging to *other* applications, **you MUST run this script with Administrator privileges.**
    -   To do this, open your command prompt or PowerShell as an Administrator before running the Python script.
    -   *Why?* The Windows API (`SetWindowDisplayAffinity`) used for protection requires administrative rights to modify display properties of windows owned by other processes. Without admin rights, protection will likely fail (often with an "Access Denied" error in the logs) or only work on windows created by the script itself.

## 5. Using the Interface

The main window of Screen Capture Protector is designed to be simple and informative.

**(Imagine a screenshot of the UI here if this were rich markdown - for now, textual description)**

-   **Process List:**
    -   This list shows currently running applications with their names and Process IDs (PIDs).
    -   Click on an application in this list to select it as the target for protection.
-   **Refresh List Button:**
    -   Click this button to update the Process List with the latest set of running applications.
-   **Protect Selected Process Button:**
    -   Once you've selected a process, click this button to apply screen capture protection to its main window(s).
    -   The Status Label will update, and details will appear in the Log View. This button is enabled only when a process is selected and not already protected.
-   **Unprotect Process Button:**
    -   If a process is currently protected and selected in the list, this button becomes active. Click it to remove the protection.
-   **Status Label:**
    -   Displays the current protection status:
        -   `Status: Not Protected` (Gray): No process is currently being protected.
        -   `Status: Actively Protecting [AppName] (PID: XXXX)` (Green): Protection is active for the specified application.
        -   `Status: Failed to protect...` or `Status: Protection API not available...` (Red/Orange): An issue occurred. Check the Log View for details.
-   **Log View:**
    -   Provides real-time messages about application activity:
        -   `ℹ️ Selected process...`: When you select a process.
        -   `ℹ️ Attempting to protect...`: When you activate protection.
        -   `✔️ Protection successfully applied...`: Confirmation of success.
        -   `ℹ️ Protection deactivated...`: Confirmation of deactivation.
        -   `❌ Error...` or `⚠️ Warning...`: Indicates a problem (e.g., access denied, process not found). Read the message for details.

## 6. How It Works (Briefly)

This application uses a Windows API function called `SetWindowDisplayAffinity`. Instead of traditional, complex "API hooking," this function tells Windows how a specific window's content should be treated concerning display and capture.

-   When you "Protect" a window, the application sets its display affinity to `WDA_EXCLUDEFROMCAPTURE` (or `WDA_MONITOR` as a fallback). This flag instructs Windows to prevent the window's contents from being included in most standard screen captures (e.g., PrintScreen, Snipping Tool, many third-party tools using common Windows APIs).
-   Because capture tools cannot "see" the window's content (it often appears as a black or empty area in the capture), any detection mechanisms within the target application that rely on performing a test capture will likely be fooled into thinking no capture is happening or that the window is not visible/capturable.
-   This is a "pure Python" approach because it uses the built-in `ctypes` library to call this standard Windows function, requiring no external compiled files or DLL injection.

## 7. Troubleshooting

-   **Protection Not Working / "Access Denied" in Logs:**
    -   The most common reason is that the application was not run with **Administrator privileges**. Close the app and re-run it from an Admin command prompt/PowerShell.
-   **Target Application Not Listed:**
    -   Click the "Refresh List" button.
    -   Ensure the target application is running and has a visible window. Some background processes or processes without standard windows may not be listable or have protectable windows. Processes with very low PIDs (e.g., system processes) are also typically filtered out.
-   **Errors in Log View:**
    -   Read the error message carefully. It often provides clues (e.g., "Process with PID XXXX not found," "Failed to get window handle," specific Windows error codes).
-   **Application Crashes (Unlikely but possible):**
    -   Note any error messages in the console and consider reporting them as an issue with details about your OS version and what you were doing.

## 8. Limitations

-   **Administrator Rights:** Essential for broad effectiveness against other processes.
-   **Existing Windows Only:** Protection is applied to windows that exist when you click "Protect Selected Process." If the target application creates new windows *after* protection is activated, those new windows will not automatically be protected. You may need to re-apply protection (select the process and click "Protect" again).
-   **Not Foolproof:** While effective against many common detection methods based on standard capture APIs, highly sophisticated or custom-built detection mechanisms might still identify capture attempts through other means (e.g., analyzing mouse cursor behavior, specific driver interactions, kernel-level monitoring, etc.). This tool is not a guaranteed bypass for all scenarios, especially robust anti-cheat or DRM systems.
-   **Windows Specific:** The core protection mechanism (`SetWindowDisplayAffinity`) is exclusive to the Windows operating system. The application will run on other OSes, but the protection features will be disabled.
-   **Fallback Behavior:** If `WDA_EXCLUDEFROMCAPTURE` fails (e.g., due to insufficient permissions for that specific flag, or on an OS version that doesn't fully support it despite being Win10 2004+), the application attempts to use `WDA_MONITOR`. This is a less comprehensive protection (window appears black in captures from indirect displays) but still offers some utility.

## 9. System Tray and Settings

-   **System Tray:** When you close the main window (using the 'X' button), the application minimizes to the system tray (notification area) and continues running.
    -   **Right-click** the Screen Capture Protector icon in the system tray to:
        -   **Show:** Restore the main window.
        -   **Settings:** Open the settings window (see below).
        -   **Quit:** Exit the application.
-   **Settings Window:**
    -   **Disallowed Processes List:** You can view and manage a list of process names (e.g., `obs64.exe`, `snippingtool.exe`). If the application detects any of these processes running (based on a periodic check), it can display a tray notification. This is separate from the active protection feature.
    -   **Application Settings:**
        -   `Auto-start protection when application launches`: This refers to the general screen overlay feature (a legacy option that makes the whole screen semi-transparent). It's not the main `SetWindowDisplayAffinity` protection.
        -   `Minimize to tray on application startup`: If checked, the main window won't show on startup, and the app will run directly in the system tray.

---
Thank you for using Screen Capture Protector!
"""
