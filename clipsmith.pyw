# Clipboard monitor: strips the trailing slash from a copied URL (any copy method).
# Windows, macOS and Linux (Wayland via wl-clipboard, X11 via xclip/xsel).
import os, re, shutil, subprocess, sys, time

URL = re.compile(r'^\s*https?://\S+/\s*$')

def clean(text):
    return text.strip().rstrip('/') if URL.match(text) else None

# Win+V history keeps the original copy too; delete it so only the clean URL remains.
PS_DELETE = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$C=[Windows.ApplicationModel.DataTransfer.Clipboard,Windows.ApplicationModel.DataTransfer,ContentType=WindowsRuntime]
$asTask=[System.WindowsRuntimeSystemExtensions].GetMethods()|?{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'}|select -First 1
function Await($op,$t){$x=$asTask.MakeGenericMethod($t).Invoke($null,@($op));$x.Wait();$x.Result}
for($n=0; $n -lt 10; $n++){
  $r=Await ($C::GetHistoryItemsAsync()) ([Windows.ApplicationModel.DataTransfer.ClipboardHistoryItemsResult])
  $hit=$false
  foreach($i in $r.Items){ try { if((Await ($i.Content.GetTextAsync()) ([string])).Trim() -eq '%s'){ [void]$C::DeleteItemFromHistory($i); $hit=$true } } catch {} }
  if($hit){ break }; Start-Sleep -Milliseconds 300
}
"""

if sys.platform == 'win32':
    import base64, ctypes
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


    def drop_from_history(text):
        cmd = PS_DELETE % text.strip().replace("'", "''")
        enc = base64.b64encode(cmd.encode('utf-16-le')).decode()
        subprocess.Popen(['powershell', '-NoProfile', '-EncodedCommand', enc],
                         creationflags=subprocess.CREATE_NO_WINDOW)

    def after_fix(original):
        drop_from_history(original)

    def watch(on_change):
        # event-driven: Windows notifies us the moment the clipboard changes
        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
        u32.DefWindowProcW.argtypes = [w.HWND, w.UINT, w.WPARAM, w.LPARAM]
        u32.DefWindowProcW.restype = ctypes.c_ssize_t
        u32.CreateWindowExW.restype = w.HWND
        u32.CreateWindowExW.argtypes = [w.DWORD, w.LPCWSTR, w.LPCWSTR, w.DWORD, ctypes.c_int, ctypes.c_int,
                                        ctypes.c_int, ctypes.c_int, w.HWND, w.HMENU, w.HINSTANCE, w.LPVOID]
        WM_CLIPBOARDUPDATE, HWND_MESSAGE = 0x031D, w.HWND(-3)

        def proc(hwnd, msg, wp, lp):
            if msg == WM_CLIPBOARDUPDATE:
                on_change()
                return 0
            return u32.DefWindowProcW(hwnd, msg, wp, lp)

        class WNDCLASS(ctypes.Structure):
            _fields_ = [('style', w.UINT), ('lpfnWndProc', WNDPROC), ('cbClsExtra', ctypes.c_int),
                        ('cbWndExtra', ctypes.c_int), ('hInstance', w.HINSTANCE), ('hIcon', w.HICON),
                        ('hCursor', w.HANDLE), ('hbrBackground', w.HBRUSH), ('lpszMenuName', w.LPCWSTR),
                        ('lpszClassName', w.LPCWSTR)]

        wndproc = WNDPROC(proc)
        wc = WNDCLASS(lpfnWndProc=wndproc, lpszClassName='ClipSmith')
        u32.RegisterClassW(ctypes.byref(wc))
        hwnd = u32.CreateWindowExW(0, 'ClipSmith', 'ClipSmith', 0, 0, 0, 0, 0, HWND_MESSAGE, None, None, None)
        u32.AddClipboardFormatListener(hwnd)
        msg = w.MSG()
        while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            u32.TranslateMessage(ctypes.byref(msg))
            u32.DispatchMessageW(ctypes.byref(msg))

else:
    if sys.platform == 'darwin':
        GET, SET = ['pbpaste'], ['pbcopy']
    elif os.environ.get('WAYLAND_DISPLAY') and shutil.which('wl-paste'):
        GET, SET = ['wl-paste', '-n', '-t', 'text'], ['wl-copy']
    elif shutil.which('xclip'):
        GET, SET = ['xclip', '-o', '-selection', 'clipboard'], ['xclip', '-selection', 'clipboard']
    elif shutil.which('xsel'):
        GET, SET = ['xsel', '-b', '-o'], ['xsel', '-b', '-i']
    else:
        sys.exit('ClipSmith needs wl-clipboard (Wayland), xclip or xsel (X11)')
    ENV = {**os.environ, 'LC_CTYPE': 'UTF-8'}  # pbpaste/pbcopy default to ASCII without it

    def get_text():
        r = subprocess.run(GET, capture_output=True, env=ENV)
        return r.stdout.decode('utf-8', 'replace') if r.returncode == 0 else None

    def set_text(s):
        subprocess.run(SET, input=s.encode(), env=ENV,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def after_fix(original):
        pass

    def watch(on_change):
        # no change notification without native bindings, so poll the text itself
        last = None
        while True:
            t = get_text()
            if t != last:
                last = t
                on_change()
            time.sleep(0.2)

def on_change():
    t = get_text()
    fixed = t and clean(t)
    if fixed:
        set_text(fixed)
        after_fix(t)

watch(on_change)
