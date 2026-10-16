# uinput-expander

A small, dependency-free text expander for **GNOME on Wayland**. It detects what you type
by reading the keyboard devices directly (`evdev`) and inserts the replacement through a
**virtual keyboard created with `uinput`** — so it never touches the clipboard, needs no
root, and does not depend on X11 or on any portal.

Written because every other option failed on GNOME, each one for a documented reason.

## Why not the alternatives (all measured, not guessed)

| Approach | Why it fails on GNOME/Wayland |
|---|---|
| **espanso** (X11 build) | Detection uses the X11 `XRecord` extension, which **XWayland does not provide**. Worker crashes with exit code 101, in a restart loop. |
| **espanso** (Wayland build) | Works, but non-ASCII text (á, ã, ç, ê) is routed to the **clipboard**, and on GNOME that path makes a **small popup flicker near the cursor** on every expansion. Also: the trigger word is **not deleted** when the clipboard write fails, and the upstream fix for that (`espanso#2654`) was **never merged** — 2.4.1, the latest release, still has it. |
| `quantavil/text-expander-wayland`, `Westra126/TextExpander` | Rust, lightweight, even read espanso config files — but they inject through the **wlroots virtual-keyboard protocol**, which **Mutter does not implement**. Works on Sway/Hyprland/KDE, not on GNOME. One of them says so in its own README. |
| `ydotool` | Not installed with its daemon here (`ydotoold` missing), and it is a tool, not an expander. |
| **This** | Detection by `evdev`, injection by `uinput`. No clipboard anywhere, therefore no flicker by construction. |

## How it works

1. **Detection** — reads every `/dev/input/event*` that `udev` marks as a keyboard
   (needs the `input` group; see Permissions). Keeps a rolling buffer of the last 48
   characters, interpreted with the keyboard layout (see *Layout* below).
2. **Trigger match** — when the buffer ends with a trigger from the config, it waits for
   the **key release**, then deletes the trigger with backspaces and types the replacement.
   Expanding on key *press* instead races the physical key and makes applications eat a
   character (this cost an afternoon: the `c` of *Bacharelado* kept disappearing).
3. **Injection** — a virtual keyboard created in the kernel via `/dev/uinput`. No X11, no
   portal, no clipboard.

Resource use is trivial: two Python processes, no background CPU when idle.

## Requirements

- Linux with **Wayland** (works on GNOME; nothing here is GNOME-specific except the reason
  it exists)
- Python 3 (no third-party modules)
- Your user in the **`input`** group: `sudo usermod -aG input "$USER"` (log out and back in)
- Write access to `/dev/uinput`. Many distributions grant it with a udev rule; check with
  `getfacl /dev/uinput`. If it is not granted, add a rule:

  ```
  # /etc/udev/rules.d/99-uinput.rules
  KERNEL=="uinput", GROUP="input", MODE="0660"
  ```

  `sudo setcap cap_dac_override+p ./expansor.py` also works but is **less safe** — a
  capability on a file the user can rewrite is a privilege-escalation path. Prefer the group.

## Install

```bash
git clone https://github.com/<user>/uinput-expander
cd uinput-expander
./install.sh              # copies to ~/.local/bin/expansor and enables the user service
```

Then edit `~/.config/expansor/gatilhos.tsv` (one `trigger<TAB>replacement` per line) and
restart: `systemctl --user restart expansor.service`.

## Configuration

`~/.config/expansor/gatilhos.tsv`:

```
# trigger<TAB>replacement
saudacao	Olá! Tudo bem?
assinatura	Nome Sobrenome — empresa@exemplo.com
```

Empty lines and lines starting with `#` are ignored. There are no app-specific rules, and
none are planned: on GNOME there is no reliable way to know which window has focus.

## Layout (important)

Keycodes are physical positions; the compositor applies the layout. **Characters that need
`Shift` are layout-specific**, and the map shipped here was measured on a **Brazilian (ABNT2)
keyboard**. Measured values, for reference:

| Character | Keys |
|---|---|
| `:` | Shift + 53 |
| `"` | Shift + 41 |
| `^` | Shift + 40 |
| `<` `>` | Shift + 51 / Shift + 52 |
| `'` | 41 |
| `/` | 89 |
| `?` | Shift + 89 |
| `\` | 86 |
| `|` | Shift + 86 |
| `ç` | 39 |
| acute (á é í ó ú) | 26, then the vowel |
| tilde (ã õ) | 40, then the vowel |
| circumflex (ê â) | Shift + 40, then the vowel |

**On another layout**, measure your own instead of trusting the table: `tools/calibrar.py`
opens a test window, types each candidate key and shows what came out. Adapt `SHIFT_EXTRA`
and `ACENTOS` in `src/uinput_type.py`. This is the part most likely to need work for your
keyboard — please send measurements as an issue or PR.

## Timing (also measured)

- **2 ms between pressing and releasing each key.** Without it, applications treat the key
  as a repeat and drop characters at random.
- **~45 ms between a dead key and its vowel**, so the composition completes.
- **11 ms between keystrokes** is what this machine sustains without losses. If you see
  dropped characters, raise it (`pausa=` in `src/expansor.py`).

### And one trap worth knowing if you write this yourself

The virtual keyboard must declare **every** keycode it may ever emit
(`UI_SET_KEYBIT`). Declaring only the keys already in your map looks fine and fails
silently: the kernel **discards events for undeclared keycodes**, so the symptom is a
character that simply never appears — no error, no log line. That is also why probing an
unknown key with a partially declared device proves nothing.

## Known limitations

- Layout-specific `Shift` symbols (see above).
- The tool ignores virtual keyboards named `Typeless Keyboard Helper` (so dictated text does
  not trigger expansions when a dictation app is installed). Adapt the name filter in
  `descobrir_teclados()` for other apps.
- It never reads its **own** virtual keyboard — doing so would be an infinite loop.

## License

MIT (see `LICENSE`).

## Credits and authorship

This project exists because a user needed text expansion on **GNOME/Wayland** and every
existing option failed on that setup. The diagnosis, the design and the code were produced
by **Hermes**, an autonomous agent by **Nous Research**, running on the **DeepSeek V4 Flash**
model (`deepseek-v4-flash`, provider `deepseek`).

What was actually done by the agent, with measurement rather than guesswork:

- reproduced and instrumented the `espanso` failures on Wayland (X11 build: `X11Source`
  unavailable under XWayland, worker exiting 101 in a loop; Wayland build: clipboard path
  producing the GNOME popup, with the upstream fix `espanso#2654` never merged);
- ruled out the ready-made Wayland expanders by reading their injection mechanism
  (wlroots virtual-keyboard, absent in Mutter);
- wrote the `evdev` detection and the `uinput` injection from scratch;
- measured the Brazilian keymap by probing the real keyboard (dead-key sequences included);
- isolated the two timing requirements — 2 ms between press and release, and the gap needed
  by dead keys — and the key-release race that was swallowing characters;
- sanitised this repository so that no personal data from the user's machine is published.

Repository maintained by **Osvaldo Takai**. The agent's identity used in the commits is
`Hermes Agent`, with the commit address `hermes-agent@users.noreply.github.com`
(a GitHub no-reply address: it does not pretend to be a mailbox that exists).

**Testing** was done in daily use by **Osvaldo Takai** — the person living with the problem,
which is the part an agent cannot do for itself. Every defect worth fixing came from his
reports: the missing `c` of *Bacharelado*, the dot swallowed by the e-mail trigger, the
letter-by-letter slowness, and the popup flicker that ended up removing espanso from the
machine altogether.
