HOW TO BUILD WINDOWS, MACOS, AND LINUX VERSIONS WITH GITHUB

1. Create a new GitHub repository.
2. Upload everything INSIDE this folder to the repository root.
   Make sure the .github folder is uploaded too.
3. Open the repository's Actions tab.
4. Select "Build Tanks for Windows, macOS, and Linux".
5. Click "Run workflow" and then the green "Run workflow" button.
6. Wait for all three jobs to finish.
7. Open the completed workflow run and download these artifacts:
   - Tanks-Windows
   - Tanks-macOS
   - Tanks-Linux

Each artifact contains a ZIP. Recipients do not need Python.

MAC FIRST OPEN
Because the app is not Apple-signed, the Mac user may need to:
1. Extract Tanks-macOS.zip.
2. Right-click Tanks.app.
3. Choose Open.
4. Choose Open again in the warning.

NETWORKING
The current join-code discovery is designed for players on the same local network.
The host may need to allow the app through the firewall.
