
## Requirements

obapps4 uses GTK3 and python-xlib, both of which depend on system libraries that must be
installed before the tool can be used.


## Dependencies

**Debian / Ubuntu:**
```bash
sudo apt install libgirepository-2.0-dev libcairo2-dev pkg-config python3-dev gir1.2-gtk-3.0
```

**Arch Linux:**
```bash
sudo pacman -S gobject-introspection gtk3 cairo pkgconf
```

**UV:**
[Installation Instructions](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)

However, pip can also be used:
```bash
pip install uv
```

## Install and Upgrade

```bash
# Install
uv tool install git+https://github.com/aaron-imbrock/obapps4

# Upgrade
uv tool upgrade obapps4
```

Or from a local clone:
```bash
git clone https://github.com/aaron-imbrock/obapps4
uv tool install ./obapps4
```

The `obapps` command will then be available in your shell

## Development

```bash
git clone https://github.com/aaron-imbrock/obapps4
cd obapps4
uv sync
uv run obapps
```

## License

See [LICENSE](LICENSE)