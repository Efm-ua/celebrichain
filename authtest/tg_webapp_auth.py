import hmac
import hashlib
import base64
from typing import Dict, Tuple, Optional

try:
    import nacl.signing
    import nacl.encoding
    import nacl.exceptions

    HAS_NACL = True
except ImportError:
    HAS_NACL = False


def parse_init_data(init_data: str) -> Dict[str, str]:
    pairs = [p for p in init_data.split("&") if "=" in p]
    return {k: v for k, v in (p.split("=", 1) for p in pairs)}


def build_data_check_string(fields: Dict[str, str], exclude: Tuple[str, ...]) -> str:
    items = [(k, fields[k]) for k in sorted(fields) if k not in exclude]
    return "\n".join(f"{k}={v}" for k, v in items)


def build_ed25519_data_check_string(bot_id: str, fields: Dict[str, str]) -> str:
    items = [(k, fields[k]) for k in sorted(fields) if k not in ("hash", "signature")]
    return f"{bot_id}:WebAppData\n" + "\n".join(f"{k}={v}" for k, v in items)


def check_hmac(init_data: str, bot_token: str) -> Tuple[bool, str, str]:
    fields = parse_init_data(init_data)
    if "hash" not in fields:
        return False, "", "No hash in initData."
    data_check_string = build_data_check_string(fields, exclude=("hash",))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return computed_hash == fields["hash"], computed_hash, fields["hash"]


def check_ed25519(
    init_data: str, bot_id: str, signature_b64: str, public_key_hex: str
) -> Optional[bool]:
    if not HAS_NACL:
        raise ImportError("PyNaCl is required for Ed25519 signature check.")
    fields = parse_init_data(init_data)
    data_check_string = build_ed25519_data_check_string(bot_id, fields)
    public_key = nacl.signing.VerifyKey(
        public_key_hex, encoder=nacl.encoding.HexEncoder
    )
    try:
        signature = base64.urlsafe_b64decode(
            signature_b64 + "=" * (-len(signature_b64) % 4)
        )
        public_key.verify(data_check_string.encode(), signature)
        return True
    except nacl.exceptions.BadSignatureError:
        return False
    except Exception as e:
        return None
