
import os
import base64

def find_icon_path(icon_name):
    icon_name = icon_name.get('application.icon_name', None)
    if icon_name:
        icon_path = f"/usr/share/icons/hicolor/128x128/apps/{icon_name}.png"
        expanded_path = os.path.expanduser(icon_path)
        if os.path.exists(expanded_path):
            icon_base64 = convert_icon_to_base64(expanded_path)
            return icon_base64
    return None

def convert_icon_to_base64(icon_path):
    with open(icon_path, "rb") as icon_file:
        icon_data = icon_file.read()
        base64_icon = base64.b64encode(icon_data).decode('utf-8')
        return base64_icon
    

# print(find_icon_path("strawberry"))