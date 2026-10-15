# ClipSmith

Cross-platform clipboard enhancer. Currently it strips the trailing slash from copied URLs (`https://x.com/foo/` → `https://x.com/foo`), whatever app or shortcut you copied from. Non-URL text is untouched.

On Windows, the slashed original is also removed from Win+V clipboard history, so only the clean URL remains.

## Requirements

- Python 3, no pip packages
- Windows: nothing else
- macOS: nothing else (uses `pbpaste`/`pbcopy`)
- Linux: `wl-clipboard` (Wayland) or `xclip`/`xsel` (X11)

## Run

`pythonw clipsmith.pyw` on Windows, `python3 clipsmith.pyw` on macOS/Linux.

## Start at login

- Windows: `powershell -ExecutionPolicy Bypass -File install-startup.ps1`
- macOS/Linux: `./install-startup.sh` (LaunchAgent on macOS, XDG autostart on Linux)
