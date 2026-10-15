# Adds clipmon to Windows startup and launches it now.
$dir = $PSScriptRoot
$pyw = (Get-Command pythonw).Source
$lnk = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\clipmon.lnk"
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnk)
$s.TargetPath = $pyw
$s.Arguments = "`"$dir\clipmon.pyw`""
$s.WorkingDirectory = $dir
$s.Save()
Get-CimInstance Win32_Process -Filter "name='pythonw.exe'" | ? CommandLine -match 'clipmon' | % { Stop-Process -Id $_.ProcessId -Force }
Start-Process $pyw "`"$dir\clipmon.pyw`"" -WorkingDirectory $dir
"Installed: $lnk"
