
from contextlib import suppress
from threading import Thread
import asyncio
import pulsectl
import pulsectl_asyncio
from pulsectl import PulseIndexError, PulseError
from pprint import pprint

from audiocontroller import controller

from tpClient import TPClient, g_log
from TPPEntry import TP_PLUGIN_SETTINGS, TP_PLUGIN_ACTIONS, TP_PLUGIN_CONNECTORS, PLUGIN_ID, TP_PLUGIN_INFO, PLUGIN_NAME, PLUGIN_RELEASE_INFO, __version__


## This is working..

class PulseListener:
    """Class to assist with reading volume levels from pulseaudio"""

    def __init__(self):
        self.thread = None
        self.enabled = False
        self.pulse = None
        self.reconnect_delay = 5  # seconds
        

        # Keep last known state (or None) so that we don't repeatedly
        # send messages for every little PA/PW signal


    def start(self):
        """
        Start the PulseListener
        """
        if not self.thread:
            self.thread = Thread(target=self.thread_loop)
            self.thread.start()
            
    def stop(self):
        """
        Stop the PulseListener
        """
        self.enabled = False
        self.thread.join()
        self.thread = None

    def thread_loop(self):
        """
        Start the event loop
        """
        global loop
        g_log.info("Starting the event Loop")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.pulse_loop())
        
        g_log.info("Stopped the event Loop")

    async def listen(self):
        """
        Async to connect to pulse and listen for events
        """
        try:
            async with pulsectl_asyncio.PulseAsync('eventListener') as pulse:
                self.pulse = pulse
                async for event in pulse.subscribe_events('all'):
                    await self.handle_events(event)

        except pulsectl.pulsectl.PulseDisconnected:
            g_log.info("Pulse has gone away")
        except pulsectl.pulsectl.PulseError as e:
            g_log.error(f"Pulse error {e}")
        finally:
            g_log.info("Disconnected from PulseAudio")

    async def pulse_loop(self):
        """
        Listen on event loop with reconnection logic
        """
        while True:
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
            # Assuming `pulse` is accessed through `self.pulse` in your class
            #sink_input_Info = await self.pulse.sink_input_info(index)
            #app_name = sink_input_Info.proplist.get('application.name', '').lower()
            
            sink_input_Info, app_name = await self.fetch_thingy('sink_input', index)

            if app_name in controller.apps:
                # Update existing app information
                controller.apps[app_name]['info'] = sink_input_Info
                controller.apps[app_name]['volume'] = sink_input_Info.volume.values[0]

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
                controller.apps[app_name] = {
                    'index': index,
                    'properties': sink_input_Info.proplist,
                    'info': sink_input_Info,
                    'volume': sink_input_Info.volume.values[0]
                }

                # Create new states
                states = [
                    {
                        "id": PLUGIN_ID + f".createState.{app_name}.muteState",
                        "desc": f"{app_name} Mute State",
                        "parentGroup": "Audio process state",
                        "value": "unmuted" if sink_input_Info.mute == 0 else "muted"
                    },
                    {
                        "id": PLUGIN_ID + f".createState.{app_name}.volume",
                        "desc": f"{app_name} Volume",
                        "parentGroup": "Audio process state",
                        "value": str(round(sink_input_Info.volume.values[0]))
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

            g_log.info(f"EVENT: SinkInput Name: {sink_input_Info.name}, Muted: {sink_input_Info.mute}, Volume: {sink_input_Info.volume.values[0]}, index {sink_input_Info.index}")

        except pulsectl.pulsectl.PulseIndexError:
            g_log.error(f"Error: Sink input with index {index} not found.")
        except Exception as e:
            g_log.error(f"Sink Input Error {e}")


    async def fetch_thingy(self, facility, index):
        if facility == 'sink':
            item_info = await self.pulse.sink_info(index)
            item_name = item_info.name
        elif facility == 'source':
            item_info = await self.pulse.source_info(index)
            item_name = item_info.name
        elif facility == 'sink_input':
            item_info = await self.pulse.sink_input_info(index)
            item_name = item_info.proplist.get('application.name', '').lower()
        elif facility == 'source_output':
            item_info = await self.pulse.source_output_info(index)
            item_name = item_info.name
        else:
            raise ValueError(f"Unsupported facility: {facility}")

        return item_info, item_name

        

    async def process_sink(self, index):
        """
        When a sink event is received, process the sink information
        """
        try:
            sink_info, sink_name = await self.fetch_thingy('sink', index)
            # sink_info = await self.pulse.sink_info(index)
            # sink_name = sink_info.name

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

        except pulsectl.pulsectl.PulseIndexError:
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
            source_info, source_name = await self.fetch_thingy('source', index)

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
            
            app_connector_id = (
                f"pc_{TP_PLUGIN_INFO['id']}_"
                f"{TP_PLUGIN_CONNECTORS['Windows Audio']['id']}|"
                f"{TP_PLUGIN_CONNECTORS['Windows Audio']['data']['deviceType']['id']}=Input|"
                f"{TP_PLUGIN_CONNECTORS['Windows Audio']['data']['deviceOption']['id']}=default"
            )
            if app_connector_id in TPClient.shortIdTracker:
                TPClient.shortIdUpdate(
                    TPClient.shortIdTracker[app_connector_id],
                    round(source_info.volume.values[0]*100)
                )
                
            g_log.info(f"EVENT: Source Name: {source_name}, Muted: {source_info.mute}, Volume: {source_info.volume.values[0]}")
        except pulsectl.pulsectl.PulseOperationFailed as e:
            g_log.error(f"Failed to retrieve source list: {e}")
        except Exception as e:
            g_log.error(f"Source Info Error {e}")



    # async def processChanges(self, facility, index):
    #     """ 
    #     Get the details of the device after an event
    #     """
    #     if facility == 'sink':
    #         await self.process_sink(index)

    #     elif facility == 'source':
    #         await self.process_source(index)

    #     elif facility == 'sink_input':
    #         await self.process_sink_input(index)
 
    #     elif facility == 'source_output':
    #         for output in await self.pulse.source_output_list():
    #             if output.index == index:
    #                 g_log.debug(f"EVENT: SourceOutput Name: {output.name}, Muted: {output.mute}, Volume: {output.volume.values[0]}")
    #                 break

    #     elif facility == 'server':
    #         server_info = await self.pulse.server_info()
    #         g_log.info(f"EVENT: Server Name: {server_info}")
            
    #     else:
    #         g_log.info(f"Unknown facility: {facility}")
            


    async def handle_events(self, ev):
        """
        Handle PulseAudio events
        """
        g_log.debug(f"Event received: {ev}")
        
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
                        pass

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
                        if ev.index in controller.output_devices:
                            item_info = controller.output_devices.pop(ev.index)
                            item_name = item_info.name
                    case 'source':
                        if ev.index in controller.input_devices:
                            item_info = controller.input_devices.pop(ev.index)
                            item_name = item_info.name
                    case 'sink_input':
                        if ev.index in controller.apps:
                            item_info = controller.apps.pop(ev.index)
                            item_name = item_info.proplist.get('application.name', '').lower()
                    case _:
                        g_log.info(f"Unhandled removal event: {ev}")

                if item_info and item_name:
                    print(f"Removal event for {ev.facility}: {item_name} - {item_info}")
                    # Your logic for handling removal events using item_info and item_name
                else:
                    g_log.warning(f"Failed to fetch details for removal event: {ev}")

                
        


if __name__ == "__main__":
    pulseListener = PulseListener()
    pulseListener.start()















# def stateUpdater(id, description, value, parentGroup=None):
#     TPClient.stateUpdate(id, description, value)

# class PulseAudioEventHandler:
#     def __init__(self):
#         self.last_processed_index = None

#     async def handle_sink_input_change(self, index):
#         # Check if this index was recently processed to debounce rapid updates
#         if index == self.last_processed_index:
#             return
        
#         try:
#             async with pulsectl_asyncio.PulseAsync('event-printer') as pulse:
#                 sink_input_info = await pulse.sink_input_info(index)
#                 print(f"Sink input info: {sink_input_info.volume}, Muted: {sink_input_info.mute}")
                
#                 # Update the last processed index
#                 self.last_processed_index = index
#         except pulsectl_asyncio.PulseError as e:
#             print(f"Error retrieving sink input info: {e}")

#     async def listen(self):
#         async with pulsectl_asyncio.PulseAsync('event-printer') as pulse:
#             async for event in pulse.subscribe_events('all'):
#                 print(f"Pulse event received: {event}")

#                 if event.facility == 'sink_input':
#                     if event.t == 'new':
#                         print("A new sink input has been created.")
#                         # Handle new sink input
#                     elif event.t == 'change':
#                         print("A sink input has changed.")
#                         # Handle changes in sink input (e.g., volume or mute state change)
#                         asyncio.create_task(self.handle_sink_input_change(event.index))
#                     elif event.t == 'remove':
#                         print("A sink input has been removed.")
#                         # Handle removal of sink input

#     async def main(self):
#         # Run listen() coroutine in task to allow cancelling it
#         listen_task = asyncio.create_task(self.listen())

#         # Wait for listen task to complete
#         await listen_task

# if __name__ == "__main__":
#     handler = PulseAudioEventHandler()
#     asyncio.run(handler.main())



# import pulsectl
# import threading
# import queue
# import time

# class PulseAudioEventHandler:
#     def __init__(self):
#         self.event_queue = queue.Queue()
#         self.stop_event = threading.Event()
        
#         self.pulse = pulsectl.Pulse('event-listener')
#         self.pulse.event_mask_set('all')
#         self.pulse.event_callback_set(self.event_callback)
        
#         self.worker_thread = threading.Thread(target=self.worker)
#         self.worker_thread.start()

#     def event_callback(self, ev):
#         print(f"Event received: {ev}")
#         print(f"Event type: {ev.t}")
#         print(f"Event facility: {ev.facility}")
#         print(f"Event index: {ev.index}")
        
#         # Enqueue the event information
#         self.event_queue.put(ev)

#     def worker(self):
#         worker_pulse = pulsectl.Pulse('worker')
        
#         while not self.stop_event.is_set():
#             try:
#                 ev = self.event_queue.get(timeout=1)
#             except queue.Empty:
#                 continue
            
#             if ev.t == pulsectl.PulseEventTypeEnum.change and ev.facility == pulsectl.PulseEventFacilityEnum.sink_input:
#                 print("A sink input has changed.")
#                 # Retrieve the sink input info object
#                 try:
#                     sink_input_info = worker_pulse.sink_input_info(ev.index)
#                     print(f"Sink input info: {sink_input_info.volume}")
#                 except pulsectl.PulseError as e:
#                     print(f"Error retrieving sink input info: {e}")

#     def start(self):
#         # Start the event listener
#         self.pulse.event_listen()

#     def stop(self):
#         # Signal the worker thread to stop
#         self.stop_event.set()
#         self.worker_thread.join()

# if __name__ == "__main__":
#     handler = PulseAudioEventHandler()
#     handler.start()
    
#     try:
#         while True:
#             time.sleep(1)
#     except KeyboardInterrupt:
#         pass
#     finally:
#         handler.stop()
