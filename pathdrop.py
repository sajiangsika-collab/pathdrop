# -*- coding: utf-8 -*-
"""
路径抓取器 PathDrop  v1.1
把电脑上的任何东西（文件 / 视频 / 图片 / 文件夹 / 程序 ...）拖进窗口，
立刻显示它的完整路径，支持一键复制。

v1.1 新增：列头排序 · 详情面板（图片分辨率 / 视频时长）· SHA256 校验值 ·
           复制后自动收起 · Esc 收起 · 再次打开程序自动唤回已运行的窗口

运行：python pathdrop.py
"""

import os
import re
import sys
import json
import csv
import glob
import time
import queue
import shutil
import socket
import hashlib
import datetime
import threading
import subprocess
import urllib.parse
import webbrowser
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk, filedialog, messagebox

from tkinterdnd2 import TkinterDnD, DND_FILES, DND_TEXT

APP_NAME = "路径抓取器 PathDrop"
APP_VER = "1.4"
PORT = 51943

IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"

# ---------------- 配色（浅色主题） ----------------
C_BG = "#F5F6F8"
C_PANEL = "#FFFFFF"
C_BORDER = "#DDE1E7"
C_TEXT = "#1F2329"
C_MUTED = "#8A9099"
C_ACCENT = "#2F6FED"
C_ACCENT_SOFT = "#EAF1FE"
C_HOVER = "#F0F2F5"

# 字体在运行时按系统可用字体挑（Windows / macOS / Linux 都能显示中文）
FONT_FAMILY = "Microsoft YaHei UI"
FONT_MONO_FAMILY = "Consolas"
FONT_UI = (FONT_FAMILY, 10)
FONT_UI_S = (FONT_FAMILY, 9)
FONT_TITLE = (FONT_FAMILY, 15, "bold")
FONT_MONO = (FONT_MONO_FAMILY, 10)

TYPE_RULES = [
    ("视频", "#B45309", {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v",
                     ".mpg", ".mpeg", ".ts", ".m2ts", ".rmvb", ".rm", ".3gp", ".vob", ".asf"}),
    ("音频", "#7C3AED", {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".aiff", ".ape", ".opus"}),
    ("图片", "#0E7490", {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg", ".tif", ".tiff",
                     ".heic", ".ico", ".raw", ".cr2", ".nef", ".arw", ".psd", ".ai"}),
    ("文档", "#1D4ED8", {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md",
                     ".csv", ".rtf", ".epub", ".mobi", ".pages", ".numbers", ".key", ".odt"}),
    ("压缩包", "#6B7280", {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso", ".cab"}),
    ("程序", "#B91C1C", {".exe", ".msi", ".bat", ".cmd", ".com", ".dll", ".lnk", ".apk", ".appx"}),
    ("代码", "#0F766E", {".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yml", ".yaml",
                     ".java", ".c", ".cpp", ".h", ".go", ".rs", ".php", ".sh", ".sql", ".ipynb"}),
]
EXT2TYPE = {}
for _n, _c, _es in TYPE_RULES:
    for _e in _es:
        EXT2TYPE[_e] = (_n, _c)

TYPE_OTHER = ("其他", "#4B5563")
TYPE_DIR = ("文件夹", "#15803D")
TYPE_URL = ("网址", "#1A73E8")

IMG_EXT = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
AV_EXT = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg",
          ".mpeg", ".ts", ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma"}


def res_path(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def config_dir():
    """各系统的用户配置目录"""
    if IS_WIN:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        return os.path.join(base, "PathDrop")
    if IS_MAC:
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "PathDrop")
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "pathdrop")


def downloads_dir():
    p = os.path.join(os.path.expanduser("~"), "Downloads")
    if os.path.isdir(p):
        return p
    p2 = os.path.join(os.path.expanduser("~"), "下载")
    return p2 if os.path.isdir(p2) else p


def open_default(path):
    """用系统默认程序打开（跨平台）"""
    if IS_WIN:
        os.startfile(path)                      # noqa: S606
    elif IS_MAC:
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def reveal_path(path):
    """在文件管理器里定位文件（跨平台）"""
    path = os.path.abspath(path)
    if IS_WIN:
        subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
    elif IS_MAC:
        subprocess.Popen(["open", "-R", path])
    else:
        subprocess.Popen(["xdg-open", path if os.path.isdir(path) else os.path.dirname(path)])


def init_fonts(root):
    """按系统实际可用字体挑一组，保证三平台都能正常显示中文"""
    global FONT_FAMILY, FONT_MONO_FAMILY, FONT_UI, FONT_UI_S, FONT_TITLE, FONT_MONO
    try:
        fams = set(tkfont.families(root))
    except Exception:
        return
    for cand in ("Microsoft YaHei UI", "微软雅黑", "PingFang SC", "Hiragino Sans GB",
                 "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei",
                 "Noto Sans CJK JP", "DejaVu Sans", "Helvetica"):
        if cand in fams:
            FONT_FAMILY = cand
            break
    for cand in ("Consolas", "Menlo", "DejaVu Sans Mono", "Courier New"):
        if cand in fams:
            FONT_MONO_FAMILY = cand
            break
    FONT_UI = (FONT_FAMILY, 10)
    FONT_UI_S = (FONT_FAMILY, 9)
    FONT_TITLE = (FONT_FAMILY, 15, "bold")
    FONT_MONO = (FONT_MONO_FAMILY, 10)


CONFIG_DIR = config_dir()
SETTING_FILE = os.path.join(CONFIG_DIR, "setting.json")
try:
    os.makedirs(CONFIG_DIR, exist_ok=True)
except OSError:
    pass


def pkey(path):
    return os.path.normcase(os.path.normpath(path))


# ---------------- 从一段文字里辨认路径 ----------------
_WRAP_PAIRS = [('"', '"'), ("'", "'"), ("“", "”"), ("‘", "’"), ("「", "」"), ("『", "』"),
               ("《", "》"), ("<", ">"), ("【", "】"), ("(", ")"), ("（", "）"),
               ("[", "]"), ("{", "}")]
_TAIL_JUNK = "，。；、！？：）)】》>”\"'’…,.;:!?)]}"


def _strip_wrap(s):
    """去掉包裹的引号/括号，以及句末的标点"""
    s = str(s).strip().lstrip("\ufeff")
    changed = True
    while changed and len(s) > 2:
        changed = False
        for a, b in _WRAP_PAIRS:
            if s.startswith(a) and s.endswith(b) and len(s) > 2:
                s = s[1:-1].strip()
                changed = True
                break
    return s.strip().rstrip(_TAIL_JUNK).strip()


def _to_local(s):
    """file:///C:/x、%USERPROFILE%\\x、/C:/x 统一成本地路径"""
    s = str(s).strip()
    if s[:5].lower() == "file:":
        s = s[5:]
        if s.startswith("///"):
            s = s[3:]
        elif s.startswith("//"):
            s = s[2:]
        s = urllib.parse.unquote(s)
    s = os.path.expandvars(os.path.expanduser(s))
    if re.match(r"^/[A-Za-z]:", s):
        s = s[1:]
    return s


def _norm(p):
    try:
        return os.path.normpath(p)
    except Exception:
        return p


_ABS_PATH_RE = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:[\\/]|\\\\)[^\r\n\t]*")
_POSIX_PATH_RE = re.compile(r"(?<![A-Za-z0-9:/])(?:~?/(?:[^\s\"'<>，。；）】》”]+))" )
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")
_DRIVE_ROOT_RE = re.compile(r"^[A-Za-z]:[\\/]?$")


def _too_short(p):
    """盘符根目录（D:\\）、空路径之类的不算有效路径"""
    return (not p) or len(p) <= 4 or bool(_DRIVE_ROOT_RE.match(p))


# ---------------- 网址 ----------------
_URL_RE = re.compile(r"(?<![A-Za-z0-9])("
                     r"(?:https?|ftp|file)://[^\s\"'<>，。；）】》”]+"
                     r"|www\.[^\s\"'<>，。；）】》”]+)", re.I)


def is_url(s):
    s = str(s).strip()
    if _SCHEME_RE.match(s):
        return s[:5].lower() != "file:"      # file:/// 当本地路径处理
    return bool(re.match(r"^www\.", s, re.I))


def url_parts(url):
    u = str(url).strip()
    if u.lower().startswith("www."):
        u = "http://" + u
    try:
        p = urllib.parse.urlsplit(u)
        host = p.netloc
        name = urllib.parse.unquote(os.path.basename(p.path.rstrip("/")))
        return {"scheme": p.scheme, "host": host, "name": name,
                "path": p.path, "query": p.query}
    except Exception:
        return {"scheme": "", "host": "", "name": "", "path": "", "query": ""}


def url_filename(url):
    return url_parts(url)["name"]


def local_candidates(url, limit=3):
    """按网址里推断的文件名，去 下载/桌面/主目录 找同名的本地文件"""
    name = url_filename(url)
    if not name or len(name) < 2:
        return []
    stem, ext = os.path.splitext(name)
    home = os.path.expanduser("~")
    desk = os.path.join(home, "Desktop")
    if not os.path.isdir(desk):
        desk = os.path.join(home, "桌面")
    dirs = [downloads_dir(), desk, home]
    hits = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for pat in (name, f"{stem} (*){ext}", f"{stem}(*){ext}", f"{stem}*{ext}"):
            try:
                for p in glob.glob(os.path.join(d, pat)):
                    if os.path.isfile(p) and p not in hits:
                        hits.append(p)
            except Exception:
                pass
    hits = [p for p in hits if os.path.basename(p) == name or
            re.match(r"^" + re.escape(stem) + r"[ (]*\d*\)?" + re.escape(ext) + "$",
                     os.path.basename(p), re.I)]
    hits.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0, reverse=True)
    return hits[:limit]


def guess_paths(text):
    """从任意文字里抽出路径和网址。
    返回 (本机存在的路径, 看着像路径但不存在, 网址)"""
    found, guess, urls = [], [], []

    def push(lst, p):
        if p and p not in lst:
            lst.append(p)

    for line in str(text).replace("\r\n", "\n").split("\n"):
        line = line.strip()
        if not line:
            continue

        # 0) 网址（一行里可能混着好几个）
        for m in _URL_RE.finditer(line):
            u = _strip_wrap(m.group(1))
            if is_url(u):
                push(urls, u)
        if urls and _SCHEME_RE.match(line) and not _ABS_PATH_RE.search(line):
            continue

        # 1) 整行就是一个路径
        whole = _norm(_to_local(_strip_wrap(line)))
        if whole and os.path.exists(whole) and not _too_short(whole):
            push(found, whole)
            continue

        # 2) 路径混在句子里：从盘符/UNC 起截取，从长到短试，命中就收
        hit = False
        segs = [m.group(0) for m in _ABS_PATH_RE.finditer(line)]
        if not IS_WIN:            # macOS / Linux 的 /Users/... 、~/... 写法
            segs += [m.group(0) for m in _POSIX_PATH_RE.finditer(line)]
        for seg in segs:
            for cut in range(len(seg), 2, -1):
                cand = _norm(_to_local(_strip_wrap(seg[:cut])))
                if _too_short(cand) or not os.path.exists(cand):
                    continue
                push(found, cand)
                hit = True
                break
            if hit:
                break
        if hit:
            continue

        # 3) 本机不存在：仍然保留“像路径”的东西（方便复制），标为已不存在
        cand = _norm(_to_local(_strip_wrap(line)))
        looks_abs = bool(_ABS_PATH_RE.match(cand)) or (not IS_WIN and cand.startswith("/"))
        if looks_abs and not _too_short(cand):
            push(guess, cand)
        else:
            m = _ABS_PATH_RE.search(line)
            if m:
                cand = _norm(_to_local(_strip_wrap(m.group(0))))
                if not _too_short(cand):
                    push(guess, cand)

    return found, guess, urls


def classify(path):
    if os.path.isdir(path):
        return TYPE_DIR
    return EXT2TYPE.get(os.path.splitext(path)[1].lower(), TYPE_OTHER)


def human_size(n):
    if n is None:
        return "-"
    if n < 1024:
        return f"{n} B"
    for unit in ("KB", "MB", "GB", "TB"):
        n /= 1024.0
        if n < 1024:
            return f"{n:.1f} {unit}" if n < 100 else f"{n:.0f} {unit}"
    return f"{n:.0f} PB"


def human_time(sec):
    sec = int(sec)
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def folder_size(path, limit=4000):
    total, count = 0, 0
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
                count += 1
                if count >= limit:
                    return total
    except OSError:
        pass
    return total


def image_size(path):
    """纯 Python 读图片头拿宽高，不依赖 Pillow"""
    try:
        with open(path, "rb") as f:
            h = f.read(32)
            if len(h) < 26:
                return None
            if h[:8] == b"\x89PNG\r\n\x1a\n":
                return int.from_bytes(h[16:20], "big"), int.from_bytes(h[20:24], "big")
            if h[:6] in (b"GIF87a", b"GIF89a"):
                return int.from_bytes(h[6:8], "little"), int.from_bytes(h[8:10], "little")
            if h[:2] == b"BM":
                return int.from_bytes(h[18:22], "little"), int.from_bytes(h[22:26], "little")
            if h[:4] == b"RIFF" and h[8:12] == b"WEBP":
                if h[12:16] == b"VP8X":
                    return (1 + int.from_bytes(h[24:27], "little"),
                            1 + int.from_bytes(h[27:30], "little"))
            if h[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    b = f.read(1)
                    if not b:
                        break
                    if b != b"\xff":
                        continue
                    m = f.read(1)
                    while m == b"\xff":
                        m = f.read(1)
                    if not m:
                        break
                    if m[0] in (0xD8, 0xD9) or 0xD0 <= m[0] <= 0xD7 or m[0] == 0x01:
                        continue
                    ln = int.from_bytes(f.read(2), "big")
                    if 0xC0 <= m[0] <= 0xCF and m[0] not in (0xC4, 0xC8, 0xCC):
                        d = f.read(5)
                        return int.from_bytes(d[3:5], "big"), int.from_bytes(d[1:3], "big")
                    f.seek(max(ln - 2, 1), 1)
    except Exception:
        pass
    return None


def media_duration(path):
    """装了 ffprobe 才读得到时长，没有就返回 None"""
    exe = shutil.which("ffprobe")
    if not exe:
        return None
    try:
        kw = {"creationflags": 0x08000000} if IS_WIN else {}
        out = subprocess.run([exe, "-v", "error", "-show_entries", "format=duration",
                              "-of", "default=nw=1:nk=1", path],
                             capture_output=True, text=True, timeout=4, **kw)
        return float(out.stdout.strip())
    except Exception:
        return None


class PathDrop(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.items = []
        self.index_of = {}
        self.settings = self.load_settings()
        self.sort_col, self.sort_rev = None, False
        self._hash_cache = {}
        self._ui_q = queue.Queue()

        self.title(f"{APP_NAME}  v{APP_VER}")
        self.configure(bg=C_BG)
        self.geometry(self.settings.get("geometry", "1120x760"))
        self.minsize(880, 560)
        self.topmost_var = tk.BooleanVar(value=bool(self.settings.get("topmost", False)))
        self.recursive_var = tk.BooleanVar(value=bool(self.settings.get("recursive", False)))
        self.collapse_var = tk.BooleanVar(value=bool(self.settings.get("collapse_after_copy", False)))
        self.attributes("-topmost", bool(self.topmost_var.get()))
        init_fonts(self)
        # 图标：Windows 用 .ico；macOS / Linux 用 .png
        if IS_WIN:
            try:
                self.iconbitmap(res_path("app.ico"))
            except Exception:
                pass
        else:
            try:
                self._icon_img = tk.PhotoImage(file=res_path("app.png"))
                self.iconphoto(True, self._icon_img)
            except Exception:
                pass

        self._build_style()
        self._build_ui()
        self._center()
        self._bind_dnd()
        self._bind_keys()
        self._pump_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _pump_ui(self):
        """把后台线程的结果安全地搬到主线程执行"""
        while True:
            try:
                fn = self._ui_q.get_nowait()
            except queue.Empty:
                break
            try:
                fn()
            except Exception:
                pass
        self.after(120, self._pump_ui)

    # ---------------- 配置 ----------------
    def load_settings(self):
        for p in (SETTING_FILE, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                             "pathdrop_setting.json")):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                continue
        return {}

    def save_settings(self):
        try:
            data = {"geometry": self.geometry(),
                    "topmost": bool(self.topmost_var.get()),
                    "recursive": bool(self.recursive_var.get()),
                    "collapse_after_copy": bool(self.collapse_var.get())}
            with open(SETTING_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth() - w) // 2
        y = max(30, (self.winfo_screenheight() - h) // 2 - 40)
        self.geometry(f"+{x}+{y}")

    # ---------------- 样式 ----------------
    def _build_style(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except tk.TclError:
            pass
        st.configure("Treeview", background=C_PANEL, fieldbackground=C_PANEL, foreground=C_TEXT,
                     rowheight=28, borderwidth=0, font=FONT_UI)
        st.configure("Treeview.Heading", background="#F0F2F5", foreground=C_MUTED,
                     relief="flat", font=(FONT_FAMILY, 9, "bold"), padding=(8, 6))
        st.map("Treeview", background=[("selected", C_ACCENT_SOFT)], foreground=[("selected", C_TEXT)])
        st.map("Treeview.Heading", background=[("active", "#E8EBF0")])
        st.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        st.configure("Vertical.TScrollbar", background="#E3E6EB", troughcolor=C_PANEL,
                     borderwidth=0, arrowsize=12)
        st.configure("Horizontal.TScrollbar", background="#E3E6EB", troughcolor=C_PANEL,
                     borderwidth=0, arrowsize=12)

    def _btn(self, parent, text, cmd, primary=False):
        bg, fg, abg = (C_ACCENT, "#FFFFFF", "#275FD0") if primary else (C_PANEL, C_TEXT, C_HOVER)
        return tk.Button(parent, text=text, command=cmd, font=FONT_UI_S, bg=bg, fg=fg,
                         activebackground=abg, activeforeground=fg, relief="flat", bd=0,
                         padx=12, pady=6, cursor="hand2", highlightthickness=1,
                         highlightbackground=C_BORDER, highlightcolor=C_BORDER)

    # ---------------- 界面 ----------------
    def _build_ui(self):
        head = tk.Frame(self, bg=C_BG)
        head.pack(fill="x", padx=18, pady=(12, 4))
        tk.Label(head, text="把文件拖进来，路径自动出现", bg=C_BG, fg=C_TEXT,
                 font=FONT_TITLE).pack(anchor="w")
        tk.Label(head, text="文件 / 视频 / 图片 / 文件夹直接拖进来；文字里的路径、网页链接也能拖进来识别",
                 bg=C_BG, fg=C_MUTED, font=FONT_UI_S).pack(anchor="w", pady=(2, 0))

        # 拖拽区
        self.dropzone = tk.Frame(self, bg=C_PANEL, height=94,
                                 highlightthickness=2, highlightbackground="#C9D3E4")
        self.dropzone.pack(fill="x", padx=18, pady=(8, 8))
        self.dropzone.pack_propagate(False)
        self.dz_icon = tk.Label(self.dropzone, text="↓", bg=C_PANEL, fg=C_ACCENT,
                                font=(FONT_FAMILY, 20))
        self.dz_icon.pack(pady=(8, 0))
        self.dz_text = tk.Label(self.dropzone, text="拖文件 / 文件夹 / 文字路径 / 网页链接，都行",
                                bg=C_PANEL, fg=C_TEXT, font=(FONT_FAMILY, 11))
        self.dz_text.pack()
        self.dz_hint = tk.Label(self.dropzone, text="或点这里选择文件",
                                bg=C_PANEL, fg=C_ACCENT, font=(FONT_FAMILY, 9, "underline"),
                                cursor="hand2")
        self.dz_hint.pack(pady=(2, 4))
        for w in (self.dropzone, self.dz_icon, self.dz_text, self.dz_hint):
            w.bind("<Button-1>", lambda e: self.pick_files())

        # 列表
        table_wrap = tk.Frame(self, bg=C_BORDER)
        table_wrap.pack(fill="both", expand=True, padx=18)
        cols = ("idx", "name", "type", "size", "mtime", "path")
        self.tree = ttk.Treeview(table_wrap, columns=cols, show="headings", selectmode="extended")
        self.heads = {"idx": ("#", 42), "name": ("名称", 200), "type": ("类型", 64),
                      "size": ("大小", 84), "mtime": ("修改时间", 126), "path": ("完整路径", 460)}
        for c in cols:
            text, width = self.heads[c]
            self.tree.heading(c, text=text, command=lambda cc=c: self.sort_by(cc))
            anchor = "center" if c in ("idx", "type", "mtime") else ("e" if c == "size" else "w")
            self.tree.column(c, width=width, minwidth=40, anchor=anchor, stretch=(c == "path"))
        vs = ttk.Scrollbar(table_wrap, orient="vertical", command=self.tree.yview)
        hs = ttk.Scrollbar(table_wrap, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        table_wrap.rowconfigure(0, weight=1)
        table_wrap.columnconfigure(0, weight=1)
        self.tree.bind("<Double-1>", self.on_double)
        self.tree.bind("<Button-3>", self.on_right_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.empty_tip = tk.Label(self.tree, text="列表还是空的", bg=C_PANEL, fg="#B9BEC7",
                                  font=(FONT_FAMILY, 11))

        # 详情面板
        det = tk.Frame(self, bg=C_BG)
        det.pack(fill="x", padx=18, pady=(8, 0))
        top = tk.Frame(det, bg=C_BG)
        top.pack(fill="x")
        tk.Label(top, text="完整路径", bg=C_BG, fg=C_MUTED, font=FONT_UI_S).pack(side="left")
        tk.Button(top, text="算 SHA256", command=self.calc_sha, font=(FONT_FAMILY, 8),
                  bg=C_BG, fg=C_ACCENT, activebackground=C_BG, activeforeground=C_ACCENT,
                  relief="flat", bd=0, cursor="hand2").pack(side="right")
        self.preview_var = tk.StringVar(value="")
        self.preview = tk.Entry(det, textvariable=self.preview_var, font=FONT_MONO, bg=C_PANEL,
                                fg=C_TEXT, relief="flat", bd=0, highlightthickness=1,
                                highlightbackground=C_BORDER, highlightcolor=C_ACCENT,
                                readonlybackground=C_PANEL, state="readonly")
        self.preview.pack(fill="x", ipady=5, pady=(2, 3))
        self.info_var = tk.StringVar(value="—")
        tk.Label(det, textvariable=self.info_var, bg=C_BG, fg=C_MUTED, font=FONT_UI_S,
                 anchor="w", justify="left", wraplength=1060).pack(fill="x")

        # 工具栏
        bar = tk.Frame(self, bg=C_BG)
        bar.pack(fill="x", padx=18, pady=(8, 2))
        self._btn(bar, "复制选中路径", self.copy_selected, True).pack(side="left")
        for t, c in (("复制全部", self.copy_all), ("复制为 CSV", self.copy_csv),
                     ("打开所在位置", self.open_location), ("导出列表", self.export_list),
                     ("清空", self.clear_all)):
            self._btn(bar, t, c).pack(side="left", padx=(8, 0))

        opts = tk.Frame(bar, bg=C_BG)
        opts.pack(side="right")
        for text, var, cmd in (("窗口置顶", self.topmost_var, self.toggle_topmost),
                               ("展开文件夹内容", self.recursive_var, self.save_settings),
                               ("复制后收起", self.collapse_var, self.save_settings)):
            tk.Checkbutton(opts, text=text, variable=var, bg=C_BG, fg=C_TEXT, activebackground=C_BG,
                           activeforeground=C_TEXT, selectcolor=C_PANEL, font=FONT_UI_S, bd=0,
                           highlightthickness=0, cursor="hand2", command=cmd).pack(side="left", padx=(10, 0))

        self.status_var = tk.StringVar(value="等待拖入…")
        tk.Label(self, textvariable=self.status_var, bg=C_BG, fg=C_MUTED, font=FONT_UI_S,
                 anchor="w").pack(fill="x", padx=18, pady=(2, 8))

        self.menu = tk.Menu(self, tearoff=0, font=FONT_UI_S)
        self.menu.add_command(label="复制路径", command=self.copy_selected)
        self.menu.add_command(label="复制文件名", command=self.copy_names)
        self.menu.add_command(label="复制 SHA256", command=self.calc_sha)
        self.menu.add_command(label="在浏览器打开", command=self.open_url)
        self.menu.add_command(label="打开所在位置", command=self.open_location)
        self.menu.add_separator()
        self.menu.add_command(label="从列表移除", command=self.remove_selected)
        self.update_empty_tip()

    def update_empty_tip(self):
        if self.items:
            self.empty_tip.place_forget()
        else:
            self.empty_tip.place(relx=0.5, rely=0.42, anchor="center")

    # ---------------- 拖拽 / 快捷键 ----------------
    def _bind_dnd(self):
        for w in (self, self.dropzone, self.tree):
            try:
                w.drop_target_register(DND_FILES, DND_TEXT)
                w.dnd_bind("<<Drop>>", self.on_drop)
                w.dnd_bind("<<DropEnter>>", self.on_drag_enter)
                w.dnd_bind("<<DropLeave>>", self.on_drag_leave)
            except Exception:
                pass

    def _bind_keys(self):
        self.bind("<Control-c>", lambda e: self.copy_selected())
        self.bind("<Control-a>", lambda e: self.select_all())
        self.bind("<Control-v>", self.paste_paths)
        self.bind("<Delete>", lambda e: self.remove_selected())
        self.bind("<Escape>", lambda e: self.collapse())

    def on_drag_enter(self, event=None):
        self.dropzone.configure(highlightbackground=C_ACCENT, bg=C_ACCENT_SOFT)
        for w in (self.dz_icon, self.dz_text, self.dz_hint):
            w.configure(bg=C_ACCENT_SOFT)
        self.dz_text.configure(text="松手即可获取路径")

    def on_drag_leave(self, event=None):
        self.dropzone.configure(highlightbackground="#C9D3E4", bg=C_PANEL)
        for w in (self.dz_icon, self.dz_text, self.dz_hint):
            w.configure(bg=C_PANEL)
        self.dz_text.configure(text="拖文件 / 文件夹 / 文字路径 / 网页链接，都行")

    def on_drop(self, event):
        self.on_drag_leave()
        raw = getattr(event, "data", "")
        dtype = str(getattr(event, "type", "") or "")
        if isinstance(raw, (tuple, list)):      # 少数情况下会拿到多段数据
            raw = " ".join(str(x) for x in raw)
        text = str(raw)

        # 文件/文件夹拖入
        if "Files" in dtype or (text.lstrip().startswith("{") and text.rstrip().endswith("}")):
            paths = self._split_files(text)
            if paths:
                self.add_paths(paths)
                return
        # 文字拖入（从聊天、文档、浏览器里拖一段路径过来）
        self.add_from_text(text)

    def _split_files(self, raw):
        try:
            return [p for p in self.tk.splitlist(raw) if str(p).strip()]
        except Exception:
            s = str(raw).strip()
            if s.startswith("{") and s.endswith("}"):
                s = s[1:-1]
            return [s] if s else []

    def add_from_text(self, text, quiet=False):
        """把一段文字里的路径 / 网址识别出来加入列表"""
        found, guess, urls = guess_paths(text)
        if found or urls:
            self.add_paths(found + urls)
            return True
        if guess:
            self.add_paths(guess)
            self.status_var.set(
                f"这段文字里有 {len(guess)} 个像路径的内容，但本机找不到，已按原样列出（表中标为「已不存在」）")
            return True
        if not quiet:
            self.status_var.set("拖进来的文字里没认出路径或网址；可以直接拖文件本身，或用 Ctrl+V 粘贴")
        return False

    def pick_files(self):
        paths = filedialog.askopenfilenames(title="选择文件（可多选）")
        if paths:
            self.add_paths(list(paths))

    # ---------------- 数据 ----------------
    def add_paths(self, paths):
        added, skipped, t0 = 0, 0, time.time()
        walked = []
        for p in paths:
            p = str(p).strip()
            if not p:
                continue
            if is_url(p):                     # 网址原样收下，不参与路径规范化
                walked.append(p)
                continue
            p = os.path.normpath(p)
            if self.recursive_var.get() and os.path.isdir(p):
                walked.append(p)
                try:
                    for root, dirs, files in os.walk(p):
                        for n in dirs + files:
                            walked.append(os.path.join(root, n))
                except OSError:
                    pass
            else:
                walked.append(p)

        for p in walked:
            it = self.make_item(p)
            k = it["key"]
            if k in self.index_of:
                skipped += 1
                continue
            self.items.append(it)
            self.index_of[k] = len(self.items) - 1
            added += 1

        self.refresh_tree()
        msg = f"新增 {added} 项"
        if skipped:
            msg += f"，跳过重复 {skipped} 项"
        self.status_var.set(f"{msg} · 耗时 {(time.time() - t0) * 1000:.0f} ms")

    def make_item(self, path):
        path = str(path)
        if is_url(path):
            parts = url_parts(path)
            name = parts["name"] or parts["host"] or path
            return {"path": path, "name": name, "type": TYPE_URL[0], "color": TYPE_URL[1],
                    "size": None, "mtime": None, "exists": True, "kind": "url",
                    "key": "url:" + path.lower(), "host": parts["host"],
                    "ext": os.path.splitext(parts["name"])[1].lower()}
        name = os.path.basename(path) or path
        tname, color = classify(path)
        exists = os.path.exists(path)
        size = mtime = None
        if exists:
            try:
                st = os.stat(path)
                mtime = st.st_mtime
                size = folder_size(path) if os.path.isdir(path) else st.st_size
            except OSError:
                pass
        return {"path": path, "name": name, "type": tname, "color": color,
                "size": size, "mtime": mtime, "exists": exists, "kind": "file",
                "key": pkey(path), "ext": os.path.splitext(path)[1].lower()}

    # ---------------- 排序 ----------------
    def sort_by(self, col):
        if self.sort_col == col:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_col, self.sort_rev = col, False
        self.refresh_tree()

    def _sorted_items(self):
        c, rev = self.sort_col, self.sort_rev
        if c is None:
            return list(self.items)
        keys = {"name": lambda it: it["name"].lower(),
                "type": lambda it: it["type"],
                "size": lambda it: it["size"] or 0,
                "mtime": lambda it: it["mtime"] or 0,
                "path": lambda it: it["path"].lower()}
        if c == "idx":
            return list(self.items)
        return sorted(self.items, key=keys[c], reverse=rev)

    # ---------------- 渲染 ----------------
    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        rows = self._sorted_items()
        self.index_of.clear()
        for i, it in enumerate(rows, 1):
            self.index_of[it["key"]] = i - 1
            mt = (datetime.datetime.fromtimestamp(it["mtime"]).strftime("%Y-%m-%d %H:%M")
                  if it["mtime"] else "—")
            if it["kind"] == "url":
                mt = "—"
            elif not it["exists"]:
                mt = "（已不存在）"
            size_txt = human_size(it["size"])
            if it["kind"] == "url":
                size_txt = "—"
            if it["type"] == "文件夹" and it["size"] is not None:
                size_txt = "≥" + size_txt
            self.tree.insert("", "end", iid=f"r{i}",
                             values=(i, it["name"], it["type"], size_txt, mt, it["path"]),
                             tags=(f"t{i}",))
            self.tree.tag_configure(f"t{i}", foreground=it["color"] if it["exists"] else "#B9BEC7")
        self._refresh_headings()
        self.update_empty_tip()
        self.update_stats()

    def _refresh_headings(self):
        for c, (text, _w) in self.heads.items():
            arrow = ""
            if c == self.sort_col and c != "idx":
                arrow = " ▾" if self.sort_rev else " ▴"
            self.tree.heading(c, text=text + arrow)

    def update_stats(self):
        if not self.items:
            self.status_var.set("等待拖入…")
            self.preview_var.set("")
            self.info_var.set("—")
            return
        total = sum((it["size"] or 0) for it in self.items)
        cnt = {}
        for it in self.items:
            cnt[it["type"]] = cnt.get(it["type"], 0) + 1
        detail = " · ".join(f"{k} {v}" for k, v in sorted(cnt.items(), key=lambda x: -x[1]))
        self.status_var.set(f"共 {len(self.items)} 项 · 合计 {human_size(total)} · {detail}")

    def selected_paths(self):
        out = []
        for iid in self.tree.selection():
            vals = self.tree.item(iid, "values")
            if vals and len(vals) >= 6:
                out.append(vals[5])
        return out

    def _selected_items(self):
        """选中行对应的数据项（路径 / 网址都支持）"""
        out = []
        for iid in self.tree.selection():
            vals = self.tree.item(iid, "values")
            if not vals or len(vals) < 6:
                continue
            raw = vals[5]
            k = ("url:" + raw.lower()) if is_url(raw) else pkey(raw)
            it = next((x for x in self.items if x["key"] == k), None)
            if it:
                out.append(it)
        return out

    def on_select(self, event=None):
        paths = self.selected_paths()
        if not paths:
            self.preview_var.set("")
            self.info_var.set("—" if not self.items else "选中一行查看详情")
            return
        self.preview_var.set(paths[0] if len(paths) == 1 else f"已选中 {len(paths)} 项")
        if len(paths) > 1:
            total = 0
            for p in paths:
                try:
                    total += os.path.getsize(p)
                except OSError:
                    pass
            self.info_var.set(f"已选中 {len(paths)} 项 · 合计 {human_size(total)}")
            return
        p = paths[0]
        bits = []
        it = next((x for x in self.items if x["key"] == (("url:" + p.lower()) if is_url(p) else pkey(p))), None)

        # 网址：显示域名、推断文件名，并去下载目录里找同名本地文件
        if it and it["kind"] == "url":
            parts = url_parts(p)
            bits.append("网址")
            if parts["host"]:
                bits.append(parts["host"])
            if parts["name"]:
                bits.append(f"文件名 {parts['name']}")
            cands = local_candidates(p)
            if cands:
                cand = cands[0]
                try:
                    t = datetime.datetime.fromtimestamp(os.path.getmtime(cand)).strftime("%m-%d %H:%M")
                except OSError:
                    t = "—"
                bits.append(f"本地同名文件 {cand}（{t}）")
                if len(cands) > 1:
                    bits.append(f"另有 {len(cands) - 1} 个候选")
            else:
                bits.append("下载 / 桌面里没找到同名文件")
            self.info_var.set(" · ".join(bits))
            return

        if it:
            bits.append(it["type"])
            bits.append(human_size(it["size"]))
            if it["mtime"]:
                bits.append(datetime.datetime.fromtimestamp(it["mtime"]).strftime("%Y-%m-%d %H:%M:%S"))
        ext = os.path.splitext(p)[1].lower()
        if ext in IMG_EXT:
            wh = image_size(p)
            if wh and wh[0] and wh[1]:
                bits.append(f"{wh[0]} × {wh[1]} 像素")
        elif ext in AV_EXT:
            dur = media_duration(p)
            if dur:
                bits.append(f"时长 {human_time(dur)}")
            else:
                bits.append("时长需装 ffprobe 才能读")
        if it and it["key"] in self._hash_cache:
            bits.append("SHA256 " + self._hash_cache[it["key"]])
        self.info_var.set(" · ".join(bits) if bits else "—")

    # ---------------- 复制 / 导出 ----------------
    def _copy(self, text, tip):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set(f"{tip}（已复制到剪贴板）")
        if self.collapse_var.get():
            self.after(300, self.collapse)

    def copy_selected(self):
        paths = self.selected_paths()
        if not paths:
            self.status_var.set("先选中一行，或直接点「复制全部」")
            return
        self._copy("\n".join(paths), f"已复制 {len(paths)} 条路径")

    def copy_all(self):
        if not self.items:
            return
        self._copy("\n".join(it["path"] for it in self.items), f"已复制全部 {len(self.items)} 条路径")

    def copy_names(self):
        names = []
        for it in self._selected_items():
            names.append(it["name"])
        if names:
            self._copy("\n".join(names), "已复制文件名")

    def copy_csv(self):
        paths = set(self.selected_paths()) or {it["path"] for it in self.items}
        if not paths:
            return
        lines = ["名称,类型,大小(字节),完整路径"]
        for it in self.items:
            if it["path"] in paths:
                size = "" if it["kind"] == "url" else (it["size"] or 0)
                lines.append(f'{it["name"]},{it["type"]},{size},"{it["path"]}"')
        self._copy("\n".join(lines), "已复制 CSV")

    def export_list(self):
        if not self.items:
            return
        default = f"路径列表_{datetime.datetime.now():%Y%m%d_%H%M}.csv"
        fp = filedialog.asksaveasfilename(title="导出列表", defaultextension=".csv",
                                          initialfile=default,
                                          filetypes=[("CSV 表格", "*.csv"), ("文本文件", "*.txt")])
        if not fp:
            return
        try:
            if fp.lower().endswith(".txt"):
                with open(fp, "w", encoding="utf-8") as f:
                    for it in self.items:
                        f.write(it["path"] + "\n")
            else:
                with open(fp, "w", encoding="utf-8-sig", newline="") as f:
                    w = csv.writer(f)
                    w.writerow(["序号", "名称", "类型", "大小(字节)", "修改时间", "SHA256", "完整路径"])
                    for i, it in enumerate(self.items, 1):
                        mt = (datetime.datetime.fromtimestamp(it["mtime"]).strftime("%Y-%m-%d %H:%M:%S")
                              if it["mtime"] else "")
                        w.writerow([i, it["name"], it["type"],
                                    "" if it["kind"] == "url" else (it["size"] or 0), mt,
                                    self._hash_cache.get(it["key"], ""), it["path"]])
            self.status_var.set(f"已导出到 {fp}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    # ---------------- 动作 ----------------
    def calc_sha(self):
        items = self._selected_items()
        if not items:
            self.status_var.set("先选中要算哈希的文件")
            return
        it = items[0]
        if it["kind"] == "url":
            self.status_var.set("网址没有 SHA256；先下载到本地再算")
            return
        p = it["path"]
        if not os.path.isfile(p):
            self.status_var.set("文件夹不计算哈希")
            return
        if it["key"] in self._hash_cache:
            self._copy(self._hash_cache[it["key"]], "SHA256")
            return
        self.status_var.set(f"正在计算 {os.path.basename(p)} 的 SHA256 …")

        def work():
            try:
                h = hashlib.sha256()
                with open(p, "rb") as f:
                    for chunk in iter(lambda: f.read(1 << 20), b""):
                        h.update(chunk)
                digest = h.hexdigest()
            except Exception as e:
                digest = f"失败：{e}"
            self._ui_q.put(lambda: self._hash_done(it["key"], digest))

        threading.Thread(target=work, daemon=True).start()

    def _hash_done(self, key, digest):
        self._hash_cache[key] = digest
        self._copy(digest, "SHA256")
        self.on_select()

    def open_location(self):
        items = self._selected_items()
        if not items:
            self.status_var.set("先选中一行")
            return
        it = items[0]
        if it["kind"] == "url":
            cands = local_candidates(it["path"])
            if not cands:
                self.status_var.set("这是网址，本机下载 / 桌面里也没找到同名文件，双击可直接用浏览器打开")
                return
            self.status_var.set(f"本地同名文件：{cands[0]}")
            try:
                reveal_path(cands[0])
            except Exception as e:
                self.status_var.set(f"打开失败：{e}")
            return
        p = it["path"]
        try:
            if os.path.isdir(p):
                open_default(p)
            elif os.path.exists(p):
                reveal_path(p)
            else:
                self.status_var.set("该路径已不存在")
        except Exception as e:
            self.status_var.set(f"打开失败：{e}")

    def open_url(self):
        items = self._selected_items()
        urls = [it["path"] for it in items if it["kind"] == "url"]
        if not urls:
            self.status_var.set("选中的不是网址")
            return
        for u in urls[:5]:
            try:
                webbrowser.open(u)
            except Exception as e:
                self.status_var.set(f"打不开：{e}")

    def on_double(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        p = self.tree.item(iid, "values")[5]
        if is_url(p):
            try:
                webbrowser.open(p)
            except Exception as e:
                self.status_var.set(f"打不开：{e}")
            return
        if os.path.exists(p):
            try:
                open_default(p)
            except Exception as e:
                self.status_var.set(f"打不开：{e}")
        else:
            self.status_var.set("该路径已不存在")

    def on_right_click(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            if iid not in self.tree.selection():
                self.tree.selection_set(iid)
            self.menu.tk_popup(event.x_root, event.y_root)

    def select_all(self):
        self.tree.selection_set(self.tree.get_children())

    def remove_selected(self):
        keys = {it["key"] for it in self._selected_items()}
        if not keys:
            return
        self.items = [it for it in self.items if it["key"] not in keys]
        self.refresh_tree()

    def clear_all(self):
        if not self.items:
            return
        self.items.clear()
        self.refresh_tree()

    def paste_paths(self, event=None):
        try:
            text = self.clipboard_get()
        except Exception:
            return
        if not self.add_from_text(text, quiet=True):
            self.status_var.set("剪贴板里没有能识别的路径或网址")

    # ---------------- 窗口 ----------------
    def collapse(self):
        self.iconify()

    def restore_window(self):
        self.deiconify()
        try:
            self.state("normal")
        except Exception:
            pass
        self.lift()
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.user32.ShowWindow(hwnd, 9)          # SW_RESTORE
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        try:
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(900, lambda: self.attributes("-topmost", bool(self.topmost_var.get())))
        except Exception:
            pass

    def toggle_topmost(self):
        self.attributes("-topmost", bool(self.topmost_var.get()))
        self.save_settings()

    def on_close(self):
        self.save_settings()
        self.destroy()

    # ---------------- 单实例 ----------------
    def try_activate_existing(self):
        try:
            s = socket.create_connection(("127.0.0.1", PORT), timeout=0.5)
            s.sendall(b"show")
            s.close()
            return True
        except OSError:
            return False

    def start_server(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind(("127.0.0.1", PORT))
            srv.listen(4)
        except OSError:
            return

        def loop():
            while True:
                try:
                    c, _ = srv.accept()
                except OSError:
                    return
                try:
                    if c.recv(16).strip() == b"show":
                        self._ui_q.put(self.restore_window)
                except Exception:
                    pass
                finally:
                    try:
                        c.close()
                    except Exception:
                        pass

        threading.Thread(target=loop, daemon=True).start()


if __name__ == "__main__":
    app = PathDrop()
    if app.try_activate_existing():
        app.destroy()
        sys.exit(0)
    app.start_server()
    app.mainloop()
