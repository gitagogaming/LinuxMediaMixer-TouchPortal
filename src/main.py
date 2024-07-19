####  requirements - ewmh, touchportal-api, pulsectl

from argparse import ArgumentParser
import asyncio
import sys
import time

import TouchPortalAPI as TP
from windowmonitor import WindowMonitor
from audiocontroller import AudioController
from eventListener import PulseListener
from TPPEntry import TP_PLUGIN_SETTINGS, TP_PLUGIN_ACTIONS, TP_PLUGIN_CONNECTORS, PLUGIN_ID, TP_PLUGIN_INFO, PLUGIN_NAME, PLUGIN_RELEASE_INFO, __version__
from tpClient import TPClient, g_log
# from update_check import plugin_update_check, download_update

### input/output slidrs are not updating when changing externally.. believe they use to but now we added in a new thingy...

def handleSettings(settings, on_connect=False):
    settings = { list(settings[i])[0] : list(settings[i].values())[0] for i in range(len(settings)) }
    g_log.info(f"Settings: {settings}")

    if (value := settings.get("Browser Apps")) is not None:
        TP_PLUGIN_SETTINGS['BrowserApps']['value'] = value
        print()
        controller.browserApps = [app.strip() for app in value.split(',')]



@TPClient.on(TP.TYPES.onNotificationOptionClicked)
def onNoticationClicked(data):
    pass
    # if data['optionId'] == f"{PLUGIN_ID}.settings.error.options":
    #     url = "https://dashboard.ngrok.com/signup"
    #     webbrowser.open(url, new=0, autoraise=True)
        
    # elif data['optionId'] == f"{PLUGIN_ID}.update.download":
    #     if PLUGIN_RELEASE_INFO['downloadURL']:
    #         download_URL = PLUGIN_RELEASE_INFO['downloadURL']
    #         g_log.info("Downloading the update...")
    #         tpp_file = download_update(download_URL)
    #         if tpp_file:
    #             os.startfile(tpp_file)
    #     else:
    #         g_log.error("Error downloading the update, download URL not found.", download_URL)
            
    # elif data['optionId'] == f"{PLUGIN_ID}.update.manual":
    #     if PLUGIN_RELEASE_INFO['htmlURL']:
    #         webbrowser.open(PLUGIN_RELEASE_INFO['htmlURL'], new=0, autoraise=True)
    #     else:
    #         g_log.error("Error opening the download page, URL not found.", PLUGIN_RELEASE_INFO['htmlURL'])



#--- On Startup ---#
@TPClient.on(TP.TYPES.onConnect)
def onConnect(data):
    g_log.info(f"Connected to TP v{data.get('tpVersionString', '?')}, plugin v{data.get('pluginVersion', '?')}.")
    g_log.debug(f"Connection: {data}")
    if settings := data.get('settings'):
        handleSettings(settings, True)
 
    # try:
    #     global PLUGIN_RELEASE_INFO
    #     PLUGIN_RELEASE_INFO = plugin_update_check(str(data['pluginVersion']))
        
    #     if PLUGIN_RELEASE_INFO['patchnotes']:
    #         patchNotes = f"A new version of {PLUGIN_NAME} is available and ready to Download.\nThis may include Bug Fixes and or New Features\n\nPatch Notes\n{PLUGIN_RELEASE_INFO['patchnotes']}"
    #     elif PLUGIN_RELEASE_INFO['patchnotes'] == "":
    #         patchNotes = f"A new version of {PLUGIN_NAME} is available and ready to Download.\nThis may include Bug Fixes and or New Features"
    #     if PLUGIN_RELEASE_INFO['version']:
    #         TPClient.showNotification(
    #             notificationId= f"{PLUGIN_ID}.TP.Plugins.Update_Check",
    #             title=f"{PLUGIN_NAME} {PLUGIN_RELEASE_INFO['version']} is available",
    #             msg=patchNotes,
    #             options= [
    #             {
    #             "id":f"{PLUGIN_ID}.update.download",
    #             "title":"(Auto) Download & Update!"
    #             },
    #             {
    #             "id":f"{PLUGIN_ID}.update.manual",
    #             "title":"(Manual) Open Plugin Download Page"
    #             }])
    # except Exception as e:
    #     print("Error Checking for Updates", e)
    
    # asyncio.run(controller.start())
    
    initializeController()
    monitor.start() ## Listening for current active window ot change..
    
    apps = controller.get_app_list()
    # g_log.debug(f"on Connect Apps{apps.keys()}")
    
    # controller.get_current_default_devices()
    # controller.start_periodic_check()
    # print("THE INPUT", controller.defaultDevices['input'].description)


    TPClient.choiceUpdate(PLUGIN_ID + ".act.Mute/Unmute.data.process", list(apps.keys()))
    TPClient.choiceUpdate(PLUGIN_ID + ".act.Inc/DecrVol.data.process", list(apps.keys()))
    TPClient.choiceUpdate(PLUGIN_ID + ".connector.APPcontrol.data.slidercontrol", list(apps.keys()))
    TPClient.choiceUpdate(PLUGIN_ID + ".act.ChangeAudioOutput.data.device", list(controller.output_devices.keys()))
    # TPClient.choiceUpdate(PLUGIN_ID + ".connector.WinAudio.devices", list(controller.input_devices.keys()))
    
    
    # TPClient.choiceUpdate(PLUGIN_ID + ".connector.WinAudio.devices", list(controller.output_devices.keys()))
    # TPClient.choiceUpdate(PLUGIN_ID + ".act.changeDeviceMute.devices", list(controller.output_devices.keys()))
    
    
    
    
    
#--- Settings handler ---#
@TPClient.on(TP.TYPES.onSettingUpdate)
def onSettingUpdate(data):
    g_log.info(f"Settings: {data}")
    handleSettings(data['values'])





@TPClient.on(TP.TYPES.onConnectorChange)
def connectors(data):
    g_log.debug(f"connector Change: {data}")
    if data['connectorId'] == TP_PLUGIN_CONNECTORS["APP control"]['id']:
        if data['data'][0]['value'] == "Master Volume":
            # setMasterVolume(data['value'])
            # controller.set_volume(data['data'][0]['value'], data['value'])
            pass
        elif data['data'][0]['value'] == "Current app":
            activeWindow = monitor.get_current_window()
            
            # print("This is the active window by the way...", activeWindow['app_name'])
            
            if activeWindow != "":
                try:
                    controller.set_app_volume(activeWindow['app_name'], data['value'], "Set")
                except Exception as e:
                    g_log.error(e)
                    pass
        else:
            try:
                controller.set_app_volume(data['data'][0]['value'], data['value'], "Set")
            except Exception as e:
                g_log.debug(f"Exception in other app volume change Error: {str(e)}")
    elif data['connectorId'] == TP_PLUGIN_CONNECTORS["Windows Audio"]["id"]:
        controller.set_volume(data['data'][0]['value'], "Set", data['value'], data['data'][1]['value'])

    time.sleep(0.1)



def initializeController(initial_delay=2, max_delay=32):
    attempt = 0
    delay = initial_delay

    while True:
        attempt += 1
        g_log.info(f"Initialization attempt {attempt}")

        controller.start()

        if controller.initialization_complete.wait(timeout=10):
            g_log.info("PulseAudio Controller initialized.")
            pulseListener.start()
            return 

        g_log.info(f"Initialization attempt {attempt} failed. Retrying in {delay} seconds...")
        controller.stop()  # Clean up before retrying
        time.sleep(delay)

        # Exponential backoff
        delay = min(delay * 2, max_delay)

        # Reset delay after reaching max_delay
        if delay == max_delay:
            delay = initial_delay





#--- On Hold handler ---#
@TPClient.on(TP.TYPES.onHold_down)
def holdingButton(data):
    g_log.info(f"holdingButton: {data}")
    while True:
        if TPClient.isActionBeingHeld(TP_PLUGIN_ACTIONS['Inc/DecrVol']['id']):
            g_log.debug(f"App: {data['data'][0]['value']} Action {data['data'][1]['value']}   Volume Value: {data['data'][2]['value']}")
            controller.set_app_volume(data['data'][0]['value'], data['data'][2]['value'], data['data'][1]['value'])

        elif TPClient.isActionBeingHeld(TP_PLUGIN_ACTIONS['setDeviceVolume']['id']):
            g_log.debug(f"Device: {data['data'][0]['value']} Action {data['data'][1]['value']}   Volume Value: {data['data'][2]['value']} ")
            controller.set_volume(data['data'][0]['value'], data['data'][1]['value'], data['data'][2]['value'], data['data'][3]['value'])   
        else:
            break   
        time.sleep(0.1)





#--- Action handler ---#
@TPClient.on(TP.TYPES.onAction)
def onAction(data: dict):
    g_log.debug(f"Action: {data}")
    if not (action_data := data.get('data')) or not (actionid := data.get('actionId')):
        return

    elif actionid == TP_PLUGIN_ACTIONS['AppMute']['id']:
        if action_data[0]['value'] != '':
            muteChoice = action_data[1]['value']
            if action_data[0]['value'] == "Current app":
                activeWindow = monitor.get_current_window()
                if activeWindow != "":
                    controller.set_app_mute(activeWindow, muteChoice)
                    # muteAndUnMute(os.path.basename(activeWindow), action_data[1]['value'])
            elif action_data[0]['value'] == "Master Volume":
                pass # idk
            else:
                controller.set_app_mute(action_data[0]['value'], muteChoice)

    elif actionid == TP_PLUGIN_ACTIONS['Inc/DecrVol']['id']:
        if action_data[0]['value'] == "Current app":
            activeWindow = monitor.get_current_window()
            if activeWindow != "":
                controller.set_app_volume(activeWindow, action_data[1]['value'], action_data[1]['value'])
        else:
            controller.set_app_volume(action_data[0]['value'],  action_data[1]['value'], action_data[1]['value'])
            
    elif actionid == TP_PLUGIN_ACTIONS['setDeviceVolume']['id']:
        controller.set_volume(action_data[0]['value'], action_data[1]['value'], data['data'][2]['value'], action_data[3]['value'])
            
    elif actionid == TP_PLUGIN_ACTIONS['ChangeOut/Input']['id']:
        controller.set_default_device(action_data[0]['value'], action_data[1]['value'])

    elif actionid == TP_PLUGIN_ACTIONS['setDeviceMute']['id']:
        controller.set_mute(action_data[0]['value'], action_data[1]['value'], action_data[2]['value'])





@TPClient.on(TP.TYPES.onListChange)
def onListChange(data):
    g_log.info(f"onlistChange: {data}")
    
    if data['actionId'] == TP_PLUGIN_ACTIONS["setDeviceVolume"]["id"] and \
        data["listId"] == TP_PLUGIN_ACTIONS["setDeviceVolume"]["data"]["deviceType"]["id"]:
        try:
            if data['value'] == "Input":
                TPClient.choiceUpdate(PLUGIN_ID + ".act.changeDeviceVolume.devices", list(controller.input_devices.keys()))
            elif data['value'] == "Output":
                TPClient.choiceUpdate(PLUGIN_ID + ".act.changeDeviceVolume.devices", list(controller.output_devices.keys()))
         # pass  # updateDevice(data['value'], TP_PLUGIN_ACTIONS["setDeviceVolume"]["data"]["deviceOption"]["id"], data['instanceId'])
        except Exception as e:
            g_log.info(f"Update device setDeviceVolume error {e}")
            
    elif data['actionId'] == TP_PLUGIN_CONNECTORS["Windows Audio"]["id"] and \
        data["listId"] == (listId := TP_PLUGIN_CONNECTORS["Windows Audio"]["data"]["deviceType"]["id"]):
            try:
                if data['value'] == "Input":
                    TPClient.choiceUpdate(PLUGIN_ID + ".connector.WinAudio.devices", list(controller.input_devices.keys()))
                elif data['value'] == "Output":
                    TPClient.choiceUpdate(PLUGIN_ID + ".connector.WinAudio.devices", list(controller.output_devices.keys()))
                # updateDevice(data['value'], listId, data['instanceId'])
            except Exception as e:
               g_log.warning(f"Update device setDeviceVolume error {e}")
               
    elif data['actionId'] == TP_PLUGIN_ACTIONS["setDeviceMute"]["id"] and \
        data["listId"] == (listId:= TP_PLUGIN_ACTIONS['setDeviceMute']["data"]["deviceType"]["id"]):
            try:
                if data['value'] == "Input":
                    TPClient.choiceUpdate(PLUGIN_ID + ".act.changeDeviceMute.devices", list(controller.input_devices.keys()))
                elif data['value'] == "Output":
                    TPClient.choiceUpdate(PLUGIN_ID + ".act.changeDeviceMute.devices", list(controller.output_devices.keys()))
            except Exception as e:
                g_log.error(f"ChoiceUpdate for changeDeviceMute Failed {e}")
                
    elif data['actionId'] == TP_PLUGIN_ACTIONS["ChangeOut/Input"]["id"] and \
        data["listId"] == (listId:= TP_PLUGIN_ACTIONS['ChangeOut/Input']["data"]["optionSel"]["id"]):
            try:
                if data['value'] == "Input":
                    TPClient.choiceUpdate(PLUGIN_ID + ".act.ChangeAudioOutput.data.device", list(controller.input_devices.keys()))
                elif data['value'] == "Output":
                    TPClient.choiceUpdate(PLUGIN_ID + ".act.ChangeAudioOutput.data.device", list(controller.output_devices.keys()))
            except Exception as e:
                g_log.error(f"ChoiceUpdate for ChangeOut/Input Failed {e}")
    


    # if data['actionId'] == TP_PLUGIN_ACTIONS["ChangeOut/Input"]['id'] and \
        # data['listId'] == TP_PLUGIN_ACTIONS["ChangeOut/Input"]["data"]["optionSel"]["id"]:
        # try:
            # pass #updateDevice(data['value'], TP_PLUGIN_ACTIONS["ChangeOut/Input"]['data']['deviceOption']['id'], data['instanceId'])
        # except Exception as e:
            # g_log.info("Update device input/output KeyError: " + str(e))
    # if data['actionId'] == TP_PLUGIN_ACTIONS["ToggleOut/Input"]['id'] and \
        # data['listId'] == TP_PLUGIN_ACTIONS["ToggleOut/Input"]["data"]["optionSel"]["id"]:
        # try:
            # pass #updateDevice(data['value'], TP_PLUGIN_ACTIONS["ToggleOut/Input"]['data']['deviceOption1']['id'], data['instanceId'])
            # pass #updateDevice(data['value'], TP_PLUGIN_ACTIONS["ToggleOut/Input"]['data']['deviceOption2']['id'], data['instanceId'])
        # except Exception as e:
            # g_log.info("Update device input/output KeyError: " + str(e))
    # if data['actionId'] == TP_PLUGIN_ACTIONS["AppAudioSwitch"]["id"] and \
    #     data["listId"] == TP_PLUGIN_ACTIONS["AppAudioSwitch"]["data"]["deviceType"]["id"]:
    #     try:
    #        pass # updateDevice(data['value'], TP_PLUGIN_ACTIONS["AppAudioSwitch"]["data"]["devicelist"]["id"], data['instanceId'])
    #     except Exception as e:
    #         g_log.info("Update device input/output KeyError: " + str(e))



# Shutdown handler
@TPClient.on(TP.TYPES.onShutdown)
def onShutdown(data:dict):
    g_log.info('Received shutdown event from TP Client.')
    
    monitor.stop()
    pulseListener.stop()
    controller.stop()



## main
async def main():
    global TPClient
    ret = 0  # sys.exit() value

    logFile = f"./{PLUGIN_ID}.log"
    logStream = sys.stdout
    
    parser = ArgumentParser(fromfile_prefix_chars='@')
    parser.add_argument("-d", action='store_true',
                        help="Use debug logging.")
    parser.add_argument("-w", action='store_true',
                        help="Only log warnings and errors.")
    parser.add_argument("-q", action='store_true',
                        help="Disable all logging (quiet).")
    parser.add_argument("-l", metavar="<logfile>",
                        help=f"Log file name (default is '{logFile}'). Use 'none' to disable file logging.")
    parser.add_argument("-s", metavar="<stream>",
                        help="Log to output stream: 'stdout' (default), 'stderr', or 'none'.")

    # this processes the actual command line and populates the `opts` dict.
    opts = parser.parse_args()
    del parser

    # trim option string (they may contain spaces if read from config file)
    opts.l = opts.l.strip() if opts.l else 'none'
    opts.s = opts.s.strip().lower() if opts.s else 'stdout'

    # Set minimum logging level based on passed arguments
    logLevel = "DEBUG"
    if opts.q: logLevel = None
    elif opts.d: logLevel = "DEBUG"
    elif opts.w: logLevel = "WARNING"

    # set log file if -l argument was passed
    if opts.l:
        logFile = None if opts.l.lower() == "none" else opts.l
    # set console logging if -s argument was passed
    if opts.s:
        if opts.s == "stderr": logStream = sys.stderr
        elif opts.s == "stdout": logStream = sys.stdout
        else: logStream = None
        
    TPClient.setLogFile(logFile)
    TPClient.setLogStream(logStream)
    TPClient.setLogLevel(logLevel)


    g_log.info(f"Starting {TP_PLUGIN_INFO['name']} v{__version__} on {sys.platform}.")

    try:
        TPClient.connect()
        g_log.info('TP Client closed.')
    except KeyboardInterrupt:
        g_log.warning("Caught keyboard interrupt, exiting.")
    except Exception:
        from traceback import format_exc
        g_log.error(f"Exception in TP Client:\n{format_exc()}")
        ret = -1
    finally:
        TPClient.disconnect()

    del TPClient

    g_log.info(f"{TP_PLUGIN_INFO['name']} stopped.")
    return ret



if __name__ == "__main__":
    controller = AudioController()
    monitor = WindowMonitor(controller)
    pulseListener = PulseListener(controller)
    asyncio.run(main())
    
    
    





# monitor = WindowMonitor()

# # # controller.set_volume("output", "default", 0.1)
# # # controller.set_volume("input", 0.5)
# # # controller.set_mute("output", "default", 1)
# # # controller.set_mute("output", "default", 0)

# # controller.set_default_device("input", "Built-in Audio Analog Stereo")
# # controller.set_app_volume("Firefox", 1.0)
# controller.set_app_mute("Firefox", 0)







# import time
# # For demonstration.. not needed all the time as we use TP and it keeps everything running
# while True:
#     # print(monitor.currentWindow)
#     if monitor.currentWindow:
#         pass
#         # print(monitor.currentWindow['app_name'])
#         # controller.set_app_mute("current window", 1)
#     time.sleep(1)



