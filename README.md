# AAF Reader

A browser-based AAF (Advanced Authoring Format) metadata inspector. Drop an AAF file and instantly see what's inside. Your files never leave your browser.

## What it extracts

- **File overview** — creating application, version, platform, creation date, AAF version
- **Media summary** — video resolution, codec, frame rate, color space, bit depth; audio sample rate, bit depth, channels
- **Compositions** — name, duration, edit rate, timecodes, track counts
- **Master clips** — clip names and slot counts
- **Clip metadata** — UserComments and Attributes per clip (scene, slate, take, soundroll, camera, lens, color)
- **Source references** — network locator paths (MXF media references), tape source names, per-source media descriptors
- **Mob counts** — total mobs, compositions, master mobs, source mobs

## Quick start

Serve the `frontend/` directory with any static file server:

```bash
cd frontend
python3 -m http.server 8765
```

Open http://localhost:8765 and drop an AAF file.

First parse takes 10-15 seconds (downloads Pyodide runtime + installs Python packages). Repeat parses are near-instant.

## How it works

AAF parsing runs entirely in your browser using [Pyodide](https://pyodide.org) (Python compiled to WebAssembly). A Web Worker loads Pyodide, installs [pyaaf2](https://github.com/markreidvfx/pyaaf2) and [olefile](https://github.com/decalage2/olefile) from vendored wheels, then parses the file. Results come back as JSON and render in vanilla JS.

No server, no upload, no backend.

## Privacy

Your AAF files never leave your browser. Parsing happens entirely in WebAssembly on your machine. The only network requests are for the Pyodide runtime (CDN) and Google Fonts on first load.

## Tech stack

- **Parser** — Python ([pyaaf2](https://github.com/markreidvfx/pyaaf2)) running in-browser via [Pyodide](https://pyodide.org) WebAssembly
- **Frontend** — Vanilla HTML/JS/CSS (no framework)
- **Design** — Custom design system ([DESIGN.md](DESIGN.md)): Satoshi + DM Sans + JetBrains Mono, warm amber accent
- **Deployment** — Static site (GitHub Pages, any CDN, any file server)

## Supported AAF sources

Tested with exports from Avid Media Composer. Should work with AAFs from any application that writes standard AAF files (Premiere Pro, DaVinci Resolve, etc.) since pyaaf2 implements the full AAF object specification.

## License

MIT
