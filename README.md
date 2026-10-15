# ClipSmith

Windows clipboard monitor that strips the trailing slash from copied URLs (`https://x.com/foo/` → `https://x.com/foo`). Non-URL text is untouched.

Run: `pythonw clipsmith.pyw` (no dependencies; add a shortcut to `shell:startup` to autostart).

Install to startup (and launch now): `powershell -ExecutionPolicy Bypass -File install-startup.ps1`

The slashed original is also removed from Win+V clipboard history, so only the clean URL remains.
