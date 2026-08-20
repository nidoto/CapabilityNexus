"""二维码工具测试：生成 PNG 并校验大小/文件有效。

qrcode 未安装时跳过（CI/开发环境按需 pip install -r requirements.txt）。
"""

import os

import pytest

qrcode = pytest.importorskip("qrcode")

from tools.qrcode_utils import generate_qr_png


def test_generate_qr_png_creates_file():
    path = generate_qr_png("http://192.168.1.10:8765/")
    try:
        assert os.path.exists(path)
        assert path.endswith(".png")
        size = os.path.getsize(path)
        assert size > 0
        # PNG 文件头校验
        with open(path, "rb") as f:
            assert f.read(8) == b"\x89PNG\r\n\x1a\n"
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_generate_qr_png_distinct_urls():
    a = generate_qr_png("http://192.168.1.10:8765/")
    b = generate_qr_png("http://10.0.0.5:8765/")
    try:
        with open(a, "rb") as fa, open(b, "rb") as fb:
            assert fa.read() != fb.read()
    finally:
        for p in (a, b):
            if os.path.exists(p):
                os.remove(p)
