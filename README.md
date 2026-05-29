# Board Word Finder

Find a component on a circuit board by typing its silkscreen label. Take photos of a
board, let the tool read every printed label (OCR), then search a name like `PU1` and it
zooms to that spot and draws a box around it.

Built for laptop board repair — especially when you have the **schematic** (so you know a
component's name) but **no boardview** to show where that part physically sits. Snap a few
photos and this finds the part on the board for you.

## What it does

- Reads silkscreen text off your own photos using OCR (PP-OCRv4).
- Handles labels printed at **any angle** (upright, sideways, upside-down).
- **Search** with typo tolerance (it knows OCR mixes up `O/0`, `I/1`, `S/5`...).
- Keep **multiple boards** and switch between them.
- **Share** a board you already processed as a single file — someone else imports it and
  searches instantly, with no OCR and no need for the original photos.

## Requirements

- Windows
- [Python 3.10+](https://www.python.org/downloads/) (tick *"Add Python to PATH"* when installing)

## Install

1. Download or clone this repo.
2. Double-click **`setup.bat`** — it installs everything into a local `.venv`.

## Run

Double-click **`Start Word Finder.bat`**. Your browser opens the tool. Keep the small black
window open while using it; close it to stop.

## Using it

1. **Pick a board** from the dropdown (top-left).
2. **Type a label** (e.g. `PU1`) — matches are listed; click one to jump to it.
3. **Prev / Next** flip through the board's photos; **Fit image** zooms out; **Show all
   labels** outlines everything found.

### Add a board

Click **+ Add** and choose the folder with that board's photos. The tool reads **all**
photos in the folder as one board, so put every shot of that board (both sides, several
shots each) in the same folder. Processing a folder of large photos takes a few minutes
(a progress bar shows).

**Photo tips — this matters a lot for accuracy:**

- **Use several overlapping close-up photos per side, not one wide shot of the whole side.**
  Silkscreen text is tiny; a single full-board photo usually doesn't have enough detail to
  read it. Cover each side with multiple shots — the tool indexes them all and you flip
  through them with Prev / Next.
- **Zoom 2x–3x on your phone** before each shot. This avoids the wide-angle lens distortion
  that warps text near the edges and gives sharper, more readable characters.
- Keep shots **sharp, straight-on, and well-lit**, and avoid glare on the board.

### Share / manage boards

- **Export** — save the selected board as a `.zip` to send to anyone.
- **Import** — load a `.zip` someone sent you; it appears in your dropdown instantly.
- **Delete** — remove a board you no longer need (your original photo folder is untouched).

Boards travel as these `.zip` files (e.g. via GitHub Releases) — board photos are **not**
committed to the repo.

## How it works

- `server.py` — small local web server (`http://localhost:8731`) plus a tiny API.
- `ocr_lib.py` — tiles each photo, runs OCR at 0/90/180/270 degrees, maps boxes back, and
  de-duplicates. Very large photos are downscaled to keep things fast.
- `boards_store.py` — stores each board under `app/boards/<id>/` and packs/unpacks the
  shareable `.zip` files.
- `app/viewer.html` + `app/app.js` — the search interface (HTML canvas).

Command line (optional): `python build_index.py "C:\path\to\photos" --name "My Board"`.

## Notes

- OCR is very good but not perfect; search is typo-tolerant and you confirm visually.
- Everything runs locally — nothing is uploaded.
