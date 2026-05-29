"""Opens a native 'choose folder' dialog and prints the chosen path.
Run as a subprocess by server.py so tkinter has its own main thread."""
import sys
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)
title = sys.argv[1] if len(sys.argv) > 1 else "Choose the folder with this board's photos"
path = filedialog.askdirectory(title=title)
root.destroy()
sys.stdout.write(path or "")
