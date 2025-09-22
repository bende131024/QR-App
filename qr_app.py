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

# Szerver URL (frissítsd a Render URL-re telepítés után, pl. https://your-app.onrender.com)
SERVER_URL = "https://qr-app-uvm4.onrender.com"  # Helyi teszteléshez; frissítsd a Render URL-re!

# --- Globális változók és adatok ---
adatok = []
fix_mezok = ["Sorszám", "Fémzárszám", "Beszállító", "Név", "Hely", "Súly", "Megjegyzés", "Osztály"]
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

def api_update_row(sorszam, row_data):
    try:
        response = requests.put(f"{SERVER_URL}/edit/{sorszam}", json=row_data)
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
        
        if field in listak:
            entry = ttk.Combobox(ablak, values=listak[field], width=48)
        else:
            entry = tk.Entry(ablak, width=50)

        entry.grid(row=i, column=1, padx=5, pady=5)
        
        if modositott_sor:
            ertek = modositott_sor.get(field, "")
            if isinstance(entry, ttk.Combobox):
                entry.set(ertek)
            else:
                entry.insert(0, ertek)
        entries[field] = entry

    def ment():
        sor = {field: entries[field].get() for field in entries}
        if not sor.get("Sorszám"):
            messagebox.showerror("Hiba", "A Sorszám mező kötelező!")
            return
        if modositott_sor and idx is not None:
            adatok[idx] = sor
            if not api_update_row(sor["Sorszám"], sor):
                return
        else:
            # Ellenőrizd, hogy a sorszám egyedi-e
            if any(d.get("Sorszám") == sor["Sorszám"] for d in adatok):
                messagebox.showerror("Hiba", "A Sorszám már létezik!")
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
    sor_beviteli_ablak(modositott_sor=adatok[idx], idx=idx)

# --- Legördülő listák szerkesztése ablak ---
def legordulo_listak_szerkesztese_ablak():
    ablak = tk.Toplevel(root)
    ablak.title("Legördülő listák szerkesztése")
    
    for i, (nev, opciok) in enumerate(listak.items()):
        frame = tk.LabelFrame(ablak, text=nev)
        frame.pack(padx=10, pady=5, fill="both", expand=True)

        lb = tk.Listbox(frame)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        for elem in opciok:
            lb.insert(tk.END, elem)
        
        def frissit_lista(listbox, field_name):
            listbox.delete(0, tk.END)
            for elem in listak[field_name]:
                listbox.insert(tk.END, elem)

        def hozzaad_elem(listbox, field_name):
            uj_elem = simpledialog.askstring(f"Új elem a(z) {field_name} listába", "Add meg az új elemet:", parent=ablak)
            if uj_elem and uj_elem not in listak[field_name]:
                listak[field_name].append(uj_elem)
                frissit_lista(listbox, field_name)
                sync_to_server()
                update_tree()
        
        def torol_elem(listbox, field_name):
            selected_indices = listbox.curselection()
            if not selected_indices:
                messagebox.showwarning("Figyelem", "Válassz ki egy elemet a törléshez!")
                return
            
            selected_text = listbox.get(selected_indices[0])
            if messagebox.askyesno("Törlés", f"Biztosan törlöd a(z) '{selected_text}' elemet?"):
                listak[field_name].remove(selected_text)
                frissit_lista(listbox, field_name)
                sync_to_server()
                update_tree()

        gomb_frame = tk.Frame(frame)
        gomb_frame.pack(side=tk.RIGHT, padx=5)
        
        tk.Button(gomb_frame, text="Hozzáadás", command=lambda lb=lb, nev=nev: hozzaad_elem(lb, nev)).pack(pady=5)
        tk.Button(gomb_frame, text="Törlés", command=lambda lb=lb, nev=nev: torol_elem(lb, nev)).pack(pady=5)

# --- Mezők kezelése ablak ---
def mezok_kezelese_ablak():
    ablak = tk.Toplevel(root)
    ablak.title("Mezők kezelése")
    
    frame_listbox = tk.Frame(ablak)
    frame_listbox.pack(padx=10, pady=10)

    lb = tk.Listbox(frame_listbox, width=50)
    lb.pack(side=tk.LEFT, fill=tk.Y, expand=True)
    
    scrollbar = ttk.Scrollbar(frame_listbox, orient="vertical", command=lb.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    lb.configure(yscrollcommand=scrollbar.set)
    
    def frissit_listbox():
        lb.delete(0, tk.END)
        for m in mezok:
            lb.insert(tk.END, m)

    frissit_listbox()
    
    def hozzaad_mezo():
        nev = simpledialog.askstring("Új mező", "Add meg az új mező nevét:", parent=ablak)
        if nev and nev not in mezok:
            mezok.append(nev)
            frissit_listbox()
            sync_to_server()
            update_tree()
    
    def torol_mezo():
        try:
            selected_idx = lb.curselection()[0]
            nev = mezok[selected_idx]
            if nev in fix_mezok:
                messagebox.showwarning("Figyelem", "Ezt a mezőt nem lehet törölni!")
                return
            if messagebox.askyesno("Törlés", f"Biztosan törlöd a(z) '{nev}' mezőt?"):
                mezok.remove(nev)
                if nev in listak:
                    del listak[nev]
                frissit_listbox()
                sync_to_server()
                update_tree()
        except IndexError:
            messagebox.showwarning("Figyelem", "Válassz ki egy mezőt a törléshez!")
            
    def make_dropdown_field():
        try:
            selected_idx = lb.curselection()[0]
            nev = mezok[selected_idx]
            if nev in listak:
                messagebox.showwarning("Figyelem", "Ez a mező már legördülő lista!")
                return
            listak[nev] = []
            sync_to_server()
            update_tree()
        except IndexError:
            messagebox.showwarning("Figyelem", "Válassz ki egy mezőt!")
    
    def fel():
        try:
            i = lb.curselection()[0]
            if i > 0:
                mezok[i-1], mezok[i] = mezok[i], mezok[i-1]
                frissit_listbox()
                lb.select_set(i-1)
                sync_to_server()
                update_tree()
        except IndexError:
            messagebox.showwarning("Figyelem", "Válassz ki egy mezőt!")
    
    def le():
        try:
            i = lb.curselection()[0]
            if i < len(mezok) - 1:
                mezok[i], mezok[i+1] = mezok[i+1], mezok[i]
                frissit_listbox()
                lb.select_set(i+1)
                sync_to_server()
                update_tree()
        except IndexError:
            messagebox.showwarning("Figyelem", "Válassz ki egy mezőt!")

    frame_buttons = tk.Frame(ablak)
    frame_buttons.pack(pady=5)
    
    tk.Button(frame_buttons, text="Hozzáadás", command=hozzaad_mezo).pack(side=tk.LEFT, padx=5, pady=5)
    tk.Button(frame_buttons, text="Törlés", command=torol_mezo).pack(side=tk.LEFT, padx=5, pady=5)
    
    make_dropdown_button = tk.Button(frame_buttons, text="Legördülővé tesz", command=make_dropdown_field)
    make_dropdown_button.pack(side=tk.LEFT, padx=5, pady=5)
    make_dropdown_button.config(state="disabled")

    tk.Button(frame_buttons, text="Fel", command=fel).pack(side=tk.LEFT, padx=5, pady=5)
    tk.Button(frame_buttons, text="Le", command=le).pack(side=tk.LEFT, padx=5, pady=5)

    def on_select(event):
        selected_indices = lb.curselection()
        if not selected_indices:
            make_dropdown_button.config(state="disabled")
            return
        
        selected_field = lb.get(selected_indices[0])
        if selected_field not in fix_mezok and selected_field not in listak:
            make_dropdown_button.config(state="normal")
        else:
            make_dropdown_button.config(state="disabled")

    lb.bind("<<ListboxSelect>>", on_select)

# --- QR generálás és nyomtatás/mentés ---
def qr_generalas():
    selected = tree.selection()
    if not selected:
        messagebox.showwarning("Figyelem", "Válassz ki legalább egy sort a QR generáláshoz!")
        return

    qr_popup = tk.Toplevel(root)
    qr_popup.title("QR kódok")
    qr_popup.geometry("400x600")

    main_frame = tk.Frame(qr_popup)
    main_frame.pack(fill=tk.BOTH, expand=1)

    my_canvas = tk.Canvas(main_frame)
    my_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

    my_scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=my_canvas.yview)
    my_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    my_canvas.configure(yscrollcommand=my_scrollbar.set)
    my_canvas.bind('<Configure>', lambda e: my_canvas.configure(scrollregion=my_canvas.bbox("all")))

    second_frame = tk.Frame(my_canvas)
    my_canvas.create_window((0, 0), window=second_frame, anchor="nw")

    qr_images = []
    for sel in selected:
        idx = int(sel)
        sor = adatok[idx]
        
        sorszam = sor.get("Sorszám", "")
        if not sorszam:
            messagebox.showwarning("Figyelem", "Hiányzik a Sorszám mező!")
            continue
        
        qr_text = f"{SERVER_URL}/edit/{sorszam}"
        
        qr_code_size = 350
        qr_img = qrcode.make(qr_text).resize((qr_code_size, qr_code_size))
        qr_images.append(qr_img)

        qr_item_frame = tk.Frame(second_frame)

        img = ImageTk.PhotoImage(qr_img)
        qr_label = tk.Label(qr_item_frame, image=img)
        qr_label.image = img
        qr_label.pack(pady=(10, 5))

        def create_ment_qr_command(img_to_save):
            def ment_qr():
                path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
                if path:
                    img_to_save.save(path)
                    messagebox.showinfo("Mentve", f"QR kód elmentve: {path}")
            return ment_qr

        save_button = tk.Button(qr_item_frame, text="Mentés", command=create_ment_qr_command(qr_img))
        save_button.pack(pady=(0, 10))
        
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