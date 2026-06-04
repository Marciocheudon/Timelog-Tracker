# TimeLog Tracker

TimeLog Tracker is a small Python desktop app for tracking raid/work sessions and taking screenshots automatically. Screenshots include a timer card with the current session time.

The app stores data next to the script or executable:

- `timelog_data.json`
- `screenshots/`

## Features

- Current session timer with pause/resume
- Total worked time
- Automatic screenshots at random intervals
- Manual screenshot button
- Screenshot overlay card with the current session timer
- Monthly history with worked time and screenshot count
- Dark UI

## Requirements

- Python 3.9 or newer
- Tkinter
- Pillow

Tkinter usually comes with Python on Windows and macOS. On Linux, it may need to be installed separately.

## Run From Source

Clone the repository and enter the project folder:

```bash
git clone https://github.com/YOUR_USER/YOUR_REPO.git
cd YOUR_REPO
```

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

Windows:

```bat
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run the app:

```bash
python main.py
```

## Linux Notes

If Tkinter is missing, install it with your package manager.

Ubuntu/Debian:

```bash
sudo apt update
sudo apt install python3-tk
```

Fedora:

```bash
sudo dnf install python3-tkinter
```

Arch:

```bash
sudo pacman -S tk
```

On Wayland, screenshots may depend on desktop/session permissions. If screenshot capture does not work, try running under an X11 session.

## macOS Notes

macOS may ask for Screen Recording permission the first time screenshots are captured.

Go to:

```text
System Settings > Privacy & Security > Screen Recording
```

Enable permission for the terminal or app you use to run TimeLog Tracker.

## Windows Notes

Run from source:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python main.py
```

## Build Executables

This project uses PyInstaller to generate executables.

The base command is:

```bash
pyinstaller --noconfirm --clean --onefile --windowed --name TimeLogTracker main.py
```

PyInstaller builds executables for the operating system where it runs.

That means:

- Build `.exe` on Windows
- Build macOS executable/app on macOS
- Build Linux binary on Linux

You cannot reliably create a Windows `.exe` directly from macOS with PyInstaller.

## Build Windows `.exe`

On Windows, double-click:

```text
build_windows.bat
```

Output:

```text
dist\TimeLogTracker.exe
```

The person using the final `.exe` does not need Python installed.

Or run manually:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pyinstaller --noconfirm --clean --onefile --windowed --name TimeLogTracker main.py
```

The executable will be created at:

```text
dist\TimeLogTracker.exe
```

Keep `TimeLogTracker.exe` in a writable folder. The app creates `timelog_data.json` and `screenshots/` next to the executable.

## Build macOS Executable

On macOS:

```bash
./build_macos.sh
```

Output:

```text
dist/TimeLogTracker
```

## Build Linux Executable

On Linux:

```bash
./build_linux.sh
```

Output:

```text
dist/TimeLogTracker
```

## Data Files

TimeLog Tracker writes user data next to the script or executable:

```text
timelog_data.json
screenshots/
```

Do not delete these if you want to keep your history and screenshots.
