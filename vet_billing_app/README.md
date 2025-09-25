
# Vets One — Local Billing System (Desktop)

A simple **offline** billing app for a veterinary clinic. Create invoices that look like your template, save them as formatted PDFs to a date-based folder, and (optionally) print to a connected printer.

## Highlights
- Local-only: SQLite database (`data/vetsone.db`) on disk
- Generate **PDF invoices** (via `reportlab`) styled like your template
- Save PDFs under `invoices/YYYY/MM/`
- Search & reopen past bills in the app
- Print to default system printer (Windows/macOS/Linux)
- Easy to extend later for web hosting

## Quick Start
1. **Install Python 3.9+**.
2. Create and activate a virtualenv (recommended).
3. Install deps:
   ```bash
   pip install reportlab pillow
   ```
4. Run the app:
   ```bash
   python main.py
   ```

> Optional: On Linux/macOS ensure the `lp`/`lpr` command exists for printing (CUPS).  
> On Windows, the app uses `os.startfile(path, "print")`. For more control, you can later add `pywin32`.

## Files
- `main.py` — Tkinter desktop app
- `invoice_pdf.py` — PDF generation (ReportLab)
- `db.py` — SQLite models & helpers
- `printing.py` — cross‑platform print helper
- `assets/logo.png` — your logo placeholder (replace with your own)
- `data/` — DB storage (created at first run)
- `invoices/YYYY/MM/` — PDFs saved here (auto-created)

## Notes
- You can modify header text and fields in `invoice_pdf.py` to match branding exactly.
- The line‑item table supports up to 12 rows by default (change `MAX_ROWS` in `main.py` if you like).
- The receipt number can be auto‑generated (prefix + incremental) or typed manually.

## Roadmap Ideas
- Add taxes/discounts fields
- Export to CSV for accounting
- Build a small Flask API to sync invoices later
- User roles & authentication (for a hosted version)
