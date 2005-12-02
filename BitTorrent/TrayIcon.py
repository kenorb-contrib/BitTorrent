import os

from BitTorrent import app_name
from BitTorrent.GUI import gtk_wrap
from BitTorrent.platform import image_root

if os.name == 'nt':
    from systray import systray

    class TrayIcon(systray.Control):
        def __init__(self, initial_state, toggle_func=None, quit_func=None):
            # BUG: image_root is useless, path must be relative
            iconpath = os.path.join('images/logo', 'bittorrent_icon_16.ico')
            systray.Control.__init__(self, app_name, iconpath)

            self.toggle_func = toggle_func
            self.quit_func   = quit_func

            self.toggle_state = initial_state
            title = None
            if self.toggle_state:
                title = _("Hide %s") % app_name
            else:
                title = _("Show %s") % app_name
                
            self.toggle_item = systray.MenuItem(name='toggle',
                                                title=title)
            
            self.toggle_item.onclick = self.toggle
            self.on_double_click = self.toggle

            self.add_menuitem(self.toggle_item)
            self.default_menu_index = 1

        def set_title(self, title):
            if hasattr(self, 'systray'):
                # FIXME: pysystray bug means this might fail, but who cares?
                try:
                    self.systray.text = title
                except:
                    pass

        def on_quit(self, *args):
            if self.quit_func is not None:
                self._callout(self.quit_func)

        def change_text(self, b):
            # ow.
            if not hasattr(self, "systray"):
                return
            s = self.systray
            self.toggle_state = b
            if self.toggle_state:
                s.menu.items['toggle'].title = _("Hide %s") % app_name
            else:
                s.menu.items['toggle'].title = _("Show %s") % app_name
                    
        def toggle(self, s):
            if self.toggle_func is not None:
                self._callout(self.toggle_func)
            self.change_text(not self.toggle_state)

        def _callout(self, func):
            if callable(func):
                gtk_wrap(func)
            
else:
    # No tray icon for *your* OS !
    class TrayIcon:
        def func(*a, **kw):
            pass
        __init__ = enable = disable = set_title = func


if __name__ == '__main__':
    import threading
    ti = TrayIcon()
    th = threading.Thread(target=ti.start, args=())
    th.start()
