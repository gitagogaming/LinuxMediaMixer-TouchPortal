
import sys
import logging
import traceback

import TouchPortalAPI as TP, logging
from TPPEntry import  PLUGIN_ID, __version__



try:
    TPClient = TP.Client(
        pluginId = PLUGIN_ID,             # required ID of this plugin
        sleepPeriod = 0.05,               # allow more time than default for other processes
        autoClose = True,                 # automatically disconnect when TP sends "closePlugin" message
        checkPluginId = True,             # validate destination of messages sent to this plugin
        maxWorkers = 4,                   # run up to 4 event handler threads
        updateStatesOnBroadcast = False,  # do not spam TP with state updates on every page change
    )
except Exception as e:
    sys.exit(f"Could not create TP Client, exiting. Error was:\n{repr(e)}")



import logging
import traceback

class gLog:
    def __init__(self, plugin_id):
        self.logger = logging.getLogger(plugin_id)      
        self.logger.handlers.clear()
        
        # Create console handler and set level to debug
        ch = logging.StreamHandler(sys.stdout)
        # ch = logging.StreamHandler()

        # Create formatter
        formatter = logging.Formatter('%(asctime)s.%(msecs)03d [%(levelname)s][%(filename)s:%(lineno)d](%(funcName)s) %(message)s',
                                      datefmt='%b%d %H:%M:%S')
        ch.setFormatter(formatter)
        
        # Add ch to logger
        self.logger.addHandler(ch)
        
        # Prevent propagation to parent loggers
        self.logger.propagate = False


    def info(self, message):
        self.logger.info(message, stacklevel=2)
    
    def debug(self, message):
        self.logger.debug(message, stacklevel=2)
    
    def warning(self, message):
        self.logger.warning(message, stacklevel=2)
    
    def error(self, message):
        self.logger.error(message, stacklevel=2)
        # Capture and log the traceback information
        exc_type, exc_value, exc_traceback = traceback.sys.exc_info()
        if exc_traceback:
            self.logger.error("Traceback: %s", traceback.format_exc(), stacklevel=2)

    def critical(self, message):
        self.logger.critical(message, stacklevel=2)
        # Capture and log the traceback information
        exc_type, exc_value, exc_traceback = traceback.sys.exc_info()
        if exc_traceback:
            self.logger.critical("Traceback: %s", traceback.format_exc(), stacklevel=2)

g_log = gLog(PLUGIN_ID)

