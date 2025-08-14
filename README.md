
# Expediente Médico 1.3.0 — FULL (PDF calibrado integrado)
- Base estable con calendario (teléfono + día anterior/siguiente + selector).
- Pantalla de inicio con logo y datos de ajustes.
- Consultas previas con enlace al detalle.
- Recetas con aprendizaje de medicamentos/dosificaciones, recomendaciones y próxima cita.
- **Botón "Imprimir (PDF calibrado)"** que genera un PDF alineado con posiciones acordadas (Y=26.7 cm).

## Deploy (Render)
Build: `pip install --no-cache-dir -r requirements.txt`
Start: `uvicorn app.main:app --host 0.0.0.0 --port 10000`



## Build
```
pip install --no-cache-dir -r requirements.txt
```

## Start
```
uvicorn app.main:app --host 0.0.0.0 --port 10000
```
