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
                           ├──► Gemini (the brain) ──► picks a skill ──► confirm? ──► runs it
 typing ───────────────────┘          ▲                                   │
                                       └──────── result fed back ─────────┘
```

- **Brain:** Google **Gemini** (free tier). It decides *which* skill to run with
  *which* arguments, and can chain several steps. It sits behind a small `Brain`
  interface, so a local model or another provider can be swapped in later without
  touching any skill.
- **Skills:** small Python functions registered with an `@skill` decorator
  (`assistant/skills/`). Each advertises itself to Gemini automatically.
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

### 2. Add your Gemini API key

1. Get a free key: <https://aistudio.google.com/apikey>
2. Copy the template and edit it:

   ```bash
   copy .env.example .env
   ```

3. Put your key in `.env`:

   ```
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
- Gemini's free tier has generous but real rate limits, and requests go to Google.
- This is a personal-use tool. Review `run_python`/shell actions before approving.
