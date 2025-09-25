
import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "vetsone.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS invoices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                receipt_no TEXT UNIQUE,
                date TEXT,
                payment_method TEXT,
                customer_name TEXT,
                address TEXT,
                telephone TEXT,
                email TEXT,
                subtotal REAL,
                total REAL,
                pdf_path TEXT
            )
            '''
        )
        c.execute(
            '''
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                invoice_id INTEGER,
                item_no TEXT,
                description TEXT,
                qty REAL,
                unit_price REAL,
                line_total REAL,
                FOREIGN KEY(invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
            )
            '''
        )
        conn.commit()

def save_invoice(inv: Dict[str, Any], items: List[Dict[str, Any]]):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute(
            '''INSERT INTO invoices
               (receipt_no, date, payment_method, customer_name, address, telephone, email, subtotal, total, pdf_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                inv["receipt_no"], inv["date"], inv["payment_method"], inv["customer_name"],
                inv["address"], inv["telephone"], inv["email"], inv["subtotal"], inv["total"], inv["pdf_path"]
            )
        )
        invoice_id = c.lastrowid
        for it in items:
            c.execute(
                '''INSERT INTO items (invoice_id, item_no, description, qty, unit_price, line_total)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (invoice_id, it["item_no"], it["description"], it["qty"], it["unit_price"], it["line_total"])
            )
        conn.commit()
        return invoice_id

def list_invoices(limit: int = 100):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM invoices ORDER BY date DESC, id DESC LIMIT ?', (limit,))
        return [dict(r) for r in c.fetchall()]

def get_invoice_by_receipt(receipt_no: str):
    with get_conn() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM invoices WHERE receipt_no = ?', (receipt_no,))
        inv = c.fetchone()
        if not inv: return None, []
        inv = dict(inv)
        c.execute('SELECT * FROM items WHERE invoice_id = ? ORDER BY id', (inv["id"],))
        items = [dict(r) for r in c.fetchall()]
        return inv, items
