
from TouchPortalAPI import tppbuild
from TPPEntry import PLUGIN_NAME, PLUGIN_FOLDER, PLUGIN_ICON, __version__



#PLUGIN_MAIN = f"{PLUGIN_NAME}.py"
PLUGIN_MAIN = "main.py"



PLUGIN_EXE_NAME = f"{PLUGIN_NAME}_Plugin"


PLUGIN_EXE_ICON = rf"{PLUGIN_ICON}"


PLUGIN_ENTRY = "TPPEntry.py"


PLUGIN_ENTRY_INDENT = 2


PLUGIN_ROOT = PLUGIN_FOLDER


PLUGIN_ICON =  rf"{PLUGIN_ICON}"


OUTPUT_PATH = "../"


PLUGIN_VERSION = str(__version__)


ADDITIONAL_FILES = [
    "start.sh"
    ]

if PLUGIN_ICON != "":
    ADDITIONAL_FILES.append(PLUGIN_ICON)


ADDITIONAL_TPPSDK_ARGS = []

ADDITIONAL_PYINSTALLER_ARGS = [
    "--log-level=WARN",
    #  "--noconsole"
]

# validateBuild()

if __name__ == "__main__":
    tppbuild.runBuild()
