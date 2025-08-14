from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

# Modelo de ejemplo
class Camion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patente = db.Column(db.String(20), nullable=False)
    chofer = db.Column(db.String(50), nullable=False)
    destino = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="Disponible")

@app.route("/")
def home():
    camiones = Camion.query.all()
    return render_template("index.html", camiones=camiones)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Crea la base de datos si no existe
    app.run(debug=True)
