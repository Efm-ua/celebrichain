import sys
import argparse
from tg_webapp_auth import check_hmac, check_ed25519

PROD_PUBLIC_KEY = "e7bf03a2fa4602af4580703d88dda5bb59f32ed8b02a56c187fe7d34caed242d"
TEST_PUBLIC_KEY = "40055058a4ee38156a06562e52eece92a771bcd8346a8c4615cb7376eddf72ec"


def main():
    parser = argparse.ArgumentParser(description="Check Telegram WebApp initData auth.")
    parser.add_argument(
        "--init-data", required=True, help="initData string from Telegram WebApp"
    )
    parser.add_argument("--bot-token", required=True, help="Bot token")
    parser.add_argument("--bot-id", required=True, help="Bot ID (digits only)")
    parser.add_argument(
        "--public-key", default=PROD_PUBLIC_KEY, help="Ed25519 public key (hex)"
    )
    args = parser.parse_args()

    print("--- HMAC (hash) check ---")
    ok, computed, received = check_hmac(args.init_data, args.bot_token)
    print(f"Computed hash:  {computed}")
    print(f"Received hash:  {received}")
    print(f"Valid:          {ok}")

    # Ed25519 signature check (if present)
    from tg_webapp_auth import parse_init_data

    fields = parse_init_data(args.init_data)
    signature = fields.get("signature")
    if signature:
        print("\n--- Ed25519 (signature) check ---")
        try:
            valid = check_ed25519(
                args.init_data, args.bot_id, signature, args.public_key
            )
            print(f"Valid: {valid}")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("\nNo signature field in initData.")


if __name__ == "__main__":
    main()
