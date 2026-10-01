"""
Font2TTF - המרת קבצי פונט (OTF / WOFF / WOFF2 / TTF) ל-TTF, בקבוצות.
התקנה:  pip install fonttools brotli
אופציונלי (גרירת קבצים לחלון):  pip install tkinterdnd2
"""
import multiprocessing
import os
import queue
import threading
import tkinter as tk
from concurrent.futures import ProcessPoolExecutor, as_completed
from tkinter import filedialog, messagebox, ttk

from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    BaseTk = TkinterDnD.Tk
    HAS_DND = True
except Exception:
    BaseTk = tk.Tk
    HAS_DND = False

EXTS = {".ttf", ".otf", ".woff", ".woff2"}


# ---------- לוגיקת ההמרה ----------

def _otf_to_ttf(font, max_err=1.0):
    """המרת קווי מתאר CFF (קוביים) ל-glyf (ריבועיים)."""
    glyph_order = font.getGlyphOrder()
    gs = font.getGlyphSet()
    quad = {}
    for name in glyph_order:
        pen = TTGlyphPen(gs)
        gs[name].draw(Cu2QuPen(pen, max_err, reverse_direction=True))
        quad[name] = pen.glyph()

    font["loca"] = newTable("loca")
    font["glyf"] = glyf = newTable("glyf")
    glyf.glyphOrder = glyph_order
    glyf.glyphs = quad
    del font["CFF "]
    if "VORG" in font:
        del font["VORG"]
    glyf.compile(font)

    hmtx = font["hmtx"]
    for name, g in glyf.glyphs.items():
        if hasattr(g, "xMin"):
            hmtx[name] = (hmtx[name][0], g.xMin)

    font["maxp"] = maxp = newTable("maxp")
    maxp.tableVersion = 0x00010000
    maxp.maxZones = 1
    maxp.maxTwilightPoints = 0
    maxp.maxStorage = 0
    maxp.maxFunctionDefs = 0
    maxp.maxInstructionDefs = 0
    maxp.maxStackElements = 0
    maxp.maxSizeOfInstructions = 0
    maxp.maxComponentElements = max(
        (len(getattr(g, "components", [])) for g in glyf.glyphs.values()), default=0
    )

    post = font["post"]
    post.formatType = 2.0
    post.extraNames = []
    post.mapping = {}
    post.glyphOrder = glyph_order

    font.sfntVersion = "\x00\x01\x00\x00"


def convert_one(src, out_dir):
    """ממיר קובץ אחד. מחזיר (src, שגיאה או None)."""
    try:
        base = os.path.splitext(os.path.basename(src))[0]
        dst = os.path.join(out_dir, base + ".ttf")
        font = TTFont(src)
        font.flavor = None  # הסרת עטיפת WOFF/WOFF2
        if font.sfntVersion == "OTTO" and "CFF " in font:
            _otf_to_ttf(font)
        font.save(dst)
        font.close()
        return src, None
    except Exception as e:
        return src, str(e)


# ---------- ממשק ----------

class App(BaseTk):
    def __init__(self):
        super().__init__()
        self.title("Font2TTF")
        self.geometry("560x520")
        self.minsize(480, 420)
        self.files = []
        self.q = queue.Queue()
        self.busy = False

        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Button(top, text="הוסף קבצים", command=self.add_files).pack(side="right", padx=3)
        ttk.Button(top, text="הוסף תיקייה", command=self.add_folder).pack(side="right", padx=3)
        ttk.Button(top, text="נקה", command=self.clear).pack(side="left", padx=3)

        mid = ttk.Frame(self, padding=(10, 0))
        mid.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(mid, selectmode="extended", activestyle="none")
        sb = ttk.Scrollbar(mid, command=self.listbox.yview)
        self.listbox.config(yscrollcommand=sb.set)
        sb.pack(side="left", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)
        self.listbox.bind("<Delete>", self.remove_selected)

        if HAS_DND:
            self.listbox.drop_target_register(DND_FILES)
            self.listbox.dnd_bind("<<Drop>>", self.on_drop)

        out = ttk.Frame(self, padding=10)
        out.pack(fill="x")
        ttk.Label(out, text="תיקיית פלט:").pack(side="right")
        self.out_var = tk.StringVar()
        ttk.Entry(out, textvariable=self.out_var).pack(side="right", fill="x", expand=True, padx=5)
        ttk.Button(out, text="בחר…", command=self.pick_out).pack(side="right")

        bot = ttk.Frame(self, padding=(10, 0, 10, 10))
        bot.pack(fill="x")
        self.progress = ttk.Progressbar(bot, mode="determinate")
        self.progress.pack(fill="x", pady=(0, 6))
        self.status = ttk.Label(bot, text="הוסף קבצים כדי להתחיל" + (" (או גרור לכאן)" if HAS_DND else ""))
        self.status.pack(side="right")
        self.btn = ttk.Button(bot, text="המר ל-TTF", command=self.start)
        self.btn.pack(side="left")

    # --- ניהול רשימה ---
    def _add(self, paths):
        known = set(self.files)
        for p in paths:
            if os.path.splitext(p)[1].lower() in EXTS and p not in known:
                self.files.append(p)
                self.listbox.insert("end", os.path.basename(p))
                known.add(p)
        self.status.config(text=f"{len(self.files)} קבצים ברשימה")

    def add_files(self):
        self._add(filedialog.askopenfilenames(
            filetypes=[("Fonts", "*.ttf *.otf *.woff *.woff2"), ("All", "*.*")]))

    def add_folder(self):
        d = filedialog.askdirectory()
        if d:
            found = []
            for root, _, names in os.walk(d):
                found += [os.path.join(root, n) for n in sorted(names)]
            self._add(found)

    def on_drop(self, event):
        paths = []
        for p in self.tk.splitlist(event.data):
            if os.path.isdir(p):
                for root, _, names in os.walk(p):
                    paths += [os.path.join(root, n) for n in sorted(names)]
            else:
                paths.append(p)
        self._add(paths)

    def remove_selected(self, _=None):
        for i in reversed(self.listbox.curselection()):
            self.listbox.delete(i)
            del self.files[i]
        self.status.config(text=f"{len(self.files)} קבצים ברשימה")

    def clear(self):
        if not self.busy:
            self.files.clear()
            self.listbox.delete(0, "end")
            self.progress["value"] = 0
            self.status.config(text="הרשימה ריקה")

    def pick_out(self):
        d = filedialog.askdirectory()
        if d:
            self.out_var.set(d)

    # --- המרה ---
    def start(self):
        if self.busy or not self.files:
            return
        out_dir = self.out_var.get().strip()
        if not out_dir:
            out_dir = os.path.join(os.path.dirname(self.files[0]), "TTF")
            self.out_var.set(out_dir)
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError as e:
            messagebox.showerror("שגיאה", f"לא ניתן ליצור את תיקיית הפלט:\n{e}")
            return
        self.busy = True
        self.btn.config(state="disabled")
        self.progress.config(maximum=len(self.files), value=0)
        threading.Thread(target=self.worker, args=(list(self.files), out_dir), daemon=True).start()
        self.after(100, self.poll)

    def worker(self, files, out_dir):
        errors = []
        done = 0
        with ProcessPoolExecutor() as ex:
            futs = [ex.submit(convert_one, f, out_dir) for f in files]
            for fut in as_completed(futs):
                src, err = fut.result()
                done += 1
                if err:
                    errors.append((os.path.basename(src), err))
                self.q.put(("progress", done, len(files)))
        self.q.put(("done", errors, out_dir))

    def poll(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == "progress":
                    self.progress["value"] = msg[1]
                    self.status.config(text=f"{msg[1]} / {msg[2]}")
                else:
                    self.finish(msg[1], msg[2])
                    return
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def finish(self, errors, out_dir):
        self.busy = False
        self.btn.config(state="normal")
        ok = len(self.files) - len(errors)
        self.status.config(text=f"הסתיים: {ok} הומרו, {len(errors)} נכשלו")
        if errors:
            details = "\n".join(f"{n}: {e}" for n, e in errors[:15])
            messagebox.showwarning("הסתיים עם שגיאות", f"{ok} הומרו.\n\nנכשלו:\n{details}")
        else:
            if messagebox.askyesno("הסתיים", f"{ok} קבצים הומרו בהצלחה.\nלפתוח את התיקייה?"):
                try:
                    os.startfile(out_dir)  # Windows
                except AttributeError:
                    import subprocess, sys
                    subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", out_dir])


if __name__ == "__main__":
    multiprocessing.freeze_support()  # נדרש ל-PyInstaller ב-Windows
    App().mainloop()
