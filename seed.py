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
    roles = ["admin", "chofer", "despachador"]
    ciudades = ["Santiago", "Temuco", "Valdivia"]
    users = []
    for i in range(10):  
        user = User(
            username=fake.user_name(),
            role=random.choice(roles),
            password=generate_password_hash("1234")  # contraseña simple de prueba
        )
        db.session.add(user)
        users.append(user)
    
    db.session.commit()

    # ========================
    # CREAR CAMIONES
    # ========================
    choferes = [u for u in users if u.role == "chofer"]
    trucks = []
    for i in range(10):  # 10 camiones
        truck = Truck(
            plate=fake.bothify(text='???###'),  # genera placas tipo ABC123
            status=random.choice(["disponible", "en ruta"]),
            driver_id=random.choice(choferes).id if choferes else None
        )
        db.session.add(truck)
        trucks.append(truck)
    
    db.session.commit()

    # ========================
    # CREAR RUTAS
    # ========================
    for i in range(20): 
        route = Route(
    origin=random.choice(ciudades),
    destination=random.choice(ciudades),
    status=random.choice(["pendiente", "en curso", "finalizada"]),
    truck_id=random.choice(trucks).id if trucks else None
        )
        db.session.add(route)
    
    db.session.commit()

    print("Datos de prueba generados con Faker ✅")
