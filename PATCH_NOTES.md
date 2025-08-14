
# Parche exprés (routers + JS)

Este parche agrega:
1) Endpoints JSON para **crear citas** (`POST /api/appointments`) y **listar calendario por día** (`GET /api/calendar`).
2) JS no intrusivo para asegurar que **Agregar medicamento** funcione y que **Guardar cita** muestre feedback ✅ y refresque el calendario.

## 1) Habilitar el router en `app/main.py` (2 líneas)

```python
from app.routers.appointments import make_router   # [AÑADIR]

# después de crear `app = FastAPI(...)` y `engine = create_engine(...)`
app.include_router(make_router(engine))            # [AÑADIR]
```

> Nota: Tu `main.py` del ZIP tiene fragmentos con `...` (truncado). En tu repo local **no deben existir**. Agrega solo esas 2 líneas donde corresponda. Si usas "startup" para crear tablas, déjalo igual.

## 2) Incluir el JS al final de `app/templates/base.html` antes de `</body>`

```html
<script src="/static/patch.js"></script> <!-- [AÑADIR] -->
```

## 3) (Opcional) Añadir contenedor de calendario en `/expediente` o `patient_detail.html`

En el lugar donde quieras listar las citas del día:

```html
<div class="card">
  <h3>Calendario del día</h3>
  <div class="calendar-controls">
    <button type="button" onclick="(function(){const d=new Date(document.getElementById('calendar-day').value||new Date());d.setDate(d.getDate()-1);const iso=d.toISOString().slice(0,10);document.getElementById('calendar-day').value=iso;cargarCalendario(iso);})();">←</button>
    <input type="date" id="calendar-day" onchange="cargarCalendario(this.value)">
    <button type="button" onclick="(function(){const d=new Date(document.getElementById('calendar-day').value||new Date());d.setDate(d.getDate()+1);const iso=d.toISOString().slice(0,10);document.getElementById('calendar-day').value=iso;cargarCalendario(iso);})();">→</button>
  </div>
  <ul id="calendar-list"></ul>
</div>
```

Con esto, al **Guardar cita** desde la receta o consulta, verás el ✅ y la cita aparecerá en el calendario del día.

---

## Comandos
```
pip install --no-cache-dir -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 10000
```
