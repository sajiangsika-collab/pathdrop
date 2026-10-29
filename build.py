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

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "PathDrop"
VER = "1.4"
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"

REQUIRED = ("pathdrop.py", "app.ico", "app.png")


def ensure_assets():
    """app.ico / app.png 缺失时用 make_icon.py 现场生成"""
    if all(os.path.exists(os.path.join(HERE, f)) for f in REQUIRED):
        return
    print("[build] 图标缺失，正在生成 …")
    subprocess.check_call([sys.executable, os.path.join(HERE, "make_icon.py")], cwd=HERE)


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
        args += ["--icon", "app.ico"]
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
