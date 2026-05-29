"""Local backend for the Board Word Finder.

Serves the app/ folder and a small API:
  GET  /api/boards         -> list of indexed boards
  GET  /api/boards/<id>    -> one board's label index
  GET  /api/status         -> progress of the current add-board job
  POST /api/add_board      -> pick a folder (native dialog) and OCR it into a new board
                              (optional JSON {"path": "...", "name": "..."} skips the dialog)
"""
import os, sys, re, json, shutil, threading, subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import boards_store

ROOT = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(ROOT, "app")
PORT = 8731
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")

STATUS = {"state": "idle", "msg": "", "done": 0, "total": 0, "board_id": None, "board_name": None}
LOCK = threading.Lock()


def set_status(**kw):
    STATUS.update(kw)


def _pick(script):
    try:
        r = subprocess.run([sys.executable, os.path.join(ROOT, script)],
                           capture_output=True, text=True, timeout=300)
        return (r.stdout or "").strip()
    except Exception:
        return ""


def pick_folder():
    return _pick("pick_folder.py")


def pick_file():
    return _pick("pick_file.py")


def _do_import(path):
    set_status(state="processing", msg="Importing shared board...", done=0, total=0)
    meta = boards_store.import_board(path)
    set_status(state="done", msg=f"Imported '{meta['name']}'", done=meta["images"],
               total=meta["images"], board_id=meta["id"], board_name=meta["name"])


def run_import_job():
    try:
        set_status(state="picking", msg="Choose a board file (.zip) to import...", done=0, total=0,
                   board_id=None, board_name=None)
        path = pick_file()
        if not path:
            set_status(state="idle", msg="Cancelled.")
            return
        _do_import(path)
    except Exception as e:
        set_status(state="error", msg=str(e))
    finally:
        LOCK.release()


def _import_path(path):
    try:
        _do_import(path)
    except Exception as e:
        set_status(state="error", msg=str(e))
    finally:
        LOCK.release()


def run_add_job(path_hint=None, name=None):
    try:
        if path_hint:
            folder = path_hint
        else:
            set_status(state="picking", msg="Waiting for you to choose a folder...", done=0, total=0)
            folder = pick_folder()
            if not folder:
                set_status(state="idle", msg="Cancelled.")
                return
        set_status(state="processing", msg="Reading photos...", done=0, total=0,
                   board_id=None, board_name=name or os.path.basename(folder.rstrip("/\\")))

        def prog(d, t, n):
            set_status(state="processing", done=d, total=t,
                       msg=(f"Reading text from photo {min(d + 1, t)} of {t}..."
                            if n != "done" else "Finishing up..."))

        meta = boards_store.add_board(folder, name=name, progress=prog)
        set_status(state="done", msg=f"Added '{meta['name']}'", done=meta["images"],
                   total=meta["images"], board_id=meta["id"], board_name=meta["name"])
    except Exception as e:
        set_status(state="error", msg=str(e))
    finally:
        LOCK.release()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=APP, **k)

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self.path = "/viewer.html"
            return super().do_GET()
        if self.path == "/api/boards":
            return self._json({"boards": boards_store.list_boards()})
        if self.path == "/api/status":
            return self._json(STATUS)
        if self.path.startswith("/api/boards/"):
            bid = self.path[len("/api/boards/"):]
            if not ID_RE.match(bid):
                return self._json({"error": "bad id"}, 400)
            b = boards_store.get_board(bid)
            return self._json(b if b else {"error": "not found"}, 200 if b else 404)
        if self.path.startswith("/api/export/"):
            bid = self.path[len("/api/export/"):]
            if not ID_RE.match(bid):
                return self._json({"error": "bad id"}, 400)
            try:
                zpath, name = boards_store.export_board(bid)
            except Exception as e:
                return self._json({"error": str(e)}, 404)
            try:
                fname = re.sub(r"[^A-Za-z0-9 ._-]", "_", name) + " (wordfinder).zip"
                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
                self.send_header("Content-Length", str(os.path.getsize(zpath)))
                self.end_headers()
                with open(zpath, "rb") as f:
                    shutil.copyfileobj(f, self.wfile)
            finally:
                os.remove(zpath)
            return
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/add_board":
            ln = int(self.headers.get("Content-Length") or 0)
            payload = {}
            if ln:
                try:
                    payload = json.loads(self.rfile.read(ln) or b"{}")
                except Exception:
                    payload = {}
            if not LOCK.acquire(blocking=False):
                return self._json({"started": False, "msg": "A board is already being processed."}, 409)
            set_status(state="starting", msg="Starting...", done=0, total=0,
                       board_id=None, board_name=None)
            threading.Thread(target=run_add_job,
                             kwargs={"path_hint": payload.get("path"), "name": payload.get("name")},
                             daemon=True).start()
            return self._json({"started": True})
        if self.path == "/api/import_board":
            ln = int(self.headers.get("Content-Length") or 0)
            payload = {}
            if ln:
                try:
                    payload = json.loads(self.rfile.read(ln) or b"{}")
                except Exception:
                    payload = {}
            if not LOCK.acquire(blocking=False):
                return self._json({"started": False, "msg": "A board is already being processed."}, 409)
            set_status(state="starting", msg="Starting...", done=0, total=0,
                       board_id=None, board_name=None)
            if payload.get("path"):
                p = payload["path"]
                threading.Thread(target=lambda: _import_path(p), daemon=True).start()
            else:
                threading.Thread(target=run_import_job, daemon=True).start()
            return self._json({"started": True})
        if self.path == "/api/delete_board":
            ln = int(self.headers.get("Content-Length") or 0)
            payload = {}
            if ln:
                try:
                    payload = json.loads(self.rfile.read(ln) or b"{}")
                except Exception:
                    payload = {}
            bid = payload.get("id", "")
            if not ID_RE.match(bid):
                return self._json({"error": "bad id"}, 400)
            try:
                boards_store.delete_board(bid)
            except Exception as e:
                return self._json({"error": str(e)}, 404)
            return self._json({"ok": True, "boards": boards_store.list_boards()})
        return self._json({"error": "unknown"}, 404)


def main():
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"Board Word Finder running at http://localhost:{PORT}/viewer.html")
    print("Keep this window open. Close it to stop.")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
