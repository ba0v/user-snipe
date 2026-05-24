import asyncio
import aiohttp
import string
import itertools
import os
import time

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

CONCURRENCY      = 200
RETRY_DELAY      = 5.0
BATCH_SIZE       = 1000
PROXIES          = []   # e.g. ["http://user:pass@host:port", ...]
DISCORD_WEBHOOK  = ""   # paste your Discord webhook URL here

CHECKPOINT_FILE  = "checkpoint.txt"
OUTPUT_FILE      = "available_usernames.txt"

available: list[str] = []
checked = 0
_proxy_iter = itertools.cycle(PROXIES) if PROXIES else None


def get_proxy() -> str | None:
    return next(_proxy_iter) if _proxy_iter else None


async def notify_discord(session: aiohttp.ClientSession, username: str) -> None:
    if not DISCORD_WEBHOOK:
        return
    try:
        await session.post(DISCORD_WEBHOOK, json={"content": f"available username found: **{username}**"})
    except Exception:
        pass


async def check_username(session: aiohttp.ClientSession, sem: asyncio.Semaphore, username: str) -> tuple[str, bool]:
    async with sem:
        for attempt in range(3):
            try:
                async with session.get(
                    CHECK_URL.format(username),
                    timeout=aiohttp.ClientTimeout(total=10),
                    proxy=get_proxy(),
                ) as resp:
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


def load_checkpoint() -> int:
    if os.path.exists(CHECKPOINT_FILE):
        try:
            return int(open(CHECKPOINT_FILE).read().strip())
        except ValueError:
            pass
    return 0


def save_checkpoint(index: int) -> None:
    with open(CHECKPOINT_FILE, "w") as f:
        f.write(str(index))


async def main() -> None:
    global checked

    all_chars = CHARS + SPECIAL_CHARS
    if not SPECIAL_CHARS or ALLOW_SPECIAL_AT_ENDS:
        total = len(all_chars) ** USERNAME_LENGTH
    else:
        middle_len = USERNAME_LENGTH - 2
        total = len(CHARS) ** 2 * len(all_chars) ** middle_len

    start_index = load_checkpoint()
    checked = start_index

    print(f"{PLATFORM_NAME} {USERNAME_LENGTH}-character username checker")
    print("=" * 45)
    print(f"total combinations : {total:,}")
    print(f"concurrency        : {CONCURRENCY}")
    if start_index:
        print(f"resuming from      : {start_index:,}")
    print(f"press ctrl+c to stop early\n")

    sem = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    start_time = time.monotonic()

    async with aiohttp.ClientSession(connector=connector) as session:
        gen = username_generator()
        if start_index:
            next(itertools.islice(gen, start_index, start_index), None)

        while True:
            batch = list(itertools.islice(gen, BATCH_SIZE))
            if not batch:
                break

            results = await asyncio.gather(*[check_username(session, sem, u) for u in batch])

            for username, is_available in results:
                checked += 1
                if is_available:
                    available.append(username)
                    asyncio.create_task(notify_discord(session, username))
                    with open(OUTPUT_FILE, "a") as f:
                        f.write(username + "\n")

                elapsed = time.monotonic() - start_time
                rate = (checked - start_index) / elapsed if elapsed > 0 else 0
                remaining = (total - checked) / rate if rate > 0 else 0
                eta = f"{int(remaining // 3600)}h {int((remaining % 3600) // 60)}m" if rate > 0 else "?"
                pct = checked / total * 100
                status = "AVAILABLE" if is_available else "taken"
                print(f"  [{status:9s}] {username}  ({pct:.1f}% — {checked:,}/{total:,} — eta {eta})")

            save_checkpoint(checked)

    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)

    print(f"\n{'=' * 45}")
    print(f"checked  : {checked:,}")
    print(f"available: {len(available)}")

    if available:
        print("\navailable usernames:")
        for name in sorted(available):
            print(f"  {name}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nstopped early.")
        if available:
            print(f"{len(available)} available username(s) saved to {OUTPUT_FILE}")
