
import threading 
import asyncio
import pulsectl_asyncio

from tpClient import TPClient, g_log
from TPPEntry import  PLUGIN_ID, __version__


class AudioController(object):
    def __init__(self) -> None:
        self.pulse = None
        self.loop = None
        self.thread = None
        self.initialization_complete = threading.Event()

        self.output_devices = {}
        self.input_devices = {}
        self.cards = {}
        self.apps = {}
        
    def _run_event_loop(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._async_init())
        self.loop.run_forever()

    async def _async_init(self):
        try:
            await self.initialize_pulse()
            self.initialization_complete.set() 
        except Exception as e:
            g_log.error(f"Error during initialization: {e}")

    def start(self):
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()

        if not self.initialization_complete.wait(timeout=10):  # Wait for initialization to complete
            g_log.error("Failed to initialize PulseAudio within timeout.")
            return

    def stop(self):
        """
          Call Stop on shutdown 
        """
        if self.loop and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self._cleanup)
        if self.thread:
            self.thread.join()

    def _cleanup(self):
        asyncio.create_task(self._async_cleanup())

    async def _async_cleanup(self):
        if self.pulse:
            await self.pulse.disconnect()
        self.loop.stop()

    def run_coroutine(self, coro_func, *args):
        if self.loop.is_closed():
            g_log.info("Event loop is closed. Cannot proceed.")
            return
        future = asyncio.run_coroutine_threadsafe(coro_func(*args), self.loop)
        try:
            return future.result(timeout=5)  # Wait for up to 5 seconds
        except asyncio.TimeoutError:
            g_log.error("Operation timed out")
        except Exception as e:
            g_log.error(f"Operation failed: {e}")

    def get_app_list(self):
        """ We could make this fetch new apps instead of relying on the stored ones ?"""
        return self.apps

    def removeAudioState(self, app_name):
        """ 
        UNUSED CURRENTLY
        """
        TPClient.removeStateMany([
                PLUGIN_ID + f".createState.{app_name}.muteState",
                PLUGIN_ID + f".createState.{app_name}.volume",
                PLUGIN_ID + f".createState.{app_name}.active"
                ])
        del self.apps[app_name]
        # self.updateVolumeMixerChoicelist() # Update with new changes

    async def initialize_pulse(self):
        try:
            self.pulse = pulsectl_asyncio.PulseAsync('volume-manager')
            await self.pulse.connect()
            await self.get_devices()
            await self.get_app_inputs()
        except Exception as e:
            g_log.error(f"Unexpected error during PulseAudio initialization: {e}")

    async def get_devices(self):
        if not self.pulse:
            g_log.info("PulseAudio connection not established.")
            return
        
        self.output_devices.clear()
        self.input_devices.clear()
        
        for device in await self.pulse.sink_list():
            # if device.proplist.get('device.class') == 'sound':
                self.output_devices[device.description] = device
                g_log.debug(f"\nOutput device found: {device.description} | Name: {device.name} | Index: {device.index} | Properties: {device.proplist}")

            # print("\n")

        # print("Fetching source (input) devices...")
        for device in await self.pulse.source_list():
            # if device.proplist.get('device.class') == 'sound':# and 'monitor' not in device.name:
                self.input_devices[device.description] = device
                # self.output_devices[device.description] = device
                g_log.debug(f"\nInput device found: {device.description} | Name: {device.name} | Index: {device.index} | Properties: {device.proplist}")
       
        ## 
        ## sink_list, source_list and card_list dont seem to show anything to properly identify it for us.. although it should be there somewhere..
        # this command below allows to set the default device to the hdmi output - but not sure how to get that set up here or how to find it technically
        # pacmd set-card-profile alsa_card.pci-0000_00_1b.0 output:hdmi-stereo
        ## This one allows testing of audio over that hdmi channel
        # speaker-test -D hdmi:0 -c 2

        # for card in await self.pulse.card_list():
        #     print(f"Card #{card.index}")
        #     print(f"\tName: {card.name}")
        #     print(f"\tDriver: {card.driver}")
        #     print(f"\tProperties:")
        #     for key, value in card.proplist.items():
        #         print(f"\t\t{key}: {value}")
        #     print(f"\tProfiles:")
        #     for profile in card.profiles:
        #         print(f"\t\t{profile.name}: {profile.description}")
        #         if "hdmi" in profile.name.lower():  # Adjust this condition based on your specific profiles
        #             print(f"\t\t  Available: {profile.available}")
        #             print(f"\t\t  Priority: {profile.priority}")
        #             # You can add more conditions or actions based on profile properties

        #     print(f"\tActive Profile: {card.profile}")
        #     print(f"\tPorts:")
        #     for port in card.ports:
        #         print(f"\t\t{port.name}: {port.description}")

        #     self.cards[card.description] = {
        #         'index': card.index,
        #         # 'profiles': {profile.name: profile.description for profile in card.profiles}
        #     }
        # print("The cards are: ", self.cards)
        # Additional check for any other devices not categorized
        # cards = await self.pulse.card_list()
        # for card in cards:
        #     has_output = False
        #     has_input = False
        #     for profile in card.profile_list:
        #         if profile.available:
        #             if profile.n_sinks > 0:
        #                 has_output = True
        #             if profile.n_sources > 0:
        #                 has_input = True
        #     card_description = card.proplist.get('device.description', f"Unknown Card {card.index}")
        #     if has_output:
        #         self.output_devices[card_description] = card
        #         print(f"Card {card_description} added as an output device.")
        #     if has_input:
        #         self.input_devices[card_description] = card
        #         print(f"Card {card_description} added as an input device.")
        
    async def _get_device(self, device_type, source):
        """  For now the device will always be default
            until we find a user who can show a way to use cables outside of default
            """
        device_type = device_type.lower()
        if device_type == "output":
            device = self.output_devices.get(source) if source != "default" else await self._current_default_device(device_type)
        elif device_type == "input":
            device = self.input_devices.get(source) if source != "default" else await self._current_default_device(device_type)
        else:
            g_log.info(f"Invalid device type: {device_type}")
            return None

        if not device:
            g_log.info(f"Device with description '{source}' not found.")
            return None
        
        g_log.debug(f"Device found: {device}")
        return device

    async def _current_default_device(self, atype):
        """
        Get the current default device for the specified type (input or output)
        """
        if atype == "output":
            device = await self.pulse.get_sink_by_name('@DEFAULT_SINK@')
        if atype == "input":
            device = await self.pulse.get_source_by_name('@DEFAULT_SOURCE@')

        g_log.debug(f"Current default {atype} device: {device}")
        return device
    

    async def get_app_inputs(self):
        """
        This retrieves all the apps/windows currently open and available
        example: Firefox, Discord, etc..
        """
        self.apps = {} 
        for input in await self.pulse.sink_input_list():
            states = []
            app_name = input.proplist.get('application.name', 'Unknown')

            ## I created a virtual cable and it appeared here.. and it has no application name so it broke it...
            ## For now this is a temporary fix
            if app_name == 'Unknown':
                app_name = input.proplist.get('media.name', "Unknown")

            info = await self.pulse.sink_input_info(input.index)
            app_info = {                ## SET APP MUTE IS ONLY PLACE THIS INDEX IS UTILIZED??
                'index': input.index,  # Store index for volume adjustment - we could use other things technically now as index changes
                'properties': input.proplist,
                'info': info,
                'volume': round(info.volume.values[0])
            }
            self.apps[app_name.lower()] = app_info

            states = [
                {   
                    "id": PLUGIN_ID + f".createState.{app_name.lower()}.muteState",
                    "desc": f"{app_name.lower()} Mute State",
                    "parentGroup": "Audio process state",
                    "value": "unmuted" if input.mute == 0 else "muted"
                },
                {
                    "id": PLUGIN_ID + f".createState.{app_name.lower()}.volume",
                    "desc": f"{app_name.lower()} Volume",
                    "parentGroup": "Audio process state",
                    "value": str(round(info.volume.values[0]*100))
                }
            ]
            
            g_log.debug(f"App: {app_name.lower()} | Data: {app_info}")
            
            TPClient.createStateMany(states)
            
        g_log.debug(f"Apps Retrieved {self.apps}")


    def set_app_volume(self, app_name, volume, action='set'):
        """Adjusts the volume of the specified app. Action can be 'set', 'increase', or 'decrease'."""
        self.run_coroutine(self._set_app_volume, app_name, volume, action)
    async def _set_app_volume(self, app_name, volume, action):
        if not self.pulse or not self.pulse.connected:
            g_log.info("PulseAudio connection not available...")
            return
        
        app_info = self.apps.get(app_name.lower())

        if not app_info:
            g_log.info(f"Application '{app_name}' not found.")
            return

        if hasattr(app_info['info'], 'volume'):
            current_volume = app_info['info'].volume.values[0]
        else:
            g_log.info(f"No volume attribute found for '{app_name}'")
            return
        
        if action == 'Increase':
            volume = min(1.0, current_volume + volume)
        elif action == 'Decrease':
            volume = max(0.0, current_volume - volume)
        elif action == 'Set':
            volume = float(volume)
        else:
            g_log.info(f"Unknown volume action: {action}")
            return

        # Ensure volume is within valid range
        volume = max(0.0, min(1.0, volume))
        g_log.info(f"Setting volume for {app_name} to {volume * 100}%")

        try:
            await self.pulse.volume_set_all_chans(app_info['info'], volume)
        except asyncio.exceptions.InvalidStateError as e:
            g_log.error(f"Invalid state error: {e}")
            g_log.error(f"App: {app_name}, Volume: {volume}, Action: {action} App info: {app_info}")
        except Exception as e:
            g_log.error(f"Unexpected error in _set_app_volume: {e}")

        g_log.info(f"Volume for {app_name} {action} to {volume * 100}%")



    def set_app_mute(self, app_name, command):
        """Mute, Unmute or Toggle the specified app."""
        self.run_coroutine(self._set_app_mute, app_name, command)
    async def _set_app_mute(self, app_name, command):
        
        app_info = self.apps[app_name] ## Getting current object/state of the app stored locally
        command_actions = {
            "Mute": lambda: 1,
            "Unmute": lambda: 0,
            "Toggle": lambda: 0 if app_info['info'].mute else 1
        }
        mute = command_actions[command]()
        
        if app_info:
            await self.pulse.sink_input_mute(app_info['index'], mute)
            g_log.info(f"App Mute | Application '{app_name}' muted: {mute}")
        else:
            g_log.info(f"App Mute | Application '{app_name}' not found.")
     
            

    def set_volume(self, device_type, action, volume):
        """Set the volume of the specified device."""
        self.run_coroutine(self._set_volume, device_type, action, volume)
    async def _set_volume(self, device_type:str, action:str="set", volume:str="25"):
        """ 
        - Currently only seems to be effective for the default device
        - Need to find a way to see results of setting the volume of a specific device if possible (OBS STUDIO? - by listening)
        """
        device = None
        device_type = device_type.lower()
        device = await self._current_default_device(device_type)
        if not device:
            g_log.info(f"set_volume: ({device_type}) Device not found.")
            return
        
        current_volume = device.volume.values[0]
        
        if action == 'Increase':
            volume = min(1.0, current_volume + volume)
        elif action == 'Decrease':
            volume = max(0.0, current_volume - volume)
        elif action == 'Set':
            volume = float(volume)/ 100
        else:
            g_log.info(f"Unknown volume action: {action}")
            return
        
        g_log.debug(f"Set Volume: {device_type} volume:{volume} - Device: {device}")
        await self.pulse.volume_set_all_chans(device, volume)



    def set_mute(self, device_type, source, mute):
        """Mute, Unmute or Toggle the specified device."""
        self.run_coroutine(self._set_mute, device_type, source, mute)
    async def _set_mute(self, device_type, source, command):
        device = await self._get_device(device_type, source)
        
        command_actions = {
            "Mute": lambda: 1,
            "Unmute": lambda: 0,
            "Toggle": lambda: 0 if device.mute else 1
        }
        mute = command_actions[command]()
            
        await self.pulse.mute(device, int(mute))
    
    
    
    def set_default_device(self, device_type, source):
        """Set the default device for the specified type (input or output)."""
        self.run_coroutine(self._set_default_device, device_type, source)
    async def _set_default_device(self, device_type, source):
        device = await self._get_device(device_type, source)
        await self.pulse.default_set(device)

    

controller = AudioController()
















    # def increase_volume(self, device_type, source, volume):
    #     if device_type == "output":
    #         device = self.output_devices.get(source) if source != "default" else self._current_default_device(device_type)
    #     elif device_type == "input":
    #         device = self.input_devices.get(source) if source != "default" else self._current_default_device(device_type)
        
    #     if not device:
    #         g_log.info(f"Device with description '{source}' not found.")
    #         return
        
    #     currentVolume = device.volume.value_flat
    #     self.pulse.volume_set(device, currentVolume.volume.value_flat + volume)


    # def decrease_volume(self, device_type, source, volume):    
    #     if device_type == "output":
    #         device = self.output_devices.get(source) if source != "default" else self._current_default_device(device_type)
    #     elif device_type == "input":
    #         device = self.input_devices.get(source) if source != "default" else self._current_default_device(device_type)
        
    #     if not device:
    #         g_log.info(f"Device with description '{source}' not found.")
    #         return
        
    #     currentVolume = device.volume.value_flat
    #     self.pulse.volume_set(device, currentVolume.volume.value_flat - volume)