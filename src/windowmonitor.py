from ewmh import EWMH
import threading
from Xlib import display, X

from tpClient import g_log


class WindowMonitor:
    def __init__(self):
        self.currentWindow = None
        self.ewmh = EWMH()
        self.display = display.Display()
        self.root = self.display.screen().root
        self.focus_thread = None
        g_log.info("WindowMonitor initialized")


    def get_active_window_info(self):
        window = self.ewmh.getActiveWindow()
        if window:
            try:
                window_class = window.get_wm_class()
                if window_class:
                    app_name = window_class[1] if len(window_class) > 1 else window_class[0]
                else:
                    app_name = "Unknown"
                
                window_name = self.ewmh.getWmName(window).decode('utf-8') if self.ewmh.getWmName(window) else "Unknown"
                
                pid = self.ewmh.getWmPid(window)
                
                return {
                    "window": window,
                    "app_name": app_name,
                    "window_name": window_name,
                    "pid": pid
                }
            except Exception as e:
                g_log.error(f"Error getting window info: {e}")
                return None
        return None

    def window_focus_thread(self):
        self.root.change_attributes(event_mask=X.PropertyChangeMask)
        last_window_info = None

        while True:
            event = self.display.next_event()
            if event.type == X.PropertyNotify:
                if event.atom == self.display.get_atom("_NET_ACTIVE_WINDOW"):
                    current_window_info = self.get_active_window_info()
                    if current_window_info and current_window_info != last_window_info:
                        self.currentWindow = current_window_info
                        g_log.debug(f"Focus changed to: {self.currentWindow['app_name']} - {self.currentWindow['window_name']}")
                        last_window_info = current_window_info

    def start(self):
        self.focus_thread = threading.Thread(target=self.window_focus_thread, daemon=True)
        self.focus_thread.start()
        
    def stop(self):
        if self.focus_thread:
            self.focus_thread.join()
            self.focus_thread = None

    def get_current_window(self):
        return self.currentWindow


monitor = WindowMonitor()