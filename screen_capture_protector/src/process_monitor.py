import psutil

class ProcessMonitor:
    def __init__(self, disallowed_processes=None):
        if disallowed_processes is None:
            # Default list of common screen capture / recording software
            self.disallowed_processes = [
                "obs64.exe", "obs32.exe", "SnippingTool.exe", "XboxGameBar.exe",
                "wfica32.exe", # Citrix Receiver
                "Zoom.exe", "Teams.exe", # Meeting software with recording
                "greenshot.exe", "ShareX.exe", "Lightshot.exe", # Other screenshot tools
                # Add more based on operating system or known software
                # For macOS: "QuickTime Player.app", "screencapture"
                # For Linux: "gnome-screenshot", "ksnip", "flameshot"
            ]
        else:
            self.disallowed_processes = disallowed_processes

    def find_disallowed_processes(self):
        """
        Checks for running processes that are in the disallowed list.
        Returns a list of names of found disallowed processes.
        """
        found_processes = []
        for proc in psutil.process_iter(['name', 'exe']): # Request name and executable path
            try:
                proc_name = proc.info['name']
                # proc_exe = proc.info['exe'] # Executable path, can be useful for more specific checks

                # Normalize process name for comparison (e.g., lowercase)
                if proc_name.lower() in [dp.lower() for dp in self.disallowed_processes]:
                    found_processes.append(proc_name)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                # Handle cases where process info isn't accessible or process has terminated
                pass
        return list(set(found_processes)) # Return unique names

    def update_disallowed_list(self, new_list):
        """Updates the list of disallowed processes."""
        self.disallowed_processes = new_list

# Example usage (optional, for testing this module directly)
if __name__ == "__main__":
    monitor = ProcessMonitor()
    print("Monitoring for disallowed processes...")

    # To test, you might need to run some of the disallowed processes
    # For example, open SnippingTool.exe on Windows if it's in the list

    detected = monitor.find_disallowed_processes()
    if detected:
        print(f"Detected disallowed processes: {', '.join(detected)}")
    else:
        print("No disallowed processes detected at this time.")

    # Example of updating the list
    # monitor.update_disallowed_list(["notepad.exe"]) # Now monitors for notepad
    # print("\nUpdated list to monitor for 'notepad.exe'.")
    # detected = monitor.find_disallowed_processes()
    # if detected:
    #     print(f"Detected: {', '.join(detected)}")
    # else:
    #     print("Notepad not detected.")
