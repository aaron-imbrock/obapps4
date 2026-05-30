#  obapps
#
#  Openbox Application Settings Editor
License = """
MIT License

Copyright (c) 2010 Eric Bohlman
Copyright (c) 2020 gcurse (github.com/gCurse)
Copyright (c) 2026 Aaron Imbrock

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

from importlib.metadata import version as _pkg_version
version = _pkg_version("obapps4")

import sys
from xml.dom.minidom import parse
from xml.dom import Node

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
from gi.repository import Gtk, Gdk

from . import utils as obaxutils


MODEL_KEYS = ["name", "class", "role", "title", "type"]
COLUMNS = [("Name", 150), ("Class", 150), ("Role", 150), ("Title", 150), ("Type", 80)]


class OBappsel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.model = None
        self.notify = None
        self.inhibit_notify = False

        self.store = Gtk.ListStore(*([str] * len(MODEL_KEYS)))
        self.treeview = Gtk.TreeView(model=self.store)
        self.treeview.set_headers_visible(True)

        for col_idx, (title, width) in enumerate(COLUMNS):
            renderer = Gtk.CellRendererText()
            renderer.set_property("editable", True)
            renderer.connect("edited", self._on_cell_edited, col_idx)
            col = Gtk.TreeViewColumn(title, renderer, text=col_idx)
            col.set_resizable(True)
            col.set_min_width(width)
            col.set_sizing(Gtk.TreeViewColumnSizing.GROW_ONLY)
            self.treeview.append_column(col)

        self.treeview.get_selection().connect("changed", self._on_selection_changed)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(150)
        scroll.add(self.treeview)
        self.pack_start(scroll, True, True, 0)

        bbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)

        btn_add = Gtk.Button.new_from_icon_name("list-add-symbolic", Gtk.IconSize.BUTTON)
        btn_add.connect("clicked", self._on_new)
        bbox.pack_start(btn_add, False, False, 0)

        btn_pick = Gtk.Button(label="Pick")
        btn_pick.set_tooltip_text("Click on a window to set selected item's name/class/role/type")
        btn_pick.connect("clicked", self._on_pick)
        bbox.pack_start(btn_pick, False, False, 0)

        btn_up = Gtk.Button.new_from_icon_name("go-up-symbolic", Gtk.IconSize.BUTTON)
        btn_up.connect("clicked", self._on_up)
        bbox.pack_start(btn_up, False, False, 0)

        btn_down = Gtk.Button.new_from_icon_name("go-down-symbolic", Gtk.IconSize.BUTTON)
        btn_down.connect("clicked", self._on_down)
        bbox.pack_start(btn_down, False, False, 0)

        btn_del = Gtk.Button.new_from_icon_name("list-remove-symbolic", Gtk.IconSize.BUTTON)
        btn_del.connect("clicked", self._on_delete)
        bbox.pack_start(btn_del, False, False, 0)

        self.pack_start(bbox, False, False, 2)

    def set_notify(self, func):
        self.notify = func

    def set_model(self, model):
        self.model = model
        self.inhibit_notify = True
        self.store.clear()
        for item in self.model.Items():
            self.model.SetCurrent(item)
            self.store.append([self.model.Get(k) for k in MODEL_KEYS])
        self.inhibit_notify = False
        self._select_row(0)

    def _on_selection_changed(self, selection):
        if not self.inhibit_notify:
            self._do_notify()

    def _on_cell_edited(self, renderer, path, new_text, col_idx):
        row_idx = int(path)
        self.store[row_idx][col_idx] = new_text
        self.model.SetCurrent(row_idx)
        self.model.Set(MODEL_KEYS[col_idx], new_text)
        self._do_notify()

    def _on_new(self, button):
        self.store.append([""] * len(MODEL_KEYS))
        self.model.Append()
        self._select_row(len(self.store) - 1)

    def _on_pick(self, button):
        toplevel_win = self.get_toplevel().get_window()
        cursor = Gdk.Cursor.new_for_display(Gdk.Display.get_default(), Gdk.CursorType.CROSSHAIR)
        seat = Gdk.Display.get_default().get_default_seat()
        result = seat.grab(toplevel_win, Gdk.SeatCapabilities.ALL_POINTING,
                           False, cursor, None, None, None)
        if result != Gdk.GrabStatus.SUCCESS:
            print(f"Warning: could not grab pointer (status: {result})")
            return
        self._pick_handler_id = self.get_toplevel().connect("button-press-event", self._on_picked)

    def _on_picked(self, widget, event):
        seat = Gdk.Display.get_default().get_default_seat()
        seat.ungrab()
        widget.disconnect(self._pick_handler_id)

        info = obaxutils.get_window_info(
            ("_OB_APP_NAME", "_OB_APP_CLASS", "_OB_APP_ROLE", "_OB_APP_TITLE", "_OB_APP_TYPE")
        )
        if info is None:
            return
        sel = self._get_sel()
        if sel is None:
            self._on_new(None)
            sel = len(self.store) - 1
        self.model.SetCurrent(sel)
        for col_idx, val in enumerate(info):
            v = val.decode("utf-8") if isinstance(val, bytes) else (val or "")
            self.store[sel][col_idx] = v
            self.model.Set(MODEL_KEYS[col_idx], v)
        self._select_row(sel)

    def _on_up(self, button):
        sel = self._get_sel()
        if sel is not None and sel > 0:
            self._swap_rows(sel, sel - 1)
            self.model.Move(sel, sel - 1)
            self._select_row(sel - 1)

    def _on_down(self, button):
        sel = self._get_sel()
        if sel is not None and sel < len(self.store) - 1:
            self._swap_rows(sel, sel + 1)
            self.model.Move(sel, sel + 1)
            self._select_row(sel + 1)

    def _on_delete(self, button):
        sel = self._get_sel()
        if sel is None:
            return
        it = self.store.get_iter(Gtk.TreePath(sel))
        self.store.remove(it)
        self.model.Delete(sel)
        self._select_row(min(sel, len(self.store) - 1))

    def _swap_rows(self, i, j):
        row_i = list(self.store[i])
        row_j = list(self.store[j])
        for col in range(len(MODEL_KEYS)):
            self.store[i][col] = row_j[col]
            self.store[j][col] = row_i[col]

    def _get_sel(self):
        model, it = self.treeview.get_selection().get_selected()
        if it is None:
            return None
        return model.get_path(it).get_indices()[0]

    def _select_row(self, index):
        if len(self.store) == 0:
            return
        index = max(0, min(index, len(self.store) - 1))
        path = Gtk.TreePath(index)
        self.treeview.get_selection().select_path(path)
        self.treeview.scroll_to_cell(path, None, False, 0, 0)
        self._do_notify()

    def _do_notify(self):
        if self.notify is None or self.model is None:
            return
        sel = self._get_sel()
        if sel is not None:
            self.model.SetCurrent(sel)
            self.notify(self.model)
        for col in self.treeview.get_columns():
            col.queue_resize()


class SettingsPanel(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.set_border_width(4)
        self.inhibit_onchanged = False
        self.rbs = {}
        self.settings = None

        self._make_radioboxes([
            [
                ("Focus",    ["Yes", "No", "NA"], "focus"),
                ("Decorate", ["Yes", "No", "NA"], "decor"),
            ],
            [
                ("Iconize", ["Yes", "No", "NA"], "iconic"),
                ("Shade",   ["Yes", "No", "NA"], "shade"),
            ],
            ("Fullscreen", ["Yes", "No", "NA"], "fullscreen"),
            ("Maximize", ["Vertical", "Horizontal", "Both", "No", "NA"], "maximized"),
            ("Layer", ["Normal", "Above", "Below", "NA"], "layer"),
        ])

        pos_frame = Gtk.Frame(label="Position")
        pos_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        pos_box.set_border_width(4)
        self.posx = self._add_entry(pos_box, "X:", 6, 'Position or "center"')
        self.posy = self._add_entry(pos_box, "Y:", 6, 'Position or "center"')
        self.posmon = self._add_entry(pos_box, "Monitor:", 3, "")
        self.force = Gtk.CheckButton(label="Force")
        self.force.connect("toggled", self._on_changed)
        pos_box.pack_start(self.force, False, False, 2)
        pos_frame.add(pos_box)
        self.pack_start(pos_frame, False, False, 2)

        desk_frame = Gtk.Frame()
        desk_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        desk_box.set_border_width(4)
        self.desktop = self._add_entry(desk_box, "Desktop:", 5, '1 is first, "all" for all desktops')
        desk_frame.add(desk_box)
        self.pack_start(desk_frame, False, False, 2)

        self._make_radioboxes([
            [
                ("Skip pager",   ["Yes", "No", "NA"], "skip_pager"),
                ("Skip taskbar", ["Yes", "No", "NA"], "skip_taskbar"),
            ],
        ])

    def _add_entry(self, box, label, chars, tooltip):
        box.pack_start(Gtk.Label(label=label), False, False, 0)
        entry = Gtk.Entry()
        entry.set_width_chars(chars)
        if tooltip:
            entry.set_tooltip_text(tooltip)
        entry.connect("changed", self._on_changed)
        box.pack_start(entry, False, False, 2)
        return entry

    def _make_radioboxes(self, items):
        for item in items:
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
            if isinstance(item[0], (list, tuple)):
                for subitem in item:
                    self._add_radiobox(hbox, subitem)
            else:
                self._add_radiobox(hbox, item)
            self.pack_start(hbox, False, False, 0)

    def _add_radiobox(self, parent, item):
        label, choices, key = item
        frame = Gtk.Frame(label=label)
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        box.set_border_width(2)
        group = None
        radio_buttons = []
        for choice in choices:
            if group is None:
                rb = Gtk.RadioButton.new_with_label(None, choice)
                group = rb
            else:
                rb = Gtk.RadioButton.new_with_label_from_widget(group, choice)
            rb.connect("toggled", self._on_changed)
            box.pack_start(rb, False, False, 0)
            radio_buttons.append((choice, rb))
        self.rbs[key] = radio_buttons
        frame.add(box)
        parent.pack_start(frame, False, False, 2)

    def _on_changed(self, widget):
        if self.inhibit_onchanged or self.settings is None:
            return
        if isinstance(widget, Gtk.RadioButton) and not widget.get_active():
            return
        self.settings.Set("x", self.posx.get_text())
        self.settings.Set("y", self.posy.get_text())
        self.settings.Set("monitor", self.posmon.get_text())
        self.settings.Set("force", self.force.get_active())
        self.settings.Set("desktop", self.desktop.get_text())
        for key, rbs in self.rbs.items():
            for choice, rb in rbs:
                if rb.get_active():
                    self.settings.Set(key, choice.lower())
                    break

    def new_settings(self, model):
        self.settings = model
        self.inhibit_onchanged = True
        self.posx.set_text(model.Get("x"))
        self.posy.set_text(model.Get("y"))
        self.posmon.set_text(model.Get("monitor"))
        self.force.set_active(model.Get("force"))
        self.desktop.set_text(model.Get("desktop"))
        for key, rbs in self.rbs.items():
            val = (model.Get(key) or "NA").lower()
            for choice, rb in rbs:
                if choice.lower() == val:
                    rb.set_active(True)
                    break
        self.inhibit_onchanged = False


class OBAppsModel:
    def __init__(self, path, fileobj):
        self.app = None
        self.path = path
        self.dom = parse(fileobj)
        t = self.dom.getElementsByTagName("applications")
        if len(t):
            self.parent = t[0]
        else:
            self.parent = self.dom.createElement("applications")
            self.dom.documentElement.appendChild(self.parent)
        self.apps = self.parent.getElementsByTagName("application")
        self.current_item = None

    def Items(self):
        return list(range(len(self.apps)))

    def Append(self):
        self.parent.appendChild(self.dom.createElement("application"))
        self.parent.appendChild(self.dom.createTextNode("\n"))
        self.apps = self.parent.getElementsByTagName("application")

    def Delete(self, index):
        self.parent.removeChild(self.apps[index])
        self.apps = self.parent.getElementsByTagName("application")

    def Get(self, key):
        if self.current_item is None:
            if key == "force":
                return False
            return ""
        xltab = {"True": "Yes", "False": "No", "Default": "NA"}
        if key in ("name", "class", "role", "type", "title"):
            if self.app.hasAttribute(key):
                val = self.app.getAttribute(key)
                if val == "":
                    val = '""'
            else:
                val = ""
        elif key in ("x", "y", "monitor"):
            val = ""
            t = self.app.getElementsByTagName("position")
            if len(t):
                val = self._get_one(key, parent=t[0])
            if val == "default":
                val = ""
        elif key == "force":
            val = False
            t = self.app.getElementsByTagName("position")
            if len(t):
                res = t[0].getAttribute("force")
                val = res.lower() in ("true", "yes")
        else:
            val = self._get_one(key)
            val = val.capitalize()
            val = xltab.get(val, val)
            if key == "maximized" and val == "Yes":
                val = "Both"
            if key == "desktop" and val == "NA":
                val = ""
        return val

    def Set(self, key, val):
        if self.current_item is None:
            return
        if key in ("name", "class", "role", "type", "title"):
            if self.app.hasAttribute(key):
                self.app.removeAttribute(key)
            if val != "":
                if val == "''" or val == '""':
                    val = ""
                self.app.setAttribute(key, val)
        elif key in ("x", "y", "monitor"):
            val = val or "default"
            t = self.app.getElementsByTagName("position")
            if len(t) == 0:
                if key != "x" or val == "default":
                    return
                el = self.dom.createElement("position")
                self.app.appendChild(el)
            else:
                el = t[0]
            self._set_one(key, val, parent=el)
        elif key == "force":
            force = (val and "yes") or "no"
            t = self.app.getElementsByTagName("position")
            if len(t):
                t[0].setAttribute("force", force)
        else:
            if key == "maximized" and val == "both":
                val = "yes"
            if val == "na" or val == "":
                val = "default"
            self._set_one(key, val)

    def Move(self, fromp, to):
        old = self.parent.removeChild(self.apps[fromp])
        self.parent.insertBefore(old, self.apps[to])
        self.current_item = to
        self.apps = self.parent.getElementsByTagName("application")

    def SetCurrent(self, index):
        self.current_item = index
        if index is not None:
            self.app = self.apps[index]

    def Save(self):
        with open(self.path, "w") as rc_file:
            self.dom.writexml(rc_file)

    def _get_one(self, key, parent=None):
        val = ""
        if parent is None:
            parent = self.app
        t = parent.getElementsByTagName(key)
        if len(t):
            for n in t[0].childNodes:
                if n.nodeType == Node.TEXT_NODE:
                    val = n.nodeValue.strip()
                    break
        return val

    def _set_one(self, key, val, parent=None):
        if parent is None:
            parent = self.app
        t = parent.getElementsByTagName(key)
        if len(t) == 0:
            if val == "default":
                return
            el = self.dom.createElement(key)
            parent.appendChild(el)
            el.appendChild(self.dom.createTextNode(val))
        else:
            for n in t[0].childNodes:
                if n.nodeType == Node.TEXT_NODE:
                    n.nodeValue = val


HELP_TEXT = """\
<span size="large" weight="bold">OBApps4 Help</span>

<b>Overview</b>

OBApps4 manages per-application settings for the Openbox window manager, stored
in the &lt;applications&gt; section of rc.xml. Each row matches one window rule;
Openbox applies all matching rules in order, so placement matters.

Use the Pick button to click a running window and auto-fill its identity fields
(Name, Class, Role, Title, Type). Leave any field blank to match anything.
Wildcards * and ? are supported in name, class, role, and title fields.

<b>NA</b> omits the setting from rc.xml; Openbox uses its default behavior. \
<b>No</b> writes the setting explicitly, actively suppressing the feature. \

<b>Application Fields</b>

<b>Focus:</b> Whether Openbox tries to give the window focus when it appears.
Setting Yes does not guarantee focus; some restrictions may apply.

<b>Iconize:</b> Make the window iconified (minimized) when it appears, or not.

<b>Shade:</b> Make the window shaded (title bar only) when it appears, or not.

<b>Fullscreen:</b> Make the window fullscreen when it appears.

<b>Maximize:</b> Horizontal, Vertical, or Both.
Note: "Both" is stored as "yes" in rc.xml.

<b>Layer:</b> Set the stacking layer: Above, Normal, or Below.

<b>Position:</b> Where the window opens. X and Y accept a pixel value or "center";
negative values measure from the right or bottom edge.
Both X and Y must be set for position to take effect.
Force overrides applications that ignore position hints.
Monitor specifies the target display (1 = first, or "mouse").

<b>Desktop:</b> Which desktop the window opens on. 1 is the first desktop;
use "all" to show on all desktops.

<b>Skip pager:</b> Ask not to be shown in pagers.

<b>Skip taskbar:</b> Ask not to be shown in taskbars;
window cycling (Alt+Tab) will also skip the window.

Click Apply to save changes to rc.xml and signal Openbox to reload immediately."""



class HelpWindow(Gtk.Window):
    def __init__(self, parent):
        super().__init__(title="Help", transient_for=parent)
        self.set_default_size(520, 500)
        self.set_border_width(8)
        px, py = parent.get_position()
        pw = parent.get_size()[0]
        self.move(px + pw + 8, py)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(vbox)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        label = Gtk.Label()
        label.set_markup(HELP_TEXT)
        label.set_line_wrap(True)
        label.set_xalign(0)
        label.set_yalign(0)
        label.set_margin_start(8)
        label.set_margin_end(8)
        label.set_margin_top(8)
        label.set_margin_bottom(8)
        scroll.add(label)

        vbox.pack_start(scroll, True, True, 0)

        bbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btn_close = Gtk.Button(label="Close")
        btn_close.connect("clicked", lambda w: self.destroy())
        bbox.pack_end(btn_close, False, False, 0)
        vbox.pack_start(bbox, False, False, 0)

        self.show_all()


class WLFrame(Gtk.Window):
    def __init__(self):
        super().__init__(title="OBApps4")
        self.set_border_width(5)
        self.connect("delete-event", Gtk.main_quit)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.add(vbox)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.appsel = OBappsel()
        hbox.pack_start(self.appsel, True, True, 0)
        self.panel = SettingsPanel()
        hbox.pack_start(self.panel, False, False, 0)
        vbox.pack_start(hbox, True, True, 0)

        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(sep, False, False, 2)

        bbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        btn_about = Gtk.Button(label="About")
        btn_about.connect("clicked", self._on_about)
        bbox.pack_start(btn_about, False, False, 0)

        btn_help = Gtk.Button(label="Help")
        btn_help.connect("clicked", self._on_help)
        bbox.pack_start(btn_help, False, False, 0)

        btn_apply = Gtk.Button(label="Apply")
        btn_apply.connect("clicked", self._on_apply)
        bbox.pack_end(btn_apply, False, False, 0)

        btn_close = Gtk.Button(label="Close")
        btn_close.connect("clicked", lambda w: Gtk.main_quit())
        bbox.pack_end(btn_close, False, False, 0)

        vbox.pack_start(bbox, False, False, 0)

        self.appsel.set_notify(self.panel.new_settings)

        path = sys.argv[1] if len(sys.argv) >= 2 else obaxutils.get_ob_config_path()
        if path is None:
            self.destroy()
            return

        try:
            rc_file = open(path, "r")
        except IOError as ex:
            self._error(f"Cannot load {path}: {ex}")
            self.destroy()
            return

        self.model = OBAppsModel(path, rc_file)
        rc_file.close()
        self.appsel.set_model(self.model)

    def _on_help(self, button):
        HelpWindow(self)

    def _on_about(self, button):
        dlg = Gtk.AboutDialog(parent=self)
        dlg.set_program_name("OBApps4")
        dlg.set_version(version)
        dlg.set_comments("Openbox Application Settings Editor")
        dlg.set_copyright("(C) 2010 Eric Bohlman\n(C) 2020 gcurse (github.com/gCurse)\n(C) 2026 Aaron Imbrock (github.com/aimbrock)")
        dlg.set_authors(["Aaron Imbrock <aimbrock@gmail.com>"])
        dlg.set_license(License)
        dlg.set_website("https://github.com/aaron-imbrock/obapps4")
        dlg.set_website_label("OBApps4 home page")
        dlg.run()
        dlg.destroy()

    def _on_apply(self, button):
        try:
            self.model.Save()
            obaxutils.reconfigure_openbox()
        except IOError as ex:
            self._error(f"Cannot save {self.model.path}: {ex}")

    def _error(self, msg):
        dlg = Gtk.MessageDialog(parent=self, flags=0,
                                message_type=Gtk.MessageType.ERROR,
                                buttons=Gtk.ButtonsType.OK, text=msg)
        dlg.run()
        dlg.destroy()


def main():
    frame = WLFrame()
    frame.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
