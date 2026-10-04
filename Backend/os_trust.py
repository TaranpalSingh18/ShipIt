import os
import ssl
import tempfile
from pathlib import Path


def enable() -> None:
    """Point HTTPS clients at the OS certificate store.

    Python's bundled CA list does not include the local issuer on this
    machine, so Groq calls fail before discovery can finish.
    """
    _allow_unicode_logs()
    if os.environ.get("SSL_CERT_FILE") or os.name != "nt":
        return

    bundle = _windows_ca_bundle()
    if bundle is None:
        return

    os.environ["SSL_CERT_FILE"] = str(bundle)
    os.environ["REQUESTS_CA_BUNDLE"] = str(bundle)
    os.environ["CURL_CA_BUNDLE"] = str(bundle)


def _allow_unicode_logs() -> None:
    import sys

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            continue


def _windows_ca_bundle() -> Path | None:
    path = Path(tempfile.gettempdir()) / "shipit-windows-ca.pem"
    if path.exists() and path.stat().st_size > 0:
        return path

    pems = list(_windows_certificates())
    if not pems:
        return None

    path.write_text("".join(pems), encoding="ascii")
    return path


def _windows_certificates():
    import ctypes
    from ctypes import wintypes

    crypt32 = ctypes.WinDLL("crypt32.dll")

    class CERT_CONTEXT(ctypes.Structure):
        _fields_ = [
            ("dwCertEncodingType", wintypes.DWORD),
            ("pbCertEncoded", ctypes.POINTER(ctypes.c_byte)),
            ("cbCertEncoded", wintypes.DWORD),
            ("pCertInfo", ctypes.c_void_p),
            ("hCertStore", ctypes.c_void_p),
        ]

    open_store = crypt32.CertOpenSystemStoreW
    open_store.argtypes = [wintypes.HANDLE, wintypes.LPCWSTR]
    open_store.restype = ctypes.c_void_p

    enum_certs = crypt32.CertEnumCertificatesInStore
    enum_certs.argtypes = [ctypes.c_void_p, ctypes.POINTER(CERT_CONTEXT)]
    enum_certs.restype = ctypes.POINTER(CERT_CONTEXT)

    close_store = crypt32.CertCloseStore
    close_store.argtypes = [ctypes.c_void_p, wintypes.DWORD]

    for store_name in ("ROOT", "CA"):
        store = open_store(0, store_name)
        if not store:
            continue
        try:
            context = enum_certs(store, None)
            while context:
                encoded = ctypes.string_at(
                    context.contents.pbCertEncoded,
                    context.contents.cbCertEncoded,
                )
                yield ssl.DER_cert_to_PEM_cert(encoded)
                context = enum_certs(store, context)
        finally:
            close_store(store, 0)
