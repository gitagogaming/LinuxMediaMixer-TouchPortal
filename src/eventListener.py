import threading
import asyncio
import pulsectl_asyncio

from audiocontroller import AudioController
from findIcon import find_icon_path
from tpClient import TPClient, g_log
from TPPEntry import TP_PLUGIN_CONNECTORS, PLUGIN_ID, TP_PLUGIN_INFO, __version__


class PulseListener:
    """Class to assist with reading volume levels from pulseaudio"""

    def __init__(self, controller:AudioController):
        self.thread = None
        self.enabled = False
        self.pulse = None
        self.reconnect_delay = 5
        self.controller = controller
        self.stop_event = threading.Event()

    def start(self):
        """
        Start the PulseListener
        """
        if not self.thread:
            self.stop_event.clear()
            self.thread = threading.Thread(target=self.thread_loop)
            self.thread.start()

    def stop(self):
        """
        Stop the PulseListener
        """
        self.stop_event.set()  # Signal the thread to stop
        if self.thread:
            self.thread.join(timeout=5)  # Wait up to 10 seconds for the thread to finish
            if self.thread.is_alive():
                g_log.warning("Thread did not terminate in time, manual intervention may be required")
            self.thread = None
        g_log.info("PulseListener Stopped")

    def thread_loop(self):
        """
        Start the event loop
        """
        global loop
        g_log.info("Starting the event Loop")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self.pulse_loop())
        except asyncio.CancelledError:
            g_log.info("Event loop was cancelled")
        finally:
            loop.close()
            g_log.info("Stopped the event Loop")
            
    async def listen(self):
        """
        Async to connect to pulse and listen for events
        """
        try:
            async with pulsectl_asyncio.PulseAsync('eventListener') as pulse:
                self.pulse = pulse
                async for event in pulse.subscribe_events('all'):
                    if self.stop_event.is_set():
                        break  # Exit the loop if stop_event is set
                    await self.handle_events(event)

        except pulsectl_asyncio.pulsectl.PulseDisconnected:
            g_log.info("Pulse has gone away")
        except pulsectl_asyncio.pulsectl.PulseError as e:
            g_log.error(f"Pulse error {e}")
        finally:
            g_log.info("Disconnected from PulseAudio")

    async def pulse_loop(self):
        """
        Listen on event loop with reconnection logic
        """
        while not self.stop_event.is_set():
            try:
                await self.listen()
            except Exception as e:
                g_log.error(f"Error in pulse loop: {e}")
                g_log.info(f"Attempting to reconnect in {self.reconnect_delay} seconds...")
                await asyncio.sleep(self.reconnect_delay)
                
       
            
    async def process_sink_input(self, index):
        """
        When a sink input event is received, process the sink input information
        """
        try:
            sink_input_Info, app_name = await self.fetch_info('sink_input', index)
            g_log.debug(f"Process Sink Input | {sink_input_Info}")

            if app_name in self.controller.apps:
                # Update existing app information
                self.controller.apps[app_name]['info'] = sink_input_Info
                self.controller.apps[app_name]['volume'] = sink_input_Info.volume.values[0]

                # Update states
                states = [
                    {
                        "id": PLUGIN_ID + f".createState.{app_name.lower()}.muteState",
                        "value": "unmuted" if sink_input_Info.mute == 0 else "muted"
                    },
                    {
                        "id": PLUGIN_ID + f".createState.{app_name.lower()}.volume",
                        "value": str(round(sink_input_Info.volume.values[0]*100))
                    }
                ]
                TPClient.stateUpdateMany(states)
            else:
                # New app/sink found, add to controller
                g_log.debug(f"New app/sink found: {app_name}")
                self.controller.apps[app_name] = {
                    'index': index,
                    'properties': sink_input_Info.proplist,
                    'info': sink_input_Info,
                    'volume': sink_input_Info.volume.values[0]
                }

                app_icon = find_icon_path(sink_input_Info.proplist)
                
                # Create new states
                states = [
                    {
                        "id": PLUGIN_ID + f".createState.{app_name.lower()}.muteState",
                        "desc": f"{app_name.lower()} Mute State",
                        "parentGroup": "Audio process state",
                        "value": "unmuted" if sink_input_Info.mute == 0 else "muted"
                    },
                    {
                        "id": PLUGIN_ID + f".createState.{app_name.lower()}.volume",
                        "desc": f"{app_name.lower()} Volume",
                        "parentGroup": "Audio process state",
                        "value": str(round(sink_input_Info.volume.values[0]))
                    },
                    {
                        "id": PLUGIN_ID + f".createState.{app_name.lower()}.icon",
                        "desc": f"{app_name.lower()} Icon",
                        "parentGroup": "Audio process state",
                        "value": app_icon if app_icon != None else ""
                    }
                ]
                TPClient.createStateMany(states)

            ## attempting to update the connector regardless if new or not..
            app_connector_id = f"pc_{TP_PLUGIN_INFO['id']}_{TP_PLUGIN_CONNECTORS['APP control']['id']}|{TP_PLUGIN_CONNECTORS['APP control']['data']['appchoice']['id']}={app_name.lower()}"
            if app_connector_id in TPClient.shortIdTracker:
                TPClient.shortIdUpdate(
                    TPClient.shortIdTracker[app_connector_id],
                    round(sink_input_Info.volume.values[0]*100)
                )

            TPClient.choiceUpdate(PLUGIN_ID + ".connector.APPcontrol.data.slidercontrol", list(self.controller.apps.keys()))
            
            g_log.info(f"EVENT: SinkInput Name: {sink_input_Info.name}, Muted: {sink_input_Info.mute}, Volume: {sink_input_Info.volume.values[0]}, index {sink_input_Info.index}")
        except pulsectl_asyncio.pulsectl.PulseIndexError:
            g_log.error(f"Error: Sink input with index {index} not found.")
        except Exception as e:
            g_log.error(f"Sink Input Error {e}")


    async def fetch_info(self, facility, index):
        match facility:
            case 'sink':
                item_info = await self.pulse.sink_info(index)
                item_name = item_info.name
            case 'source':
                item_info = await self.pulse.source_info(index)
                item_name = item_info.description
            case 'sink_input':
                item_info = await self.pulse.sink_input_info(index)
                item_name = item_info.proplist.get('application.name', '').lower()
            case 'source_output':
                item_info = await self.pulse.source_output_info(index)
                item_name = item_info.name
            case __:
                raise ValueError(f"Unsupported facility: {facility}")
                
        return item_info, item_name

        

    async def process_sink(self, index):
        """
        When a sink event is received, process the sink information
        """
        try:
            sink_info, sink_name = await self.fetch_info('sink', index)

            states = [
                {
                    "id": PLUGIN_ID + f".sink.{sink_name}.volume",
                    "desc": f"{sink_name} Volume",
                    "parentGroup": "Audio sink state",
                    "value": str(round(sink_info.volume.values[0]*100))
                },
                {
                    "id": PLUGIN_ID + f".sink.{sink_name}.muteState",
                    "desc": f"{sink_name} Mute State",
                    "parentGroup": "Audio sink state",
                    "value": "unmuted" if sink_info.mute == 0 else "muted"
                }
            ]
            TPClient.createStateMany(states)
            
            app_connector_id = (
                f"pc_{TP_PLUGIN_INFO['id']}_"
                f"{TP_PLUGIN_CONNECTORS['Windows Audio']['id']}|"
                f"{TP_PLUGIN_CONNECTORS['Windows Audio']['data']['deviceType']['id']}=Output|"
                f"{TP_PLUGIN_CONNECTORS['Windows Audio']['data']['deviceOption']['id']}=default"
            )
            if app_connector_id in TPClient.shortIdTracker:
                TPClient.shortIdUpdate(
                    TPClient.shortIdTracker[app_connector_id],
                    round(sink_info.volume.values[0]*100)
                )
  
            g_log.info(f"EVENT: Sink Name: {sink_name}, Muted: {sink_info.mute}, Volume: {sink_info.volume.values[0]}")
        except pulsectl_asyncio.pulsectl.PulseIndexError:
            g_log.error(f"Error: Sink with index {index} not found.")
        except Exception as e:
            g_log.error(f"Sink Info Error {e}")



    async def process_source(self, index):
        """ 
        When a source event is received, process the source information
        """
        try:
            # Iterate through source list to find the specific source by index
            # source_info = await self.pulse.source_info(index)
            # source_name = source_info.name
            source_info, source_name = await self.fetch_info('source', index)

            states = [
                {
                    "id": PLUGIN_ID + f".createState.{source_name}.volume",
                    "desc": f"{source_name} Volume",
                    "parentGroup": "Audio source state",
                    "value": str(round(source_info.volume.values[0]*100))
                },
                {
                    "id": PLUGIN_ID + f".createState.{source_name}.muteState",
                    "desc": f"{source_name} Mute State",
                    "parentGroup": "Audio source state",
                    "value": "unmuted" if source_info.mute == 0 else "muted"
                }
            ]
            TPClient.createStateMany(states)
            # Construct the initial app_connector_id
            app_connector_id = (
                f"pc_{TP_PLUGIN_INFO['id']}_"
                f"{TP_PLUGIN_CONNECTORS['Windows Audio']['id']}|"
                f"{TP_PLUGIN_CONNECTORS['Windows Audio']['data']['deviceType']['id']}=Input|"
                f"{TP_PLUGIN_CONNECTORS['Windows Audio']['data']['deviceOption']['id']}={source_name}"
            )

            # Check and update if the initial app_connector_id exists in TPClient.shortIdTracker
            if app_connector_id in TPClient.shortIdTracker:
                TPClient.shortIdUpdate(
                    TPClient.shortIdTracker[app_connector_id],
                    round(source_info.volume.values[0] * 100)
                )

            # Check if default_input description matches source_name
            default_input = self.controller.defaultDevices['input']
            if default_input.description == source_name:
                # Set the Default Connector to match
                updated_app_connector_id = app_connector_id.rsplit('=', 1)[0] + "=default"

                if updated_app_connector_id in TPClient.shortIdTracker:
                    TPClient.shortIdUpdate(
                        TPClient.shortIdTracker[updated_app_connector_id],
                        round(source_info.volume.values[0] * 100)
                    )

            
            # app_connector_id = (
            #     f"pc_{TP_PLUGIN_INFO['id']}_"
            #     f"{TP_PLUGIN_CONNECTORS['Windows Audio']['id']}|"
            #     f"{TP_PLUGIN_CONNECTORS['Windows Audio']['data']['deviceType']['id']}=Input|"
            #     f"{TP_PLUGIN_CONNECTORS['Windows Audio']['data']['deviceOption']['id']}={source_name}"
            # )
            
            # if app_connector_id in TPClient.shortIdTracker:
            #     TPClient.shortIdUpdate(
            #         TPClient.shortIdTracker[app_connector_id],
            #         round(source_info.volume.values[0]*100)
            #     )
            
            # default_input = await controller._get_current_default_device('input')
            # if default_input.description == source_name:
            #     app_connector_id = (
            #     f"pc_{TP_PLUGIN_INFO['id']}_"
            #     f"{TP_PLUGIN_CONNECTORS['Windows Audio']['id']}|"
            #     f"{TP_PLUGIN_CONNECTORS['Windows Audio']['data']['deviceType']['id']}=Input|"
            #     f"{TP_PLUGIN_CONNECTORS['Windows Audio']['data']['deviceOption']['id']}=default"
            #     )
            
            #     if app_connector_id in TPClient.shortIdTracker:
            #         TPClient.shortIdUpdate(
            #             TPClient.shortIdTracker[app_connector_id],
            #             round(source_info.volume.values[0]*100)
            #         )
                  
            g_log.info(f"EVENT: Source Name: {source_name}, Muted: {source_info.mute}, Volume: {source_info.volume.values[0]}")
        except pulsectl_asyncio.pulsectl.PulseOperationFailed as e:
            g_log.error(f"Failed to retrieve source list: {e}")
        except Exception as e:
            g_log.error(f"Source Info Error {e}")


    async def handle_events(self, ev):
        """
        Handle PulseAudio events
        """
        # g_log.debug(f"Event received: {ev}")
        
        ## we still need to determine if its a change/new/remove so we can remove things as needed.. 
        ## when things chagne, if its not avaialble it creates it so we only need to worry about removals
        
        match ev.t:
            ### If new or change, we process it the same way
            case 'new' | 'change':
                match ev.facility:
                    case 'sink':
                        # await self.processChanges('sink', ev.index)
                        await self.process_sink(ev.index)

                    case 'source':
                        # await self.processChanges('source', ev.index)
                        await self.process_source(ev.index)

                    case 'server':
                        # await self.processChanges('server', ev.index)
                        server_info = await self.pulse.server_info()
                        g_log.info(f"EVENT: Server Name: {server_info}")

                    case 'source_output':
                        # await self.processChanges('source_output', ev.index)
                        for output in await self.pulse.source_output_list():
                            if output.index == ev.index:
                                g_log.debug(f"EVENT: SourceOutput Name: {output.name}, Muted: {output.mute}, Volume: {output.volume.values[0]}")
                                break
                        
                    case 'sink_input':
                        # await self.processChanges('sink_input', ev.index)
                        await self.process_sink_input(ev.index)

                    case 'client':
                        return
                        # pass

                    case 'card':
                        g_log.info(f"Card Event: {ev} - Nothing done here....")

                    case _:
                        g_log.info(f"Unhandled event: {ev}")
                        pass
                    
            ## If its a removal, we need to remove the sink/source/input from the controller      
            case 'remove':
                item_info = None
                item_name = None

                match ev.facility:
                    case 'sink':
                        if ev.index in self.controller.output_devices:
                            item_info = self.controller.output_devices.pop(ev.index)
                            item_name = item_info.name
                    case 'source':
                        if ev.index in self.controller.input_devices:
                            item_info = self.controller.input_devices.pop(ev.index)
                            item_name = item_info.name
                    case 'sink_input':
                        for app in list(self.controller.apps.keys()):
                            if self.controller.apps[app]['info'].index == ev.index:
                                item_info = self.controller.apps.pop(app)
                                item_name = item_info['info'].proplist.get('application.name', '').lower()
                                
                                if TPClient.isConnected():
                                    TPClient.choiceUpdate(PLUGIN_ID + ".connector.APPcontrol.data.slidercontrol", list(self.controller.apps.keys()))
                    case _:
                        g_log.info(f"Unhandled removal event: {ev}")
                        return

                if item_info and item_name:
                    ## send upadte to TP for some sort of event? seems not needed i guess?
                    g_log.info(f"\nEVENT | Removed {str(ev.facility)}: {item_name} - {item_info}")
                    # Your logic for handling removal events using item_info and item_name
                else:
                    g_log.warning(f"Failed to fetch details for removal event: {ev}")

                
        


# if __name__ == "__main__":
#     pulseListener = PulseListener()
#     pulseListener.start()

