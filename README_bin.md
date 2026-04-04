# Quickstart guide to use the binary distribution of quickice-gui

* Linux binary: 
    * Download `quickice-v2.0.0-linux-x86_64.tar.gz` under "Assets".
    * How to use the binary:
        1. extract the tarball: `tar xfz quickice-v2.0.0-linux-x86_64.tar.gz`
        2. cd to the package directory: `cd package` 
            * On local linux machine with full features: `./quickice-gui/quickice-gui`
            * Remotely via ssh, enable the 3D viewer if the system support: `QUICKICE_FORCE_VTK=true ./quickice-gui/quickice-gui`

* Windows executable (via github actions): 
    * Download `quickice-v2.0.0-windows-x86_64.zip` under "Assets".
    * How to use the binary:
        1. extract the package 
        2. go to `package\quickice-gui`, double-click `quickice-gui.exe` to launch the GUI.
