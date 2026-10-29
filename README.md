# 路径抓取器 PathDrop

**把文件、文件夹、文字里的路径、网页链接拖进窗口，立刻显示完整路径，一键复制。**

[![platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-2F6FED)](https://github.com/sajiangska-collab/pathdrop/releases)
[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![python](https://img.shields.io/badge/python-3.10%2B-3776AB)](https://www.python.org/)
[![build](https://github.com/sajiangska-collab/pathdrop/actions/workflows/build.yml/badge.svg)](https://github.com/sajiangska-collab/pathdrop/actions/workflows/build.yml)

![界面截图](docs/screenshot.png)

平时要复制某个文件的路径，得在资源管理器里按住 Shift 右键、或者手动往地址栏里抠，
遇到长路径和中文目录更麻烦。这个小工具把这件事变成"拖一下就完事"：
拖进来就直接看到完整路径，点一下就进剪贴板。

## 功能

- **任意格式**：文件、视频、图片、音频、文档、压缩包、程序、代码、文件夹都认，按扩展名自动归类上色
- **拖文字也认**：从聊天窗口、记事本、Word 里拖一段带路径的文字进来，自动把路径抠出来（支持引号、书名号、`file:///`、`%USERPROFILE%` 等写法）
- **拖链接也认**：网页链接作为「网址」列出，并自动去 `下载` / `桌面` 里找同名本地文件，告诉你它落在哪个路径
- **信息够用**：名称、类型、大小、修改时间、完整路径；图片显示分辨率，视频显示时长（需本机有 ffprobe）
- **顺手的小动作**：列头排序、复制选中 / 全部 / CSV、复制 SHA256、打开所在位置、导出 CSV / TXT
- **不打扰**：窗口置顶、复制后自动收起（Esc 也可收起），再次双击图标唤回原窗口，不会开第二个
- **免安装**：单个可执行文件，不写注册表，设置存在用户配置目录

## 下载

到 [Releases](https://github.com/sajiangska-collab/pathdrop/releases) 下载对应系统的包：

| 系统 | 文件 | 说明 |
| --- | --- | --- |
| Windows 10/11 (x64) | `PathDrop-1.4-windows-x64.zip` | 解压后双击 `PathDrop.exe`，免安装 |
| macOS (Intel / Apple Silicon) | `PathDrop-1.4-macos.zip` | 解压得到 `PathDrop.app`；未签名，首次需右键 →「打开」 |
| Linux (x64) | `PathDrop-1.4-linux-x64.tar.gz` | 解压后 `chmod +x PathDrop && ./PathDrop`，需要系统有 X11 |

> 三个平台的包由 GitHub Actions 在各自系统上原生构建，见 [build.yml](.github/workflows/build.yml)。
> 没有代码签名，Windows SmartScreen / macOS Gatekeeper 可能提示"未知开发者"，属于正常现象。

## 使用

1. 打开程序
2. 把文件 / 文件夹从资源管理器拖进窗口（拖到窗口任意位置都行）
3. 选中要的那行 → 点「复制选中路径」，或者直接 `Ctrl+C`

| 操作 | 说明 |
| --- | --- |
| 双击某行 | 用系统默认程序打开（网址则用浏览器打开） |
| 右键 | 复制路径 / 复制文件名 / 复制 SHA256 / 在浏览器打开 / 打开所在位置 / 移除 |
| `Ctrl+C` | 复制选中路径（没选中时用「复制全部」） |
| `Ctrl+A` | 全选 |
| `Ctrl+V` | 把剪贴板里的文字/路径/链接加进列表 |
| `Esc` | 收起窗口；再双击一次图标可唤回 |
| 点列头 | 按该列排序，再点一次反向 |
| `Delete` | 从列表移除选中项 |

右下角三个开关：**窗口置顶**、**展开文件夹内容**（拖文件夹时把里面的文件也列出来）、**复制后收起**。

## 能识别哪些写法

| 拖进来的内容 | 结果 |
| --- | --- |
| `C:\Users\me\Desktop\报告.docx` | 原样识别 |
| `"C:\...\会议 纪要.docx"` | 去掉引号 |
| `《C:\...\会议 纪要.docx》` | 去掉书名号 |
| `file:///C:/Users/me/%E6%8A%A5%E5%91%8A.docx` | 转本地路径并解码 `%20` |
| `我已经把文件存到 C:\...\报告.docx 里了` | 从句子中抠出来 |
| `C:/Users/me/Desktop`（正斜杠） | 转成标准路径 |
| `%USERPROFILE%\Desktop` | 展开环境变量 |
| `/Users/me/Desktop/a.txt`、`~/a.txt`（macOS / Linux） | 识别 POSIX 路径 |
| `https://example.com/a.mp4` / `www.bilibili.com/video/BV1xx` | 作为「网址」列出并找本地同名文件 |
| `今天下午三点开会` | 不乱加，只给提示 |

## 从源码运行

```bash
# Linux 先装 tkinter
sudo apt install python3-tk        # Debian/Ubuntu
# sudo dnf install python3-tkinter # Fedora

pip install -r requirements.txt
python pathdrop.py
```

## 自己打包

```bash
pip install -r requirements.txt pyinstaller pillow
python build.py --package
```

产物：Windows `dist/PathDrop.exe`、macOS `dist/PathDrop.app`、Linux `dist/PathDrop`；
加 `--package` 会在 `release/` 下生成对应压缩包。

> PyInstaller 不能交叉编译，macOS / Linux 的包必须在对应系统上打。仓库里的
> GitHub Actions 已经配好了三平台矩阵，推一个 `v*` 标签就会自动构建并发布到 Releases。

## 项目结构

```
pathdrop.py     主程序（单文件，约 1100 行，tkinter + tkinterdnd2）
build.py        三平台统一打包脚本
make_icon.py    生成 app.ico / app.png / docs/icon-512.png
requirements.txt
快速上手.txt     随发布包附带的说明
docs/           截图与图标
.github/workflows/build.yml   三平台 CI 构建 + 发版
```

## 数据与隐私

- 纯本地程序，不联网、不上传任何文件内容
- 拖入网址时只做字符串解析和本地目录查找，**不会发起网络请求**
- 设置保存在 `%APPDATA%\PathDrop\setting.json`（macOS 为 `~/Library/Application Support/PathDrop/`，Linux 为 `~/.config/pathdrop/`）

## 已知限制

- 只做路径展示与复制，不修改、不移动文件
- 文件夹大小是粗略统计（最多算 4000 个文件），显示为 `≥` 开头的近似值
- 视频时长依赖本机 `ffprobe`，没装就只显示基础信息
- macOS / Linux 版功能与 Windows 一致，但 Windows 特有的"资源管理器定位"在其它系统上换成了 Finder / 文件管理器定位

## 更新日志

- **1.4** 跨平台适配（macOS / Linux 可运行、可打包）；字体与图标按系统自动选择
- **1.3** 支持拖入网页链接，作为「网址」条目并查找本地同名文件
- **1.2** 支持拖入文字，识别句子里的路径与 `file:///`、环境变量等写法
- **1.1** 列头排序、详情面板（分辨率/时长）、SHA256、复制后收起、单实例唤回
- **1.0** 基础功能：拖文件显示路径、分类、复制、导出

## 许可证

[MIT](LICENSE) © 2026 sajiangska-collab
