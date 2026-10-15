# Clipboard monitor: strips the trailing slash from a copied URL (any copy method).
import base64, ctypes, re, subprocess, time
from ctypes import wintypes as w

u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32
u32.GetClipboardData.restype = w.HANDLE
u32.SetClipboardData.argtypes = [w.UINT, w.HANDLE]
k32.GlobalAlloc.restype = w.HGLOBAL
k32.GlobalAlloc.argtypes = [w.UINT, ctypes.c_size_t]
k32.GlobalLock.restype = ctypes.c_void_p
k32.GlobalLock.argtypes = [w.HGLOBAL]
k32.GlobalUnlock.argtypes = [w.HGLOBAL]
CF_UNICODETEXT, GMEM_MOVEABLE = 13, 0x2
URL = re.compile(r'^\s*https?://\S+/\s*$')

def open_cb():
    for _ in range(10):
        if u32.OpenClipboard(None):
            return True
        time.sleep(0.05)
    return False

def get_text():
    if not u32.IsClipboardFormatAvailable(CF_UNICODETEXT) or not open_cb():
        return None
    try:
        h = u32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return None
        p = k32.GlobalLock(h)
        try:
            return ctypes.wstring_at(p)
        finally:
            k32.GlobalUnlock(h)
    finally:
        u32.CloseClipboard()

def set_text(s):
    data = ctypes.create_unicode_buffer(s)
    size = ctypes.sizeof(data)
    h = k32.GlobalAlloc(GMEM_MOVEABLE, size)
    ctypes.memmove(k32.GlobalLock(h), data, size)
    k32.GlobalUnlock(h)
    if not open_cb():
        return
    try:
        u32.EmptyClipboard()
        u32.SetClipboardData(CF_UNICODETEXT, h)
    finally:
        u32.CloseClipboard()

# Win+V history keeps the original copy too; delete it so only the clean URL remains.
PS_DELETE = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$C=[Windows.ApplicationModel.DataTransfer.Clipboard,Windows.ApplicationModel.DataTransfer,ContentType=WindowsRuntime]
$asTask=[System.WindowsRuntimeSystemExtensions].GetMethods()|?{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'}|select -First 1
function Await($op,$t){$x=$asTask.MakeGenericMethod($t).Invoke($null,@($op));$x.Wait();$x.Result}
$r=Await ($C::GetHistoryItemsAsync()) ([Windows.ApplicationModel.DataTransfer.ClipboardHistoryItemsResult])
foreach($i in $r.Items){ if((Await ($i.Content.GetTextAsync()) ([string])).Trim() -eq '%s'){ [void]$C::DeleteItemFromHistory($i) } }
"""

def drop_from_history(text):
    cmd = PS_DELETE % text.strip().replace("'", "''")
    enc = base64.b64encode(cmd.encode('utf-16-le')).decode()
    subprocess.Popen(['powershell', '-NoProfile', '-EncodedCommand', enc],
                     creationflags=subprocess.CREATE_NO_WINDOW)

last = None
while True:
    seq = u32.GetClipboardSequenceNumber()
    if seq != last:
        # let the copying app finish writing before we open the clipboard
        time.sleep(0.5)
        if u32.GetClipboardSequenceNumber() != seq:
            continue
        last = seq
        t = get_text()
        if t and URL.match(t):
            set_text(t.strip().rstrip('/'))
            drop_from_history(t)
            last = u32.GetClipboardSequenceNumber()
    time.sleep(0.3)
