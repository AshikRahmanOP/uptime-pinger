# uptime-pinger

![CI](https://github.com/YOUR-USERNAME/uptime-pinger/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A small Python DevOps tool that checks your websites on a schedule and sends you a
**Telegram** or **Discord** message when one goes down, and again when it comes back up.

```
2026-11-22 22:45:17 INFO    UP    Google               https://www.google.com (200, 596.7 ms)
2026-11-22 22:45:17 INFO    UP    GitHub               https://github.com (200, 853.4 ms)
2026-11-22 22:45:26 WARNING DOWN  NotFound             https://github.com/this/page/... (Expected 200, got 404)
```

> Replace `YOUR-USERNAME` in the badge link above with your GitHub username after you push.

---

## Table of contents

1. [Features](#features)
2. [Project structure](#project-structure)
3. [Quick start](#quick-start)
4. [Setting up alerts](#setting-up-alerts)
5. [Running with Docker](#running-with-docker)
6. [Free monitoring with GitHub Actions](#free-monitoring-with-github-actions)
7. [Running the tests](#running-the-tests)
8. [How I built it, step by step](#how-i-built-it-step-by-step)
9. [Putting it on GitHub](#putting-it-on-github)
10. [Glossary for beginners](#glossary-for-beginners)
11. [Ideas to extend it](#ideas-to-extend-it)

---

## Features

- Checks any number of websites listed in a simple `config.yaml` file.
- A site is **up** if it answers with the expected HTTP status code (200 by default) before a timeout.
- Sends alerts to **Telegram** and/or **Discord**.
- **No alert spam:** it alerts only when a site *changes* state (up to down, or down to up).
- `--once` mode for scripts, cron jobs and CI. It exits with code `1` if any site is down.
- Runs in **Docker**, with a `docker-compose.yml` that restarts it automatically.
- **CI pipeline** on GitHub Actions: lint, tests on 3 Python versions, and a Docker build.
- **Free hosted monitoring**: a scheduled GitHub Actions workflow checks your sites every 15 minutes.
- 23 automated tests. They use fake HTTP responses, so they never touch the real internet.

---

## Project structure

```
uptime-pinger/
├── uptime_pinger/            # The Python package (the actual app)
│   ├── __init__.py           # Marks the folder as a package, holds the version
│   ├── __main__.py           # Command-line entry point (python -m uptime_pinger)
│   ├── config.py             # Reads and validates config.yaml
│   ├── checker.py            # Checks one website
│   ├── notifier.py           # Sends Telegram / Discord messages
│   └── monitor.py            # The loop + "only alert on change" logic
├── tests/                    # Automated tests (pytest)
├── .github/workflows/
│   ├── ci.yml                # Lint + test + Docker build on every push
│   └── uptime-check.yml      # Scheduled check every 15 minutes
├── config.yaml               # The list of sites to check
├── .env.example              # Template for your secret tokens
├── requirements.txt          # Libraries the app needs
├── requirements-dev.txt      # Extra libraries for testing and linting
├── pyproject.toml            # Project metadata + tool settings
├── Dockerfile                # How to build the Docker image
├── docker-compose.yml        # How to run the container easily
├── .dockerignore             # Files Docker should not copy
├── .gitignore                # Files Git should not track
└── LICENSE                   # MIT license
```

---

## Quick start

You need **Python 3.10 or newer** and **Git**.

**1. Get the code**

```bash
git clone https://github.com/YOUR-USERNAME/uptime-pinger.git
cd uptime-pinger
```

**2. Create a virtual environment and install the libraries**

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> If PowerShell says running scripts is disabled, run
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again.

**3. Edit `config.yaml`** and put in the sites you want to watch:

```yaml
interval: 60            # seconds between checks

sites:
  - name: My Blog
    url: https://myblog.com
  - name: My API
    url: https://api.myapp.com/health
    expected_status: 200
    timeout: 5
```

**4. Run it**

```bash
python -m uptime_pinger --once      # check every site one time, then exit
python -m uptime_pinger             # keep checking forever (Ctrl+C to stop)
python -m uptime_pinger --help      # see all options
```

| Option | What it does |
|---|---|
| `-c`, `--config FILE` | Use a different config file (default `config.yaml`) |
| `--once` | Check one time and exit |
| `-v`, `--verbose` | Show extra debug logs |
| `--version` | Print the version |

**Exit codes** (useful in scripts):

| Code | Meaning |
|---|---|
| `0` | All sites are up |
| `1` | At least one site is down (`--once` mode) |
| `2` | The config file is missing or invalid |

---

## Setting up alerts

Without any alert channel, the tool still works. It just prints results to the screen.
To get messages on your phone, copy the template and fill it in:

```bash
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
```

`.env` is listed in `.gitignore`, so your secrets will **never** be uploaded to GitHub.

### Telegram

1. In Telegram, open a chat with **@BotFather** and send `/newbot`. Follow the steps.
2. BotFather gives you a **token** like `123456:ABC-xyz`. Put it in `TELEGRAM_BOT_TOKEN`.
3. Open a chat with your new bot and send it any message, like "hi".
4. In your browser, open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`.
5. Find `"chat":{"id":123456789` in the text. That number is your `TELEGRAM_CHAT_ID`.

### Discord

1. In your Discord server, open **Server Settings > Integrations > Webhooks**.
2. Click **New Webhook**, pick a channel, then **Copy Webhook URL**.
3. Paste it into `DISCORD_WEBHOOK_URL`.

Your `.env` should look like this:

```
TELEGRAM_BOT_TOKEN=123456:ABC-xyz
TELEGRAM_CHAT_ID=123456789
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Run the tool again and you will see `Alerts enabled: telegram, discord`.
To test an alert, add a fake site such as `https://this-does-not-exist-12345.com` to `config.yaml`.

---

## Running with Docker

Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) first.

```bash
# Build the image
docker build -t uptime-pinger .

# Run it once
docker run --rm uptime-pinger --once

# Or run it in the background with docker compose
docker compose up -d --build
docker compose logs -f        # watch the logs (Ctrl+C stops watching, not the app)
docker compose down           # stop it
```

The compose file:

- reads your secrets from `.env`,
- mounts `config.yaml` into the container, so you can edit sites without rebuilding
  (run `docker compose restart` after editing),
- restarts the container automatically if it crashes or the computer reboots.

---

## Free monitoring with GitHub Actions

You don't need a server. GitHub can run the check for you every 15 minutes, for free.

1. Push this project to GitHub (see [Putting it on GitHub](#putting-it-on-github)).
2. In your repo, go to **Settings > Secrets and variables > Actions > New repository secret**.
3. Add `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` and/or `DISCORD_WEBHOOK_URL`.
4. Go to the **Actions** tab, pick **Scheduled uptime check**, and click **Run workflow** to test it.

Things to know:

- Each scheduled run starts fresh and remembers nothing. So while a site stays down,
  you get an alert **every 15 minutes**. The long-running mode (Docker) only alerts on changes.
- GitHub can delay scheduled runs by a few minutes when it is busy.
- GitHub pauses scheduled workflows in public repos after 60 days with no commits.
  Push any small change, or re-enable it in the Actions tab.

---

## Running the tests

```bash
pip install -r requirements-dev.txt
ruff check .      # lint: finds style problems and common bugs
pytest -v         # run all tests
```

---

## How I built it, step by step

This section explains every step and **why** it was done, so you can rebuild it yourself
or explain it in an interview.

### Step 1: Plan before coding

Before writing code, I wrote down what the tool must do:

1. Read a list of websites from a file.
2. Visit each website and decide if it is up or down.
3. Send a message when something changes.
4. Repeat every N seconds.

Each of those became **one Python file** with one job. Small files with one job each are
easier to read, test and fix. This idea is called *separation of concerns*.

| Job | File |
|---|---|
| Read the list of sites | `config.py` |
| Check one site | `checker.py` |
| Send a message | `notifier.py` |
| Repeat and decide when to alert | `monitor.py` |
| Handle the command line | `__main__.py` |

### Step 2: Create the folder and a virtual environment

```bash
mkdir uptime-pinger
cd uptime-pinger
python -m venv .venv
.venv\Scripts\Activate.ps1      # macOS/Linux: source .venv/bin/activate
```

A **virtual environment** (`.venv`) is a private box of Python libraries just for this
project. Without it, every project on your computer would share the same libraries, and
different versions would clash.

### Step 3: Choose and install the libraries

`requirements.txt` lists what the app needs:

```
requests>=2.32,<3          # makes HTTP requests (visits websites, calls APIs)
PyYAML>=6.0.2,<7           # reads the config.yaml file
python-dotenv>=1.0,<2      # loads secrets from the .env file
```

`requirements-dev.txt` adds tools only developers need: `pytest` for tests, `responses`
to fake HTTP calls in tests, and `ruff` for linting. The line `-r requirements.txt`
at the top means "also install everything in requirements.txt".

The `>=2.32,<3` part means "version 2.32 or newer, but not 3". A new major version
can break things, so we block it.

```bash
pip install -r requirements-dev.txt
```

### Step 4: The config file and `config.py`

I used **YAML** for the config because it is easy for humans to read and edit:

```yaml
interval: 60
sites:
  - name: Google
    url: https://www.google.com
```

`config.py` turns that text into Python objects using **dataclasses**:

```python
@dataclass
class Site:
    name: str
    url: str
    expected_status: int = 200
    timeout: float = 10.0
```

A dataclass is a short way to make a class that just holds data. The `= 200` gives a
default value, so you don't have to write it in the YAML for every site.

`load_config()` also **validates** the file. It raises a clear `ConfigError` if the
file is missing, the site list is empty, a URL doesn't start with `http`, or the
interval is too small. Failing early with a clear message is much better than crashing
later with a confusing one.

I used `yaml.safe_load` instead of `yaml.load`. The `safe_` version cannot run code
hidden inside a YAML file, so it is the secure choice.

### Step 5: Checking a site in `checker.py`

```python
start = time.perf_counter()
try:
    response = requests.get(site.url, timeout=site.timeout)
except requests.RequestException as exc:
    return CheckResult(site, False, None, None, error=type(exc).__name__)
```

Key ideas:

- **Always set a timeout.** Without one, `requests.get` can wait forever on a dead server
  and the whole tool would freeze.
- **Catch `requests.RequestException`.** This one exception covers timeouts, DNS errors,
  refused connections and SSL errors. All of those mean "down".
- **`time.perf_counter()`** is a precise stopwatch. I use it to measure response time in ms.
- The function **returns** a `CheckResult` instead of printing. That makes it easy to test
  and easy to reuse.

### Step 6: Sending alerts in `notifier.py`

Both Telegram and Discord accept a simple HTTP POST with a JSON body:

```python
# Telegram
requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
              json={"chat_id": chat_id, "text": message})

# Discord
requests.post(webhook_url, json={"content": message})
```

I made a small base class `Notifier` with a `send(message)` method, and one subclass per
service. The rest of the app doesn't care which service is used. It just calls `send()`.
Adding Slack or email later means writing one new class. This is called *polymorphism*.

**Secrets come from environment variables**, never from code. `notifiers_from_env()` only
creates a notifier if its secrets are set. When sending fails, I log only the error
*type*, because the full error message could contain the bot token.

### Step 7: The monitor loop and "no spam" logic in `monitor.py`

The simple approach would be "if a site is down, send an alert". But then a site that is
down for an hour sends 60 messages. Instead, the monitor **remembers the last state** of
each site in a dictionary:

```python
previous = self.last_state.get(url)   # True, False, or None (never seen)
self.last_state[url] = r.is_up

if previous is None:
    should_alert = not r.is_up        # first check: alert only if already down
else:
    should_alert = previous != r.is_up  # alert only when the state CHANGES
```

| Before | Now | Alert? |
|---|---|---|
| never checked | up | no |
| never checked | down | yes, DOWN |
| up | up | no |
| up | down | yes, DOWN |
| down | down | no (this is the "no spam" part) |
| down | up | yes, RECOVERED |

`run_forever()` is just a `while True` loop: check everything, then `time.sleep(interval)`.

### Step 8: The command line in `__main__.py`

A file named `__main__.py` inside a package lets you run the package with
`python -m uptime_pinger`. I used **argparse** (built into Python) to add options like
`--once` and `--config`. It also creates `--help` automatically.

I made `main()` **return an exit code** instead of calling `sys.exit` everywhere.
Exit codes are how programs tell scripts and CI systems whether they succeeded.
`0` means success, anything else means a problem. That's why `--once` returns `1`
when a site is down: GitHub Actions marks the run as failed, and you see a red X.

`load_dotenv()` reads the `.env` file into environment variables at startup.

I used Python's **logging** module instead of `print`. Logging adds timestamps and
levels (INFO, WARNING, ERROR), and you can turn on debug output with `-v`.

### Step 9: Writing tests with pytest

Tests are small programs that check your code still works. Run them after every change.
Each test file in `tests/` matches one app file.

The tricky part is that the app talks to the internet, and tests should not. The internet
is slow, and websites change. So I used the **`responses`** library to fake HTTP replies:

```python
@responses.activate
def test_site_is_down_on_wrong_status():
    responses.get("https://example.com", status=500)   # pretend the site returns 500
    result = check_site(Site(name="Example", url="https://example.com"))
    assert not result.is_up
```

For the monitor tests, I wrote a `FakeNotifier` that stores messages in a list instead of
sending them. Then the test can check exactly which alerts would have been sent.

Other pytest features used:

- `tmp_path`: a fresh temporary folder for writing test config files.
- `monkeypatch`: sets or removes environment variables only for one test.
- `pytest.raises`: checks that the code raises the right error.

### Step 10: Linting with ruff

A **linter** reads your code and finds problems without running it: unused imports,
undefined names, messy import order, old-style syntax. `ruff` is very fast and is set up
in `pyproject.toml`:

```toml
[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]   # style, errors, import order, bugbear, upgrades
```

### Step 11: Packaging it in Docker

**Docker** packs the app plus Python plus its libraries into one *image*. That image
runs the same way on any computer or server. The `Dockerfile` is the recipe:

```dockerfile
FROM python:3.12-slim                 # start from a small official Python image
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt   # install libraries first...
COPY uptime_pinger/ ./uptime_pinger/                 # ...then copy the code
COPY config.yaml .
RUN useradd --create-home appuser
USER appuser                          # don't run as root
ENTRYPOINT ["python", "-m", "uptime_pinger"]
CMD ["--config", "config.yaml"]
```

Why this order? Docker caches each step. Libraries change rarely and code changes
often. Installing libraries **before** copying the code means a code change doesn't
force Docker to reinstall everything. Builds stay fast.

Why `USER appuser`? If someone ever broke into the container, they would not have root
power. Running as a normal user is a basic security habit.

`ENTRYPOINT` is the fixed command. `CMD` gives default arguments you can override, as in
`docker run uptime-pinger --once`.

`.dockerignore` keeps `.env`, `.venv`, tests and Git files **out** of the image. This
makes the image smaller and keeps your secrets out of it.

### Step 12: docker compose

Typing long `docker run` commands gets old. `docker-compose.yml` saves the settings in a file:

- `restart: unless-stopped`: Docker restarts the app after a crash or reboot.
- `env_file: .env`: passes your secrets into the container.
- `volumes: ./config.yaml:/app/config.yaml:ro`: shares your config file with the
  container as read-only (`ro`). You can change sites without rebuilding the image.

### Step 13: CI with GitHub Actions

**CI (Continuous Integration)** means every time you push code, a robot checks it
automatically. `.github/workflows/ci.yml` tells GitHub to:

1. Run on every `push` and `pull_request`.
2. Start a fresh Ubuntu machine.
3. Install Python. A **matrix** runs the job 3 times, for Python 3.11, 3.12 and 3.13.
4. Install the libraries, run `ruff`, then run `pytest`.
5. If tests pass (`needs: test`), build the Docker image and run it with `--version` as a
   quick **smoke test**.

If anything fails, you get a red X on GitHub and an email. The badge at the top of this
README shows the current status.

### Step 14: Scheduled monitoring with GitHub Actions

`.github/workflows/uptime-check.yml` uses a **cron** schedule:

```yaml
on:
  schedule:
    - cron: "*/15 * * * *"     # every 15 minutes
  workflow_dispatch:           # also allow a manual "Run workflow" button
```

Cron's five fields are minute, hour, day of month, month and day of week.
`*/15` in the minute field means "every 15 minutes".

The secrets are passed in from **GitHub Secrets** with `${{ secrets.NAME }}`. GitHub
hides them in logs, and they are never stored in the code.

### Step 15: Git hygiene

- `.gitignore` stops Git from tracking `.env` (secrets), `.venv` (huge and
  machine-specific) and cache folders.
- `.env.example` **is** committed. It shows others which variables they need,
  without any real values.
- `LICENSE` (MIT) tells people they are allowed to use your code.

---

## Putting it on GitHub

The project already has a local Git repository with a first commit. To upload it:

1. Go to [github.com/new](https://github.com/new) and create a repo named `uptime-pinger`.
   **Don't** tick "Add a README", since you already have one.
2. In this folder, run:

```bash
git remote add origin https://github.com/YOUR-USERNAME/uptime-pinger.git
git branch -M main
git push -u origin main
```

3. Open the **Actions** tab on GitHub and watch the CI run turn green.
4. Edit the badge link at the top of this README to use your username, then:

```bash
git add README.md
git commit -m "Update CI badge link"
git push
```

Before every push, it's a good habit to run `git status` and check that `.env` is **not** listed.

---

## Glossary for beginners

| Term | Meaning |
|---|---|
| **HTTP status code** | A number a website sends back. `200` = OK, `404` = not found, `500` = server error. |
| **Timeout** | How long to wait for an answer before giving up. |
| **Virtual environment** | A private set of Python libraries for one project. |
| **Environment variable** | A named value set outside your code, used for settings and secrets. |
| **Webhook** | A URL you send data to, to trigger something, like posting a Discord message. |
| **Linter** | A tool that finds problems in code without running it. |
| **Unit test** | A small automated check of one piece of code. |
| **Mocking** | Replacing a real thing, like the internet, with a fake one during tests. |
| **Docker image** | A packaged app with everything it needs to run. |
| **Container** | A running copy of a Docker image. |
| **CI** | Continuous Integration: automatic checks on every push. |
| **Cron** | A format for saying "run this on a schedule". |
| **Exit code** | A number a program returns when it ends. `0` means success. |

---

## Ideas to extend it

Good next steps once you are comfortable:

- Check sites **in parallel** with `concurrent.futures.ThreadPoolExecutor`.
- Alert only after **2 failures in a row**, to avoid false alarms from one slow reply.
- Check that the page **contains a keyword**, not just the status code.
- Warn when an **SSL certificate** is about to expire.
- Save results to **SQLite** and show response-time history.
- Add a **Slack** or **email** notifier, which means one new class in `notifier.py`.
- Publish the image to **GitHub Container Registry** from the CI pipeline.

---

## License

[MIT](LICENSE)
