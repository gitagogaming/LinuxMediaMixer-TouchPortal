from ewmh import EWMH
import threading
from Xlib import display, X

from TPPEntry import PLUGIN_ID
from tpClient import g_log, TPClient
from audiocontroller import AudioController

class WindowMonitor:
    def __init__(self, controller: AudioController):
        self.currentwindow = None
        self.ewmh = EWMH()
        self.display = display.Display()
        self.root = self.display.screen().root
        self.focus_thread = None
        self._stop_event = threading.Event()  # Event for signaling thread to stop

        g_log.info("WindowMonitor initialized")
        
        self.controller = controller
        
    def currentWindow(self):
        return self.currentwindow


    def get_active_window_info(self):
        window = self.ewmh.getActiveWindow()
        if window:
            try:
                if TPClient.isConnected() == False:
                    return
                
                window_class = window.get_wm_class()
                # if window_class:
                #     app_name = window_class[1] if len(window_class) > 1 else window_class[0]
                # else:
                #     app_name = "Unknown"
                    
                app_name = window_class[1] if len(window_class) > 1 else window_class[0] if window_class else "Unknown"

                
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

        while not self._stop_event.is_set():  # Check if the stop event is set
            event = self.display.next_event()
            try:
                if event.type == X.PropertyNotify:
                    if event.atom == self.display.get_atom("_NET_ACTIVE_WINDOW"):
                        current_window_info = self.get_active_window_info()
                        if current_window_info and current_window_info != last_window_info:
                            self.currentwindow = current_window_info
                            last_window_info = current_window_info

                            TPClient.stateUpdate(PLUGIN_ID + ".state.currentFocusedAPP", self.currentwindow['app_name'] )

                            current_app_info = self.controller.apps.get(self.currentwindow['app_name'], None)

                            if current_app_info:
                                current_app_volume = current_app_info.get('volume', 0)
                                TPClient.stateUpdate(PLUGIN_ID + ".state.currentAppVolume", str(round(current_app_volume*100)))

                            g_log.debug(f"Focus changed to: {self.currentwindow['app_name']} - {self.currentwindow['window_name']}")
            except Exception as e:
                g_log.error("Something went terrible wrong, but we should be ok..")



    def start(self):
        self.focus_thread = threading.Thread(target=self.window_focus_thread, daemon=True)
        self.focus_thread.start()
        
    def stop(self):
        if self.focus_thread:
            self._stop_event.set()  # Signal the thread to stop
            self.focus_thread.join(timeout=1)  # Wait up to 1 second for the thread to finish
            if self.focus_thread.is_alive():
                g_log.warning("Thread did not terminate in time, manual intervention may be required")
                # Additional debug logging
                g_log.warning(f"Current state of _stop_event: {self._stop_event.is_set()}")
                g_log.warning(f"Thread status: {'Running' if self.focus_thread and self.focus_thread.is_alive() else 'Stopped'}")

            self.focus_thread = None
            g_log.info("Window Monitor stopped")


    def get_current_window(self):
        return self.currentWindow()


