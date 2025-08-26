from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.config['SECRET_KEY'] = 'mmarinliventuslab2004'  # contraseña secreta para sesiones


# Configuración de la base de datos SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# LOGIN MANAGER
# ========================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # si alguien no logueado entra a ruta protegida → va a /login

# ======== MODELOS ========

class User( UserMixin,db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)  # chofer, despachador, admin.
    password = db.Column(db.String(200), nullable=False)  # contraseña hasheada

class Truck(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    plate = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="disponible")
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    driver = db.relationship('User', backref='truck')

class Route(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pendiente")
    truck_id = db.Column(db.Integer, db.ForeignKey('truck.id'))
    
    truck = db.relationship('Truck', backref='routes')

class Tracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'))
    location = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime)

# ======== INICIALIZAR DB ========
if __name__ == '__main__':
    #with app.app_context():#
        #db.create_all()#
    #print("Base de datos creada.")#
    
    hashed_password = generate_password_hash("contraseña123", method="pbkdf2:sha256")

    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def home():
    return redirect(url_for("login"))

    
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash (user.password, password): 
            login_user(user)

            # Redirección según rol
            if user.role == "admin":
                return redirect(url_for("dashboard_admin"))
            elif user.role == "chofer":
                return redirect(url_for("dashboard_chofer")) 
            elif user.role == "despachador":
                return redirect(url_for("dashboard_despachador"))
            else:
                return "Rol no reconocido", 403

        return "Usuario o contraseña incorrectos", 401

    return render_template("login.html")

@app.route("/dashboard_admin")
@login_required
def dashboard_admin():
    if current_user.role != "admin":
        return "No autorizado", 403
    return render_template("dashboard_admin.html")

@app.route("/dashboard_chofer")
@login_required
def dashboard_chofer():
    if current_user.role != "chofer":
        return "No autorizado", 403

    truck = Truck.query.filter_by(driver_id=current_user.id).first()

    # Rutas asignadas al chofer
    assigned_routes = Route.query.filter_by(truck_id=truck.id).all() if truck else []

    # Rutas sin camión asignado y pendientes (rutas disponibles para tomar)
    available_routes = Route.query.filter_by(truck_id=None, status="pendiente").all()

    return render_template(
        "dashboard_chofer.html",
        truck=truck,
        assigned_routes=assigned_routes,
        available_routes=available_routes
    )

@app.route("/update_route_status/<int:route_id>/<status>")
@login_required
def update_route_status(route_id, status):
    if current_user.role != "chofer":
        return "No autorizado", 403

    route = Route.query.get_or_404(route_id)


    # Manejar request para cambiar estado: 'en_progreso' o 'completada'
    if status == "en_progreso":
        # Chofer intenta tomar una ruta pendiente o iniciar una ruta ya asignada a su camión
        if route.status == "pendiente" and route.truck_id is None:
            truck = Truck.query.filter_by(driver_id=current_user.id).first()
            if not truck:
                return "No tienes camión asignado", 400

            route.truck_id = truck.id
            route.status = "en_progreso"
        else:
            # Si la ruta ya está asignada, validar que corresponda al chofer y permitir cambiar a en_progreso
            if not route.truck or route.truck.driver_id != current_user.id:
                return "No autorizado", 403
            route.status = "en_progreso"

    elif status == "completada":
        # Solo el chofer asignado puede marcarla como completada
        if not route.truck or route.truck.driver_id != current_user.id:
            return "No autorizado", 403
        route.status = "completada"

    else:
        return "Estado no soportado", 400

    db.session.commit()
    return redirect(url_for("dashboard_chofer"))

@app.route("/asignar_ruta/<int:route_id>")
@login_required
def asignar_ruta(route_id):
    if current_user.role != "chofer":
        return "No autorizado", 403

    route = Route.query.get_or_404(route_id)

    # Validar que la ruta esté disponible
    if route.status != "pendiente" or route.truck_id is not None:
        return "Ruta no disponible", 400

    # Buscar el camión del chofer actual
    truck = Truck.query.filter_by(driver_id=current_user.id).first()
    if not truck:
        return "No tienes camión asignado", 400

    # Asignar ruta
    route.truck_id = truck.id
    route.status = "en_progreso"
    db.session.commit()

    return redirect(url_for("dashboard_chofer")) 

@app.route("/dashboard_despachador")
@login_required
def dashboard_despachador():
    if current_user.role != "despachador":
        return "No autorizado", 403
    return render_template("dashboard_despachador.html")

@app.route("/mapa_data")
@login_required
def mapa_data():
    camiones = []
    rutas = Route.query.join(Truck).filter(Truck.driver_id == current_user.id).all()

    ciudades_coords = {
        "Santiago": [-33.4489, -70.6693],
        "Valparaíso": [-33.0472, -71.6127],
        "Concepción": [-36.8201, -73.0444],
        "Antofagasta": [-23.6509, -70.3975],
        "La Serena": [-29.9027, -71.2520],
        "Rancagua": [-34.1701, -70.7447],
        "Temuco": [-38.7397, -72.5984],
        "Puerto Montt": [-41.4717, -72.9369],
        "Valdivia": [-39.8196, -73.2459],
        "Arica": [-18.4783, -70.3126]
    }

    for ruta in rutas:
        if ruta.status in ["pendiente", "en_progreso"]:
            ciudad = ruta.origin
        elif ruta.status == "completada":
            ciudad = ruta.destination
        else:
            continue

        coords = ciudades_coords.get(ciudad)
        if coords and ruta.truck:
            camiones.append({
                "plate": ruta.truck.plate,
                "status": ruta.status,
                "coords": coords
            })

    return jsonify(camiones)


@app.route("/mapa")
def mapa():
    return render_template("mapa_chofer.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)