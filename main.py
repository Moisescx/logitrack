from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import random
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, login_required,
    logout_user, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

from collections import Counter
from datetime import datetime
import os
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf



app = Flask(__name__)
# Use an environment variable for secret key in production. Fallback to a dev key.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')


# Configuración de la base de datos SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Inicializar CSRF Protection (para formularios y llamadas AJAX)
csrf = CSRFProtect()
csrf.init_app(app)

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
    cargo = db.Column(db.String(50), nullable=True)
    driver_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    dispatcher_id = db.Column(db.Integer, db.ForeignKey("user.id"))  #qué despachador lo controla

    
    driver = db.relationship('User', foreign_keys=[driver_id], backref='driven_truck')
    dispatcher = db.relationship('User', foreign_keys=[dispatcher_id], backref='dispatched_trucks')


class Route(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    origin = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pendiente")
    truck_id = db.Column(db.Integer, db.ForeignKey('truck.id'))
    start_time = db.Column(db.DateTime, nullable=True)
    
    truck = db.relationship('Truck', backref='routes')

class Tracking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    route_id = db.Column(db.Integer, db.ForeignKey('route.id'))
    location = db.Column(db.String(200))
    timestamp = db.Column(db.DateTime)

# ======== INICIALIZAR DB ========
if __name__ == '__main__':
    # Use this block to create DB or run the app in development.
    # with app.app_context():
    #     db.create_all()
    pass

    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_csrf_token():
    # expose a CSRF token in templates (useful for AJAX fetch requests)
    try:
        token = generate_csrf()
    except Exception:
        token = ""
    return dict(csrf_token=token)

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

@app.route("/dashboard_chofer")
@login_required
def dashboard_chofer():
    if current_user.role != "chofer":
        return "No autorizado", 403

    truck = Truck.query.filter_by(driver_id=current_user.id).first()

    # Rutas asignadas al chofer
    # Rutas asignadas al chofer (incluye en_progreso). Template JS ocultará en_progreso por defecto
    assigned_routes = Route.query.filter_by(truck_id=truck.id).all() if truck else []

    return render_template(
        "dashboard_chofer.html",
        truck=truck,
        assigned_routes=assigned_routes
    )

@app.route("/update_route_status/<int:route_id>/<status>", methods=["POST"])
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
            route.start_time = datetime.utcnow()
        else:
            # Si la ruta ya está asignada, validar que corresponda al chofer y permitir cambiar a en_progreso
            if not route.truck or route.truck.driver_id != current_user.id:
                return "No autorizado", 403
            route.status = "en_progreso"
            route.start_time = datetime.utcnow()

    elif status == "completada":
        # Solo el chofer asignado puede marcarla como completada
        if not route.truck or route.truck.driver_id != current_user.id:
            return "No autorizado", 403
        route.status = "completada"
        route.start_time = None

    else:
        return "Estado no soportado", 400

    db.session.commit()
    return redirect(url_for("dashboard_chofer"))

@app.route("/asignar_ruta/<int:route_id>", methods=["POST"])
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

    # Camiones de su flota
    trucks = Truck.query.filter_by(dispatcher_id=current_user.id).all()

    # Rutas pendientes SOLO de sus camiones
    available_routes = Route.query.filter(
        (Route.truck_id == None) & (Route.status == "pendiente")
    ).all()

    # Rutas en progreso o completadas de sus camiones
    my_routes = Route.query.join(Truck).filter(Truck.dispatcher_id == current_user.id).all()

    return render_template(
        "dashboard_despachador.html",
        trucks=trucks,
        available_routes=available_routes,
        my_routes=my_routes
    )


@app.route('/asignar_chofer/<int:route_id>')
@login_required
def asignar_chofer(route_id):
    """Muestra una página con los camiones del despachador para elegir a cuál asignar la ruta."""
    if current_user.role != 'despachador':
        return "No autorizado", 403

    route = Route.query.get_or_404(route_id)
    if route.status != 'pendiente' or route.truck_id is not None:
        return "Ruta no disponible", 400

    # Camiones del despachador (incluye ocupados/disponibles para mostrar carga y chofer)
    trucks = Truck.query.filter_by(dispatcher_id=current_user.id).all()

    return render_template('select_truck.html', route=route, trucks=trucks)


@app.route('/asignar_chofer_confirm/<int:route_id>/<int:truck_id>', methods=['POST'])
@login_required
def asignar_chofer_confirm(route_id, truck_id):
    """Ejecuta la asignación de una ruta a un camión seleccionado por el despachador."""
    if current_user.role != 'despachador':
        return "No autorizado", 403

    route = Route.query.get_or_404(route_id)
    truck = Truck.query.get_or_404(truck_id)

    # Validar que el camión pertenezca al despachador
    if truck.dispatcher_id != current_user.id:
        return "No autorizado: camión fuera de tu flota", 403

    if route.status != 'pendiente' or route.truck_id is not None:
        return "Ruta no disponible", 400

    # Asignar
    route.truck_id = truck.id
    route.status = 'en_progreso'
    truck.status = 'en ruta'
    db.session.commit()

    return redirect(url_for('dashboard_despachador'))

@app.route("/mapa_data")
@login_required
def mapa_data():
    camiones = []

    # Obtener el camión del chofer actual
    truck = Truck.query.filter_by(driver_id=current_user.id).first()
    if not truck:
        return jsonify(camiones)

    rutas = Route.query.filter_by(truck_id=truck.id).all()

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
        # Normalizar varios nombres de estado posibles
        status = (ruta.status or '').lower()
        if status in ["pendiente", "en_progreso", "en curso", "en ruta"]:
            # punto cerca del origen (simula inicio / en progreso)
            ciudad = ruta.origin
            coords = ciudades_coords.get(ciudad)
            if coords:
                jitter = [random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2)]
                point = [coords[0] + jitter[0], coords[1] + jitter[1]]
            else:
                continue
        elif status in ["completada", "finalizada"]:
            ciudad = ruta.destination
            coords = ciudades_coords.get(ciudad)
            if coords:
                point = coords
            else:
                continue
        else:
            continue

        camiones.append({
            "plate": truck.plate,
            "status": ruta.status,
            "coords": point
        })

    return jsonify(camiones)


@app.route("/mapa")
def mapa():
    return render_template("mapa_chofer.html")


@app.route("/mapa_despachador_data")
@login_required
def mapa_despachador_data():
    """Devuelve marcadores para todas las rutas de la flota del despachador actual."""
    camiones = []
    if current_user.role != 'despachador':
        return jsonify(camiones)

    # Obtener todos los camiones del despachador
    trucks = Truck.query.filter_by(dispatcher_id=current_user.id).all()

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

    for truck in trucks:
        routes = Route.query.filter_by(truck_id=truck.id).all()
        for ruta in routes:
            status = (ruta.status or '').lower()
            if status in ["pendiente", "en_progreso", "en curso", "en ruta"]:
                ciudad = ruta.origin
                coords = ciudades_coords.get(ciudad)
                if coords:
                    jitter = [random.uniform(-0.2, 0.2), random.uniform(-0.2, 0.2)]
                    point = [coords[0] + jitter[0], coords[1] + jitter[1]]
                else:
                    continue
            elif status in ["completada", "finalizada"]:
                ciudad = ruta.destination
                coords = ciudades_coords.get(ciudad)
                if coords:
                    point = coords
                else:
                    continue
            else:
                continue

            camiones.append({
                "plate": truck.plate,
                "driver": truck.driver.username if truck.driver else None,
                "cargo": truck.cargo,
                "status": ruta.status,
                "coords": point,
                "route_id": ruta.id
            })

    return jsonify(camiones)


@app.route("/mapa_despachador")
@login_required
def mapa_despachador():
    if current_user.role != 'despachador':
        return "No autorizado", 403
    return render_template("mapa_despachador.html")


@app.route('/dashboard_admin')
@login_required
def dashboard_admin():
    if current_user.role != 'admin':
        return "No autorizado", 403

    # KPIs básicos
    total_trucks = Truck.query.count()
    total_drivers = User.query.filter_by(role='chofer').count()
    total_dispatchers = User.query.filter_by(role='despachador').count()
    total_routes = Route.query.count()

    # Camiones recientes (los que ya tenías)
    recent_trucks = Truck.query.order_by(Truck.id.desc()).limit(5).all()
    # Rutas recientes
    recent_routes = Route.query.order_by(Route.id.desc()).limit(5).all()

    # 📊 Extra: Distribución de camiones por estado
    truck_status_counts = (
        db.session.query(Truck.status, db.func.count(Truck.id))
        .group_by(Truck.status).all()
    )
    truck_status_data = {status: count for status, count in truck_status_counts}

    # 📊 Extra: Distribución de rutas por estado
    route_status_counts = (
        db.session.query(Route.status, db.func.count(Route.id))
        .group_by(Route.status).all()
    )
    route_status_data = {status: count for status, count in route_status_counts}

    # 📜 Extra: timeline combinado (camiones + rutas)
    recent_activity = []
    for t in recent_trucks:
        recent_activity.append({
            "type": "camión",
            "desc": f"Camión {t.plate} agregado (estado: {t.status})"
        })
    for r in recent_routes:
        txt = f"Ruta {r.origin} → {r.destination} ({r.status})"
        if r.truck:
            txt += f" asignada al camión {r.truck.plate}"
        recent_activity.append({"type": "ruta", "desc": txt})

    # Dejar máximo 6 actividades
    recent_activity = recent_activity[:6]

    return render_template(
        'dashboard_admin.html',
        total_trucks=total_trucks,
        total_drivers=total_drivers,
        total_dispatchers=total_dispatchers,
        total_routes=total_routes,
        recent_trucks=recent_trucks,
        recent_routes=recent_routes,
        truck_status_data=truck_status_data,
        route_status_data=route_status_data,
        recent_activity=recent_activity
    )



@app.route('/mapa_admin')
@login_required
def mapa_admin():
    if current_user.role != 'admin':
        return "No autorizado", 403
    return render_template('mapa_admin.html')


@app.route('/mapa_admin_data')
@login_required
def mapa_admin_data():
    """Devuelve marcadores para todas las rutas en la DB (para el admin)."""
    if current_user.role != 'admin':
        return jsonify([])

    camiones = []
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

    routes = Route.query.all()
    for ruta in routes:
        status = (ruta.status or '').lower()
        if status in ["pendiente", "en_progreso", "en curso", "en ruta"]:
            ciudad = ruta.origin
            coords = ciudades_coords.get(ciudad)
            if coords:
                jitter = [random.uniform(-0.3, 0.3), random.uniform(-0.3, 0.3)]
                point = [coords[0] + jitter[0], coords[1] + jitter[1]]
            else:
                continue
        elif status in ["completada", "finalizada"]:
            ciudad = ruta.destination
            coords = ciudades_coords.get(ciudad)
            if coords:
                point = coords
            else:
                continue
        else:
            continue

        camiones.append({
            'route_id': ruta.id,
            'origin': ruta.origin,
            'destination': ruta.destination,
            'status': ruta.status,
            'truck_plate': ruta.truck.plate if ruta.truck else None,
            'coords': point
        })

    return jsonify(camiones)


### Admin CRUD: Trucks
@app.route('/admin/trucks')
@login_required
def admin_trucks():
    if current_user.role != 'admin':
        return "No autorizado", 403
    trucks = Truck.query.all()
    return render_template('admin_trucks.html', trucks=trucks)


@app.route('/admin/trucks/new', methods=['GET', 'POST'])
@login_required
def admin_truck_new():
    if current_user.role != 'admin':
        return "No autorizado", 403
    if request.method == 'POST':
        plate = request.form.get('plate')
        status = request.form.get('status')
        cargo = request.form.get('cargo')
        dispatcher_id = request.form.get('dispatcher_id') or None
        driver_id = request.form.get('driver_id') or None

        # Validación de campos obligatorios
        if not plate or not status:
            flash('Por favor, completa los campos obligatorios: Placa y Estado.', 'error')
            drivers = User.query.filter_by(role='chofer').all()
            dispatchers = User.query.filter_by(role='despachador').all()
            return render_template('admin_truck_form.html', drivers=drivers, dispatchers=dispatchers, truck=None)

        truck = Truck(plate=plate, status=status, cargo=cargo,
                      dispatcher_id=int(dispatcher_id) if dispatcher_id else None,
                      driver_id=int(driver_id) if driver_id else None)
        db.session.add(truck)
        db.session.commit()
        flash('Camión creado correctamente.', 'success')
        return redirect(url_for('admin_trucks'))

    drivers = User.query.filter_by(role='chofer').all()
    dispatchers = User.query.filter_by(role='despachador').all()
    return render_template('admin_truck_form.html', drivers=drivers, dispatchers=dispatchers, truck=None)


@app.route('/admin/trucks/edit/<int:truck_id>', methods=['GET', 'POST'])
@login_required
def admin_truck_edit(truck_id):
    if current_user.role != 'admin':
        return "No autorizado", 403
    truck = Truck.query.get_or_404(truck_id)
    if request.method == 'POST':
        plate = request.form.get('plate')
        status = request.form.get('status')
        cargo = request.form.get('cargo')
        dispatcher_id = request.form.get('dispatcher_id') or None
        driver_id = request.form.get('driver_id') or None

        # Validación
        if not plate or not status:
            flash('Por favor, completa los campos obligatorios: Placa y Estado.', 'error')
            drivers = User.query.filter_by(role='chofer').all()
            dispatchers = User.query.filter_by(role='despachador').all()
            return render_template('admin_truck_form.html', drivers=drivers, dispatchers=dispatchers, truck=truck)

        truck.plate = plate
        truck.status = status
        truck.cargo = cargo
        truck.dispatcher_id = int(dispatcher_id) if dispatcher_id else None
        truck.driver_id = int(driver_id) if driver_id else None
        db.session.commit()
        flash('Camión actualizado correctamente.', 'success')
        return redirect(url_for('admin_trucks'))

    drivers = User.query.filter_by(role='chofer').all()
    dispatchers = User.query.filter_by(role='despachador').all()
    return render_template('admin_truck_form.html', drivers=drivers, dispatchers=dispatchers, truck=truck)


@app.route('/admin/trucks/delete/<int:truck_id>', methods=['POST'])
@login_required
def admin_truck_delete(truck_id):
    if current_user.role != 'admin':
        return "No autorizado", 403
    truck = Truck.query.get_or_404(truck_id)
    db.session.delete(truck)
    db.session.commit()
    return redirect(url_for('admin_trucks'))


### Admin CRUD: Routes
@app.route('/admin/routes')
@login_required
def admin_routes():
    if current_user.role != 'admin':
        return "No autorizado", 403
    routes = Route.query.all()
    return render_template('admin_routes.html', routes=routes)


@app.route('/admin/routes/new', methods=['GET', 'POST'])
@login_required
def admin_route_new():
    if current_user.role != 'admin':
        return "No autorizado", 403
        
    trucks = Truck.query.all()
    
    if request.method == 'POST':
        origin = request.form.get('origin')
        destination = request.form.get('destination')
        status = request.form.get('status')
        truck_id = request.form.get('truck_id') or None 

        # 2. VALIDACIÓN DE CAMPOS OBLIGATORIOS
        if not origin or not destination or not status:
            # Si falta algún campo obligatorio, mostrar un mensaje de error y volver al formulario
            flash('Por favor, rellena todos los campos obligatorios (Origen, Destino, Estado).', 'error')
            return render_template('admin_route_form.html', trucks=trucks, route=None, 
                                   origin=origin, destination=destination, status=status) 

        route = Route(origin=origin, destination=destination, status=status,
                      truck_id=int(truck_id) if truck_id else None)
        db.session.add(route)
        db.session.commit()
        flash('Ruta creada exitosamente.', 'success')
        return redirect(url_for('admin_routes'))

    return render_template('admin_route_form.html', trucks=trucks, route=None)

@app.route('/admin/routes/edit/<int:route_id>', methods=['GET', 'POST'])
@login_required
def admin_route_edit(route_id):
    if current_user.role != 'admin':
        return "No autorizado", 403
    route = Route.query.get_or_404(route_id)
    if request.method == 'POST':
        route.origin = request.form.get('origin')
        route.destination = request.form.get('destination')
        route.status = request.form.get('status')
        truck_id = request.form.get('truck_id') or None
        route.truck_id = int(truck_id) if truck_id else None
        db.session.commit()
        return redirect(url_for('admin_routes'))

    trucks = Truck.query.all()
    return render_template('admin_route_form.html', trucks=trucks, route=route)


@app.route('/admin/routes/delete/<int:route_id>', methods=['POST'])
@login_required
def admin_route_delete(route_id):
    if current_user.role != 'admin':
        return "No autorizado", 403
    route = Route.query.get_or_404(route_id)
    db.session.delete(route)
    db.session.commit()
    return redirect(url_for('admin_routes'))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)