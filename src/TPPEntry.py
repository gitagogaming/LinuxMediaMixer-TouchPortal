PLUGIN_ID = "gitago.mediaMixer"  
PLUGIN_NAME = "LinuxMediaMixer"
PLUGIN_ICON = "LinuxMediaMixer_logo_26px.png"
PLUGIN_FOLDER = "LinuxMediaMixer"

GITHUB_USER_NAME = "GitagoGaming"
GITHUB_PLUGIN_NAME = "LinuxMediaMixer-TouchPortal-Plugin"  ## Name of Github Repo
PLUGIN_RELEASE_INFO = {} # This will be updated by the update_check.py script

__version__ = 101

TP_PLUGIN_INFO = {
    "sdk": 6,
    'version': __version__,
    "name": PLUGIN_NAME,
    "id": PLUGIN_ID,
        "plugin_start_cmd_linux": f"sh %TP_PLUGIN_FOLDER%{PLUGIN_NAME}/start.sh {PLUGIN_NAME}_Plugin",
    "configuration": {
        "colorDark": "#222423",
        "colorLight": "#43a047"
    },
}

TP_PLUGIN_SETTINGS = {
    'BrowserApps': {
        'name': "Browser Apps",
        'type': "text",
        'default': "brave, firefox, chrome",
        'readOnly': False,
        'value': None  
    }
 }

TP_PLUGIN_CATEGORIES = {
    "main": {
        "id": PLUGIN_ID + ".main",
        "name": "MediaMixer Main Category",
        "imagepath": f"%TP_PLUGIN_FOLDER%{PLUGIN_NAME}\\{PLUGIN_NAME}_Logo_26px.png"
    }
}


TP_PLUGIN_ACTIONS = {
    'AppMute': {
        'category': "main",
        'id': PLUGIN_ID + ".act.Mute/Unmute",
        'name': 'Volume Mixer: Mute/Unmute process volume',
        'prefix': TP_PLUGIN_CATEGORIES['main']['name'],
        'type': "communicate",
        'tryInline': True,
        'description': "Mute/Unmute process volume",
        'format': "$[1] $[2] app",
        "doc": "Mute/Unmute process volume",
        'data': {
            'appChoice': {
                'id': PLUGIN_ID + ".act.Mute/Unmute.data.process",
                'type': "choice",
                'label': "process list",
                'default': "",
                "valueChoices": []
                
            },
            'OptionList': {
                'id': PLUGIN_ID + ".act.Mute/Unmute.data.choice",
                'type': "choice",
                'label': "Option choice",
                'default': "Toggle",
                "valueChoices": [
                    "Mute",
                    "Unmute",
                    "Toggle"
                ]
            },
        }
    },
    'Inc/DecrVol': {
        'category': "main",
        'id': PLUGIN_ID + ".act.Inc/DecrVol",
        'name': 'Adjust App Volume',
        'prefix': TP_PLUGIN_CATEGORIES['main']['name'],
        'type': "communicate",
        'tryInline': True,
        'format': "$[2] $[1] volume$[3]",
        "doc": "Increase/Decrease process volume",
        "hasHoldFunctionality": True,
        'data': {
            'AppChoice': {
                'id': PLUGIN_ID + ".act.Inc/DecrVol.data.process",
                'type': "choice",
                'label': "process list",
                'default': "",
                "valueChoices": []   
            },
            'OptionList': {
                'id': PLUGIN_ID + ".act.Inc/DecrVol.data.choice",
                'type': "choice",
                'label': "Option choice",
                'default': "Increase",
                "valueChoices": [
                    "Increase",
                    "Decrease",
                    "Set"
                ]
            },
            'Volume': {
                'id': PLUGIN_ID + ".act.Inc/DecrVol.data.Volume",
                'type': "text",
                'label': "Volume",
                "default": "10"
            },
        }
    },
    'setDeviceVolume': {
        'category': "main",
        'id': PLUGIN_ID + ".act.changeDeviceVolume",
        'name': 'Set Device Volume',
        'prefix': TP_PLUGIN_CATEGORIES['main']['name'],
        'type': "communicate",
        'tryInline': True,
        'format': f"$[2] $[1]volume to$[3]% for $[4] ",
        "doc": "Change Default Audio Devices",
        "hasHoldFunctionality": True,
        'data': {
            'deviceType': {
                'id': PLUGIN_ID + ".act.changeDeviceVolume.deviceType",
                'type': "choice",
                'label': "device type",
                'default': "Pick One",
                "valueChoices": [
                    "Output",
                    "Input"
                ]
            },
            'deviceOption': {
                'id': PLUGIN_ID + ".act.changeDeviceVolume.choice",
                'type': "choice",
                'label': "Device choice list",
                'default': "Pick One",
                "valueChoices": [
                    "Set",
                    "Increase",
                    "Decrease"
                ]
            },
            'Volume': {
                'id': PLUGIN_ID + ".act.changeDeviceVolume.Volume",
                'type': "text",
                'label': "Volume",
                "default": "25"
            },
            'deviceOption': {
                'id': PLUGIN_ID + ".act.changeDeviceVolume.devices",
                'type': "choice",
                'label': "Device choice list",
                'default': "default",
                "valueChoices": ["default"]
            },
        }
    },
    'setDeviceMute': {
        'category': "main",
        'id': PLUGIN_ID + ".act.changeDeviceMute",
        'name': 'Mute/Unmute Device',
        'prefix': TP_PLUGIN_CATEGORIES['main']['name'],
        'type': "communicate",
        'tryInline': True,
        'format': "$[3] $[1] $[2] Device",
        "doc": "Mute/Unmute Default Audio Devices",
        'data': {
            'deviceType': {
                'id': PLUGIN_ID + ".act.changeDeviceMute.deviceType",
                'type': "choice",
                'label': "device type",
                'default': "Pick One",
                "valueChoices": [
                    "Output",
                    "Input"
                ]
            },
            'deviceOption': {
                'id': PLUGIN_ID + ".act.changeDeviceMute.devices",
                'type': "choice",
                'label': "Device choice list",
                'default': "",
                "valueChoices": []
            },
            'OptionList': {
                'id': PLUGIN_ID + ".act.changeDeviceMute.choice",
                'type': "choice",
                'label': "Option choice",
                'default': "Toggle",
                "valueChoices": [
                    "Mute",
                    "Unmute",
                    "Toggle"
                ]
            },
        }     
    },
    'ChangeOut/Input': {
        'category': "main",
        'id': PLUGIN_ID + ".act.ChangeAudioOutput",
        'name': 'Audio Output/Input Device Switcher',
        'prefix': TP_PLUGIN_CATEGORIES['main']['name'],
        'type': "communicate",
        'tryInline': True,
        'format': "Change audio device$[1]$[2]",
        "doc": "Change Default Audio Devices",
        'data': {
            'optionSel': {
                'id': PLUGIN_ID + ".act.ChangeAudioOutput.choice",
                'type': "choice",
                'label': "process list",
                'default': "Pick One",
                "valueChoices": [
                    "Output",
                    "Input"
                ]
                
            },
            'deviceOption': {
                'id': PLUGIN_ID + ".act.ChangeAudioOutput.data.device",
                'type': "choice",
                'label': "Device choice list",
                'default': "",
                "valueChoices": []
            },
            'setType': {
                'id': PLUGIN_ID + ".act.ChangeAudioOutput.setType",
                'type': "choice",
                'label': "Set audio device type",
                'default': "Default",
                "valueChoices": [
                    "Default",
                    "Communications"
                ]
                
            },
        }
    },
}

TP_PLUGIN_STATES = {
    # "shop_timestamp": {
    #     "id": PLUGIN_ID + ".shop.timestamp",
    #     "type": "text",
    #     "desc": "Timestamp of the Shop Order",
    #     "default": "",
    #     "category": "shop"
    # }
    'FocusedAPP': {
        'category': "main",
        'id': PLUGIN_ID + ".state.currentFocusedAPP",
        'type': "text",
        'desc': "Volume Mixer: current focused app",
        'default': ""
    },
}



TP_PLUGIN_CONNECTORS = {
    "APP control": {
        "id": PLUGIN_ID + ".connector.APPcontrol",
        "name": "Volume Mixer: APP Volume slider",
        "format": "Control volume for $[1]",
        "label": "control app Volume",
        "data": {
            "appchoice": {
                "id": PLUGIN_ID + ".connector.APPcontrol.data.slidercontrol",
                "type": "choice",
                "label": "APP choice list for APP control slider",
                "default": "",
                "valueChoices": []
            }
        }
    },
    "Windows Audio": {
        "id": PLUGIN_ID + ".connector.WinAudio",
        "name": "Volume Mixer: Linux Volume Slider",
        "format": "Control Default Audio for $[1] device and $[2]",
        "label": "Control Linux Volume",
        "data": {
            'deviceType': {
                'id': PLUGIN_ID + ".connector.WinAudio.deviceType",
                'type': "choice",
                'label': "device type",
                'default': "Pick One",
                "valueChoices": [
                    "Output",
                    "Input"
                ]
            },
            'deviceOption': {
                'id': PLUGIN_ID + ".connector.WinAudio.devices",
                'type': "choice",
                'label': "Device choice list",
                'default': "default",
                "valueChoices": ["default"]
            },
        }
    }
}

TP_PLUGIN_EVENTS = {
    "0": {
        'id': PLUGIN_ID + ".event.newDonation",
        'name':"Kofi | New Donation",
        'category': "main",
        "format":"When receiving a new donation $val",
        "type":"communicate",
        "valueType":"choice",
        "valueChoices": [
        "True"
        ],
    "valueStateId": PLUGIN_ID + ".state.newDonation",
    }


}