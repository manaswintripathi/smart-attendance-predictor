# Smart Attendance Predictor

Built by Manaswin Tripathi (@manaswintripathi)

A simple, honest attendance tracker for college students. Add your subjects, mark each class as attended or missed, and instantly see where you stand against the **75% rule** — plus exactly how many classes you must attend in a row to get back above 75%, or how many you can still skip while staying safe.

## Features

- **Add / edit / delete subjects** — name, classes attended, total classes
- **One-tap marking** — "Attended" (+1 attended, +1 total) or "Missed" (+1 total) per subject
- **75% rule, per subject and overall** — current %, safe / below-target status
- **Predictor** — for each subject and overall:
  - classes you must attend consecutively to reach 75%
  - classes you can skip while staying at or above 75%
- **Predictor calculator** — enter any attended / total / target % and get the same answer instantly, without saving anything
- **Overall dashboard** — total attended / total classes, overall %, progress bar, and a summary of how many classes you need overall
- **Seed data included** — 6 realistic subjects totalling **134 / 181 = 74.03%** as an example; edit them, clear them, or restore the sample with one click
- **Data persists in SQLite** — no account, no cloud, your data stays in `attendance.db`
- **REST API** — every action in the UI is backed by a JSON API (see below)
- **Clean, responsive UI** — works on desktop and mobile, no build step

## How the maths works

- Percentage = `attended / total × 100`
- Classes needed to reach target `T%`: the smallest `x` with `(attended + x) / (total + x) ≥ T/100`
- Classes you can skip while staying ≥ `T%`: the largest `s` with `attended / (total + s) ≥ T/100` (0 if you are already below target)

## Setup / run

```bash
# 1. Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

The database file `attendance.db` is created automatically on first run and seeded with the sample subjects above. It is git-ignored, so your real data never gets committed.

## API

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/subjects` | List all subjects with computed stats |
| `POST` | `/api/subjects` | Add a subject — `{"name", "attended", "total"}` |
| `PUT` | `/api/subjects/<id>` | Update a subject |
| `DELETE` | `/api/subjects/<id>` | Delete a subject |
| `POST` | `/api/subjects/<id>/attend` | Mark one class attended |
| `POST` | `/api/subjects/<id>/miss` | Mark one class missed |
| `GET` | `/api/overall` | Overall attended / total / % / needed / skippable |
| `GET` | `/api/predict?attended=20&total=26&target=75` | Predictor for any numbers |
| `POST` | `/api/seed` | Delete all and restore the sample data |
| `POST` | `/api/clear` | Delete all subjects |
| `GET` | `/api/health` | `{"status": "ok"}` |

Example:

```bash
curl http://127.0.0.1:5000/api/overall
curl "http://127.0.0.1:5000/api/predict?attended=134&total=181&target=75"
```

## Project structure

```
smart-attendance-predictor/
├── app.py                 # Flask app, SQLite storage, REST API, predictor maths
├── requirements.txt       # Only Flask
├── templates/
│   └── index.html         # Dashboard UI
├── static/
│   ├── style.css          # Responsive styling
│   └── app.js             # Fetches the API, renders cards, calculator
└── attendance.db          # Created on first run (git-ignored)
```

## License

MIT — free to use and modify.

---
Built by Manaswin Tripathi (@manaswintripathi)
