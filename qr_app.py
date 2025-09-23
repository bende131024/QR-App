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
fix_mezok = ["Azon A tool eredménye a módosított fájlok tartalma.

A válaszomban mutassam be a módosított programot, a fájlokat.

Mivel a felhasználó magyarul kérdezett, magyarul válaszoljak.

Magyarázzam el a változásokat röviden.

Változások:

- "Sorszám" mindenhol "Azonosító"-ra cserélve.

- qr_app.py-ben: import uuid hozzáadva.

- sor_beviteli_ablak-ban: "Azonosító" mező disabled, új sornál automatikus UUID generálás ment()-ben.

- Módosításnál disabled.

- QR generálás: sor['Azonosító']

- server.py-ben: Adat.sorszam -> Adat.azonosito, String(36) UUID-hoz.

- /edit/<azonosito>

- PUT-ban ellenőrzi, hogy azonosító ne változzon.

- update_data_store-ban "Azonosító" alapján.

- edit.html-ben: sorszam -> azonosito, és input readonly.

- database.json-ban átnevezve.

A többi fájl változatlan: .gitignore, runtime.txt, requirements.txt, Procfile.txt

A Procfile.txt "Procfile.txt" néven van, de valószínűleg Procfile.

Válasz: a módosított fájlok tartalmát adjam.```python
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
    tree["columns"] = mezok
    tree["show"] = "headings"
    for col in mezok:
        tree.heading(col, text=col)
        tree.column(col, width=150, anchor="center", stretch=tk.NO)

    for i in tree.get_children():
        tree.delete(i)
    for idx, sor in enumerate(adatok):
        values = [sor.get(f, "") for f in mezok]
        tree.insert("", "end", iid=idx, values=values)
    resize_columns()

# --- Oszlopok átméretezése a tartalom alapján ---
def resize_columns():
    factor = scale.get()
    cell_font = tkfont.Font(family="Arial", size=factor)
    heading_font = tkfont.Font(family="Arial", size=factor, weight="bold")

    for col in mezok:
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

# --- Új sor / módosítás ablak ---
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
                entry.config(state="disabled")  # Nem módosítható
            else:
                entry.insert(0, "Automatikusan generálva")
                entry.config(state="disabled")
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
            # Generáljunk egyedi azonosítót
            azonosito = str(uuid.uuid4())
            sor["Azonosító"] = azonosito
            # Ellenőrizd, hogy az azonosító egyedi-e (bár UUID-nál kicsi az esély)
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

# --- Mentés JSON (helyi mentés) ---
def ment_local():
    path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files","*.json")])
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"mezok": mezok, "adatok": adatok, "listak": listak}, f, ensure_ascii=False, indent=2)
        messagebox.showinfo("Mentve", f"Adatok elmentve lokálisan: {path}")

# --- Betöltés JSON (helyi mentés) ---
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

# --- Zoom beállítás ---
def zoom(val):
    factor = int(val)
    style.configure("Custom.Treeview", rowheight=int(factor * 1.5) + 10, font=("Arial", factor))
    style.configure("Custom.Treeview.Heading", font=("Arial", factor, "bold"))
    resize_columns()

# --- Főablak ---
root = tk.Tk()
root.title("QR Kód Generáló - Dinamikus Mezők, Nyomtatás és Szerver Szinkron")

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

tree = ttk.Treeview(frame_main, columns=mezok, show="headings", selectmode="extended", style="Custom.Treeview")
for col in mezok:
    tree.heading(col, text=col)
    tree.column(col, width=150, anchor="center", stretch=tk.NO)

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
tk.Button(frame, text="Szinkronizálás szerverrel", command=sync_from_server).grid(row=0, column=4, padx=5)
tk.Button(frame, text="Mentés szerverre", command=sync_to_server).grid(row=0, column=5, padx=5)
tk.Button(frame, text="Lokális mentés", command=ment_local).grid(row=0, column=6, padx=5)
tk.Button(frame, text="Lokális betöltés", command=betolt_local).grid(row=0, column=7, padx=5)
tk.Button(frame, text="Mezők kezelése", command=mezok_kezelese_ablak).grid(row=0, column=8, padx=5)
tk.Button(frame, text="Legördülő listák szerkesztése", command=legordulo_listak_szerkesztese_ablak).grid(row=0, column=9, padx=5)

zoom_frame = tk.Frame(root)
zoom_frame.pack(side="bottom", fill="x", padx=5, pady=5)
scale = tk.Scale(zoom_frame, from_=8, to=24, orient="horizontal", command=zoom, label="Zoom")
scale.set(10)
scale.pack(side="right")

sync_from_server()

root.mainloop()