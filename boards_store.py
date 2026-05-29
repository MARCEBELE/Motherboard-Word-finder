"""Storage for indexed boards. Each board lives in app/boards/<id>/ with
its normalized images and a board.json. app/boards/boards.json is the registry."""
import os, json, re, time, shutil, zipfile, tempfile
import ocr_lib

MANIFEST = "wordfinder-board.json"

ROOT = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(ROOT, "app")
BOARDS = os.path.join(APP, "boards")
REG = os.path.join(BOARDS, "boards.json")


def _load_reg():
    if os.path.exists(REG):
        with open(REG, encoding="utf-8") as f:
            return json.load(f)
    return {"boards": []}


def _save_reg(reg):
    os.makedirs(BOARDS, exist_ok=True)
    with open(REG, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)


def _slug(s):
    s = re.sub(r"[^A-Za-z0-9]+", "-", s or "").strip("-").lower()
    return s or "board"


def make_id(name):
    existing = {b["id"] for b in _load_reg()["boards"]}
    base = _slug(name)
    cand, n = base, 2
    while cand in existing:
        cand = f"{base}-{n}"
        n += 1
    return cand


def list_boards():
    return _load_reg()["boards"]


def get_board(bid):
    p = os.path.join(BOARDS, bid, "board.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def delete_board(bid):
    """Remove a board from the registry and delete its folder."""
    reg = _load_reg()
    if not any(b["id"] == bid for b in reg["boards"]):
        raise ValueError("Board not found.")
    reg["boards"] = [b for b in reg["boards"] if b["id"] != bid]
    _save_reg(reg)
    shutil.rmtree(os.path.join(BOARDS, bid), ignore_errors=True)


def add_board(folder, name=None, progress=None):
    """OCR a folder of photos and register it as a new board. Returns its meta."""
    if not os.path.isdir(folder):
        raise ValueError("Folder not found.")
    name = (name or os.path.basename(os.path.normpath(folder)) or "board").strip()
    bid = make_id(name)
    bdir = os.path.join(BOARDS, bid)
    images_out = os.path.join(bdir, "images")
    url_prefix = f"boards/{bid}/images/"
    data = ocr_lib.index_folder(folder, images_out, url_prefix, progress=progress)
    if not data["images"]:
        shutil.rmtree(bdir, ignore_errors=True)
        raise ValueError("No images (.jpg/.png) found in that folder.")
    with open(os.path.join(bdir, "board.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    meta = {"id": bid, "name": name, "images": len(data["images"]),
            "labels": sum(len(im["labels"]) for im in data["images"]),
            "source": folder, "created": int(time.time())}
    reg = _load_reg()
    reg["boards"] = [b for b in reg["boards"] if b["id"] != bid] + [meta]
    _save_reg(reg)
    return meta


def export_board(bid):
    """Pack a board into a shareable .zip (manifest + images). Returns (zip_path, name)."""
    b = get_board(bid)
    if not b:
        raise ValueError("Board not found.")
    meta = next((m for m in list_boards() if m["id"] == bid), None)
    name = meta["name"] if meta else bid
    manifest = {"name": name, "images": []}
    for im in b["images"]:
        base = os.path.basename(im["file"])
        manifest["images"].append({"file": "images/" + base, "source": im.get("source"),
                                   "w": im.get("w"), "h": im.get("h"), "labels": im.get("labels", [])})
    fd, zpath = tempfile.mkstemp(suffix=".zip")
    os.close(fd)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False))
        for im in b["images"]:
            base = os.path.basename(im["file"])
            src = os.path.join(APP, im["file"].replace("/", os.sep))
            if os.path.exists(src):
                z.write(src, "images/" + base)
    return zpath, name


def import_board(zip_path):
    """Unpack a shared board .zip into a new board. Returns its meta."""
    with zipfile.ZipFile(zip_path) as z:
        names = set(z.namelist())
        if MANIFEST not in names:
            raise ValueError("This file is not a Word Finder board (.zip from Export).")
        data = json.loads(z.read(MANIFEST).decode("utf-8"))
        name = (data.get("name") or "Imported board").strip()
        bid = make_id(name)
        bdir = os.path.join(BOARDS, bid)
        images_out = os.path.join(bdir, "images")
        os.makedirs(images_out, exist_ok=True)
        out_images = []
        try:
            for im in (data.get("images") or []):
                base = os.path.basename(im.get("file", ""))
                member = "images/" + base
                if not base or member not in names:
                    continue
                with z.open(member) as src, open(os.path.join(images_out, base), "wb") as out:
                    shutil.copyfileobj(src, out)
                out_images.append({"file": f"boards/{bid}/images/{base}", "source": im.get("source"),
                                   "w": im.get("w"), "h": im.get("h"), "labels": im.get("labels", [])})
            if not out_images:
                raise ValueError("Board file had no images.")
            with open(os.path.join(bdir, "board.json"), "w", encoding="utf-8") as f:
                json.dump({"images": out_images}, f, ensure_ascii=False)
        except Exception:
            shutil.rmtree(bdir, ignore_errors=True)
            raise
    meta = {"id": bid, "name": name, "images": len(out_images),
            "labels": sum(len(im["labels"]) for im in out_images),
            "source": "imported", "created": int(time.time())}
    reg = _load_reg()
    reg["boards"] = [b for b in reg["boards"] if b["id"] != bid] + [meta]
    _save_reg(reg)
    return meta
