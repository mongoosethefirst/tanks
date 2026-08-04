TANKS - CROSS-PLATFORM SOURCE FOLDER

This same source folder can run on Windows, macOS, and Linux.
It is not one universal executable: each computer needs Python 3 and installs the dependencies in requirements.txt.

IMPORTANT
Copy all of your existing image files into:
    tanks/images

Copy PressStart2P-Regular.ttf into:
    tanks/fonts

WINDOWS
Double-click run_windows.bat

MACOS / LINUX
Open Terminal in this folder and run:
    chmod +x run_mac_linux.sh
    ./run_mac_linux.sh

NETWORKING
Players must be on the same local network unless the host configures port forwarding or uses a LAN VPN.
The host firewall may ask for permission; allow Python/the game on private networks.

BUILDING EXECUTABLES
A Windows executable must be built on Windows.
A macOS application must be built on macOS.
A Linux executable must be built on Linux.
There is no single executable file that runs unchanged on all three operating systems.
