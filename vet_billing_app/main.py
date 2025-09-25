import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from pathlib import Path
import os
import random

from db import init_db, save_invoice, list_invoices
from invoice_pdf import create_invoice_pdf
from printing import print_pdf

APP_DIR = Path(__file__).resolve().parent
INVOICE_DIR = APP_DIR / "invoices"

PAYMENT_METHODS = ["Cash", "Debit", "Credit", "Check"]
MAX_ROWS = 12

# Suggestions for the Description field
PRESET_DESCRIPTIONS = [
    "Consultation", "Drug cost", "Disposable", "Transport",
    "Surgery", "Lab tests", "Pet shop items",
]

class AutoCompleteEntry(ttk.Entry):
    """
    Dropdown always shows ALL suggestions while typing.
    Enter keeps typed text (unless list was navigated).
    Up/Down (or click) selects a suggestion. Ctrl+Space reopens.
    """
    def __init__(self, master=None, suggestions=None, **kwargs):
        super().__init__(master, **kwargs)
        self.suggestions = suggestions or []
        self.lb = None
        self.user_navigated = False
        self.bind("<KeyRelease>", self._on_keyrelease, add="+")
        self.bind("<Return>", self._on_return, add="+")
        self.bind("<Control-space>", self._force_show_all, add="+")
        self.bind("<Down>", self._on_down, add="+")
        self.bind("<Up>", self._on_up, add="+")
        self.bind("<FocusOut>", self._hide_listbox, add="+")

    def _force_show_all(self, event=None):
        self._show_listbox(self.suggestions); return "break"

    def _show_listbox(self, matches):
        if self.lb is None:
            self.lb = tk.Listbox(self.winfo_toplevel(), height=min(6, len(matches)))
            self.lb.bind("<Button-1>", self._on_click)
            self.lb.bind("<Return>", self._on_return)
        else:
            self.lb.delete(0, tk.END)
            self.lb.configure(height=min(6, len(matches)))
        for m in matches:
            self.lb.insert(tk.END, m)
        x = self.winfo_rootx(); y = self.winfo_rooty() + self.winfo_height()
        self.lb.place(x=x, y=y, width=self.winfo_width())
        if matches:
            self.lb.selection_clear(0, tk.END); self.lb.selection_set(0)

    def _hide_listbox(self, *_):
        if self.lb is not None: self.lb.place_forget()
        self.user_navigated = False

    def _on_keyrelease(self, event):
        if event.keysym in ("Return","Escape","Up","Down"): return
        self._show_listbox(self.suggestions)  # always show all suggestions while typing

    def _accept_selection(self):
        if self.lb and self.lb.size() > 0:
            try:
                idx = self.lb.curselection()[0]; value = self.lb.get(idx)
                self.delete(0, tk.END); self.insert(0, value)
            except IndexError:
                pass
        self._hide_listbox()

    def _on_return(self, event):
        if self.user_navigated and self.lb and self.lb.size() > 0:
            self._accept_selection()
        else:
            self._hide_listbox()  # keep typed text
        return "break"

    def _on_click(self, event):
        self.user_navigated = True; self._accept_selection()

    def _on_down(self, event):
        if self.lb and self.lb.size() > 0:
            self.user_navigated = True
            idxs = self.lb.curselection(); i = (idxs[0] + 1) if idxs else 0
            if i >= self.lb.size(): i = 0
            self.lb.selection_clear(0, tk.END); self.lb.selection_set(i)
        else:
            self._show_listbox(self.suggestions)
        return "break"

    def _on_up(self, event):
        if self.lb and self.lb.size() > 0:
            self.user_navigated = True
            idxs = self.lb.curselection(); i = (idxs[0] - 1) if idxs else 0
            if i < 0: i = self.lb.size() - 1
            self.lb.selection_clear(0, tk.END); self.lb.selection_set(i)
        return "break"

def ensure_dirs():
    (APP_DIR / "data").mkdir(exist_ok=True)
    (APP_DIR / "invoices").mkdir(exist_ok=True)

def generate_receipt_no():
    # Timestamp-based (practically unique). Example: R-20250925-142310
    return f"R-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

class InvoiceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vets One — Billing")
        self.geometry("1150x740")
        self.configure(padx=10, pady=10)
        ensure_dirs()
        init_db()
        self._build_ui()

    # ---------- Validation ----------
    def validate_required(self):
        name = self.customer_name.get().strip()
        phone = self.telephone.get().strip()
        missing = []
        if not name: missing.append("Customer Name")
        if not phone: missing.append("Telephone")
        if missing:
            messagebox.showerror("Required fields", "Please fill: " + ", ".join(missing))
            if not name:
                self.name_entry.focus_set()
            elif not phone:
                self.telephone_entry.focus_set()
            return False
        return True

    def _build_ui(self):
        # Header frame
        header = ttk.LabelFrame(self, text="Invoice Header")
        header.pack(fill="x", pady=6)

        self.receipt_no = tk.StringVar(value=generate_receipt_no())
        self.date = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.payment_method = tk.StringVar(value=PAYMENT_METHODS[0])
        self.customer_name, self.address, self.telephone, self.email = (tk.StringVar() for _ in range(4))

        # Row 1
        ttk.Label(header, text="Receipt # (auto)").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.receipt_entry = ttk.Entry(header, textvariable=self.receipt_no, width=24, state="readonly")
        self.receipt_entry.grid(row=0, column=1, sticky="w")
        ttk.Label(header, text="Date").grid(row=0, column=2, sticky="w", padx=6)
        ttk.Entry(header, textvariable=self.date, width=24).grid(row=0, column=3, sticky="w")
        ttk.Label(header, text="Payment").grid(row=0, column=4, sticky="w", padx=6)
        ttk.Combobox(header, values=PAYMENT_METHODS, textvariable=self.payment_method, width=12, state="readonly").grid(row=0, column=5, sticky="w")

        # Row 2 (with required markers)
        ttk.Label(header, text="Customer Name *").grid(row=1, column=0, sticky="w", padx=6)
        self.name_entry = ttk.Entry(header, textvariable=self.customer_name, width=38)
        self.name_entry.grid(row=1, column=1, columnspan=2, sticky="w")
        ttk.Label(header, text="Telephone *").grid(row=1, column=3, sticky="w", padx=6)
        self.telephone_entry = ttk.Entry(header, textvariable=self.telephone, width=20)
        self.telephone_entry.grid(row=1, column=4, sticky="w")
        ttk.Label(header, text="Email").grid(row=1, column=5, sticky="w", padx=6)
        ttk.Entry(header, textvariable=self.email, width=24).grid(row=1, column=6, sticky="w")

        # Row 3
        ttk.Label(header, text="Address").grid(row=2, column=0, sticky="w", padx=6)
        ttk.Entry(header, textvariable=self.address, width=80).grid(row=2, column=1, columnspan=5, sticky="we")

        for i in range(8):
            header.grid_columnconfigure(i, weight=1)

        # Items table
        items_frame = ttk.LabelFrame(self, text="Line Items")
        items_frame.pack(fill="both", expand=True, pady=6)

        # Columns: Item # (auto), Description, Qty, Unit Price, Line Total
        cols = ["Item #", "Description", "Qty", "Unit Price", "Line Total"]
        self.entries = []
        for row in range(MAX_ROWS):
            for col, name in enumerate(cols):
                ttk.Label(items_frame, text=name if row == 0 else "").grid(row=0, column=col, padx=6, sticky="w")

            # Item # entry (auto, readonly)
            e_item = ttk.Entry(items_frame, width=10, state="readonly")
            e_desc = AutoCompleteEntry(items_frame, suggestions=PRESET_DESCRIPTIONS, width=60)
            e_qty = ttk.Entry(items_frame, width=8)
            e_price = ttk.Entry(items_frame, width=12)
            e_total = ttk.Entry(items_frame, width=12, state="readonly")

            e_item.grid(row=row+1, column=0, padx=6, pady=2, sticky="w")
            e_desc.grid(row=row+1, column=1, padx=6, pady=2, sticky="we")
            e_qty.grid(row=row+1, column=2, padx=6, pady=2, sticky="w")
            e_price.grid(row=row+1, column=3, padx=6, pady=2, sticky="w")
            e_total.grid(row=row+1, column=4, padx=6, pady=2, sticky="w")
            items_frame.grid_columnconfigure(1, weight=1)

            def recompute_from_row(event=None, eq=e_qty, ep=e_price, et=e_total):
                try:
                    qty_txt = eq.get().strip()
                    price_txt = ep.get().strip()
                    # Default Qty = 1 if only Unit Price is provided
                    q = float(qty_txt) if qty_txt != "" else (1.0 if price_txt != "" else 0.0)
                    p = float(price_txt) if price_txt != "" else 0.0
                    et.configure(state="normal")
                    et.delete(0, tk.END)
                    et.insert(0, f"{q*p:.2f}")
                    et.configure(state="readonly")
                    self.recompute_total()
                    self.recompute_item_numbers()
                except ValueError:
                    pass

            # Enter in Description → keep text & jump to Qty
            def on_desc_enter(event, q_widget=e_qty):
                q_widget.focus_set(); return "break"

            # Bindings
            e_desc.bind("<Return>", on_desc_enter, add="+")
            e_desc.bind("<KeyRelease>", lambda e: self.recompute_item_numbers(), add="+")
            e_desc.bind("<FocusOut>", lambda e: self.recompute_item_numbers(), add="+")
            e_qty.bind("<KeyRelease>", recompute_from_row)
            e_price.bind("<KeyRelease>", recompute_from_row)
            e_qty.bind("<FocusOut>", recompute_from_row, add="+")
            e_price.bind("<FocusOut>", recompute_from_row, add="+")

            self.entries.append(dict(
                item=e_item, desc=e_desc, qty=e_qty, price=e_price, total=e_total
            ))

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

        # Initial numbering
        self.recompute_item_numbers()

    # ---------- Helpers ----------
    def recompute_total(self):
        s = 0.0
        for r in self.entries:
            try:
                s += float(r["total"].get() or 0.0)
            except Exception:
                pass
        self.subtotal_var.set(f"{s:.2f}")
        self.total_var.set(f"{s:.2f}")

    def _row_has_description(self, r):
        return bool(r["desc"].get().strip())

    def recompute_item_numbers(self):
        """Auto-assign sequential Item # for rows where Description is filled."""
        next_no = 1
        for r in self.entries:
            r["item"].configure(state="normal")
            r["item"].delete(0, tk.END)
            if self._row_has_description(r):
                r["item"].insert(0, str(next_no))
                next_no += 1
            r["item"].configure(state="readonly")

    def gather_items(self):
        # Only include rows with any content; item numbers come from auto field
        items = []
        for r in self.entries:
            desc = r["desc"].get().strip()
            qty_txt = r["qty"].get().strip()
            price_txt = r["price"].get().strip()
            if not any([desc, qty_txt, price_txt]):
                continue
            item_no = r["item"].get().strip()  # may be blank if no description
            try:
                q = float(qty_txt) if qty_txt != "" else (1.0 if price_txt != "" else 0.0)
                p = float(price_txt) if price_txt != "" else 0.0
            except:
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
        receipt = self.receipt_no.get().strip() or generate_receipt_no()
        return ydir / f"{receipt}.pdf"

    # ---------- Actions ----------
    def save_pdf(self):
        # Check required fields
        if not self.validate_required():
            return
        # Ensure item numbers up-to-date
        self.recompute_item_numbers()

        items = self.gather_items()
        self.recompute_total()
        path = self.output_path()
        data = self.invoice_meta(pdf_path=str(path))
        create_invoice_pdf(str(path), data, items, logo_path=str(APP_DIR / "assets" / "logo.png"))
        save_invoice(data, items)
        messagebox.showinfo("Saved", f"Invoice saved to:\n{path}")

    def save_and_print(self):
        if not self.validate_required():
            return
        self.save_pdf()
        path = self.output_path()
        ok, err = print_pdf(str(path))
        if not ok:
            messagebox.showerror("Print Error", f"Could not print:\n{err}")
        else:
            messagebox.showinfo("Printing", "Sent to printer.")

    def clear_form(self):
        # New receipt number each time the form is cleared
        self.receipt_no.set(generate_receipt_no())
        self.date.set(datetime.now().strftime("%Y-%m-%d %H:%M"))
        self.payment_method.set(PAYMENT_METHODS[0])
        for r in self.entries:
            for k in ("item", "desc", "qty", "price", "total"):
                w = r[k]
                w.configure(state="normal")
                w.delete(0, tk.END)
                if k in ("item", "total"):
                    w.configure(state="readonly")
        self.customer_name.set("")
        self.address.set("")
        self.telephone.set("")
        self.email.set("")
        self.subtotal_var.set("0.00")
        self.total_var.set("0.00")
        self.recompute_item_numbers()

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
