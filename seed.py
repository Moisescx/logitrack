from main import app, db, User, Truck, Route
from werkzeug.security import generate_password_hash
from faker import Faker
import random

fake = Faker()

with app.app_context():
    # ========================
    # BORRAR DATOS EXISTENTES 
    # ========================
    db.session.query(Route).delete()
    db.session.query(Truck).delete()
    db.session.query(User).delete()
    db.session.commit()

    # ========================
    # CREAR USUARIOS
    # ========================
    users = []

    # Admin
    admin = User(username="admin", role="admin", password=generate_password_hash("1234"))
    db.session.add(admin)
    users.append(admin)

    # Despachadores
    for i in range(3):  # 3 despachadores
        desp = User(username=f"despachador{i+1}", role="despachador", password=generate_password_hash("1234"))
        db.session.add(desp)
        users.append(desp)

    # Choferes
    choferes = []
    for i in range(10):  # 10 choferes
        chofer = User(username=fake.user_name(), role="chofer", password=generate_password_hash("1234"))
        db.session.add(chofer)
        choferes.append(chofer)
        users.append(chofer)

    db.session.commit()

    # ========================
    # CREAR CAMIONES
    # ========================
    trucks = []
    for chofer in choferes:
        truck = Truck(
            plate=fake.bothify(text='???###'),
            status=random.choice(["disponible", "en ruta"]),
            driver=chofer  # 🔹 usamos la relación, no el ID
        )
        db.session.add(truck)
        trucks.append(truck)

    db.session.commit()

    # ========================
    # CREAR RUTAS
    # ========================
    ciudades = ["Santiago", "Valparaíso", "Concepción", "Antofagasta", "La Serena", 
                "Rancagua", "Temuco", "Puerto Montt", "Valdivia", "Arica"]

    # Crear algunas rutas asignadas y otras disponibles (sin camión)
    for i in range(20):  # 20 rutas asignadas a camiones
        origin = random.choice(ciudades)
        destination = random.choice([c for c in ciudades if c != origin])
        route = Route(
            origin=origin,
            destination=destination,
            status=random.choice(["pendiente", "en_progreso", "completada"]),
            truck=random.choice(trucks)
        )
        db.session.add(route)

    # Rutas disponibles (sin camión) en estado 'pendiente'
    for i in range(10):  # 10 rutas sin camión
        origin = random.choice(ciudades)
        destination = random.choice([c for c in ciudades if c != origin])
        route = Route(
            origin=origin,
            destination=destination,
            status="pendiente",
            truck=None
        )
        db.session.add(route)

    db.session.commit()

    print("✅ Datos de prueba generados correctamente")
