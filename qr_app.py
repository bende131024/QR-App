import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
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
beszallito_opciok = ["Beszállító 1", "Beszállító 2", "Beszállító 3", "Lipták János - Katymár"]
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

# --- Sor beviteli ablak ---
def sor_beviteli_ablak():
    ablak = tk.Toplevel(root)
    ablak.title("Új sor bevitele")
    entry_varok = {}

    for i, mezo in enumerate(mezok):
        if mezo == "Azonosító":
            entry_varok[mezo] = tk.StringVar(value=str(uuid.uuid4()))
            tk.Label(ablak, text=mezo).grid(row=i, column=0, padx=5, pady=2)
            tk.Entry(ablak, textvariable=entry_varok[mezo], state="disabled").grid(row=i, column=1, padx=5, pady=2)
        elif mezo in listak:
            tk.Label(ablak, text=mezo).grid(row=i, column=0, padx=5, pady=2)
            combo = ttk.Combobox(ablak, values=listak[mezo], state="readonly")
            combo.grid(row=i, column=1, padx=5, pady=2)
            entry_varok[mezo] = combo
        else:
            tk.Label(ablak, text=mezo).grid(row=i, column=0, padx=5, pady=2)
            entry = tk.Entry(ablak)
            entry.grid(row=i, column=1, padx=5, pady=2)
            entry_varok[mezo] = entry

    def mentes():
        uj_sor = {"Azonosító": entry_varok["Azonosító"].get()}
        for mezo in mezok:
            if mezo != "Azonosító":
                if mezo in listak:
                    ertek = entry_varok[mezo].get()
                else:
                    ertek = entry_varok[mezo].get()
                uj_sor[mezo] = ertek if ertek else ""
        adatok.append(uj_sor)
        sync_to_server()
        update_tree()
        ablak.destroy()

    tk.Button(ablak, text="Mentés", command=mentes).grid(row=len(mezok), column=0, columnspan=2, pady=10)

# --- Módosítás ---
def modositas():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Figyelmeztetés", "Válassz ki egy sort!")
        return
    idx = selected[0]
    sor = adatok[int(idx)]
    ablak = tk.Toplevel(root)
    ablak.title("Sor módosítása")
    entry_varok = {}

    for i, mezo in enumerate(mezok):
        if mezo == "Azonosító":
            entry_varok[mezo] = tk.StringVar(value=sor[mezo])
            tk.Label(ablak, text=mezo).grid(row=i, column=0, padx=5, pady=2)
            tk.Entry(ablak, textvariable=entry_varok[mezo], state="disabled").grid(row=i, column=1, padx=5, pady=2)
        elif mezo in listak:
            tk.Label(ablak, text=mezo).grid(row=i, column=0, padx=5, pady=2)
            combo = ttk.Combobox(ablak, values=listak[mezo], state="readonly")
            combo.set(sor[mezo])
            combo.grid(row=i, column=1, padx=5, pady=2)
            entry_varok[mezo] = combo
        else:
            tk.Label(ablak, text=mezo).grid(row=i, column=0, padx=5, pady=2)
            entry = tk.Entry(ablak)
            entry.insert(0, sor[mezo])
            entry.grid(row=i, column=1, padx=5, pady=2)
            entry_varok[mezo] = entry

    def mentes():
        uj_sor = {"Azonosító": entry_varok["Azonosító"].get()}
        for mezo in mezok:
            if mezo != "Azonosító":
                if mezo in listak:
                    ertek = entry_varok[mezo].get()
                else:
                    ertek = entry_varok[mezo].get()
                uj_sor[mezo] = ertek if ertek else ""
        adatok[int(idx)] = uj_sor
        api_update_row(uj_sor["Azonosító"], uj_sor)
        update_tree()
        ablak.destroy()

    tk.Button(ablak, text="Mentés", command=mentes).grid(row=len(mezok), column=0, columnspan=2, pady=10)

# --- Törlés ---
def torles():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Figyelmeztetés", "Válassz ki egy sort!")
        return
    if messagebox.askyesno("Megerősítés", "Biztosan törlöd a kijelölt sort?"):
        idx = int(selected[0])
        azonosito = adatok[idx]["Azonosító"]
        adatok.pop(idx)
        api_update_data({"mezok": mezok, "adatok": adatok, "listak": listak})
        update_tree()

# --- QR kód generálás ---
def qr_generalas():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Figyelmeztetés", "Válassz ki egy sort!")
        return
    idx = int(selected[0])
    sor = adatok[idx]
    qr_adat = json.dumps(sor)
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(qr_adat)
    qr.make(fit=True)
    img = qr.make_image(fill="black", back_color="white")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        img.save(tmp_file.name)
        img_tk = ImageTk.PhotoImage(Image.open(tmp_file.name))
        ablak = tk.Toplevel(root)
        ablak.title("QR Kód")
        panel = tk.Label(ablak, image=img_tk)
        panel.image = img_tk
        panel.pack()
        tk.Button(ablak, text="Mentés", command=lambda: img.save(filedialog.asksaveasfilename(defaultextension=".png"))).pack()
        tk.Button(ablak, text="Bezárás", command=ablak.destroy).pack()
    os.unlink(tmp_file.name)

# --- Legördülők szerkesztése (módosítva a kéréshez) ---
def szerkesztes_legordulok():
    ablak = tk.Toplevel(root)
    ablak.title("Legördülők szerkesztése")

    # Bal oldali listbox: legördülő mezők listája (csak "Beszállító" releváns)
    tk.Label(ablak, text="Mezők").grid(row=0, column=0, padx=5, pady=5)
    field_listbox = tk.Listbox(ablak, height=10, width=20)
    field_listbox.grid(row=1, column=0, padx=5, pady=5)
    field_listbox.insert(tk.END, "Beszállító")  # Csak "Beszállító" mezőt engedélyezünk szerkesztésre

    # Jobb oldali listbox: "Beszállító" opciói
    tk.Label(ablak, text="Opcio:").grid(row=0, column=1, padx=5, pady=5)
    option_listbox = tk.Listbox(ablak, height=10, width=30)
    option_listbox.grid(row=1, column=1, padx=5, pady=5)
    for option in sorted(listak["Beszállító"]):
        option_listbox.insert(tk.END, option)

    # Gombok az opciók szerkesztéséhez (nincs új ablak)
    def uj_opcio():
        new_option = simpledialog.askstring("Új opció", "Új opció értéke:", parent=ablak)
        if new_option and new_option not in listak["Beszállító"]:
            listak["Beszállító"].append(new_option)
            option_listbox.insert(tk.END, new_option)
            sync_to_server()
            messagebox.showinfo("Siker", f"Új opció hozzáadva: {new_option}")
        elif new_option:
            messagebox.showwarning("Figyelmeztetés", "Ez az opció már létezik!")

    def modositas_opcio():
        selected = option_listbox.curselection()
        if not selected:
            messagebox.showwarning("Figyelmeztetés", "Válassz ki egy opciót!")
            return
        old_option = option_listbox.get(selected[0])
        new_option = simpledialog.askstring("Opcio módosítás", "Új érték:", initialvalue=old_option, parent=ablak)
        if new_option and new_option != old_option:
            idx = listak["Beszállító"].index(old_option)
            listak["Beszállító"][idx] = new_option
            option_listbox.delete(selected[0])
            option_listbox.insert(selected[0], new_option)
            sync_to_server()
            messagebox.showinfo("Siker", f"Opció módosítva: {old_option} -> {new_option}")
        elif new_option:
            messagebox.showwarning("Figyelmeztetés", "Nincs változás az értékben!")

    def torles_opcio():
        selected = option_listbox.curselection()
        if not selected:
            messagebox.showwarning("Figyelmeztetés", "Válassz ki egy opciót!")
            return
        option = option_listbox.get(selected[0])
        if option in listak["Beszállító"]:
            listak["Beszállító"].remove(option)
            option_listbox.delete(selected[0])
            sync_to_server()
            messagebox.showinfo("Siker", f"Opció törölve: {option}")

    tk.Button(ablak, text="Új opció", command=uj_opcio).grid(row=2, column=1, padx=5, pady=5)
    tk.Button(ablak, text="Opcio módosítás", command=modositas_opcio).grid(row=3, column=1, padx=5, pady=5)
    tk.Button(ablak, text="Törlés opció", command=torles_opcio).grid(row=4, column=1, padx=5, pady=5)

    def close():
        sync_to_server()
        update_tree()
        ablak.destroy()

    tk.Button(ablak, text="Mentés és bezárás", command=close).grid(row=5, column=0, columnspan=2, pady=10)

    ablak.transient(root)
    ablak.grab_set()
    ablak.mainloop()

# --- Új oszlop hozzáadása ---
def oszlop_hozzaadasa():
    uj_mező = simpledialog.askstring("Új oszlop", "Új oszlop neve:")
    if uj_mező and uj_mező not in mezok:
        mezok.append(uj_mező)
        update_tree()

# --- Oszlop sorrend szerkesztése ---
def oszlop_sorrend_szerkesztese():
    ablak = tk.Toplevel(root)
    ablak.title("Oszlopok sorrendje")
    listbox = tk.Listbox(ablak, height=10)
    for mezo in mezok:
        listbox.insert(tk.END, mezo)
    listbox.pack(padx=5, pady=5)

    def mentes():
        uj_sorrend = listbox.get(0, tk.END)
        mezok.clear()
        mezok.extend(uj_sorrend)
        update_tree()
        ablak.destroy()

    tk.Button(ablak, text="Mentés", command=mentes).pack(pady=5)

# --- Lokális mentés és betöltés ---
def ment_local():
    path = filedialog.asksaveasfilename(defaultextension=".json")
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"mezok": mezok, "adatok": adatok, "listak": listak}, f, ensure_ascii=False, indent=4)
        messagebox.showinfo("Mentve", f"Adatok mentve: {path}")

def betolt_local():
    path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if path:
        with open(path, "r", encoding="utf-8") as f:
            data_to_load = json.load(f)
        global adatok, mezok, listak
        adatok = data_to_load.get("adatok", [])
        mezok = data_to_load.get("mezok", fix_mezok.copy())
        listak = data_to_load.get("listak", {})
        if "Beszállító" not in listak:
            listak["Beszállító"] = ["Beszállító 1", "Beszállító 2", "Beszállító 3", "Lipták János - Katymár"]
        if "Hely" not in listak:
            listak["Hely"] = ["Raktár A", "Raktár B", "Kijelölt hely"]
        if "Osztály" not in listak:
            listak["Osztály"] = ["Fénykép", "Eladva", "Javításra"]
        sync_to_server()
        update_tree()
        messagebox.showinfo("Betöltve", f"Adatok betöltve lokálisan: {path}")

# --- Zoom ---
def zoom(val):
    factor = int(val)
    style.configure("Custom.Treeview", rowheight=int(factor * 1.5) + 10, font=("Arial", factor))
    style.configure("Custom.Treeview.Heading", font=("Arial", factor, "bold"))
    resize_columns()

# --- Főablak ---
root = tk.Tk()
root.title("QR Kód Generáló - Dinamikus Mezők, Legördülők és Oszlopok szerkesztése")

style = ttk.Style()
style.theme_use("default")

style.configure("Custom.Treeview",
                background="white",
                foreground="black",
                rowheight=25,
                fieldbackground="white",
                bordercolor="black",
                borderwidth=1,
                relief="solid",
                font=("Arial", 10))
style.map("Custom.Treeview",
          background=[("selected", "#004080")],
          foreground=[("selected", "white")])

style.configure("Custom.Treeview.Heading",
                font=("Arial", 10, "bold"),
                bordercolor="black",
                borderwidth=1,
                relief="solid")

frame_main = tk.Frame(root)
frame_main.pack(fill="both", expand=True)

tree = ttk.Treeview(frame_main, show="headings", selectmode="extended", style="Custom.Treeview")
vsb_main = ttk.Scrollbar(frame_main, orient="vertical", command=tree.yview)
hsb_main = ttk.Scrollbar(frame_main, orient="horizontal", command=tree.xview)
tree.configure(yscrollcommand=vsb_main.set, xscrollcommand=hsb_main.set)
vsb_main.pack(side="right", fill="y")
hsb_main.pack(side="bottom", fill="x")
tree.pack(fill="both", expand=True, padx=10, pady=10)

frame = tk.Frame(root)
frame.pack(pady=10)

tk.Button(frame, text="Új sor", command=lambda: sor_beviteli_ablak()).grid(row=0, column=0, padx=5)
tk.Button(frame, text="Módosítás", command=modositas).grid(row=0, column=1, padx=5)
tk.Button(frame, text="Törlés", command=torles).grid(row=0, column=2, padx=5)
tk.Button(frame, text="QR generálás", command=qr_generalas).grid(row=0, column=3, padx=5)
tk.Button(frame, text="Legördülők szerkesztése", command=szerkesztes_legordulok).grid(row=0, column=4, padx=5)
tk.Button(frame, text="Új oszlop", command=oszlop_hozzaadasa).grid(row=0, column=5, padx=5)
tk.Button(frame, text="Oszlop sorrend", command=oszlop_sorrend_szerkesztese).grid(row=0, column=6, padx=5)

tk.Button(frame, text="Szinkronizálás szerverrel", command=sync_from_server).grid(row=1, column=0, padx=5, pady=5)
tk.Button(frame, text="Mentés szerverre", command=sync_to_server).grid(row=1, column=1, padx=5, pady=5)
tk.Button(frame, text="Lokális mentés", command=ment_local).grid(row=1, column=2, padx=5, pady=5)
tk.Button(frame, text="Lokális betöltés", command=betolt_local).grid(row=1, column=3, padx=5, pady=5)

zoom_frame = tk.Frame(root)
zoom_frame.pack(side="bottom", fill="x", padx=5, pady=5)
scale = tk.Scale(zoom_frame, from_=8, to=24, orient="horizontal", command=zoom, label="Zoom")
scale.set(10)
scale.pack(side="right")

try:
    sync_from_server()
except Exception:
    update_tree()

root.mainloop()