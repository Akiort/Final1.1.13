
from fastapi import APIRouter, Form, Depends
from fastapi.responses import JSONResponse
from sqlmodel import Session, select
from datetime import datetime, date, time
from app.models import Appointment, Patient

def make_router(engine):
    router = APIRouter()

    def get_session():
        with Session(engine) as s:
            yield s

    @router.post("/api/appointments")
    def create_appointment(
        patient_id: int = Form(...),
        consulta_id: int | None = Form(None),
        fecha: str = Form(...),
        nota: str = Form(""),
        session: Session = Depends(get_session)
    ):
        try:
            dt = datetime.fromisoformat(fecha)
        except Exception:
            return JSONResponse({"ok": False, "error": "Fecha inválida"}, status_code=400)
        ap = Appointment(patient_id=patient_id, consulta_id=consulta_id, fecha=dt, nota=nota)
        session.add(ap)
        session.commit()
        return {"ok": True, "id": ap.id}

    @router.get("/api/calendar")
    def calendar(day: str, session: Session = Depends(get_session)):
        try:
            base = datetime.fromisoformat(day).date()
        except Exception:
            base = datetime.now().date()
        start = datetime.combine(base, time.min)
        end   = datetime.combine(base, time.max)

        rows = session.exec(
            select(Appointment, Patient)
            .where((Appointment.fecha >= start) & (Appointment.fecha <= end))
            .join(Patient, Patient.id == Appointment.patient_id)
            .order_by(Appointment.fecha)
        ).all()

        items = []
        for ap, p in rows:
            items.append({
                "id": ap.id,
                "hora": ap.fecha.strftime("%H:%M"),
                "paciente": p.nombre,
                "nota": ap.nota or ""
            })
        return {"ok": True, "day": base.isoformat(), "items": items}

    return router
