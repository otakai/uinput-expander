# Contributing

The most useful contribution right now is **a keymap measurement for your keyboard layout**.

Characters needing `Shift` are layout-specific, and the map in `src/uinput_type.py` was
measured on a Brazilian (ABNT2) keyboard. The Brazilian `/` and `?` keys are still missing.

## Measuring your layout (about a minute)

```bash
python3 tools/calibrar.py
```

A small window opens; the script types every candidate key and shows what each one
produced. Open an issue with the result, or send a pull request changing `SHIFT_EXTRA`
and `ACENTOS` in `src/uinput_type.py`.

## Reporting a bug

Please include:

- your keyboard layout and the character that came out wrong (or did not appear);
- whether it happens in every application or only some;
- `~/.cache/expansor/expansor.log` (it logs triggers, not what you type elsewhere).

## Before sending a pull request

- `python -m py_compile src/*.py tools/*.py`
- `bash -n install.sh`
- Keep it dependency-free: the whole point is not to need anything installed.
- Never add clipboard use: it reintroduces the popup flicker this project exists to avoid.
