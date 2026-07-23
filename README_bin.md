# QuickIce Binary Distribution Guide

The `quickice-gui` binary supports both CLI and GUI modes.

## Platform Invocation

| Platform | Command |
|----------|---------|
| Source install | `python -m quickice [options]` |
| Binary (Linux) | `quickice-gui [options]` |
| Binary (Windows) | `quickice-gui.exe [options]` |

Windows users: append `.exe` to the binary name. All flags are identical across platforms.

## CLI Mode

Pass computation flags to run in CLI mode:

```bash
# Generate ice structure
quickice-gui -T 300 -P 0.1 -N 100

# Force CLI mode (skip GUI import entirely, useful in headless environments)
quickice-gui --cli -T 300 -P 0.1 -N 100
```

For full CLI documentation, see [docs/cli-reference.md](docs/cli-reference.md).

## GUI Mode

### Double-click launch (easiest)

Launcher scripts are included in the distribution so you can open the GUI with a double-click:

| Platform | File | Note |
|----------|------|------|
| Linux | `QuickIce.sh` | May need `chmod +x` first; some file managers open `.sh` in a text editor by default — right-click → Run instead |
| Windows | `QuickIce.bat` | Double-click directly |

These scripts live at the top level of the extracted package, next to the `quickice-gui/` folder, and simply pass `--gui` to the binary.

### Linux binary

* Download `quickice-v4.7.0-linux-x86_64.tar.gz` under "Assets".
* How to use the binary:
    1. Extract the tarball: `tar xfz quickice-v4.7.0-linux-x86_64.tar.gz`
    2. cd to the package directory: `cd package`
        * Double-click: `./QuickIce.sh` (or right-click → Run)
        * On local Linux machine with full features: `./quickice-gui/quickice-gui --gui`
        * Remotely via ssh, enable the 3D viewer if the system supports it: `QUICKICE_FORCE_VTK=true ./quickice-gui/quickice-gui --gui`

CLI flags also work with the binary (e.g., `./quickice-gui/quickice-gui -T 300 -P 0.1 -N 100`).

### Windows executable

* Download `quickice-v4.7.0-windows-x86_64.zip` under "Assets".
* How to use the binary:
    1. Extract the package
    2. Double-click `QuickIce.bat` at the top level to launch the GUI
    3. Or go to `package\quickice-gui` and double-click `quickice-gui.exe` (opens CLI help — you must use `QuickIce.bat` or run `quickice-gui.exe --gui`)
