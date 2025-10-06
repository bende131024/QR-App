from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import json
from sqlalchemy.exc import IntegrityError
from datetime import datetime

app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Adatbázis modellek
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
    azonosito = db.Column(db.String(36), unique=True, nullable=False)
    data = db.Column(db.Text, nullable=False)  # JSON string dinamikus mezőkhöz

class Beolvasas(db.Model):  # Új model a beolvasott helyekhez
    id = db.Column(db.Integer, primary_key=True)
    azonosito = db.Column(db.String(36), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    long = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Adatbázis táblák létrehozása
with app.app_context():
    db.create_all()

# Segédfunkció az adatbázis JSON formátumba konvertálására
def get_data_store():
    mezok = [m.name for m in Mezo.query.order_by(Mezo.order).all()]
    listak = {}
    for lista in Lista.query.all():
        if lista.field_name not in listak:
            listak[lista.field_name] = []
        listak[lista.field_name].append(lista.option)
    adatok = [json.loads(adat.data) for adat in Adat.query.all()]
    return {"mezok": mezok, "adatok": adatok, "listak": listak}

# Segédfunkció az adatbázis frissítésére JSON-ból
def update_data_store(data):
    try:
        # Meglévő adatok törlése
        db.session.query(Mezo).delete()
        db.session.query(Lista).delete()
        db.session.query(Adat).delete()

        # Mezők beszúrása
        for i, name in enumerate(data.get("mezok", [])):
            db.session.add(Mezo(name=name, order=i))

        # Legördülő listák beszúrása
        for field_name, options in data.get("listak", {}).items():
            for option in options:
                db.session.add(Lista(field_name=field_name, option=option))

        # Adatok beszúrása
        for row in data.get("adatok", []):
            if "Azonosító" in row:
                db.session.add(Adat(azonosito=row["Azonosító"], data=json.dumps(row)))

        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        raise Exception(f"Adatbázis hiba: Valószínűleg duplikált Azonosító. Részletek: {str(e)}")
    except Exception as e:
        db.session.rollback()
        raise Exception(f"Adatbázis hiba: {str(e)}")

@app.route('/data', methods=['GET'])
def get_data():
    return jsonify(get_data_store())

@app.route('/update', methods=['POST'])
def update_data():
    try:
        new_data = request.json
        update_data_store(new_data)
        return {"status": "success"}, 200
    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

@app.route('/edit/<azonosito>', methods=['GET', 'PUT'])
def edit_row(azonosito):
    if request.method == 'GET':
        row = Adat.query.filter_by(azonosito=azonosito).first()
        if not row:
            return "Termék nem található", 404
        data_store = get_data_store()
        return render_template('edit.html',
                               azonosito=azonosito,
                               row=json.loads(row.data),
                               mezok=data_store["mezok"],
                               listak=data_store["listak"])
    
    elif request.method == 'PUT':
        updated_row = request.json
        row = Adat.query.filter_by(azonosito=azonosito).first()
        if not row:
            return "Termék nem található", 404
        # Azonosító ne legyen módosítható
        if updated_row.get("Azonosító") != azonosito:
            return {"status": "error", "message": "Az azonosító nem módosítható!"}, 400
        row.data = json.dumps(updated_row)
        try:
            db.session.commit()
            return {"status": "success"}, 200
        except IntegrityError as e:
            db.session.rollback()
            return {"status": "error", "message": f"Adatbázis hiba: Valószínűleg duplikált Azonosító. Részletek: {str(e)}"}, 500
        except Exception as e:
            db.session.rollback()
            return {"status": "error", "message": str(e)}, 500

@app.route('/log_location/<azonosito>', methods=['POST'])  # Új endpoint a hely rögzítésére
def log_location(azonosito):
    data = request.json
    lat = data.get('lat')
    long = data.get('long')
    if not lat or not long:
        return {"status": "error", "message": "Hiányzó helyadatok"}, 400
    try:
        new_log = Beolvasas(azonosito=azonosito, lat=lat, long=long)
        db.session.add(new_log)
        db.session.commit()
        return {"status": "success"}, 200
    except Exception as e:
        db.session.rollback()
        return {"status": "error", "message": str(e)}, 500

@app.route('/get_locations', methods=['GET'])  # Endpoint a helyek lekérdezésére (JSON)
def get_locations():
    locations = Beolvasas.query.all()
    return jsonify([{
        'azonosito': loc.azonosito,
        'lat': loc.lat,
        'long': loc.long,
        'timestamp': loc.timestamp.isoformat()
    } for loc in locations])

@app.route('/map', methods=['GET'])  # Új route a térkép HTML-hez
def show_map():
    return render_template('map.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)