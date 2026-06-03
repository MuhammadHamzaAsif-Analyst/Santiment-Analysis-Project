# Flask + MySQL Data UI (Search / Filter / Sort)

## Setup

1) Create and activate a virtual environment (recommended).

2) Install dependencies:

```bash
pip install -r requirements.txt
```

3) Create a `.env` file (copy from `.env.example`) and set:
- `DB_NAME`
- `DB_TABLE`
- `DB_USER`
- `DB_PASSWORD`

## Run

```bash
python app.py
```

Open the UI at `http://127.0.0.1:5000/`.

## DSA concepts used

- **Merge sort**: stable in-memory sorting for any selected column.
- **Binary search**: exact-match filtering uses a sorted array + binary search to find the matching range.
- **Pagination**: shows only the current page to keep rendering fast.
