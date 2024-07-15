
import sys
import logging

import TouchPortalAPI as TP
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

class gLog:
    def __init__(self, plugin_id):
        self.logger = logging.getLogger(plugin_id)
        
    def info(self, message):
        self.logger.info(message)
    
    def debug(self, message):
        self.logger.debug(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def critical(self, message):
        self.logger.critical(message)


g_log = gLog(PLUGIN_ID)

