![Apollo Lightning App Icon (from Google android Playstore)](https://play-lh.googleusercontent.com/MmK_EubdKrAWkhehvvxdylkQT2XNhl-wMmUj77icVe5MD12GWycWDqw8QaVBUspQEiA=w240-h480-rw)

# LED Controller CLI

LEDS controller is only controllable via their "Apollo Lightning" app. I barely use my phone (or it's often dead), so this tool became a need — and I had fun making scripts and animations for my lights.

Their Website: https://www.qh-tek.com/

## What this is

- A small command-line tool to control BLE LED controllers compatible with the Apollo app.
- Features: scanning, direct MAC connection, default MAC storage, color presets (save/load/list), mode selection, brightness and more.

## Quick start

1. Create and activate a virtual env (Windows example):

```powershell
py -m venv env
env\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run commands:

```powershell
python main.py --scan
python main.py --on
python main.py --off
python main.py --rgb 255,0,0 --brightness 90
python main.py --set-mode MODE_2 --speed 100
```

3. Save a default MAC so future commands skip scanning:

```powershell
python main.py --default-mac AA:BB:CC:DD:EE:FF
python main.py --on   # uses saved default MAC
```

Remove default MAC:

```powershell
python main.py --remove-default-mac
```

## Presets (save & load colors)

- Save a color preset (requires `--rgb`):

```powershell
python main.py --save SoftPink --rgb 255,182,193 --brightness 80
```

- List saved presets:

```powershell
python main.py --presets
python main.py --colours   # alias
```

- Load and apply a preset:

```powershell
python main.py --load SoftPink --on
```

- Remove a preset:

```powershell
python main.py --remove-preset SoftPink
```

Saved presets and the default MAC are stored in `.led_controller_config.json` next to `main.py` (or next to the executable when built).

## Building a single executable

Install PyInstaller and build:

```powershell
pip install pyinstaller
pyinstaller --onefile --name led-controller --collect-all bleak main.py
```

The built exe will be in `dist\led-controller.exe`.

You can also use the included `build.bat` if present.

## Notes

- On Windows the `bleak.backends.corebluetooth` warning during build is harmless — it's the macOS backend being skipped.
- If you run into issues, make sure the correct Python interpreter/venv is active (use `python`, not `py`, while the venv is activated).

## License & Contribute

Drop issues or PRs on the project repository. No attached license by default — add one if you want to reuse this code publicly.

---
Created to make my lights usable without the phone app and to experiment with animations.

