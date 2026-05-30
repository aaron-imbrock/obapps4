# obapps4

A graphical editor for the Openbox window manager's per-application settings (`rc.xml`).

## Requirements

obapps4 uses GTK3 and python-xlib, both of which depend on system libraries that must be
installed before the tool can be used.

**Debian / Ubuntu:**
```bash
sudo apt install libgirepository-2.0-dev libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0
```

**Arch Linux:**
```bash
sudo pacman -S gobject-introspection gtk3 cairo pkgconf
```

## Install

```bash
uv tool install git+https://github.com/aaron-imbrock/obapps4
```

Or from a local clone:
```bash
git clone https://github.com/aaron-imbrock/obapps4
uv tool install ./obapps4
```

The `obapps` command will then be available in your shell.

## Usage

```bash
obapps
```

By default obapps edits `~/.config/openbox/rc.xml` (or whichever config file Openbox was
started with). Pass a path to edit a different file:

```bash
obapps ~/.config/openbox/myrc.xml
```

### Notes

- Click any cell in the list to edit name, class, role, title, or type inline.
- **Pick** — changes the cursor to a crosshair; click on any window to populate the selected
  entry's fields from that window's X11 properties. Creates a new entry if none is selected.
- **Apply** — writes changes to `rc.xml` and sends Openbox a reconfigure signal immediately.
- Blank name/class/role/title/type fields are not stored as attributes (i.e. they match any
  window). To match a window whose field is literally blank, enter `""` or `''`.

## Development

```bash
git clone https://github.com/aaron-imbrock/obapps4
cd obapps4
uv sync
uv run obapps
```

## License

MIT — see [LICENSE](LICENSE)
