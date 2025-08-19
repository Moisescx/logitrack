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

    # Admin fijo
    admin = User(username="admin", role="admin", password=generate_password_hash("1234"))
    db.session.add(admin)
    users.append(admin)

    # Despachadores (3 o 4 al azar)
    for i in range(random.randint(3, 4)):
        desp = User(
            username=f"despachador{i+1}",
            role="despachador",
            password=generate_password_hash("1234")
        )
        db.session.add(desp)
        users.append(desp)

    # Choferes (ej: 20 choferes fake)
    for i in range(20):  
        chofer = User(
            username=fake.user_name(),
            role="chofer",
            password=generate_password_hash("1234")
        )
        db.session.add(chofer)
        users.append(chofer)

    db.session.commit()

    # ========================
    # CREAR CAMIONES
    # ========================
    choferes = [u for u in users if u.role == "chofer"]
    trucks = []
    for chofer in choferes:
        truck = Truck(
            plate=fake.bothify(text='???###'),
            status=random.choice(["disponible", "en ruta"]),
            driver_id=chofer.id
        )
        db.session.add(truck)
        trucks.append(truck)

    db.session.commit()

    # ========================
    # CREAR RUTAS
    # ========================
    ciudades = [
        "Santiago", "Valparaíso", "Concepción", "Antofagasta", "La Serena",
        "Rancagua", "Temuco", "Puerto Montt", "Valdivia", "Arica"
    ]

    for i in range(100):  # 🚀 ahora 100 rutas
        origin = random.choice(ciudades)
        destination = random.choice([c for c in ciudades if c != origin])
        route = Route(
            origin=origin,
            destination=destination,
            status=random.choice(["pendiente", "en curso", "finalizada"]),
            truck_id=random.choice(trucks).id if trucks else None
        )
        db.session.add(route)

    db.session.commit()

    print("✅ Datos de prueba generados: 1 admin, varios despachadores, choferes, camiones y 100 rutas")
