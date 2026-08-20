"""二维码工具：把手机 Web 服务网址生成为可扫码的 PNG。

仅依赖纯 Python 的 qrcode 库，不引入 Pillow 等编译依赖。Tk 8.6+ 自带 PNG 支持，
可直接用 tk.PhotoImage(file=...) 显示生成的 PNG。

若运行环境未安装 qrcode，generate_qr_png 抛 ImportError，由调用方降级为文本展示。
"""

import os
import tempfile


def generate_qr_png(url, box_size=8, border=4):
    """把 url 生成为二维码 PNG，返回临时文件路径。

    调用方负责在不再需要时清理该文件（或在进程退出时随 temp 目录回收）。
    未安装 qrcode 时抛 ImportError。
    """
    import qrcode

    qr = qrcode.QRCode(
        version=None,  # 自动选择最小可用版本
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    fd, path = tempfile.mkstemp(prefix="cnx-qr-", suffix=".png")
    with os.fdopen(fd, "wb") as f:
        img.save(f, format="PNG")
    return path
