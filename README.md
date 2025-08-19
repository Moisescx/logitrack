Clonar el repositorio

git clone https://github.com/Moisescx/logitrack.git

cd https://github.com/Moisescx/logitrack.git

Crear y activar el ambiente virtual

Windows:

python -m venv venv
venv\Scripts\activate

Linux/Mac:

python3 -m venv venv
source venv/bin/activate

Instalar dependencias

pip install -r requirements.txt

Base de datos

El archivo database.db no se incluye en el repositorio.

Si no tienes la base de datos, ejecuta la aplicación y se generará automáticamente (si el código ya está configurado para eso).

Si se necesita una base de datos inicial, se compartirá aparte.

Flujo de trabajo en equipo

Antes de empezar a trabajar:

git pull

Después de hacer cambios:

git add .
git commit -m "Descripción clara de los cambios"
git push

⚠ Notas importantes

No modificar el archivo requirements.txt a menos que realmente se necesite agregar o cambiar una librería.

Si instalas una nueva librería, recuerda actualizar el archivo:

pip freeze > requirements.txt

Nunca subas el venv ni database.db al repositorio.