# Documentación técnica — LogiTrack (ES)

## Resumen técnico
Aplicación web monolítica para gestión de flota y rutas. Backend en Python/Flask con SQLAlchemy y frontend basado en plantillas Jinja2 y JavaScript (vanilla). Base de datos SQLite utilizada en desarrollo.

## Stack
- Python 3.x
- Flask (microframework)
- Flask-Login (autenticación de sesiones)
- Flask-SQLAlchemy (ORM)
- Jinja2 (templates)
- TailwindCSS (estilos)
- JavaScript (cliente, sin frameworks)
- SQLite (base de datos)

## Estructura principal
- `main.py` — aplicación Flask, modelos, rutas/endpoints y lógica principal.
- `templates/` — plantillas Jinja2 (dashboards, formularios, vistas de mapa).
- `static/` — recursos estáticos (imágenes).
- `seed.py` — script de datos de ejemplo.
- `instance/database.db` — base de datos SQLite (desarrollo).
- `docs/` — documentación.

## Modelos (SQLAlchemy)
Resumen de tablas y campos relevantes:

- User
  - id: Integer
  - username: String
  - role: String ("chofer" | "despachador" | "admin")
  - password: String (hash)

- Truck
  - id: Integer
  - plate: String
  - status: String
  - cargo: String
  - driver_id: Integer → FK User.id
  - dispatcher_id: Integer → FK User.id

- Route
  - id: Integer
  - origin: String
  - destination: String
  - status: String ("pendiente" | "en_progreso" | "completada")
  - truck_id: Integer → FK Truck.id
  - start_time: DateTime (nullable)

- Tracking
  - id: Integer
  - route_id: Integer → FK Route.id
  - location: String
  - timestamp: DateTime


## Endpoints principales
- `GET /` → redirect a `/login`
- `GET, POST /login` → autenticación
- `GET /dashboard_chofer` — vista del chofer
- `GET /dashboard_despachador` — vista del despachador
- `GET /dashboard_admin` — vista admin
- `GET /update_route_status/<int:route_id>/<status>` — cambia estado; lógica para `en_progreso` y `completada` 
- `GET /asignar_chofer/<route_id>` y `/asignar_chofer_confirm/<route_id>/<truck_id>` — asignación por despachador
- `GET /mapa`, `/mapa_data`, `/mapa_despachador`, `/mapa_despachador_data` — datos/plantillas de mapas
- Rutas admin CRUD: `/admin/trucks`, `/admin/routes`, etc.

> Observación: varias operaciones mutantes usan `GET`; es recomendable migrar a `POST/PUT` y añadir protección CSRF.

## Lógica del servidor (puntos clave)
- Autorización: `@login_required` en rutas; validaciones de `current_user.role` y ownership (por ejemplo, solo el chofer asignado puede finalizar su ruta).
- `update_route_status(..., 'en_progreso')`:
  - Si la ruta es pendiente y no tiene `truck_id`, se asigna el `truck` del chofer (si existe).
  - Se setea `route.status = 'en_progreso'` y `route.start_time = datetime.utcnow()`.
- `update_route_status(..., 'completada')`: valida chofer y pone `route.status = 'completada'` y `route.start_time = None`.
- El servidor es la fuente de verdad para `start_time`; el cliente lo usa para recalcular tiempos.

## Lógica del cliente (JS) — comportamiento implementado
- Al pulsar "Iniciar":
  - `startTrip(routeId)` realiza una cuenta atrás fija de 5s (cliente).
  - Antes de redirigir a `update_route_status(.../en_progreso)` guarda `sessionStorage.visible_in_progress = routeId` para mostrar la tarjeta `en_progreso` solo en la sesión iniciadora.
- Tras el cambio a `en_progreso` y recarga:
  - La plantilla expone `route.start_time.isoformat()` en atributo `data-start-time` del botón Finalizar.
  - JS parsea `start_time` y calcula `tripRemaining = ceil(10 - elapsedSeconds)` para mostrar enteros y evitar fracciones como `10.8`.
  - Un intervalo decrementa `tripRemaining` cada segundo (si no está pausado).
  - "Emergencia": pausa/reanuda el intervalo. No se registra en servidor por defecto.
  - Cuando `tripRemaining` llega a `0`, se habilita el botón "Finalizar".

## Reglas y decisiones de diseño
- Visibilidad: las tarjetas `en_progreso` están ocultas por defecto en el dashboard del chofer; se muestran solo si `sessionStorage.visible_in_progress` coincide con la ruta (solución pedida para UX).
- Tiempo del viaje: duración efectiva en cliente = 10s (cuenta regresiva 10→0). `start_time` en DB sirve para sincronizar si el chofer recarga.
- Simplicidad: se usan GET para acciones mutantes por rapidez en desarrollo; cambiar esto en producción.

## Consideraciones técnicas y edge cases
- Dependencia del reloj del cliente: si el reloj local está desincronizado con el servidor, el cálculo de `tripRemaining` puede variar. Recomendación: devolver tiempo del servidor o usar sincronización NTP en despliegue.
- Pause (Emergencia) no persiste en servidor: si el usuario recarga durante una pausa, la pausa se pierde. Para persistencia, añadir endpoint para registrar eventos de pausa.
- sessionStorage no comparte estado entre pestañas: otra pestaña del mismo navegador no verá `visible_in_progress`. Si quieres visibilidad multi-tab, usar localStorage o control server-side.
- Concurrencia: evitar race conditions verificando el estado actual en la DB antes de escritura (y usar locking/transacciones cuando sea necesario).

## Cómo ejecutar localmente (resumen)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py   # opcional, para datos de ejemplo
python main.py
# Abrir http://127.0.0.1:5000
```

## Pruebas recomendadas
- Unit: endpoints (login, update_route_status), modelos y relaciones.
- Integration: flujo chofer (login -> iniciar -> en_progreso -> countdown -> finalizar).
- Security: probar accesos por rol no autorizados.
- Herramientas: `pytest`, `pytest-flask`.

## Mejoras sugeridas (prioridad)
1. Cambiar operaciones de estado a `POST`/`PUT` y añadir CSRF.
2. Añadir Alembic para migraciones.
3. Registrar pausas/emergencias en DB (auditoría).
4. Considerar WebSockets / SocketIO si necesitas sincronización en tiempo real entre múltiples clientes.
5. Añadir tests automáticos y pipeline CI (GitHub Actions).

## Contrato API (resumen programático)
- `GET /update_route_status/<id>/en_progreso` (actualmente GET)
  - Validaciones: ownership/estado
  - Efecto: set start_time = utcnow() y status = 'en_progreso'

- `GET /update_route_status/<id>/completada` (actualmente GET)
  - Validaciones: ownership
  - Efecto: set status = 'completada' y start_time = None
