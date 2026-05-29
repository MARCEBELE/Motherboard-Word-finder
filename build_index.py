"""CLI for the Board Word Finder.

  python build_index.py <folder> [--name "My Board"]   # add a board from a photo folder
  python build_index.py <image> --overlay              # debug: annotate one photo

Adding a board can also be done from the app itself (the "Add board" button).
"""
import sys, os
import cv2, numpy as np
import ocr_lib, boards_store


def overlay(image_path):
    img = ocr_lib.load_bgr(image_path)
    dets, W, H = ocr_lib.ocr_image(img)
    print(f"{os.path.basename(image_path)}: {len(dets)} labels ({W}x{H})")
    for d in dets:
        pts = np.array(d["box"], dtype=np.int32)
        cv2.polylines(img, [pts], True, (0, 0, 255), 2)
        cv2.putText(img, d["text"], tuple(pts[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    if img.shape[1] > 1400:
        s = 1400 / img.shape[1]
        img = cv2.resize(img, (1400, int(img.shape[0] * s)))
    out = os.path.splitext(image_path)[0] + "_overlay.jpg"
    cv2.imwrite(out, img)
    print("overlay ->", out)


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    target = args[0]
    if "--overlay" in args and os.path.isfile(target):
        overlay(target)
        return
    name = None
    if "--name" in args:
        name = args[args.index("--name") + 1]
    meta = boards_store.add_board(
        target, name=name,
        progress=lambda d, t, n: print(f"  [{d}/{t}] {n}", flush=True))
    print(f"\nAdded board '{meta['name']}' (id={meta['id']}): "
          f"{meta['images']} images, {meta['labels']} labels")


if __name__ == "__main__":
    main()
