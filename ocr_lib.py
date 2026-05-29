"""Shared OCR core for the Board Word Finder.

Reads a folder of board photos and produces a searchable label index.
Used by both build_index.py (CLI) and server.py (backend).
Engine: PP-OCRv4 via rapidocr. Handles all text orientations by running
each tile at 0/90/180/270 degrees and mapping boxes back.
"""
import os, glob
import cv2, numpy as np
from PIL import Image, ImageOps
from rapidocr import RapidOCR

# Pillow refuses very large images by default ("decompression bomb" guard). These are
# real board photos, so turn that guard off.
Image.MAX_IMAGE_PIXELS = None
# ...but cap the working resolution so a huge image doesn't exhaust memory or take many
# minutes to OCR. 60 MP is ~5x a normal phone photo. Set to None for full resolution.
MAX_WORK_PIXELS = 60_000_000

TILE = 900
OVERLAP = 220
ANGLES = [0, 90, 180, 270]
BOX_THRESH = 0.3
TEXT_SCORE = 0.35
IOU_THRESH = 0.30
IMAGE_EXTS = ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp")

_engine = None


def engine():
    global _engine
    if _engine is None:
        _engine = RapidOCR(params={"Det.limit_type": "max", "Det.limit_side_len": 1600})
    return _engine


def load_bgr(path):
    pil = Image.open(path)
    if MAX_WORK_PIXELS and pil.width * pil.height > MAX_WORK_PIXELS:
        # ask the JPEG decoder for a smaller image up front (saves memory on huge files)
        scale = (MAX_WORK_PIXELS / (pil.width * pil.height)) ** 0.5
        try:
            pil.draft("RGB", (int(pil.width * scale), int(pil.height * scale)))
        except Exception:
            pass
    pil = ImageOps.exif_transpose(pil).convert("RGB")
    if MAX_WORK_PIXELS and pil.width * pil.height > MAX_WORK_PIXELS:
        scale = (MAX_WORK_PIXELS / (pil.width * pil.height)) ** 0.5
        pil = pil.resize((max(1, int(pil.width * scale)), max(1, int(pil.height * scale))), Image.LANCZOS)
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def rotate(im, a):
    if a == 0:
        return im
    if a == 90:
        return cv2.rotate(im, cv2.ROTATE_90_CLOCKWISE)
    if a == 180:
        return cv2.rotate(im, cv2.ROTATE_180)
    return cv2.rotate(im, cv2.ROTATE_90_COUNTERCLOCKWISE)


def unrotate_pt(px, py, a, w, h):
    """Map a point in the rotated tile frame back to the original tile frame.
    w, h = ORIGINAL (unrotated) tile width/height."""
    if a == 0:
        return px, py
    if a == 90:
        return py, (h - 1 - px)
    if a == 180:
        return (w - 1 - px), (h - 1 - py)
    return (w - 1 - py), px


def tile_starts(total, tile, overlap):
    step = tile - overlap
    if total <= tile:
        return [0]
    starts = list(range(0, total - tile + 1, step))
    if starts[-1] != total - tile:
        starts.append(total - tile)
    return starts


def _aabb(box):
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    return min(xs), min(ys), max(xs), max(ys)


def _iou(a, b):
    ix0, iy0 = max(a[0], b[0]), max(a[1], b[1])
    ix1, iy1 = min(a[2], b[2]), min(a[3], b[3])
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter == 0:
        return 0.0
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _nms(dets):
    dets = sorted(dets, key=lambda d: -d["score"])
    kept, boxes = [], []
    for d in dets:
        bx = _aabb(d["box"])
        if any(_iou(bx, kb) > IOU_THRESH for kb in boxes):
            continue
        kept.append(d)
        boxes.append(bx)
    return kept


def ocr_image(img):
    H, W = img.shape[:2]
    eng = engine()
    dets = []
    for y0 in tile_starts(H, TILE, OVERLAP):
        for x0 in tile_starts(W, TILE, OVERLAP):
            x1, y1 = min(x0 + TILE, W), min(y0 + TILE, H)
            tile = img[y0:y1, x0:x1]
            tw, th = x1 - x0, y1 - y0
            for a in ANGLES:
                res = eng(rotate(tile, a), box_thresh=BOX_THRESH, text_score=TEXT_SCORE)
                if res is None or res.boxes is None:
                    continue
                for box, txt, score in zip(res.boxes, res.txts, res.scores):
                    txt = (txt or "").strip()
                    if not txt:
                        continue
                    pts = [unrotate_pt(float(p[0]), float(p[1]), a, tw, th) for p in box]
                    pts = [[round(px + x0, 1), round(py + y0, 1)] for px, py in pts]
                    dets.append({"text": txt, "score": float(score), "box": pts, "angle": a})
    return _nms(dets), W, H


def list_images(folder):
    files = []
    for ext in IMAGE_EXTS:
        files += glob.glob(os.path.join(folder, ext))
        files += glob.glob(os.path.join(folder, ext.upper()))
    return sorted(set(files))


def index_folder(folder, images_out, url_prefix, progress=None):
    """OCR every image in `folder`. Writes normalized copies to `images_out`
    and returns {"images":[{file,source,w,h,labels:[...]}]}.
    `url_prefix` is prepended to each saved image filename for the web path.
    `progress(done, total, name)` is called before each image (optional)."""
    files = list_images(folder)
    os.makedirs(images_out, exist_ok=True)
    images = []
    for i, f in enumerate(files):
        if progress:
            progress(i, len(files), os.path.basename(f))
        img = load_bgr(f)
        dets, W, H = ocr_image(img)
        name = f"img{i:02d}.jpg"
        cv2.imwrite(os.path.join(images_out, name), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
        images.append({"file": url_prefix + name, "source": os.path.basename(f),
                       "w": W, "h": H, "labels": dets})
    if progress:
        progress(len(files), len(files), "done")
    return {"images": images}
