from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)

# Configuración de la base de datos SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ======== MODELOS ========

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # chofer, despachador, etc.
    password = db.Column(db.String(200), nullable=False)  # contraseña hasheada

class Truck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="disponible")
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))

class Route(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pendiente")
    truck_id = db.Column(db.Integer, db.ForeignKey('truck.id'))

class Tracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'))
    location = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime)

# ======== INICIALIZAR DB ========
if __name__ == '__main__':
    #with app.app_context():#
        #db.create_all()#
    print("Base de datos creada.")

@app.route("/dashboard")
def dashboard():
    usuarios = User.query.all()
    camiones = Truck.query.all()
    rutas = Route.query.all()
    return render_template("dashboard.html", usuarios=usuarios, camiones=camiones, rutas=rutas)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)