import requests
import time
import string
import itertools
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# GET endpoint — no CSRF token required, works reliably
CHECK_URL = "https://api.roblox.com/users/get-by-username?username={}"

MAX_WORKERS = 20
REQUEST_DELAY = 0.05
RETRY_DELAY = 5.0
BATCH_SIZE = 200

_local = threading.local()

def get_session() -> requests.Session:
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
    return _local.session

lock = threading.Lock()
available: list[str] = []
checked = 0


def check_username(username: str) -> tuple[str, bool]:
    for attempt in range(3):
        try:
            resp = get_session().get(CHECK_URL.format(username), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                is_available = "Id" not in data
                return username, is_available
            if resp.status_code == 429:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            return username, False
        except requests.RequestException:
            time.sleep(1)
    return username, False


def worker(username: str) -> tuple[str, bool]:
    result = check_username(username)
    time.sleep(REQUEST_DELAY)
    return result


def username_generator():
    chars = string.ascii_lowercase + string.digits
    for combo in itertools.product(chars, repeat=4):
        yield "".join(combo)


def main() -> None:
    global checked

    chars = string.ascii_lowercase + string.digits
    total = len(chars) ** 4

    print("Roblox 4-Character Username Checker")
    print("=" * 45)
    print(f"Total combinations : {total:,}  (a-z + 0-9, length 4)")
    print(f"Threads            : {MAX_WORKERS}")
    print(f"Press Ctrl+C to stop early\n")

    gen = username_generator()
    try:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            while True:
                batch = list(itertools.islice(gen, BATCH_SIZE))
                if not batch:
                    break

                futures = {executor.submit(worker, u): u for u in batch}
                for future in as_completed(futures):
                    username, is_available = future.result()
                    with lock:
                        checked += 1
                        if is_available:
                            available.append(username)
                        status = "AVAILABLE" if is_available else "taken"
                        print(f"  [{status:9s}] {username}  ({checked:,} checked)")

    except KeyboardInterrupt:
        print("\nStopped early.")

    print(f"\n{'=' * 45}")
    print(f"Checked  : {checked:,}")
    print(f"Available: {len(available)}")

    if available:
        print("\nAvailable usernames:")
        for name in sorted(available):
            print(f"  {name}")

        out_path = "available_usernames.txt"
        with open(out_path, "w") as f:
            f.write("\n".join(sorted(available)) + "\n")
        print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
