"""本地自签证书生成（HTTPS 手机服务用）。

生成 RSA 自签证书与私钥，存到 config/certs/。
浏览器访问时会提示"不安全"，用户点"继续访问"即可使用完整能力
（陀螺仪等需要 secure context 的 API）。

仅用于局域网本地服务，非公开 CA 证书。
"""

import datetime
import os
import tempfile


def _cert_dir():
    """证书目录：优先使用可写的 exe 同级 config/certs；
    若不存在则回退到 _MEIPASS（打包内置的证书）。"""
    import sys as _sys

    if getattr(_sys, "frozen", False):
        # 1) exe 同级（可写，运行时生成/持久）
        exe_dir = os.path.dirname(_sys.executable)
        exe_certs = os.path.join(exe_dir, "config", "certs")
        if os.path.isdir(exe_certs) and os.listdir(exe_certs):
            return exe_certs
        # 2) _MEIPASS（打包内置证书）
        meipass = getattr(_sys, "_MEIPASS", None) or exe_dir
        return os.path.join(meipass, "config", "certs")
    else:
        base = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config",
        )
    return os.path.join(base, "certs")


CERT_DIR = _cert_dir()
CERT_FILE = os.path.join(CERT_DIR, "localhost.crt")
KEY_FILE = os.path.join(CERT_DIR, "localhost.key")


def certs_exist():
    return os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE)


def ensure_certs():
    """确保自签证书存在，返回 (cert_path, key_path) 或 (None, None)。"""
    if certs_exist():
        return CERT_FILE, KEY_FILE

    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        _write_diag("cryptography import failed")
        print("[Certs] cryptography not installed - HTTPS disabled")
        return None, None

    try:
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "CapabilityNexus Local"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "CapabilityNexus"),
        ])

        now = datetime.datetime.utcnow()
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(__import__("ipaddress").ip_address("127.0.0.1")),
            ]), critical=False)
            .sign(key, hashes.SHA256())
        )

        os.makedirs(CERT_DIR, exist_ok=True)
        with open(CERT_FILE, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        with open(KEY_FILE, "wb") as f:
            f.write(key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            ))

        print(f"[Certs] Self-signed cert generated: {CERT_FILE}")
        return CERT_FILE, KEY_FILE
    except Exception as error:
        _write_diag(f"cert generation failed: {error}")
        print(f"[Certs] Cert generation failed: {error}")
        return None, None


def _write_diag(message):
    """把证书问题写入 exe 同级诊断文件（frozen 下排查用）。"""
    try:
        import sys as _sys

        if getattr(_sys, "frozen", False):
            base = os.path.dirname(_sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base, "cert_diag.txt"), "w", encoding="utf-8") as f:
            f.write(f"{message}\n")
            import traceback as _tb
            f.write(_tb.format_exc())
    except Exception:
        pass


def ssl_context():
    """返回 HTTPS 用 ssl.SSLContext，或 None（无法生成证书时）。"""
    cert, key = ensure_certs()
    if not cert or not key:
        return None

    import ssl

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        context.load_cert_chain(certfile=cert, keyfile=key)
        return context
    except ssl.SSLError as error:
        _write_diag(f"SSL context failed: {error}")
        print(f"[Certs] SSL context failed: {error}")
        return None
