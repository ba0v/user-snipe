# username sniper

checks all possible combinations of short usernames against a platform's api and saves any available ones to a txt file. defaults to roblox 4-character usernames (a–z + 0–9), but can be configured for any platform.

## requirements

- python 3.8+
- aiohttp

pip install aiohttp

## usage

python check_usernames.py

results are printed to the terminal in real time. any available usernames are saved to `available_usernames.txt` when the run finishes or if you stop early with ctrl+c.

## configuration

edit the platform config block at the top of `check_usernames.py`:

| setting | description |
|---|---|
| `PLATFORM_NAME` | display name shown in the output |
| `CHECK_URL` | api endpoint — use `{}` where the username goes |
| `USERNAME_LENGTH` | how many characters to check |
| `CHARS` | base allowed characters (e.g. a–z + 0–9) |
| `SPECIAL_CHARS` | extra characters like `.` and `_` — leave empty if the platform doesn't allow them |
| `ALLOW_SPECIAL_AT_ENDS` | set to `True` if special characters are allowed at the start and end of a username |

also update `parse_response` to match the platform's json response:

```python
def parse_response(data: dict) -> bool:
    return True  # return True if the username is available, False if taken
```

## examples

**roblox** (default, all taken don't waste your time)
```python
PLATFORM_NAME         = "Roblox"
CHECK_URL             = "https://api.roblox.com/users/get-by-username?username={}"
SPECIAL_CHARS         = "_"
ALLOW_SPECIAL_AT_ENDS = False

def parse_response(data: dict) -> bool:
    return "Id" not in data
```

**discord**
```python
PLATFORM_NAME         = "Discord"
CHECK_URL             = "https://..."  # replace with correct endpoint
SPECIAL_CHARS         = "._"
ALLOW_SPECIAL_AT_ENDS = True

def parse_response(data: dict) -> bool:
    return True  # update to match discord's response format
```

## disclaimer

this tool interacts with platform apis. by using it, you acknowledge that:

- **YOU** are solely responsible for any consequences, including account bans, suspensions, or violations of a platform's terms of service
- the author (ba0v) is not responsible for **ANY** bans, penalties, or legal action resulting from the use of this tool
- use it at your own risk
- rate limits vary by platform — do your own research on the platform's api limits before running this tool to avoid such consequences
```

## if this helped you get a clean username, consider donating!
