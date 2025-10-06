# qr_app.py (frissített: mezők szerkesztése, raklapok helye lista, hiányzó függvények hozzáadása)
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
import webbrowser

# Szerver URL (frissítsd a Render URL-re telepítés után)
SERVER_URL = "https://qr-app-emfo.onrender.com"

# --- Globális változók és adatok ---
adatok = []
fix_mezok = ["Azonosító", "Sorszám", "Fémzárszám", "Beszállító", "Név", "Fok", "Hely", "Súly", "Megjegyzés", "Osztály"]
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

def api_get_locations():
    try:
        response = requests.get(f"{SERVER_URL}/get_locations")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        messagebox.showerror("Hiba", f"Szerver hiba: {e}")
        return []

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

# --- Mezők kezelése (hozzáadás / törlés / átnevezés / sorrend) ---
def mezok_kezelese():
    ablak = tk.Toplevel(root)
    ablak.title("Mezők szerkesztése")
    ablak.geometry("400x400")

    lb = tk.Listbox(ablak, selectmode="browse")
    lb.pack(fill="both", expand=True, padx=10, pady=10)
    def refresh_listbox():
        lb.delete(0, tk.END)
        for m in mezok:
            lb.insert(tk.END, m)
    refresh_listbox()

    def uj_mezo():
        neve = simpledialog.askstring("Új mező", "Mező neve:", parent=ablak)
        if neve:
            if neve in mezok:
                messagebox.showwarning("Figyelem", "Már létezik ilyen mező!")
                return
            mezok.append(neve)
            for r in adatok:
                r.setdefault(neve, "")
            refresh_listbox()
            update_tree()
            sync_to_server()

    def torol_mezo():
        sel = lb.curselection()
        if not sel:
            messagebox.showwarning("Figyelem", "Válassz ki egy mezőt a törléshez!")
            return
        idx = sel[0]
        nev = mezok[idx]
        if nev == "Azonosító":
            messagebox.showerror("Hiba", "Az 'Azonosító' mezőt nem lehet törölni!")
            return
        if messagebox.askyesno("Törlés", f"Törlöd a(z) '{nev}' mezőt? Ez eltávolítja a mező értékét minden sorból."):
            mezok.pop(idx)
            for r in adatok:
                if nev in r:
                    del r[nev]
            if nev in listak:
                del listak[nev]
            refresh_listbox()
            update_tree()
            sync_to_server()

    tk.Button(ablak, text="Új mező", command=uj_mezo).pack(pady=5)
    tk.Button(ablak, text="Mező törlése", command=torol_mezo).pack(pady=5)

# --- Hiányzó függvények implementációja ---
def sor_beviteli_ablak():
    ablak = tk.Toplevel(root)
    ablak.title("Új sor hozzáadása")
    ablak.geometry("400x500")

    entries = {}
    for field in mezok:
        frame = tk.Frame(ablak)
        frame.pack(fill="x", padx=10, pady=5)
        tk.Label(frame, text=field, width=15).pack(side="left")
        if field == "Azonosító":
            az = str(uuid.uuid4())
            entries[field] = tk.Entry(frame)
            entries[field].insert(0, az)
            entries[field].config(state="readonly")
            entries[field].pack(fill="x", expand=True)
        elif field in listak:
            entries[field] = ttk.Combobox(frame, values=listak[field])
            entries[field].pack(fill="x", expand=True)
        else:
            entries[field] = tk.Entry(frame)
            entries[field].pack(fill="x", expand=True)

    def mentes():
        new_row = {}
        for field in mezok:
            new_row[field] = entries[field].get()
        if api_update_row(new_row["Azonosító"], new_row):
            adatok.append(new_row)
            update_tree()
            sync_to_server()
            messagebox.showinfo("Siker", "Új sor hozzáadva!")
            ablak.destroy()
        else:
            messagebox.showerror("Hiba", "Nem sikerült hozzáadni a sort!")

    tk.Button(ablak, text="Mentés", command=mentes).pack(pady=10)

def modositas():
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("Figyelem", "Válassz ki egy sort a módosításhoz!")
        return
    idx = int(sel[0])
    row = adatok[idx]

    ablak = tk.Toplevel(root)
    ablak.title("Sor módosítása")
    ablak.geometry("400x500")

    entries = {}
    for field in mezok:
        frame = tk.Frame(ablak)
        frame.pack(fill="x", padx=10, pady=5)
        tk.Label(frame, text=field, width=15).pack(side="left")
        if field == "Azonosító":
            entries[field] = tk.Entry(frame)
            entries[field].insert(0, row[field])
            entries[field].config(state="readonly")
            entries[field].pack(fill="x", expand=True)
        elif field in listak:
            entries[field] = ttk.Combobox(frame, values=listak[field])
            entries[field].set(row.get(field, ""))
            entries[field].pack(fill="x", expand=True)
        else:
            entries[field] = tk.Entry(frame)
            entries[field].insert(0, row.get(field, ""))
            entries[field].pack(fill="x", expand=True)

    def mentes():
        updated_row = {}
        for field in mezok:
            updated_row[field] = entries[field].get()
        if api_update_row(updated_row["Azonosító"], updated_row):
            adatok[idx] = updated_row
            update_tree()
            sync_to_server()
            messagebox.showinfo("Siker", "Sor módosítva!")
            ablak.destroy()
        else:
            messagebox.showerror("Hiba", "Nem sikerült módosítani a sort!")

    tk.Button(ablak, text="Mentés", command=mentes).pack(pady=10)

def torles():
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("Figyelem", "Válassz ki egy sort a törléshez!")
        return
    idx = int(sel[0])
    row = adatok[idx]
    if messagebox.askyesno("Törlés", f"Biztosan törlöd az azonosítót: {row['Azonosító']}?"):
        adatok.pop(idx)
        update_tree()
        sync_to_server()
        messagebox.showinfo("Siker", "Sor törölve!")

def qr_generalas():
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("Figyelem", "Válassz ki legalább egy sort a QR-kód generáláshoz!")
        return
    qr_popup = tk.Toplevel(root)
    qr_popup.title("QR Kódok")
    qr_popup.geometry("400x400")

    qr_images = []
    for idx in sel:
        row = adatok[int(idx)]
        az = row["Azonosító"]
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(f"{SERVER_URL}/edit/{az}")
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        qr_images.append(img)

        img_tk = ImageTk.PhotoImage(img.resize((150, 150)))
        tk.Label(qr_popup, image=img_tk).pack(pady=10)
        qr_popup.image = img_tk  # Referencia megtartása

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

def szerkesztes_legordulok():
    ablak = tk.Toplevel(root)
    ablak.title("Legördülők szerkesztése")
    ablak.geometry("400x400")

    lb = tk.Listbox(ablak, selectmode="browse")
    lb.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh_listbox():
        lb.delete(0, tk.END)
        for field in listak:
            lb.insert(tk.END, field)
    refresh_listbox()

    def opciok_szerkesztese():
        sel = lb.curselection()
        if not sel:
            messagebox.showwarning("Figyelem", "Válassz ki egy mezőt!")
            return
        field = list(latak.keys())[sel[0]]
        opciok_ablak = tk.Toplevel(ablak)
        opciok_ablak.title(f"{field} opciók szerkesztése")
        opciok_ablak.geometry("300x300")

        opciok_lb = tk.Listbox(opciok_ablak)
        opciok_lb.pack(fill="both", expand=True, padx=10, pady=10)
        for opcio in listak[field]:
            opciok_lb.insert(tk.END, opcio)

        def uj_opcio():
            opcio = simpledialog.askstring("Új opció", "Új opció neve:", parent=opciok_ablak)
            if opcio and opcio not in listak[field]:
                listak[field].append(opcio)
                opciok_lb.insert(tk.END, opcio)
                sync_to_server()

        def torol_opcio():
            sel = opciok_lb.curselection()
            if not sel:
                messagebox.showwarning("Figyelem", "Válassz ki egy opciót!")
                return
            opcio = listak[field][sel[0]]
            if messagebox.askyesno("Törlés", f"Törlöd a(z) '{opcio}' opciót?"):
                listak[field].pop(sel[0])
                opciok_lb.delete(sel[0])
                sync_to_server()

        tk.Button(opciok_ablak, text="Új opció", command=uj_opcio).pack(pady=5)
        tk.Button(opciok_ablak, text="Opció törlése", command=torol_opcio).pack(pady=5)

    tk.Button(ablak, text="Opciók szerkesztése", command=opciok_szerkesztese).pack(pady=5)

# --- Raklapok helyeinek listája ---
def raklapok_helye():
    ablak = tk.Toplevel(root)
    ablak.title("Raklapok Helyei")
    ablak.geometry("600x400")

    lb = tk.Listbox(ablak, selectmode="browse", font=("Arial", 10))
    lb.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh_locations():
        lb.delete(0, tk.END)
        locations = api_get_locations()
        for loc in locations:
            lb.insert(tk.END, f"{loc['azonosito']} | Lat: {loc['lat']} | Long: {loc['long']} | Idő: {loc['timestamp']}")

    def on_double_click(event):
        sel = lb.curselection()
        if sel:
            idx = sel[0]
            locations = api_get_locations()
            loc = locations[idx]
            webbrowser.open(f"{SERVER_URL}/map?lat={loc['lat']}&long={loc['long']}&zoom=15")

    lb.bind("<Double-1>", on_double_click)
    refresh_locations()

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
                adatok = data_to_load.get("adatok", [])
                mezok = data_to_load.get("mezok", fix_mezok.copy())
                listak = data_to_load.get("listak", {})

                if "Beszállító" not in listak:
                    listak["Beszállító"] = ["Beszállító 1", "Beszállító 2", "Beszállító 3"]
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
root.title("QR Kód Generáló - Dinamikus Mezők és Szerver Szinkron")

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
tk.Button(frame, text="Mezők szerkesztése", command=mezok_kezelese).grid(row=0, column=5, padx=5)
tk.Button(frame, text="Szinkronizálás szerverrel", command=sync_from_server).grid(row=0, column=6, padx=5)
tk.Button(frame, text="Mentés szerverre", command=sync_to_server).grid(row=0, column=7, padx=5)
tk.Button(frame, text="Lokális mentés", command=ment_local).grid(row=0, column=8, padx=5)
tk.Button(frame, text="Lokális betöltés", command=betolt_local).grid(row=0, column=9, padx=5)
tk.Button(frame, text="Térkép", command=lambda: webbrowser.open(f"{SERVER_URL}/map")).grid(row=0, column=10, padx=5)
tk.Button(frame, text="Raklapok Helye", command=raklapok_helye).grid(row=0, column=11, padx=5)

zoom_frame = tk.Frame(root)
zoom_frame.pack(side="bottom", fill="x", padx=5, pady=5)
scale = tk.Scale(zoom_frame, from_=8, to=24, orient="horizontal", command=zoom, label="Zoom")
scale.set(10)
scale.pack(side="right")

# Inicializálás: frissítjük a Treeview-t
try:
    sync_from_server()
except Exception:
    update_tree()

root.mainloop()