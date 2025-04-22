import hmac
import hashlib
import base64
import urllib.parse
from typing import Dict, Tuple


def parse_init_data(init_data: str) -> Dict[str, str]:
    # Парсимо як query string, декодуємо значення
    return dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))


def build_data_check_string(fields: Dict[str, str], exclude: Tuple[str, ...]) -> str:
    # Видаляємо поля, які не потрібні
    items = [(k, v) for k, v in fields.items() if k not in exclude]
    # Сортуємо ключі байтово (ordinal)
    items.sort(key=lambda x: x[0].encode("utf-8"))
    # Формуємо пари ключ=значення
    return "\n".join(f"{k}={v}" for k, v in items)


def check_hmac(init_data: str, bot_token: str) -> Tuple[bool, str, str]:
    fields = parse_init_data(init_data)
    if "hash" not in fields:
        return False, "", "No hash in initData."
    data_check_string = build_data_check_string(fields, exclude=("hash",))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(
        secret_key, data_check_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return computed_hash == fields["hash"], computed_hash, fields["hash"]


def check_ed25519(
    init_data: str, bot_id: str, signature_b64: str, public_key_hex: str
) -> bool:
    import nacl.signing
    import nacl.encoding
    import nacl.exceptions

    fields = parse_init_data(init_data)
    # Формуємо data_check_string для Ed25519
    items = [(k, v) for k, v in fields.items() if k not in ("hash", "signature")]
    items.sort(key=lambda x: x[0].encode("utf-8"))
    data_check_string = f"{bot_id}:WebAppData\n" + "\n".join(
        f"{k}={v}" for k, v in items
    )
    public_key = nacl.signing.VerifyKey(
        public_key_hex, encoder=nacl.encoding.HexEncoder
    )
    signature = base64.urlsafe_b64decode(
        signature_b64 + "=" * (-len(signature_b64) % 4)
    )
    try:
        public_key.verify(data_check_string.encode("utf-8"), signature)
        return True
    except nacl.exceptions.BadSignatureError:
        return False


# === Ваші дані ===
init_data = "query_id=AAEslkpJAAAAACyWSknOcD6m&user=%7B%22id%22%3A1229624876%2C%22first_name%22%3A%22Eugene%22%2C%22last_name%22%3A%22Melnyk%22%2C%22username%22%3A%22YevgeniyMelnyk%22%2C%22language_code%22%3A%22ru%22%2C%22is_premium%22%3Atrue%2C%22allows_write_to_pm%22%3Atrue%2C%22photo_url%22%3A%22https%3A%5C%2F%5C%2Ft.me%5C%2Fi%5C%2Fuserpic%5C%2F320%5C%2F0k0yj0y-imZDDe08qXmqmO-7jQ2XPbcCykf0V8uJy9E.svg%22%7D&auth_date=1745330636&signature=shupOiUrtAk-e2POfedXrHhlVdkxHg4TZWPeRwnxpsIF-Ufx_SnbXsiSYMbBqqncBbJ_pGw-4flS7702EUceDQ&hash=ca6acf5b579276e8de12d5f9166dba0788301da563744bd094e8cf5d53687bbf"
bot_token = "8079790761:AAEIxQPRZNF3hV7U5UKyDy4l5T4e31NqRR4"
bot_id = "8079790761"
public_key_hex = "e7bf03a2fa4602af4580703d88dda5bb59f32ed8b02a56c187fe7d34caed242d"

if __name__ == "__main__":
    ok, computed, received = check_hmac(init_data, bot_token)
    print("--- HMAC (hash) check ---")
    print(f"Computed hash:  {computed}")
    print(f"Received hash:  {received}")
    print(f"Valid:          {ok}")

    fields = parse_init_data(init_data)
    signature = fields.get("signature")
    if signature:
        print("\n--- Ed25519 (signature) check ---")
        valid = check_ed25519(init_data, bot_id, signature, public_key_hex)
        print(f"Valid: {valid}")
    else:
        print("\nNo signature field in initData.")
