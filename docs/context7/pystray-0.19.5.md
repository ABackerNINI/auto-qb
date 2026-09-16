> 版本: 0.19.5 | 来源: Context7 MCP | 抓取日期: 2026-09-17

### Create a System Tray Icon with a Menu

Source: https://github.com/moses-palmer/pystray/blob/master/_autodocs/README.md

Adds a menu with interactive items to the system tray icon.

```python
from pystray import Icon, Menu, MenuItem
from PIL import Image

def create_icon():
    return Image.new('RGB', (64, 64), color='white')

menu = Menu(
    MenuItem('Open', lambda icon, item: print('open')),
    MenuItem('Exit', lambda icon, item: icon.stop())
)

icon = Icon('myapp', icon=create_icon(), menu=menu)
icon.run()
```

--------------------------------

### Displaying Notifications

Source: https://github.com/moses-palmer/pystray/blob/master/_autodocs/examples.md

Demonstrates how to trigger system notifications from a pystray menu item.

```python
from pystray import Icon, Menu, MenuItem
from PIL import Image

def create_icon():
    return Image.new('RGB', (64, 64), color='white')

def show_notification(icon, item):
    icon.notify('This is a notification!', title='My App')

def remove_notification(icon, item):
    icon.remove_notification()

menu = Menu(
    MenuItem('Show', show_notification),
    MenuItem('Hide', remove_notification),
    Menu.SEPARATOR,
    MenuItem('Exit', lambda icon, item: icon.stop())
)

icon = Icon('myapp', icon=create_icon(), menu=menu)
icon.run()
```

--------------------------------

### Detect Platform Capabilities for System Tray

Source: https://github.com/moses-palmer/pystray/blob/master/_autodocs/examples.md

Uses Icon class constants to conditionally add menu items based on platform support for menus, notifications, and default actions.

```python
from pystray import Icon, Menu, MenuItem
from PIL import Image

def create_icon():
    return Image.new('RGB', (64, 64), color='white')

menu_items = [
    MenuItem('Show Features', lambda icon, item: show_capabilities(icon))
]

if Icon.HAS_MENU:
    menu_items.extend([
        Menu.SEPARATOR,
        MenuItem('Menu Item', lambda icon, item: None)
    ])

if Icon.HAS_NOTIFICATION:
    menu_items.append(
        MenuItem('Notify', lambda icon, item: icon.notify('Hello!'))
    )

if Icon.HAS_DEFAULT_ACTION:
    menu_items.append(
        MenuItem('Default Item', lambda icon, item: None, default=True)
    )

menu_items.append(MenuItem('Exit', lambda icon, item: icon.stop()))

def show_capabilities(icon):
    msg = f'''Platform Capabilities:
    Menus: {Icon.HAS_MENU}
    Notifications: {Icon.HAS_NOTIFICATION}
    Default Action: {Icon.HAS_DEFAULT_ACTION}
    Radio Buttons: {Icon.HAS_MENU_RADIO}'''
    print(msg)

menu = Menu(*menu_items)
icon = Icon('myapp', icon=create_icon(), menu=menu)
icon.run()
```

--------------------------------

### Create a tray icon with a setup function

Source: https://github.com/moses-palmer/pystray/blob/master/_autodocs/examples.md

Uses a setup function to perform background initialization and notifications after the icon is displayed.

```python
from pystray import Icon, Menu, MenuItem
from PIL import Image
import threading
import time

def create_icon():
    image = Image.new('RGB', (64, 64), color='white')
    return image

def setup(icon):
    """Called in a background thread after icon is ready."""
    print('Icon is ready, running setup...')
    icon.visible = True
    
    # Do initialization in background
    def background_work():
        time.sleep(1)
        icon.notify('Application started!')
    
    thread = threading.Thread(target=background_work, daemon=True)
    thread.start()

menu = Menu(
    MenuItem('Quit', lambda icon, item: icon.stop())
)

icon = Icon('myapp', icon=create_icon(), menu=menu)
icon.run(setup=setup)
```

--------------------------------

### Automatic recovery on TaskbarCreated

Source: https://github.com/moses-palmer/pystray/blob/master/lib/pystray/_win32.py

Handles the WM_TASKBARCREATED message broadcast when Explorer restarts. If the icon's visible flag is True, it re-registers the icon by calling _show(), which sends Shell_NotifyIcon(NIM_ADD).

```python
    def _on_taskbarcreated(self, wparam, lparam):
        """Handles ``WM_TASKBARCREATED``.

        This message is broadcast when the notification area becomes available.
        Handling this message allows catching explorer restarts.
        """
        if self.visible:
            self._show()
```