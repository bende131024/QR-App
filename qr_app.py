import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import json
import qrcode
from PIL import Image, ImageTk
import tempfile
import os
import platform
import tkinter.font as tkfont
import requests
import uuid

# Szerver URL (frissítsd a Render URL-re telepítés után, pl. https://your-app.onrender.com)
SERVER_URL = "https://qr-app-emfo.onrender.com"  # Helyi teszteléshez; frissítsd a Render URL-re!

# --- Globális változók és adatok ---
adatok = []
fix_mezok = ["Azonosító", "Fémzárszám", "Beszállító", "Név", "Hely", "Súly", "Megjegyzés", "Osztály"]
mezok = fix_mezok.copy()

# Legördülő lista opciók
beszallito_opciok = ["Beszállító 1", "Beszállító 2", "Beszállító 3"]
hely_opciok = ["Raktár A", "Raktár B", "Kijelölt hely"]
osztaly_opciok = ["Fénykép", "Eladva", "Javításra"]

listak = {
    "Beszállító": beszallito_opciok,
    "Hely": hely_opciok,
    "Osztály": osztaly_opciok
}

# --- API segédfunkciók ---
def api_get_data():
    try:
        response = requests.get(f"{SERVER_URL}/data")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        messagebox.showerror("Hiba", f"Szerver hiba: {e}")
        return None

def api_update_data(full_data):
    try:
        response = requests.post(f"{SERVER_URL}/update", json=full_data)
        response.raise_for_status()
        return True
    except Exception as e:
        messagebox.showerror("Hiba", f"Szerver hiba: {e}")
        return False

def api_update_row(azonosito, row_data):
    try:
        response = requests.put(f"{SERVER_URL}/edit/{azonosito}", json=row_data)
        response.raise_for_status()
        return True
    except Exception as e:
        messagebox.showerror("Hiba", f"Szerver hiba: {e}")
        return False

# --- Szinkronizálás szerverrel ---
def sync_from_server():
    global adatok, mezok, listak
    data = api_get_data()
    if data:
        adatok = data.get("adatok", [])
        mezok = data.get("mezok", fix_mezok.copy())
        listak = data.get("listak", {})
        update_tree()
        messagebox.showinfo("Szinkronizálva", "Adatok szinkronizálva a szerverrel.")

def sync_to_server():
    full_data = {"mezok": mezok, "adatok": adatok, "listak": listak}
    if api_update_data(full_data):
        messagebox.showinfo("Mentve", "Adatok mentve a szerverre.")

# --- Treeview frissítése (főablak) ---
def update_tree():
    display_columns = [c for c in mezok if c != "Azonosító"]
    tree["columns"] = display_columns
    tree["show"] = "headings"

    for col in display_columns:
        tree.heading(col, text=col)
        tree.column(col, width=150, anchor="center", stretch=tk.NO)

    for i in tree.get_children():
        tree.delete(i)
    for idx, sor in enumerate(adatok):
        values = [sor.get(f, "") for f in display_columns]
        tree.insert("", "end", iid=idx, values=values)
    resize_columns()

# --- Oszlopok átméretezése ---
def resize_columns():
    factor = scale.get()
    cell_font = tkfont.Font(family="Arial", size=factor)
    heading_font = tkfont.Font(family="Arial", size=factor, weight="bold")

    for col in tree["columns"]:
        heading_width = heading_font.measure(tree.heading(col)["text"]) + 20
        max_cell_width = 0
        for child in tree.get_children():
            cell_value = tree.set(child, col)
            cell_width = cell_font.measure(cell_value) + 20
            if cell_width > max_cell_width:
                max_cell_width = cell_width
        new_width = max(heading_width, max_cell_width, 150)
        tree.column(col, width=new_width)

    tree.update_idletasks()

# --- Sor hozzáadása / módosítása ---
def sor_beviteli_ablak(modositott_sor=None, idx=None):
    ablak = tk.Toplevel(root)
    ablak.title("Sor hozzáadása / módosítása")
    entries = {}

    for i, field in enumerate(mezok):
        tk.Label(ablak, text=field).grid(row=i, column=0, padx=5, pady=5, sticky="w")
        if field == "Azonosító":
            entry = tk.Entry(ablak, width=50)
            if modositott_sor:
                entry.insert(0, modositott_sor.get(field, ""))
            else:
                entry.insert(0, "Automatikusan generálva")
            entry.config(state="readonly")
        elif field in listak:
            entry = ttk.Combobox(ablak, values=listak[field], width=48)
        else:
            entry = tk.Entry(ablak, width=50)

        entry.grid(row=i, column=1, padx=5, pady=5)

        if modositott_sor and field != "Azonosító":
            ertek = modositott_sor.get(field, "")
            if isinstance(entry, ttk.Combobox):
                entry.set(ertek)
            else:
                entry.insert(0, ertek)
        entries[field] = entry

    def ment():
        sor = {field: entries[field].get() for field in entries if field != "Azonosító"}
        if modositott_sor and idx is not None:
            sor["Azonosító"] = modositott_sor["Azonosító"]
            adatok[idx] = sor
            if not api_update_row(sor["Azonosító"], sor):
                return
        else:
            azonosito = str(uuid.uuid4())
            sor["Azonosító"] = azonosito
            if any(d.get("Azonosító") == azonosito for d in adatok):
                messagebox.showerror("Hiba", "Az azonosító már létezik! (Ritka eset)")
                return
            adatok.append(sor)
        sync_to_server()
        update_tree()
        ablak.destroy()

    tk.Button(ablak, text="Mentés", command=ment).grid(row=len(mezok), column=0, columnspan=2, pady=10)

# --- Sor törlése ---
def torles():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Figyelem", "Válassz ki egy sort a törléshez!")
        return
    if messagebox.askyesno("Törlés", "Biztosan törlöd a kiválasztott sort?"):
        for i in reversed(selected):
            del adatok[int(i)]
        sync_to_server()
        update_tree()

# --- Sor módosítása ---
def modositas():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Figyelem", "Válassz ki egy sort a módosításhoz!")
        return
    idx = int(selected[0])
    sor_beviteli_ablak(adatok[idx], idx)

# --- Legördülők szerkesztése ---
def szerkesztes_legordulok():
    ablak = tk.Toplevel(root)
    ablak.title("Legördülők szerkesztése")

    listbox_frame = tk.Frame(ablak)
    listbox_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    keys = list(listak.keys())
    lb_keys = tk.Listbox(listbox_frame, height=12)
    for k in keys:
        lb_keys.insert("end", k)
    lb_keys.pack(fill="both", expand=True)

    options_frame = tk.Frame(ablak)
    options_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)

    tk.Label(options_frame, text="Opciók:").pack(anchor="w")
    lb_opts = tk.Listbox(options_frame, height=10, selectmode="browse")
    lb_opts.pack(fill="both", expand=True)

    def load_opts(event=None):
        lb_opts.delete(0, "end")
        sel = lb_keys.curselection()
        if not sel:
            return
        key = lb_keys.get(sel[0])
        for o in listak.get(key, []):
            lb_opts.insert("end", o)

    lb_keys.bind("<<ListboxSelect>>", load_opts)

    def on_opt_select(event=None):
        selo = lb_opts.curselection()
        if selo:
            lb_opts.selection_set(selo[0])

    lb_opts.bind("<<ListboxSelect>>", on_opt_select)

    def add_list_key():
        name = simpledialog.askstring("Új lista", "Adj meg egy új legördülő mező nevet:")
        if name:
            if name in listak:
                messagebox.showwarning("Figyelem", "Már létezik ilyen lista.")
                return
            listak[name] = []
            lb_keys.insert("end", name)

    def remove_list_key():
        sel = lb_keys.curselection()
        if not sel:
            return
        key = lb_keys.get(sel[0])
        if messagebox.askyesno("Törlés", f"Biztos törlöd a '{key}' listát?"):
            del listak[key]
            lb_keys.delete(sel[0])
            lb_opts.delete(0, "end")

    def add_option():
        sel = lb_keys.curselection()
        if not sel:
            messagebox.showwarning("Figyelem", "Válassz ki előbb egy listát!")
            return
        key = lb_keys.get(sel[0])
        val = simpledialog.askstring("Új opció", "Adj meg egy új opciót:")
        if val:
            listak.setdefault(key, []).append(val)
            load_opts()

    def remove_option():
        selk = lb_keys.curselection()
        selo = lb_opts.curselection()
        if not selk or not selo:
            return
        key = lb_keys.get(selk[0])
        opt = lb_opts.get(selo[0])
        listak[key].remove(opt)
        load_opts()

    btn_frame = tk.Frame(options_frame)
    btn_frame.pack(fill="x", pady=5)
    tk.Button(btn_frame, text="Új lista", command=add_list_key).pack(side="left", padx=3)
    tk.Button(btn_frame, text="Törlés lista", command=remove_list_key).pack(side="left", padx=3)
    tk.Button(btn_frame, text="Új opció", command=add_option).pack(side="left", padx=3)
    tk.Button(btn_frame, text="Törlés opció", command=remove_option).pack(side="left", padx=3)

    def save_and_close():
        sync_to_server()
        update_tree()
        ablak.destroy()

    tk.Button(ablak, text="Mentés és bezárás", command=save_and_close).pack(pady=8)

# --- Új oszlop hozzáadása ---
def oszlop_hozzaadasa():
    name = simpledialog.askstring("Új oszlop", "Add meg az új oszlop nevét:")
    if not name:
        return
    if name in mezok:
        messagebox.showwarning("Figyelem", "Már létezik ilyen oszlop.")
        return
    position = simpledialog.askinteger("Pozíció", f"Hová helyezzük az oszlopot? (1..{len(mezok)+1}) - 1: legfelül")
    if position is None:
        return
    position = max(1, min(position, len(mezok)+1))
    insert_idx = position - 1
    mezok.insert(insert_idx, name)
    for r in adatok:
        r.setdefault(name, "")
    sync_to_server()
    update_tree()

# --- Oszlopok sorrend szerkesztése ---
def oszlop_sorrend_szerkesztese():
    ablak = tk.Toplevel(root)
    ablak.title("Oszlopok sorrendje")

    lb = tk.Listbox(ablak, selectmode="single", width=40)
    for m in mezok:
        lb.insert("end", m)
    lb.pack(side="left", fill="both", expand=True, padx=10, pady=10)

    def move_up():
        sel = lb.curselection()
        if not sel:
            return
        i = sel[0]
        if i == 0:
            return
        v = lb.get(i)
        lb.delete(i)
        lb.insert(i-1, v)
        lb.select_set(i-1)

    def move_down():
        sel = lb.curselection()
        if not sel:
            return
        i = sel[0]
        if i == lb.size()-1:
            return
        v = lb.get(i)
        lb.delete(i)
        lb.insert(i+1, v)
        lb.select_set(i+1)

    btns = tk.Frame(ablak)
    btns.pack(side="right", fill="y", padx=5, pady=10)
    tk.Button(btns, text="Fel", command=move_up, width=8).pack(pady=3)
    tk.Button(btns, text="Le", command=move_down, width=8).pack(pady=3)

    def apply_order():
        new_order = [lb.get(i) for i in range(lb.size())]
        global mezok
        mezok = new_order
        for r in adatok:
            for k in mezok:
                r.setdefault(k, "")
        sync_to_server()
        update_tree()
        ablak.destroy()

    tk.Button(ablak, text="Alkalmaz", command=apply_order).pack(pady=8)

# --- QR generálás ---
def qr_generalas():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Figyelem", "Válassz ki legalább egy sort a QR generáláshoz!")
        return

    qr_popup = tk.Toplevel(root)
    qr_popup.title("QR Kódok")
    qr_popup.geometry("800x600")

    canvas = tk.Canvas(qr_popup)
    scrollbar = ttk.Scrollbar(qr_popup, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    qr_images = []

    for i in selected:
        sor = adatok[int(i)]
        qr_data = f"{SERVER_URL}/edit/{sor['Azonosító']}"
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill="black", back_color="white")
        qr_images.append(img)

        img_tk = ImageTk.PhotoImage(img)

        qr_item_frame = tk.Frame(scrollable_frame, borderwidth=2, relief="solid", pady=10)
        label = tk.Label(qr_item_frame, text=f"Azonosító: {sor['Azonosító']}")
        label.pack(pady=5)

        qr_label = tk.Label(qr_item_frame, image=img_tk)
        qr_label.image = img_tk
        qr_label.pack(pady=(0, 10))

        qr_item_frame.pack(fill="x", expand=True, padx=10)

    update_tree()

    def nyomtat():
        for img in qr_images:
            try:
                tmpfile = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                img.save(tmpfile.name)
                tmpfile.close()
                if platform.system() == "Windows":
                    os.startfile(tmpfile.name, "print")
                else:
                    os.system(f"lpr {tmpfile.name}")
            except Exception as e:
                messagebox.showerror("Nyomtatási hiba", f"Hiba történt a nyomtatás során: {e}")

    print_button = tk.Button(qr_popup, text="Nyomtatás", command=nyomtat)
    print_button.pack(pady=10, side="bottom")

# --- Mentés JSON ---
def ment_local():
    path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files","*.json")])
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"mezok": mezok, "adatok": adatok, "listak": listak}, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Mentve", f"Adatok elmentve lokálisan: {path}")

# --- Betöltés JSON ---
def betolt_local():
    path = filedialog.askopenfilename(filetypes=[("JSON files","*.json")])
    if path:
        global adatok, mezok, listak
        with open(path, "r", encoding="utf-8") as f:
            data_to_load = json.load(f)
            if isinstance(data_to_load, list):
                adatok = data_to_load
                if adatok:
                    all_keys = set()
                    for row in adatok:
                        all_keys.update(row.keys())
                    ordered_keys = fix_mezok.copy()
                    for key in all_keys:
                        if key not in ordered_keys:
                            ordered_keys.append(key)
                    mezok = ordered_keys
                else:
                    mezok = fix_mezok.copy()
                listak = {}
            else:
                adatok = data_to_load
