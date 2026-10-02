# Jarvis — a Gemini-powered PC assistant (voice + text)

A personal assistant for your **Windows** PC. Tell it what to do in plain English
(typed or spoken) and it carries it out: open and close apps, control the mouse
and keyboard, create/move/delete files, search the web, report system status, and
more. When no built-in skill fits, it can write and run a short Python script to
get the job done — always showing you the code first.

> ⚠️ **This software controls your real computer** — mouse, keyboard, files.
> It can delete files and run commands. It's built to confirm anything risky
> before doing it, but treat it with the same care you'd give any automation tool.

---

## How it works

```
 voice ──(speech-to-text)──┐
                           ├──► the brain ──► picks a skill ──► confirm? ──► runs it
 typing ───────────────────┘        ▲                            │
                                    └──── result fed back ───────┘
```

- **Brain:** swappable, chosen with `BRAIN` in `.env`:
  - **`ollama`** (default) — a model running **on your own PC**. Free forever,
    offline, **no API key and no usage cap whatsoever**. Recommended.
  - **`gemini`** — Google's cloud API. Smarter and better at complex,
    multi-step requests, but the free tier allows only a small number of
    requests per day and needs internet.
- **Skills:** small Python functions registered with an `@skill` decorator
  (`assistant/skills/`). Each advertises itself to the brain automatically.
- **Safety:** skills marked *destructive* are confirmed before running; deletes go
  to the **Recycle Bin**; system folders are protected; every action is logged.
- **Voice** is optional and fully isolated — the assistant runs in text mode even
  if the voice libraries aren't installed.

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

Optional voice support (speech-to-text + text-to-speech):

```bash
pip install -r requirements-voice.txt
```

> Voice libraries install from prebuilt wheels on Python 3.13/3.14 (fastapi-whisper
> via ctranslate2, sounddevice, pyttsx3). Text mode works with no extra installs,
> and voice is fully optional — the assistant falls back to typing if it's missing.

### 2. Pick your brain

**Option A — local, unlimited, free (recommended)**

1. Install [Ollama](https://ollama.com/download) (Windows installer; it runs in
   the background automatically).
2. Download a model that supports tool calling:

   ```bash
   ollama pull qwen2.5:7b
   ```

3. That's it — `BRAIN=ollama` is already the default. No key, no account, no
   internet needed at runtime, and **no limit on how much you can ask**.

**Option B — Gemini (cloud, smarter, rate-limited)**

1. Get a free key: <https://aistudio.google.com/apikey>
2. Copy the template and edit it:

   ```bash
   copy .env.example .env
   ```

3. Set your key and switch brains in `.env`:

   ```
   BRAIN=gemini
   GEMINI_API_KEY=your_key_here
   ```

   (`.env` is git-ignored and never committed.)

---

## Usage

```bash
python main.py                 # type commands
python main.py --voice         # press Enter on an empty line to speak a command
python main.py --speak         # read replies aloud
python main.py --voice --speak # voice in + voice out
python main.py --wake          # hands-free: say "Hey Darling", then your command
```

In the prompt:
- Type a request and press Enter.
- In `--voice` mode, press Enter on an **empty** line to start recording, speak,
  then press Enter again to stop.
- `reset` clears the conversation; `exit` (or Ctrl+C) quits.

### Hands-free mode ("Hey Darling")

`python main.py --wake` listens continuously and sleeps until it hears the wake
phrase, then replies "Yes?" and records your command — stopping automatically when
you pause. Just speak; no typing needed.

- The wake phrase is set by `WAKE_WORD` in `.env` (default `hey darling`).
  Matching is lenient: the last word alone ("darling") also wakes it.
- Speech-to-text runs **locally and offline** (faster-whisper); nothing is sent to
  Google except the transcribed command, exactly as in typed mode.
- The first run downloads the Whisper model once.

### Example requests
- "What's my CPU and memory usage right now?"
- "Open Notepad."
- "Create a file called notes.txt on my Desktop that says 'hello world'."
- "Search the web for the fastest route to the airport."
- "Move the mouse to the center of the screen and click."
- "Delete notes.txt from my Desktop." → asks to confirm, then sends it to the Recycle Bin.
- "Rename every .txt on my Desktop to uppercase." → no single skill fits, so it
  proposes a short Python script, shows it to you, and runs it on approval.

---

## Safety model

| Guard | What it does |
|---|---|
| Confirmation gate | Destructive skills (delete, overwrite, move, close apps, shutdown, shell/code) prompt `[y/N]` before running. Toggle with `CONFIRM_DESTRUCTIVE` in `.env`. |
| Recycle Bin deletes | `delete_file` uses the Recycle Bin by default; permanent delete is opt-in. |
| Protected paths | Windows, Program Files, ProgramData, drive roots, and the app's own folder are refused for destructive ops. |
| Action log | Every skill call (args + result) is written to `assistant.log`. |
| Fail-safes | pyautogui fail-safe (move the mouse to a screen corner to abort) and Ctrl+C. |
| Confirmed code | `run_python` / `run_shell_command` always show the exact code/command first. |

---

## Adding a new skill

Create or edit a module in `assistant/skills/` and decorate a function:

```python
from assistant.registry import skill

@skill(
    "Empty the Recycle Bin.",         # shown to Gemini so it knows when to use it
    destructive=True,                  # -> asks for confirmation
    params={"confirm": "Must be true to proceed."},
)
def empty_recycle_bin(confirm: bool = False) -> str:
    ...
    return "Recycle Bin emptied."
```

Then add the module to the list in `assistant/skills/__init__.py`. The parameter
schema is derived from your type hints automatically, and the skill becomes
available to the brain on the next run.

---

## Project layout

```
main.py                     entry point (text/voice loop)
config.py                   settings + .env loading + known folders
requirements.txt            core deps
requirements-voice.txt      optional voice deps
assistant/
  registry.py               @skill decorator + execution + confirmation gate
  confirm.py                the [y/N] prompt
  safety.py                 protected paths + action logging
  brain/
    base.py                 the swappable Brain interface
    gemini_brain.py         Gemini client + tool-calling loop
  skills/
    files.py apps.py input_control.py screen.py
    system.py web.py clipboard.py code_exec.py
io_layer/
  text_io.py voice_input.py voice_output.py
```

- `voice_input.py` provides push-to-talk (`listen`), silence-stopped capture
  (`listen_command`), and wake-word detection (`listen_for_wake_word`).

---

## Notes & limits
- Windows-only (uses `os.startfile`, `shutdown`, `LockWorkStation`, media keys).
- The local brain needs a few GB of disk for the model, and quality depends on
  the model size you pick (see below).
- Gemini's free tier has real rate limits, and requests go to Google.
- This is a personal-use tool. Review `run_python`/shell actions before approving.

---

## Which brain, and which model?

| | Local (Ollama) | Gemini (cloud) |
|---|---|---|
| Cost | **Free forever** | Free tier, then paid |
| Usage limit | **None** | ~20 requests/day per model on the free tier |
| Internet | Not needed | Required |
| Privacy | Nothing leaves your PC | Commands+results go to Google |
| Quality | Good | Better at complex/multi-step requests |
| Speed | Fast after the first (model load) call | Fast, but network-bound |

**Recommended setup:** run local as your everyday brain (`BRAIN=ollama`) and
flip to `BRAIN=gemini` when you hit something the local model fumbles.

Local model size matters. With an 8 GB GPU:

| Model | Disk | Notes |
|---|---|---|
| `qwen2.5:3b` | ~2 GB | Fastest; weaker at chaining skills |
| **`qwen2.5:7b`** | **~4.7 GB** | **Best balance; fits in 8 GB VRAM (`OLLAMA_MODEL` default)** |
| `qwen2.5:14b` | ~9 GB | Smarter, but spills out of VRAM → slower |

Whatever you pick, pull it first (`ollama pull qwen2.5:14b`), then set
`OLLAMA_MODEL=qwen2.5:14b` in `.env`.

---

## Making it faster

Two things dominate the delay, and both are tunable in `.env`:

**1. The Gemini free tier (the big one).** The free tier allows only a **small
number of requests per day, per model** (we hit `limit: 20` on `gemini-3.8-flash`).
Once you exhaust it, requests fail until **midnight Pacific**. Each model has its
**own** daily bucket, so switching `GEMINI_MODEL` gives you a fresh allowance. The
assistant now tells you clearly when the daily quota is hit, instead of retrying.
- Fastest measured model with tools: **`gemini-3.6-flash`** (default).
- Other fresh buckets: `gemini-3.1-flash-lite-preview`, `gemini-3.5-flash-lite`.
- Raise the ceiling: enable billing in Google AI Studio.

**2. "Thinking" latency.** Gemini 3.x silently "thinks" before every reply, adding
several seconds. `GEMINI_THINKING_BUDGET=0` disables it — right for short PC
commands. Set `512`+ if you want better multi-step reasoning.

**3. Speech-to-text.** Local and offline, but the model choice matters:

| Setting | Effect |
|---|---|
| `WHISPER_MODEL=base.en` | English-only → **~2× faster** than multilingual `base` *and* more accurate for English. `tiny.en` is faster still but mangles words ("iPad" for "Notepad"). |
| `WHISPER_BEAM=1` | Greedy decoding — fastest. Higher is slower. |
| `WHISPER_THREADS` | `0` = use all CPU cores. |

In `--wake` mode, Whisper runs **twice** per exchange (once for the wake phrase,
once for your command), so each tweak is felt twice. The pause that ends your
command (`SILENCE_DURATION`, default 0.8s) also adds a fixed wait — lower it if
you're comfortable with a shorter window.

Typical result after tuning: a spoken command round-trips in **~4–5s**.
