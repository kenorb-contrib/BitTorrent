import os

from BitTorrent import app_name
from BitTorrent.GUI import gtk_wrap
from BitTorrent.platform import image_root

if os.name == 'nt':
    from systray import systray

    class TrayIcon(systray.Control):
        def __init__(self, initial_state, toggle_func=None, quit_func=None):
            iconpath = os.path.join(image_root, 'bittorrent.ico')

            systray.Control.__init__(self, app_name, iconpath)

            self.toggle_func = toggle_func
            self.quit_func = quit_func
            self.tooltip_text = None

            self.toggle_state = initial_state
            menu_text = self._get_text_for_state(self.toggle_state)

            self.toggle_item = systray.MenuItem(name='toggle',
                                                title=menu_text)
            
            self.toggle_item.onclick = self.toggle
            self.on_double_click = self.toggle

            self.add_menuitem(self.toggle_item)
            self.default_menu_index = 1

        def get_tooltip(self):
            return self.tooltip_text

        def set_tooltip(self, tooltip_text):
            # ow.
            if not hasattr(self, 'systray'):
                return
                
            # FIXME: pysystray bug means this might fail
            try:
                if self.tooltip_text != tooltip_text:
                    self.systray.text = tooltip_text
                    # we set our own cache after sending the value to pysystray,
                    # since it could fail
                    self.tooltip_text = tooltip_text
            except:
                pass

        def on_quit(self, *args):
            if self.quit_func is not None:
                self._callout(self.quit_func)

        def set_toggle_state(self, b):
            # ow.
            if not hasattr(self, "systray"):
                return
            
            s = self.systray
            self.toggle_state = b
            s.menu.items['toggle'].title = self._get_text_for_state(self.toggle_state)

        def _get_text_for_state(self, state):
            if state:
                text = _("Hide %s") % app_name
            else:
                text = _("Show %s") % app_name
            return text
                    
        def toggle(self, s):
            if self.toggle_func is not None:
                self._callout(self.toggle_func)
            self.set_toggle_state(not self.toggle_state)

        def _callout(self, func):
            if callable(func):
                gtk_wrap(func)
            
else:
    # No tray icon for *your* OS !
    class TrayIcon:
        def func(*a, **kw):
            pass
        __init__ = enable = disable = get_tooltip = set_tooltip = set_toggle_state = func


if __name__ == '__main__':
    import threading
    from BitTorrent.platform import install_translation
    install_translation()
    ti = TrayIcon(True)
    th = threading.Thread(target=ti.enable, args=())
    th.start()
    from time import sleep
    sleep(10)
