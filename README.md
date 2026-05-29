# Board Word Finder

Find a component on a circuit board by typing its silkscreen label. Take photos of a
motherboard, let the tool read every printed label (OCR), then search a name like `PU1`
and it zooms to that spot and draws a box around it.

Built for laptop/phone board repair, where you often need to locate a part (e.g. `PU1`,
`U3`, `LA24`) on a dense board and the printed text points in every direction.

## What it does

- Reads silkscreen text off your own photos using OCR (PP-OCRv4).
- Handles labels printed at **any angle** (upright, sideways, upside-down).
- **Search** with typo tolerance (it knows OCR mixes up `O/0`, `I/1`, `S/5`...).
- Keep **multiple boards** and switch between them.
- **Share** a board you already processed with someone else as a single file — they
  import it and search instantly, with no OCR and no need for the original photos.

## Requirements

- Windows
- [Python 3.10+](https://www.python.org/downloads/) (tick *"Add Python to PATH"* when installing)

## Install

1. Download / clone this folder.
2. Double-click **`setup.bat`** (installs everything into a local `.venv`).

## Run

Double-click **`Start Word Finder.bat`**. Your browser opens the tool. Keep the small
black window open while using it; close it to stop.

## Using it

- **Pick a board** from the dropdown, then type a label (e.g. `PU1`) and press search.
- **Prev / Next** flip through the board's photos (`Photo 3 / 8`).
- **Click a match** in the list (or press Enter) to jump to a specific hit.
- **Show all labels** outlines everything the tool found; **Fit image** zooms out.

### Add a board

Click **+ Add**, choose the folder containing that board's photos. Processing 8 large
photos takes a few minutes (a progress message shows). Use straight-on, sharp, well-lit
photos for best results.

### Share a board

- **Export**: select a board and click **Export** — you get a `.zip` to send to anyone.
- **Import**: click **Import** and pick a `.zip` someone sent you. It
  appears in your dropdown immediately (no OCR needed).

Share boards as these `.zip` files (e.g. via GitHub Releases or a link) — board photos
are **not** committed to the repo.

## How it works

- `server.py` — small local web server (`http://localhost:8731`) + API.
- `ocr_lib.py` — tiles each photo, runs OCR at 0/90/180/270 degrees, maps boxes back,
  de-duplicates.
- `boards_store.py` — stores each board under `app/boards/<id>/` and packs/unpacks the
  shareable `.zip` files.
- `app/viewer.html` + `app/app.js` — the search interface (HTML canvas).

Command line (optional): `python build_index.py "C:\path\to\photos" --name "My Board"`.

## Notes

- OCR is very good but not perfect; search is typo-tolerant and you confirm visually.
- All processing is local — nothing is uploaded.
