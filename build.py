# -*- coding: utf-8 -*-
"""
统一的打包脚本（Windows / macOS / Linux 三平台通用）

用法：
    python build.py            # 只打包，产物在 dist/
    python build.py --package  # 打包后再压成发布用的压缩包，产物在 release/

需要先装依赖：
    pip install -r requirements.txt pyinstaller pillow
"""

import os
import sys
import shutil
import zipfile
import subprocess

# Windows CI 的控制台默认是 cp1252，直接 print 中文会抛 UnicodeEncodeError。
# 这里统一切到 UTF-8，顺便让子进程也用 UTF-8。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "PathDrop"
VER = "1.4.2"
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"

REQUIRED = ("pathdrop.py", "app.ico", "app.png")


def ensure_assets():
    """app.ico / app.png 缺失时用 make_icon.py 现场生成"""
    if all(os.path.exists(os.path.join(HERE, f)) for f in REQUIRED):
        return
    print("[build] 图标缺失，正在生成 …")
    subprocess.check_call([sys.executable, os.path.join(HERE, "make_icon.py")], cwd=HERE)


def win_version_file():
    """Windows exe 的"属性 → 详细信息"里显示版本，而不是空白"""
    txt = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({VER.replace('.', ',')},0,0), prodvers=({VER.replace('.', ',')},0,0),
                    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable('080404b0', [
        StringStruct('CompanyName', 'sajiangsika-collab'),
        StringStruct('FileDescription', 'PathDrop — drag anything in, get the full path'),
        StringStruct('FileVersion', '{VER}'),
        StringStruct('InternalName', 'PathDrop'),
        StringStruct('OriginalFilename', 'PathDrop.exe'),
        StringStruct('ProductName', 'PathDrop'),
        StringStruct('ProductVersion', '{VER}')])]),
      VarFileInfo([VarStruct('Translation', [2052, 1200])])]
)"""
    out = os.path.join(HERE, "build", "version_info.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(txt)
    return out


def mac_icns():
    """macOS 的 .app 需要 .icns，用 iconutil 从 app.png 转一份"""
    if not IS_MAC:
        return None
    try:
        from PIL import Image
        iconset = os.path.join(HERE, "build", "AppIcon.iconset")
        os.makedirs(iconset, exist_ok=True)
        im = Image.open(os.path.join(HERE, "app.png")).convert("RGBA")
        for size, name in [(16, "16x16"), (32, "16x16@2x"), (32, "32x32"), (64, "32x32@2x"),
                           (128, "128x128"), (256, "128x128@2x"), (256, "256x256"),
                           (512, "256x256@2x"), (512, "512x512"), (1024, "512x512@2x")]:
            im.resize((size, size), Image.LANCZOS).save(os.path.join(iconset, f"icon_{name}.png"))
        out = os.path.join(HERE, "app.icns")
        subprocess.check_call(["iconutil", "-c", "icns", iconset, "-o", out])
        return out
    except Exception as e:
        print(f"[build] 生成 .icns 失败，用默认图标：{e}")
        return None


def build():
    ensure_assets()
    sep = ";" if IS_WIN else ":"
    args = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", NAME,
        "--collect-all", "tkinterdnd2",
        "--add-data", f"app.ico{sep}.",
        "--add-data", f"app.png{sep}.",
        "--exclude-module", "numpy",
        "--exclude-module", "PIL",
    ]
    if IS_WIN:
        args += ["--icon", "app.ico", "--version-file", win_version_file()]
    elif IS_MAC:
        icns = mac_icns()
        if icns:
            args += ["--icon", icns]
    args.append("pathdrop.py")
    print("[build] " + " ".join(args[2:]))
    subprocess.check_call(args, cwd=HERE)


def package():
    """把 dist 里的产物压成发布包"""
    rel = os.path.join(HERE, "release")
    os.makedirs(rel, exist_ok=True)
    if IS_WIN:
        zpath = os.path.join(rel, f"{NAME}-{VER}-windows-x64.zip")
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(os.path.join(HERE, "dist", f"{NAME}.exe"), f"{NAME}.exe")
            note = os.path.join(HERE, "快速上手.txt")
            if os.path.exists(note):
                z.write(note, "快速上手.txt")
    elif IS_MAC:
        zpath = os.path.join(rel, f"{NAME}-{VER}-macos.zip")
        subprocess.check_call(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                               os.path.join(HERE, "dist", f"{NAME}.app"), zpath])
    else:
        zpath = os.path.join(rel, f"{NAME}-{VER}-linux-x64.tar.gz")
        subprocess.check_call(["tar", "-czf", zpath, "-C", os.path.join(HERE, "dist"), NAME])
    print(f"[build] 发布包：{zpath}")
    return zpath


if __name__ == "__main__":
    build()
    target = os.path.join(HERE, "dist", f"{NAME}.app" if IS_MAC else
                          f"{NAME}.exe" if IS_WIN else NAME)
    if not os.path.exists(target):
        print(f"[build] 没找到产物：{target}")
        sys.exit(1)
    print(f"[build] 完成：{target}")
    if "--package" in sys.argv:
        package()
