# Tech Stack

## Language
- Python (based on `.py` files and `requirements.txt`)

## Frameworks/Libraries
- ttkbootstrap (v1.10.1+) - For enhanced Tkinter UI styling.

## UI
- Tkinter (Python Standard Library) - Core GUI framework.

## Data Storage
- JSON (Used for saving project configurations and user preferences, including file selections, in `~/.filemerger/preferences.json`).

## Architecture Decisions
- Project settings (root/output dirs, ignored types, selected paths, rules, prompt) are saved per-project in a JSON file.