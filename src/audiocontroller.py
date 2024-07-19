
import threading 
import asyncio
import pulsectl_asyncio
import concurrent.futures

from tpClient import TPClient, g_log
from TPPEntry import  PLUGIN_ID, __version__
from findIcon import find_icon_path


class AudioController(object):
    def __init__(self) -> None:
        self.pulse = None
        self.loop = None
        self.thread = None
        self.initialization_complete = threading.Event()
        
        self.defaultDevices = { 'input': {},'output':{} }
        self.output_devices = {}
        self.input_devices = {}
        self.cards = {}
        self.apps = {}

        self.browserApps = []
        
    async def periodic_device_check(self):
        """
        Periodically check and update the default devices every 45 seconds
        """
        while True:
            await self._get_current_default_devices()
            await asyncio.sleep(45)

    def start_periodic_check(self):
        """
        Start the periodic device check
        """
        asyncio.create_task(self.periodic_device_check())
        
        
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
            future = asyncio.run_coroutine_threadsafe(self._async_cleanup(), self.loop)
            try:
                future.result(timeout=5)  # Wait for up to 5 seconds
            except concurrent.futures._base.TimeoutError:
                pass
            except Exception as e:
                g_log.error(f"Error during cleanup: {e}")

        if self.thread:
            self.thread.join(timeout=5)
            if self.thread.is_alive():
                g_log.error("Thread did not finish in time")
                
    async def _async_cleanup(self):
        try:
            if self.pulse:
                self.pulse.disconnect()
                g_log.info("Controller disconnected successfully")
        except Exception as e:
            g_log.error(f"Error during pulse disconnect: {e}")
        finally:
            if self.loop and not self.loop.is_closed():
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

    async def initialize_pulse(self):
        try:
            self.pulse = pulsectl_asyncio.PulseAsync('volume-manager')
            await self.pulse.connect()
            await self.get_devices()
            await self.get_app_inputs()
            self.start_periodic_check()
        except Exception as e:
            g_log.error(f"Unexpected error during PulseAudio initialization: {e}")
            
          
            
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

        ## adding "default device" to the list of choices
        self.output_devices["default"] = "default"

        for device in await self.pulse.source_list():
            # if device.proplist.get('device.class') == 'sound':# and 'monitor' not in device.name:
                self.input_devices[device.description] = device
                # self.output_devices[device.description] = device
                g_log.debug(f"\nInput device found: {device.description} | Name: {device.name} | Index: {device.index} | Properties: {device.proplist}")
        
        ## adding "default device" to the list of choices
        self.input_devices["default"] = "default"

        ## 
        ## sink_list, source_list and card_list dont seem to show anything to properly identify it for us.. although it should be there somewhere..
        # this command below allows to set the default device to the hdmi output - but not sure how to get that set up here or how to find it technically
        # pacmd set-card-profile alsa_card.pci-0000_00_1b.0 output:hdmi-stereo
        ## This one allows testing of audio over that hdmi channel   - https://bbs.archlinux.org/viewtopic.php?id=245761
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
            device = self.output_devices.get(source) if source != "default" else self.defaultDevices[device_type]
        elif device_type == "input":
            device = self.input_devices.get(source) if source != "default" else self.defaultDevices[device_type]
        else:
            g_log.info(f"Invalid device type: {device_type}")
            return None

        if not device:
            g_log.info(f"Device with description '{source}' not found.")
            return None
        
        g_log.debug(f"Device found: {device}")
        return device

    def get_current_default_devices(self):
        self.run_coroutine(self._get_current_default_devices)
    async def _get_current_default_devices(self):
        """
        Get the current default device for the specified type (input or output)
        """
        self.defaultDevices['output'] = await self.pulse.get_sink_by_name('@DEFAULT_SINK@')
        self.defaultDevices['input'] = await self.pulse.get_source_by_name('@DEFAULT_SOURCE@')
        
        TPClient.stateUpdate(PLUGIN_ID + ".state.CurrentInputDevice", self.defaultDevices['input'].description)
        TPClient.stateUpdate(PLUGIN_ID + ".state.CurrentOutputDevice", self.defaultDevices['output'].description)

        g_log.debug(f"Default Devices Retrieved {self.defaultDevices}")
    

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
            
            # print("ON STARTTUP APP ICON", input.proplist)
            app_icon = find_icon_path(input.proplist)
                
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
                },
                {
                    "id": PLUGIN_ID + f".createState.{app_name.lower()}.icon",
                    "desc": f"{app_name.lower()} Icon",
                    "parentGroup": "Audio process state",
                    "value": app_icon if app_icon != None else ""
                }
            ]
            
            g_log.debug(f"App: {app_name.lower()} | Data: {app_info}")
            
            TPClient.createStateMany(states)
        
        ## Adding in entry for 'current app'
        # self.apps["Current app"] = "Current app"
        g_log.debug(f"Apps Retrieved {self.apps}")


    def set_app_volume(self, app_name, volume, action='set'):
        """Adjusts the volume of the specified app. Action can be 'set', 'increase', or 'decrease'."""
        self.run_coroutine(self._set_app_volume, app_name, volume, action)
    async def _set_app_volume(self, app_name, volume, action):
        if not self.pulse or not self.pulse.connected:
            g_log.info("PulseAudio connection not available...")
            return
        
        app_info = None
        volume = float(max(0, min(int(volume), 100))) / 100
            
        if app_name.lower() in self.browserApps:
            await self._setBrowserVolume(app_name, volume, action)
        else:
            app_info = self.apps.get(app_name.lower())

            if not app_info:
                g_log.debug(f"Application '{app_name}' not found. {self.apps}")
                return

            if hasattr(app_info['info'], 'volume'):
                current_volume = app_info['info'].volume.values[0]
            else:
                g_log.info(f"No volume attribute found for '{app_name}'")
                return

            if action.lower() == 'increase':
                volume = min(1.0, current_volume + volume)
            elif action.lower() == 'decrease':
                volume = max(0.0, current_volume - volume)
            elif action.lower() == 'set':
                volume = volume
            else:
                g_log.info(f"Unknown volume action: {action}")
                return

            volume = max(0.0, min(1.0, volume))
            g_log.info(f"Setting volume for {app_name} to {volume * 100}%")

            try:
                await self.pulse.volume_set_all_chans(app_info['info'], volume)
            except asyncio.exceptions.InvalidStateError as e:
                g_log.error(f"Invalid state error: {e}")
            except Exception as e:
                g_log.error(f"Unexpected error in _set_app_volume: {e}")

        g_log.info(f"Volume for {app_name} {action} to {volume * 100}%")

    async def _setBrowserVolume(self, app_name, volume, action):
        """
        Adjusts volume for all sink inputs of a browser.
        - If one audio source is different volume level we make sure they are identical upon changing
        """
        try:
            sink_inputs = await self.pulse.sink_input_list()
            app_sink_inputs = [
                si for si in sink_inputs if app_name.lower() in si.proplist.get('application.name', '').lower()
            ]
            if not app_sink_inputs:
                g_log.info(f"No {app_name.capitalize()} browser audio streams found.")
                return

            # Find the minimum current volume among all sink inputs
            min_volume = min(si.volume.values[0] for si in app_sink_inputs)

            for sink_input in app_sink_inputs:
                ### If user really wants the audio levels to be independent then enable this below 
                # min_volume = sink_input.volume.values[0]

                # Calculate the adjustment relative to the minimum volume
                if action.lower() == 'increase':
                    new_volume = min_volume + volume
                elif action.lower() == 'decrease':
                    new_volume = min_volume - volume
                elif action.lower() == 'set':
                    new_volume = volume
                else:
                    g_log.info(f"Unknown volume action: {action}")
                    return

                # Ensure volume stays within valid range
                new_volume = max(0.0, min(1.0, new_volume))

                g_log.info(f"Setting volume for {app_name.capitalize()} to {new_volume * 100}%")
                await self.pulse.volume_set_all_chans(sink_input, new_volume)

        except asyncio.exceptions.InvalidStateError as e:
            g_log.error(f"Invalid state error: {e}")
        except Exception as e:
            g_log.error(f"Unexpected error in _setBrowserVolume: {e}")


    # async def _setBrowserVolume (self, app_name, volume, action):
    #     """ When browser has multiple tabs with audio, they work independantly, so we are adjusting all of them """
    #     try:
    #         sink_inputs = await self.pulse.sink_input_list()
    #         app_sink_inputs = [
    #             si for si in sink_inputs if app_name.lower() in si.proplist.get('application.name', '').lower()
    #         ]
    #         if not app_sink_inputs:
    #             g_log.info("No Brave browser audio streams found.")
    #             return

    #         for sink_input in app_sink_inputs:
    #             current_volume = sink_input.volume.values[0]
    #             if action.lower() == 'increase':
    #                 new_volume = min(1.0, current_volume + volume)
    #             elif action.lower() == 'decrease':
    #                 new_volume = max(0.0, current_volume - volume)
    #             elif action.lower() == 'set':
    #                 new_volume = float(volume)
    #             else:
    #                 g_log.info(f"Unknown volume action: {action}")
    #                 return

    #             new_volume = max(0.0, min(1.0, new_volume))
    #             g_log.info(f"Setting volume for Brave to {new_volume * 100}%")

    #             await self.pulse.volume_set_all_chans(sink_input, new_volume)

    #     except asyncio.exceptions.InvalidStateError as e:
    #         g_log.error(f"Invalid state error: {e}")
    #     except Exception as e:
    #         g_log.error(f"Unexpected error in _set_app_volume: {e}")


    # async def _set_app_volume(self, app_name, volume, action):
    #     if not self.pulse or not self.pulse.connected:
    #         g_log.info("PulseAudio connection not available...")
    #         return
        
    #     app_info = self.apps.get(app_name.lower())

    #     if not app_info:
    #         g_log.info(f"Application '{app_name}' not found.")
    #         return

    #     if hasattr(app_info['info'], 'volume'):
    #         current_volume = app_info['info'].volume.values[0]
    #     else:
    #         g_log.info(f"No volume attribute found for '{app_name}'")
    #         return
        
    #     if action == 'Increase':
    #         volume = min(1.0, current_volume + volume)
    #     elif action == 'Decrease':
    #         volume = max(0.0, current_volume - volume)
    #     elif action == 'Set':
    #         volume = float(volume)
    #     else:
    #         g_log.info(f"Unknown volume action: {action}")
    #         return

    #     # Ensure volume is within valid range
    #     volume = max(0.0, min(1.0, volume))
    #     g_log.info(f"Setting volume for {app_name} to {volume * 100}%")

    #     try:
    #         await self.pulse.volume_set_all_chans(app_info['info'], volume)
    #     except asyncio.exceptions.InvalidStateError as e:
    #         g_log.error(f"Invalid state error: {e}")
    #         g_log.error(f"App: {app_name}, Volume: {volume}, Action: {action} App info: {app_info}")
    #     except Exception as e:
    #         g_log.error(f"Unexpected error in _set_app_volume: {e}")

    #     g_log.info(f"Volume for {app_name} {action} to {volume * 100}%")



    def set_app_mute(self, app_name, command):
        """Mute, Unmute or Toggle the specified app."""
        self.run_coroutine(self._set_app_mute, app_name, command)
    async def _set_app_mute(self, app_name, command):
        if not self.pulse or not self.pulse.connected:
            g_log.info("PulseAudio connection not available...")
            return

        if app_name.lower() in self.browserApps:
            await self._setBrowserMute(app_name, command)
        else:
            app_info = self.apps.get(app_name.lower())

            if not app_info:
                g_log.info(f"App Mute | Application '{app_name}' not found.")
                return

            current_mute = app_info['info'].mute
            command_actions = {
                "mute": lambda: 1,
                "unmute": lambda: 0,
                "toggle": lambda: 0 if current_mute else 1
            }
            mute = command_actions[command.lower()]()
            
            try:
                await self.pulse.sink_input_mute(app_info['info'].index, mute)
                g_log.info(f"App Mute | Application '{app_name}' muted: {mute}")
            except asyncio.exceptions.InvalidStateError as e:
                g_log.error(f"Invalid state error: {e}")
            except Exception as e:
                g_log.error(f"Unexpected error in _set_app_mute: {e}")

    async def _setBrowserMute(self, app_name, command):
        """ When browser has multiple tabs with audio, they work independantly, so we are adjusting all of them """
        try:
            sink_inputs = await self.pulse.sink_input_list()
            app_sink_inputs = [
                si for si in sink_inputs if app_name.lower() in si.proplist.get('application.name', '').lower()
            ]
            if not app_sink_inputs:
                g_log.info(f"No {app_name} browser audio streams found.")
                return

            for sink_input in app_sink_inputs:
                current_mute = sink_input.mute
                command_actions = {
                    "mute": lambda: 1,
                    "unmute": lambda: 0,
                    "toggle": lambda: 0 if current_mute else 1
                }
                mute = command_actions[command.lower()]()

                await self.pulse.sink_input_mute(sink_input.index, mute)
                g_log.info(f"App Mute | {app_name.capitalize()} instance muted: {mute}")

        except asyncio.exceptions.InvalidStateError as e:
            g_log.error(f"Invalid state error: {e}")
        except Exception as e:
            g_log.error(f"Unexpected error in _set_app_mute: {e}")      



    def set_volume(self, device_type, action, volume, source):
        """Set the volume of the specified device."""
        self.run_coroutine(self._set_volume, device_type, action, volume, source)
    async def _set_volume(self, device_type:str, action:str="set", volume:str="25", source:str="default"):
        """ 
        - Currently only seems to be effective for the default device
        - Need to find a way to see results of setting the volume of a specific device if possible (OBS STUDIO? - by listening)
        """
        device_type = device_type.lower()
        device = await self._get_device(device_type, source)

        if not device:
            g_log.info(f"set_volume: ({device_type}) Device not found.")
            return
        
        volume = float(max(0, min(int(volume), 100))) / 100
        current_volume = device.volume.values[0]
        
        if action == 'Increase':
            volume = min(1.0, current_volume + volume)
        elif action == 'Decrease':
            volume = max(0.0, current_volume - volume)
        elif action == 'Set':
            volume = volume
        else:
            g_log.info(f"Unknown volume action: {action}")
            return
        
        g_log.debug(f"Set Volume: {device_type} volume:{volume} - Device: {device}")
        await self.pulse.volume_set_all_chans(device, volume)



    def set_mute(self, device_type, source, mute):
        """Mute, Unmute or Toggle the specified device."""
        self.run_coroutine(self._set_mute, device_type, source, mute)
    async def _set_mute(self, device_type, source, mute):
        device = await self._get_device(device_type, source)
        
        command_actions = {
            "Mute": lambda: 1,
            "Unmute": lambda: 0,
            "Toggle": lambda: 0 if device.mute else 1
        }
        mute = command_actions[mute]()
            
        await self.pulse.mute(device, int(mute))
    
    
    
    def set_default_device(self, device_type, source):
        """Set the default device for the specified type (input or output)."""
        self.run_coroutine(self._set_default_device, device_type, source)
    async def _set_default_device(self, device_type, source):
        device = await self._get_device(device_type, source)
        
        self.defaultDevices[device_type][device.description] = device
        
        await self.pulse.default_set(device)

    

# controller = AudioController()
















    # def increase_volume(self, device_type, source, volume):
    #     if device_type == "output":
    #         device = self.output_devices.get(source) if source != "default" else self._get_current_default_device(device_type)
    #     elif device_type == "input":
    #         device = self.input_devices.get(source) if source != "default" else self._get_current_default_device(device_type)
        
    #     if not device:
    #         g_log.info(f"Device with description '{source}' not found.")
    #         return
        
    #     currentVolume = device.volume.value_flat
    #     self.pulse.volume_set(device, currentVolume.volume.value_flat + volume)


    # def decrease_volume(self, device_type, source, volume):    
    #     if device_type == "output":
    #         device = self.output_devices.get(source) if source != "default" else self._get_current_default_device(device_type)
    #     elif device_type == "input":
    #         device = self.input_devices.get(source) if source != "default" else self._get_current_default_device(device_type)
        
    #     if not device:
    #         g_log.info(f"Device with description '{source}' not found.")
    #         return
        
    #     currentVolume = device.volume.value_flat
    #     self.pulse.volume_set(device, currentVolume.volume.value_flat - volume)