# QuickIce Binary Distribution Guide

The `quickice-gui` binary supports both CLI and GUI modes.

## Platform Invocation

| Platform | Command |
|----------|---------|
| Source install | `python -m quickice [options]` |
| Binary (Linux/macOS) | `quickice-gui [options]` |
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

### Linux binary

* Download `quickice-v4.5.0-linux-x86_64.tar.gz` under "Assets".
* How to use the binary:
    1. Extract the tarball: `tar xfz quickice-v4.5.0-linux-x86_64.tar.gz`
    2. cd to the package directory: `cd package`
        * On local Linux machine with full features: `./quickice-gui/quickice-gui`
        * Remotely via ssh, enable the 3D viewer if the system supports it: `QUICKICE_FORCE_VTK=true ./quickice-gui/quickice-gui`

CLI flags also work with the binary (e.g., `./quickice-gui/quickice-gui -T 300 -P 0.1 -N 100`).

### Windows executable

* Download `quickice-v4.5.0-windows-x86_64.zip` under "Assets".
* How to use the binary:
    1. Extract the package
    2. Go to `package\quickice-gui`, double-click `quickice-gui.exe` to launch the GUI
