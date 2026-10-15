#!/bin/sh
# Adds ClipSmith to login startup (macOS LaunchAgent / Linux XDG autostart) and launches it now.
set -e
dir=$(cd "$(dirname "$0")" && pwd)
py=$(command -v python3)
script="$dir/clipsmith.pyw"
pkill -f clipsmith.pyw 2>/dev/null || true

if [ "$(uname)" = Darwin ]; then
  plist="$HOME/Library/LaunchAgents/com.smartmanoj.clipsmith.plist"
  mkdir -p "$(dirname "$plist")"
  cat > "$plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.smartmanoj.clipsmith</string>
  <key>ProgramArguments</key><array><string>$py</string><string>$script</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>
PLIST
  launchctl unload "$plist" 2>/dev/null || true
  launchctl load "$plist"
  echo "Installed: $plist"
else
  desktop="$HOME/.config/autostart/clipsmith.desktop"
  mkdir -p "$(dirname "$desktop")"
  cat > "$desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=ClipSmith
Exec=$py "$script"
X-GNOME-Autostart-enabled=true
DESKTOP
  nohup "$py" "$script" >/dev/null 2>&1 &
  echo "Installed: $desktop"
fi
