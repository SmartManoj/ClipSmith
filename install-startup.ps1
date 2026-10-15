# Adds ClipSmith to Windows startup and launches it now.
$dir = $PSScriptRoot
$pyw = (Get-Command pythonw).Source
$lnk = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\clipsmith.lnk"
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$s.TargetPath = $pyw
$s.Arguments = "`"$dir\clipsmith.pyw`""
$s.WorkingDirectory = $dir
$s.Save()
Get-CimInstance Win32_Process -Filter "name='pythonw.exe'" | ? CommandLine -match 'clipmon|clipsmith' | % { Stop-Process -Id $_.ProcessId -Force }
Start-Process $pyw "`"$dir\clipsmith.pyw`"" -WorkingDirectory $dir
"Installed: $lnk"
