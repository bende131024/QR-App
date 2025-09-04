from flask_sqlalchemy import SQLAlchemy
from flask import Flask
import os
import json

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Adatbázis modellek (ugyanazok, mint a server.py-ban)
class Mezo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    order = db.Column(db.Integer, nullable=False)

class Lista(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    field_name = db.Column(db.String(100), nullable=False)
    option = db.Column(db.String(100), nullable=False)
    __table_args__ = (db.UniqueConstraint('field_name', 'option'),)

class Adat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sorszam = db.Column(db.String(100), unique=True, nullable=False)
    data = db.Column(db.Text, nullable=False)

# Alap adatok a qr_app.py-ból
fix_mezok = ["Sorszám", "Fémzárszám", "Beszállító", "Név", "Hely", "Súly", "Megjegyzés", "Osztály"]
listak = {
    "Beszállító": ["Beszállító 1", "Beszállító 2", "Beszállító 3"],
    "Hely": ["Raktár A", "Raktár B", "Kijelölt hely"],
    "Osztály": ["Fénykép", "Eladva", "Javításra"]
}
adatok = []

# Adatbázis inicializálása
with app.app_context():
    # Táblák létrehozása
    db.create_all()

    # Meglévő adatok törlése
    db.session.query(Mezo).delete()
    db.session.query(Lista).delete()
    db.session.query(Adat).delete()

    # Mezők beszúrása
    for i, name in enumerate(fix_mezok):
        db.session.add(Mezo(name=name, order=i))

    # Legördülő listák beszúrása
    for field_name, options in listak.items():
        for option in options:
            db.session.add(Lista(field_name=field_name, option=option))

    # Adatok beszúrása (üres, mivel nincs alap adatsor)
    for row in adatok:
        if "Sorszám" in row:
            db.session.add(Adat(sorszam=row["Sorszám"], data=json.dumps(row)))

    # Mentés
    db.session.commit()

print("database.db sikeresen létrehozva az alap adatokkal.")