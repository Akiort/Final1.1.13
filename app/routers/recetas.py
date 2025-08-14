from fastapi import APIRouter, Depends, Form
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from typing import Optional
from datetime import datetime
import json

from app.models import RecetaHistory, Consulta

def make_router(engine):
    router = APIRouter()

    def get_session():
        from sqlmodel import Session as _S
        with _S(engine) as s:
            yield s

    @router.post("/receta/guardar")
    def receta_guardar(
        patient_id: int = Form(...),
        items_json: str = Form(...),
        consulta_id: Optional[int] = Form(None),
        fecha: Optional[str] = Form(None),
        recomendaciones: Optional[str] = Form(None),
        proxima_cita: Optional[str] = Form(None),
        session: Session = Depends(get_session)
    ):
        try:
            items = json.loads(items_json or "[]")
        except Exception:
            return JSONResponse({"ok": False, "error": "items_json inválido"}, status_code=400)
        if not any((i.get("nombre") and i.get("indicacion")) for i in items):
            return JSONResponse({"ok": False, "error": "Agrega al menos un medicamento con indicación"}, status_code=400)

        # Fecha segura
        fdt = datetime.utcnow()
        if fecha:
            try:
                fdt = datetime.fromisoformat(fecha) if "T" in fecha else datetime.strptime(fecha, "%Y-%m-%d")
            except Exception:
                pass

        # Si no hay consulta, intenta la del día
        if not consulta_id:
            try:
                dia_ini = fdt.replace(hour=0, minute=0, second=0, microsecond=0)
                dia_fin = fdt.replace(hour=23, minute=59, second=59, microsecond=999999)
                c = session.exec(
                    select(Consulta)
                    .where((Consulta.patient_id == patient_id) & (Consulta.fecha >= dia_ini) & (Consulta.fecha <= dia_fin))
                    .order_by(Consulta.fecha.desc())
                ).first()
                if c:
                    consulta_id = c.id
            except Exception:
                pass

        hist = None
        if consulta_id:
            hist = session.exec(
                select(RecetaHistory).where(RecetaHistory.consulta_id == consulta_id).order_by(RecetaHistory.fecha.desc())
            ).first()

        if hist:
            hist.items_json = items_json
            hist.recomendaciones = recomendaciones
            hist.proxima_cita = proxima_cita
            hist.fecha = fdt
        else:
            hist = RecetaHistory(
                patient_id=patient_id, consulta_id=consulta_id, fecha=fdt,
                items_json=items_json, recomendaciones=recomendaciones, proxima_cita=proxima_cita
            )
            session.add(hist)

        session.commit()
        return {"ok": True, "hist_id": hist.id, "consulta_id": consulta_id}

    @router.get("/receta/por-consulta/{consulta_id}")
    def receta_por_consulta(consulta_id: int, session: Session = Depends(get_session)):
        hist = session.exec(
            select(RecetaHistory).where(RecetaHistory.consulta_id == consulta_id).order_by(RecetaHistory.fecha.desc())
        ).first()
        if not hist:
            return JSONResponse({"ok": False, "error": "No hay receta ligada a esta consulta."}, status_code=404)
        try:
            items = json.loads(hist.items_json or "[]")
        except Exception:
            items = []
        return {"ok": True, "data": {
            "id": hist.id, "items": items,
            "recomendaciones": hist.recomendaciones, "proxima_cita": hist.proxima_cita,
            "fecha": hist.fecha.isoformat()
        }}
    return router
