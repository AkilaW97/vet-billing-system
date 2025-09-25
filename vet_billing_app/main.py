
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from pathlib import Path
import os

from db import init_db, save_invoice, list_invoices, get_invoice_by_receipt
from invoice_pdf import create_invoice_pdf
from printing import print_pdf

APP_DIR = Path(__file__).resolve().parent
INVOICE_DIR = APP_DIR / "invoices"

PAYMENT_METHODS = ["Cash", "Debit", "Credit", "Check"]
MAX_ROWS = 12

def ensure_dirs():
    (APP_DIR / "data").mkdir(exist_ok=True)
    INVOICE_DIR.mkdir(exist_ok=True)

class InvoiceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vets One — Billing")
        self.geometry("1100x720")
        self.configure(padx=10, pady=10)
        ensure_dirs()
        init_db()
        self._build_ui()

    def _build_ui(self):
        # Header frame
        header = ttk.LabelFrame(self, text="Invoice Header")
        header.pack(fill="x", pady=6)

        self.receipt_no = tk.StringVar()
        self.date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.payment_method = tk.StringVar(value=PAYMENT_METHODS[0])
        self.customer_name = tk.StringVar()
        self.address = tk.StringVar()
        self.telephone = tk.StringVar()
        self.email = tk.StringVar()

        # Row 1
        ttk.Label(header, text="Receipt #").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        ttk.Entry(header, textvariable=self.receipt_no, width=20).grid(row=0, column=1, sticky="w")
        ttk.Label(header, text="Date").grid(row=0, column=2, sticky="w", padx=6)
        ttk.Entry(header, textvariable=self.date, width=24).grid(row=0, column=3, sticky="w")
        ttk.Label(header, text="Payment").grid(row=0, column=4, sticky="w", padx=6)
        ttk.Combobox(header, values=PAYMENT_METHODS, textvariable=self.payment_method, width=12, state="readonly").grid(row=0, column=5, sticky="w")

        # Row 2
        ttk.Label(header, text="Customer Name").grid(row=1, column=0, sticky="w", padx=6)
        ttk.Entry(header, textvariable=self.customer_name, width=38).grid(row=1, column=1, columnspan=2, sticky="w")
        ttk.Label(header, text="Telephone").grid(row=1, column=3, sticky="w", padx=6)
        ttk.Entry(header, textvariable=self.telephone, width=20).grid(row=1, column=4, sticky="w")
        ttk.Label(header, text="Email").grid(row=1, column=5, sticky="w", padx=6)
        ttk.Entry(header, textvariable=self.email, width=24).grid(row=1, column=6, sticky="w")

        # Row 3
        ttk.Label(header, text="Address").grid(row=2, column=0, sticky="w", padx=6)
        ttk.Entry(header, textvariable=self.address, width=80).grid(row=2, column=1, columnspan=5, sticky="we")

        for i in range(7):
            header.grid_columnconfigure(i, weight=1)

        # Items table
        items_frame = ttk.LabelFrame(self, text="Line Items")
        items_frame.pack(fill="both", expand=True, pady=6)

        cols = ["Item #", "Description", "Qty", "Unit Price", "Line Total"]
        self.entries = []
        for row in range(MAX_ROWS):
            row_entries = {}
            for col, name in enumerate(cols):
                ttk.Label(items_frame, text=name if row == 0 else "").grid(row=0, column=col, padx=6, sticky="w")
            e_item = ttk.Entry(items_frame, width=10)
            e_desc = ttk.Entry(items_frame, width=60)
            e_qty = ttk.Entry(items_frame, width=8)
            e_price = ttk.Entry(items_frame, width=12)
            e_total = ttk.Entry(items_frame, width=12, state="readonly")
            e_item.grid(row=row+1, column=0, padx=6, pady=2, sticky="w")
            e_desc.grid(row=row+1, column=1, padx=6, pady=2, sticky="we")
            e_qty.grid(row=row+1, column=2, padx=6, pady=2, sticky="w")
            e_price.grid(row=row+1, column=3, padx=6, pady=2, sticky="w")
            e_total.grid(row=row+1, column=4, padx=6, pady=2, sticky="w")
            items_frame.grid_columnconfigure(1, weight=1)

            def on_change(event, erow=row, eq=e_qty, ep=e_price, et=e_total):
                try:
                    q = float(eq.get()) if eq.get() else 0.0
                    p = float(ep.get()) if ep.get() else 0.0
                    et.configure(state="normal")
                    et.delete(0, tk.END)
                    et.insert(0, f"{q*p:.2f}")
                    et.configure(state="readonly")
                    self.recompute_total()
                except ValueError:
                    pass

            e_qty.bind("<KeyRelease>", on_change)
            e_price.bind("<KeyRelease>", on_change)

            row_entries = dict(item=e_item, desc=e_desc, qty=e_qty, price=e_price, total=e_total)
            self.entries.append(row_entries)

        # Totals + actions
        totals_frame = ttk.Frame(self)
        totals_frame.pack(fill="x", pady=6)

        ttk.Label(totals_frame, text="Subtotal:").pack(side="right")
        self.subtotal_var = tk.StringVar(value="0.00")
        ttk.Label(totals_frame, textvariable=self.subtotal_var, width=12).pack(side="right", padx=6)

        ttk.Label(totals_frame, text="Total:").pack(side="right")
        self.total_var = tk.StringVar(value="0.00")
        ttk.Label(totals_frame, textvariable=self.total_var, width=12).pack(side="right", padx=6)

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=6)
        ttk.Button(actions, text="Save PDF", command=self.save_pdf).pack(side="left")
        ttk.Button(actions, text="Save + Print", command=self.save_and_print).pack(side="left", padx=6)
        ttk.Button(actions, text="Past Bills", command=self.show_history).pack(side="left", padx=6)
        ttk.Button(actions, text="Clear Form", command=self.clear_form).pack(side="left", padx=6)

    def recompute_total(self):
        s = 0.0
        for r in self.entries:
            try:
                s += float(r["total"].get() or 0.0)
            except Exception:
                pass
        self.subtotal_var.set(f"{s:.2f}")
        self.total_var.set(f"{s:.2f}")

    def gather_items(self):
        items = []
        for r in self.entries:
            item_no = r["item"].get().strip()
            desc = r["desc"].get().strip()
            qty = r["qty"].get().strip()
            price = r["price"].get().strip()
            if any([item_no, desc, qty, price]):
                try:
                    q = float(qty or 0.0); p = float(price or 0.0)
                except ValueError:
                    q, p = 0.0, 0.0
                items.append({
                    "item_no": item_no,
                    "description": desc,
                    "qty": q,
                    "unit_price": p,
                    "line_total": q*p
                })
        return items

    def invoice_meta(self, pdf_path=""):
        return {
            "receipt_no": self.receipt_no.get().strip(),
            "date": self.date.get().strip() or datetime.now().strftime("%Y-%m-%d %H:%M"),
            "payment_method": self.payment_method.get(),
            "customer_name": self.customer_name.get().strip(),
            "address": self.address.get().strip(),
            "telephone": self.telephone.get().strip(),
            "email": self.email.get().strip(),
            "subtotal": float(self.subtotal_var.get() or 0.0),
            "total": float(self.total_var.get() or 0.0),
            "pdf_path": pdf_path
        }

    def output_path(self):
        now = datetime.now()
        ydir = INVOICE_DIR / f"{now.year:04d}" / f"{now.month:02d}"
        ydir.mkdir(parents=True, exist_ok=True)
        receipt = self.receipt_no.get().strip() or f"R{now.strftime('%Y%m%d_%H%M%S')}"
        return ydir / f"{receipt}.pdf"

    def save_pdf(self):
        items = self.gather_items()
        self.recompute_total()
        path = self.output_path()
        data = self.invoice_meta(pdf_path=str(path))
        create_invoice_pdf(str(path), data, items, logo_path=str(APP_DIR / "assets" / "logo.png"))
        save_invoice(data, items)
        messagebox.showinfo("Saved", f"Invoice saved to:\n{path}")

    def save_and_print(self):
        self.save_pdf()
        path = self.output_path()
        ok, err = print_pdf(str(path))
        if not ok:
            messagebox.showerror("Print Error", f"Could not print:\n{err}")
        else:
            messagebox.showinfo("Printing", "Sent to printer.")

    def clear_form(self):
        for v in (self.receipt_no, self.customer_name, self.address, self.telephone, self.email):
            v.set("")
        self.payment_method.set(PAYMENT_METHODS[0])
        self.date.set(datetime.now().strftime("%Y-%m-%d %H:%M"))
        for r in self.entries:
            for k in r.values():
                k.configure(state="normal")
                k.delete(0, tk.END)
        self.subtotal_var.set("0.00")
        self.total_var.set("0.00")

    def show_history(self):
        win = tk.Toplevel(self)
        win.title("Past Bills")
        tv = ttk.Treeview(win, columns=("receipt","date","customer","total","path"), show="headings")
        for c, w in (("receipt",150),("date",160),("customer",240),("total",100),("path",420)):
            tv.heading(c, text=c.title())
            tv.column(c, width=w, anchor="w")
        tv.pack(fill="both", expand=True)

        for inv in list_invoices(500):
            tv.insert("", "end", values=(inv["receipt_no"], inv["date"], inv["customer_name"], f"{inv['total']:.2f}", inv["pdf_path"]))

        def open_selected():
            cur = tv.focus()
            if not cur: return
            vals = tv.item(cur)["values"]
            path = vals[4]
            if os.path.exists(path):
                os.startfile(path) if os.name == "nt" else os.system(f'xdg-open "{path}"')

        def print_selected():
            cur = tv.focus()
            if not cur: return
            vals = tv.item(cur)["values"]
            path = vals[4]
            ok, err = print_pdf(path)
            if not ok:
                messagebox.showerror("Print Error", err)

        btns = ttk.Frame(win)
        btns.pack(fill="x")
        ttk.Button(btns, text="Open PDF", command=open_selected).pack(side="left")
        ttk.Button(btns, text="Print PDF", command=print_selected).pack(side="left", padx=6)

if __name__ == "__main__":
    app = InvoiceApp()
    app.mainloop()
