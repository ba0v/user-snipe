import asyncio
import aiohttp
import string
import itertools

# --- platform config (change these for other platforms) ---
PLATFORM_NAME          = "Roblox"
CHECK_URL              = "https://api.roblox.com/users/get-by-username?username={}"
USERNAME_LENGTH        = 4
CHARS                  = string.ascii_lowercase + string.digits
SPECIAL_CHARS          = ""     # e.g. "._" for Discord-like platforms
ALLOW_SPECIAL_AT_ENDS  = False  # set True if the platform allows special chars at start/end

def parse_response(data: dict) -> bool:
    return "Id" not in data

# ----------------------------------------------------------

CONCURRENCY = 200
RETRY_DELAY = 5.0
BATCH_SIZE  = 1000

available: list[str] = []
checked = 0


async def check_username(session: aiohttp.ClientSession, sem: asyncio.Semaphore, username: str) -> tuple[str, bool]:
    async with sem:
        for attempt in range(3):
            try:
                async with session.get(CHECK_URL.format(username), timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return username, parse_response(data)
                    if resp.status == 429:
                        await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                    return username, False
            except Exception:
                await asyncio.sleep(1)
        return username, False


def username_generator():
    all_chars = CHARS + SPECIAL_CHARS
    if not SPECIAL_CHARS or ALLOW_SPECIAL_AT_ENDS:
        for combo in itertools.product(all_chars, repeat=USERNAME_LENGTH):
            yield "".join(combo)
    else:
        middle_len = USERNAME_LENGTH - 2
        for first in CHARS:
            for middle in itertools.product(all_chars, repeat=middle_len):
                for last in CHARS:
                    yield first + "".join(middle) + last


async def main() -> None:
    global checked

    all_chars = CHARS + SPECIAL_CHARS
    if not SPECIAL_CHARS or ALLOW_SPECIAL_AT_ENDS:
        total = len(all_chars) ** USERNAME_LENGTH
    else:
        middle_len = USERNAME_LENGTH - 2
        total = len(CHARS) ** 2 * len(all_chars) ** middle_len

    print(f"{PLATFORM_NAME} {USERNAME_LENGTH}-character username checker")
    print("=" * 45)
    print(f"Total combinations : {total:,}")
    print(f"Concurrency        : {CONCURRENCY}")
    print(f"Press Ctrl+C to stop early\n")

    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)

    async with aiohttp.ClientSession(connector=connector) as session:
        gen = username_generator()
        while True:
            batch = list(itertools.islice(gen, BATCH_SIZE))
            if not batch:
                break

            results = await asyncio.gather(*[check_username(session, sem, u) for u in batch])

            for username, is_available in results:
                checked += 1
                if is_available:
                    available.append(username)
                status = "AVAILABLE" if is_available else "taken"
                print(f"  [{status:9s}] {username}  ({checked:,} checked)")

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
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped early.")
        if available:
            out_path = "available_usernames.txt"
            with open(out_path, "w") as f:
                f.write("\n".join(sorted(available)) + "\n")
            print(f"Saved {len(available)} available username(s) to {out_path}")
