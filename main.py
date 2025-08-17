from flask import Flask, render_template, request, redirect, url_for
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
    
hashed_password = generate_password_hash("contraseña123", method="pbkdf2:sha256")

    
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
    
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
    
    # Obtener el camión del chofer actual
    truck = Truck.query.filter_by(driver_id=current_user.id).first()

    # Buscar rutas de ese camión
    routes = Route.query.filter_by(truck_id=truck.id).all() if truck else []

    return render_template("dashboard_chofer.html", routes=routes, truck=truck)

@app.route("/update_route_status/<int:route_id>/<status>")
@login_required
def update_route_status(route_id, status):
    if current_user.role != "chofer":
        return "No autorizado", 403

    route = Route.query.get_or_404(route_id)

    # Validar que la ruta corresponde al chofer actual
    if route.truck.driver_id != current_user.id:
        return "No autorizado", 403

    # Actualizar estado
    if status in ["en_progreso", "completada"]:
        route.status = status
        db.session.commit()

    return redirect(url_for("dashboard_chofer"))


@app.route("/dashboard_despachador")
@login_required
def dashboard_despachador():
    if current_user.role != "despachador":
        return "No autorizado", 403
    return render_template("dashboard_despachador.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)