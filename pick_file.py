"""Opens a native 'open file' dialog and prints the chosen path.
Run as a subprocess by server.py so tkinter has its own main thread."""
import sys
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
title = sys.argv[1] if len(sys.argv) > 1 else "Choose a board file to import"
path = filedialog.askopenfilename(
    title=title,
    filetypes=[("Word Finder board", "*.zip"), ("All files", "*.*")])
root.destroy()
sys.stdout.write(path or "")
