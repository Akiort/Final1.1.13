
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlmodel import SQLModel, Session, create_engine, select
from typing import Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from datetime import datetime, date, timedelta
from app.models import Patient, PatientExtra, Consulta, Ajustes, RecetaItem, Medicine, Dosificacion, Appointment, RecetaHistory
from app.routers.appointments import make_router
import json, os

DATABASE_URL = "sqlite:///./data.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

app = FastAPI(title="Expediente Médico 1.3.0 (calibrated)")
app.include_router(make_router(engine))
app.mount("/static", StaticFiles(directory="app/static"), name="static")

env = Environment(loader=FileSystemLoader("app/templates"), autoescape=select_autoescape())

def render(name: str, **ctx):
    return HTMLResponse(env.get_template(name).render(**ctx))

def get_session():
    with Session(engine) as session:
        yield session

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        ajustes = s.exec(select(Ajustes)).first()
        if not ajustes:
            ajustes = Ajustes(
                clinica_nombre="CLINICA IMAGEN",
                clinica_direccion="Tabasco 403, Valle de Aguayo, 87020 Cdad. Victoria, Tamps.",
                clinica_telefono="8341779965",
                medico_nombre="Dr. Jorge Alberto Rodríguez Martinez",
                cedula="5439453",
                cedula_especialista="1067241",
            )
            s.add(ajustes); s.commit()

# --------- Splash ---------
@app.get("/", response_class=HTMLResponse)
def bienvenida(request: Request, session: Session = Depends(get_session)):
    ajustes = session.exec(select(Ajustes)).first()
    logo_exists = os.path.exists("app/static/logo-header.png")
    return render("bienvenida.html", request=request, ajustes=ajustes, has_logo=logo_exists)

# --------- Expediente con calendario ---------
@app.get("/expediente", response_class=HTMLResponse)
def expediente_home(request: Request, q: str|None=None, fecha: str|None=None, session: Session = Depends(get_session)):
    pacientes = session.exec(select(Patient).order_by(Patient.created_at.desc())).all()
    if q:
        ql = q.lower()
        pacientes = [p for p in pacientes if ql in (p.nombre or '').lower() or ql in (p.alergias or '')]

    try:
        sel = datetime.fromisoformat(fecha) if fecha else datetime.now()
    except Exception:
        sel = datetime.now()
    dia_ini = sel.replace(hour=0, minute=0, second=0, microsecond=0)
    dia_fin = sel.replace(hour=23, minute=59, second=59, microsecond=999999)

    citas = session.exec(select(Appointment).where(Appointment.fecha >= dia_ini, Appointment.fecha <= dia_fin).order_by(Appointment.fecha.asc())).all()

    cita_rows = []
    for c in citas:
        p = session.get(Patient, c.patient_id)
        cita_rows.append({
            "id": c.id,
            "pid": p.id if p else None,
            "hora": c.fecha.strftime("%H:%M"),
            "paciente": p.nombre if p else "—",
            "telefono": p.telefono if p and p.telefono else "—",
            "notas": c.notas or ""
        })
    prev_day = (dia_ini - timedelta(days=1)).strftime("%Y-%m-%d")
    next_day = (dia_ini + timedelta(days=1)).strftime("%Y-%m-%d")
    sel_str = dia_ini.strftime("%Y-%m-%d")
    titulo = sel.strftime("%A %d/%m/%Y")

    return render("home.html", request=request, pacientes=pacientes, q=q or '',
                  citas=cita_rows, hoy=titulo, sel=sel_str, prev_day=prev_day, next_day=next_day)

# --------- Ajustes ---------
@app.get("/ajustes", response_class=HTMLResponse)
def ajustes_get(request: Request, session: Session = Depends(get_session)):
    ajustes = session.exec(select(Ajustes)).first()
    return render("ajustes.html", request=request, a=ajustes)

@app.post("/ajustes", response_class=HTMLResponse)
def ajustes_post(
    clinica_nombre: str = Form(None),
    clinica_direccion: str = Form(None),
    clinica_telefono: str = Form(None),
    medico_nombre: str = Form(None),
    cedula: str = Form(None),
    cedula_especialista: str = Form(None),
    session: Session = Depends(get_session)
):
    a = session.exec(select(Ajustes)).first()
    if not a: a = Ajustes(); session.add(a)
    a.clinica_nombre = clinica_nombre or a.clinica_nombre
    a.clinica_direccion = clinica_direccion or a.clinica_direccion
    a.clinica_telefono = clinica_telefono or a.clinica_telefono
    a.medico_nombre = medico_nombre or a.medico_nombre
    a.cedula = cedula or a.cedula
    a.cedula_especialista = cedula_especialista or a.cedula_especialista
    session.add(a); session.commit()
    return RedirectResponse("/", status_code=303)

# --------- Pacientes / Consultas ---------
@app.get("/paciente/nuevo", response_class=HTMLResponse)
def paciente_nuevo(request: Request):
    APP_OPTS = ["Diabetes Mellitus","Hipertensión Arterial","Artritis Reumatoide","Infarto Agudo del Miocardio","Hipotiroidismo","Insuficiencia renal"]
    return render("patient_form.html", request=request, paciente=None, app_opts=APP_OPTS)

@app.post("/paciente/guardar")
def paciente_guardar(
    nombre: str = Form(...),
    edad: Optional[int] = Form(None),
    sexo: Optional[str] = Form(None),
    telefono: Optional[str] = Form(None),
    alergias: Optional[str] = Form(None),
    fecha_nacimiento: Optional[str] = Form(None),
    app_sel: Optional[str] = Form(None),
    cirugias_previas: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    paciente = Patient(nombre=nombre, edad=edad, sexo=sexo, telefono=telefono, alergias=alergias)
    session.add(paciente); session.commit()
    from datetime import date as ddate
    fn = None
    try:
        fn = ddate.fromisoformat(fecha_nacimiento) if fecha_nacimiento else None
    except Exception:
        fn = None
    extras = PatientExtra(patient_id=paciente.id, fecha_nacimiento=fn, app=app_sel, cirugias_previas=cirugias_previas)
    session.add(extras); session.commit()
    return RedirectResponse(url=f"/paciente/{paciente.id}#previas", status_code=303)

@app.get("/paciente/{pid}", response_class=HTMLResponse)
def paciente_detalle(pid: int, request: Request, session: Session = Depends(get_session)):
    paciente = session.get(Patient, pid)
    if not paciente:
        return RedirectResponse("/expediente", 303)
    extra = session.exec(select(PatientExtra).where(PatientExtra.patient_id==pid)).first()
    edad_calc = paciente.edad
    if extra and extra.fecha_nacimiento:
        today = datetime.today().date()
        edad_calc = today.year - extra.fecha_nacimiento.year - ((today.month, today.day) < (extra.fecha_nacimiento.month, extra.fecha_nacimiento.day))
    app_list = (extra.app.split(",") if extra and extra.app else [])
        # Última consulta del paciente (para amarrar receta rápida)
    _ultima = session.exec(select(Consulta).where(Consulta.patient_id==pid).order_by(Consulta.fecha.desc())).first()
    ultima_consulta_id = _ultima.id if _ultima else None
    return render("patient_detail.html", request=request, p=paciente, extra=extra, edad_calc=edad_calc, app_list=app_list, ultima_consulta_id=ultima_consulta_id)

@app.post("/consulta/guardar")
def consulta_guardar(
    patient_id: int = Form(...),
    fecha: str = Form(None),
    padecimiento_actual: str = Form(None),
    exploracion_fisica: str = Form(None),
    estudios_complementarios: str = Form(None),
    diagnosticos: str = Form(None),
    plan_manejo: str = Form(None),
    ta: str = Form("120/80"),
    fc: str = Form("80 x min"),
    fr: str = Form("18 x min"),
    peso: str = Form("80 kg"),
    talla: str = Form("1.70 m"),
    notas: str = Form(None),
    session: Session = Depends(get_session)
):
    try:
        fecha_dt = datetime.fromisoformat(fecha) if fecha else datetime.now()
    except Exception:
        fecha_dt = datetime.now()
    payload = {
        "padecimiento_actual": padecimiento_actual,
        "exploracion_fisica": exploracion_fisica,
        "estudios_complementarios": estudios_complementarios,
        "diagnosticos": diagnosticos,
        "plan_manejo": plan_manejo,
        "vitales": {"TA": ta, "FC": fc, "FR": fr, "Peso": peso, "Talla": talla},
        "notas_libres": notas or ""
    }
    c = Consulta(patient_id=patient_id, fecha=fecha_dt, motivo="—", dx=diagnosticos, tratamiento=plan_manejo, notas=json.dumps(payload, ensure_ascii=False))
    session.add(c); session.commit()
    return RedirectResponse(url=f"/paciente/{patient_id}#previas", status_code=303)


@app.get("/consulta/{cid}", response_class=HTMLResponse)
def consulta_detalle(cid: int, request: Request, session: Session = Depends(get_session)):
    c = session.get(Consulta, cid)
    if not c: return RedirectResponse("/expediente", 303)
    p = session.get(Patient, c.patient_id)
    try:
        detalle = json.loads(c.notas or "{}")
    except Exception:
        detalle = {}
    
    # Receta asociada por consulta_id (preferente), fallback por día
    hist = session.exec(
        select(RecetaHistory)
        .where(RecetaHistory.consulta_id == cid)
        .order_by(RecetaHistory.fecha.desc())
    ).first()
    if not hist:
        # Fallback: recetas del mismo día para compatibilidad histórica
        dia_ini = c.fecha.replace(hour=0, minute=0, second=0, microsecond=0)
        dia_fin = c.fecha.replace(hour=23, minute=59, second=59, microsecond=999999)
        hist = session.exec(
            select(RecetaHistory)
            .where(
                (RecetaHistory.patient_id == c.patient_id) &
                (RecetaHistory.fecha >= dia_ini) &
                (RecetaHistory.fecha <= dia_fin)
            )
            .order_by(RecetaHistory.fecha.desc())
        ).first()
    # if fallback found a recipe with no consulta_id, link it now
    if hist and getattr(hist, 'consulta_id', None) in (None, 0):
        try:
            hist.consulta_id = cid
            session.add(hist)
            session.commit()
        except Exception:
            session.rollback()
            pass
    if hist:
        try:
            items = json.loads(hist.items_json or "[]")
        except Exception:
            items = []
        # --- Tratamiento simplificado (medicamento / dosis / indicaciones) ---
        tratamiento = []
        for r in items:
            nombre = (r.get("nombre") or "").strip()
            indic  = (r.get("indicacion") or "").strip()
            dosis, forma = "", ""
            if "—" in indic:
                _parts = indic.split("—", 1)
                dosis = _parts[0].strip(); forma = _parts[1].strip()
            else:
                _ls = [x.strip() for x in indic.split("\\n") if x.strip()]
                if _ls:
                    dosis = _ls[0]
                    forma = "\\n".join(_ls[1:])
            tratamiento.append({"nombre": nombre, "dosis": dosis, "indicaciones": forma})
        detalle["tratamiento"] = tratamiento
        detalle["receta"] = {
            "items": items,
            "recomendaciones": hist.recomendaciones or "",
            "proxima_cita": hist.proxima_cita or ""
        }
    return render("consulta_detail.html", request=request, c=c, p=p, detalle=detalle, receta_de_consulta=hist)

# --------- Citas ---------
@app.post("/cita/guardar")
def cita_guardar(
    patient_id: int = Form(...),
    fecha: str = Form(...),
    notas: str = Form(None),
    session: Session = Depends(get_session)
):
    try:
        dt = datetime.fromisoformat(fecha)
    except Exception:
        return JSONResponse({"ok": False, "error": "Fecha inválida"}, status_code=400)
    session.add(Appointment(patient_id=patient_id, fecha=dt, notas=notas or ""))
    session.commit()
    return JSONResponse({"ok": True})

# --------- Recetas (form, preview, imprimir, PDF calibrado) ---------
@app.get("/receta/nueva/{pid}", response_class=HTMLResponse)
def receta_form(pid: int, request: Request, session: Session = Depends(get_session)):
    paciente = session.get(Patient, pid)
    ajustes = session.exec(select(Ajustes)).first()
    consulta_id = request.query_params.get("consulta_id") if hasattr(request, "query_params") else None
    meds = session.exec(select(Medicine).order_by(Medicine.created_at.desc())).all()
    dosif = session.exec(select(Dosificacion).order_by(Dosificacion.created_at.desc())).all()
    RECOMS = [
        "Usar Cabestrillo 24hr",
        "Faja con soporte lumbar 24hr",
        "No hacer ejercicio o cargar cosas pesadas",
        "Compresas tibias 60min cada 8hr por 3 a 5 días mínimo",
        "Curaciones cada 24hr con agua y jabón",
        "Rodillera con estabilizador de rótula 24hrs",
        "Dormir de lado posición fetal con una almohada entre las piernas",
    ]
    return render("receta_form.html", request=request, p=paciente, ajustes=ajustes, hoy=datetime.now(), consulta_id=consulta_id,
                  med_sugeridos=meds, dosif_sugeridas=dosif, recoms=RECOMS)

@app.post("/receta/preview", response_class=HTMLResponse)
def receta_preview(
    patient_id: int = Form(...),
    consulta_id: Optional[str] = Form(None),
    fecha: str = Form(...),
    items_json: str = Form(...),
    recomendaciones: str = Form(None),
    proxima_cita: str = Form(None),
    session: Session = Depends(get_session)
):
    paciente = session.get(Patient, patient_id)
    ajustes = session.exec(select(Ajustes)).first()
    items = []
    import json as _json
    try:
        raw = _json.loads(items_json) if items_json else []
        for r in raw:
            if r.get("nombre") and r.get("indicacion"):
                # dicts para tojson
                items.append({"nombre": r["nombre"], "indicacion": r["indicacion"]})
    except Exception:
        items = []
    return render("receta_preview.html", p=paciente, ajustes=ajustes, fecha=fecha, items=items, consulta_id=consulta_id,
                  recomendaciones=recomendaciones, proxima_cita=proxima_cita)

@app.post("/receta/imprimir", response_class=HTMLResponse)
def receta_imprimir(
    patient_id: int = Form(...),
    fecha: str = Form(...),
    items_json: str = Form(...),
    recomendaciones: str = Form(None),
    proxima_cita: str = Form(None),
    session: Session = Depends(get_session)
):
    paciente = session.get(Patient, patient_id)
    ajustes = session.exec(select(Ajustes)).first()
    items = []
    import json as _json
    try:
        raw = _json.loads(items_json) if items_json else []
        for r in raw:
            if r.get("nombre") and r.get("indicacion"):
                items.append(RecetaItem(nombre=r["nombre"], indicacion=r["indicacion"]))
                # aprender catálogos
                nombre = r["nombre"].strip()
                if nombre and not session.exec(select(Medicine).where(Medicine.nombre==nombre)).first():
                    session.add(Medicine(nombre=nombre))
                indic = r["indicacion"].strip()
                for linea in [x.strip() for x in indic.split('\n') if x.strip()]:
                    if not session.exec(select(Dosificacion).where(Dosificacion.texto==linea)).first():
                        session.add(Dosificacion(texto=linea))
        session.commit()
    except Exception:
        items = []
    return render("receta_print.html", p=paciente, ajustes=ajustes, fecha=fecha, items=items,
                  recomendaciones=recomendaciones, proxima_cita=proxima_cita)


# PDF calibrado (según ajuste final aceptado: Y=26.7 cm)
from reportlab.pdfgen import canvas as _cv
from reportlab.lib.pagesizes import letter as _letter
from reportlab.lib.units import cm as _cm_unit

@app.post("/receta/pdf")
def receta_pdf(
    patient_id: int = Form(...),
    consulta_id: Optional[int] = Form(None),
    fecha: str = Form(...),
    items_json: str = Form(...),
    recomendaciones: Optional[str] = Form(None),
    proxima_cita: Optional[str] = Form(None),
    session: Session = Depends(get_session),
):
    from io import BytesIO
    import json as _json
    buf = BytesIO()
    c = _cv.Canvas(buf, pagesize=_letter)
    width, height = _letter

    def _cm(n: float) -> float:
        return n * _cm_unit

    c.setFont("Helvetica", 9)

    # Desplazar todo 1 renglón hacia abajo
    y_shift = 12

    # Datos paciente
    p = session.get(Patient, patient_id)
    nombre_paciente = p.nombre if p else "Paciente"

    # Coordenadas calibradas
    x_nombre = _cm(2.5)
    x_fecha = _cm(11.5)
    y_base = _cm(26.7)

    c.drawString(x_nombre, y_base - y_shift, nombre_paciente)
    c.drawString(x_fecha, y_base - y_shift, fecha)

    # Items
    try:
        items = _json.loads(items_json) if items_json else []
    except Exception:
        items = []
    # AUTOGUARDAR_CATALOGO_PDF
    try:
        for it in (items or []):
            nombre = (it.get("nombre") or "").strip()
            indic = (it.get("indicacion") or "").strip()
            if nombre and not session.exec(select(Medicine).where(Medicine.nombre==nombre)).first():
                session.add(Medicine(nombre=nombre))
            if indic:
                for linea in [x.strip() for x in indic.split('\n') if x.strip()]:
                    if not session.exec(select(Dosificacion).where(Dosificacion.texto==linea)).first():
                        session.add(Dosificacion(texto=linea))
        session.commit()
    except Exception:
        pass


    x_left = _cm(1.5)
    sangria = _cm(1)
    y = (y_base - y_shift) - _cm(0.8) - _cm(0.5)  # 2 renglones + extra y 1 renglón abajo
    for it in items:
        nombre = (it.get("nombre") or "").strip()
        indic = (it.get("indicacion") or "").strip()
        dosis = ""
        forma = ""
        if indic:
            lines = [l.strip() for l in indic.split("\n") if l.strip()] if isinstance(indic, str) else []
            if lines:
                dosis = lines[0]
                forma = "\n".join(lines[1:])
        linea1 = nombre if nombre else ""
        if dosis:
            linea1 = f"{linea1} — {dosis}" if linea1 else dosis
        c.drawString(x_left, y, linea1); y -= 12
        if forma:
            for sub in forma.split("\n"):
                c.drawString(x_left + sangria, y, sub); y -= 12
        y -= 14  # espacio entre medicamentos

    # 3 renglones antes de recomendaciones
    y -= 27
    if (recomendaciones or "").strip():
        c.drawString(x_left, y, "Recomendaciones:"); y -= 12
        for line in (recomendaciones or "").split("\n"):
            t = line.strip()
            if not t: continue
            t_fmt = f"- {t}" if not t.startswith("-") else t
            c.drawString(x_left + sangria, y, t_fmt); y -= 12

    # 1 renglón antes de próxima cita
    y -= 9
    if (proxima_cita or "").strip():
        c.drawString(x_left, y, f"Próxima cita: {proxima_cita}"); y -= 12

    c.showPage(); c.save()
    pdf = buf.getvalue(); buf.close()

    # Guardar historial de receta (igual que en imprimir)
    from datetime import datetime as _dt
    try:
        fdt = _dt.fromisoformat(fecha)
    except Exception:
        fdt = _dt.now()
        # infer consulta_id if missing (link receta to consulta del mismo día)
    try:
        if not consulta_id:
            dia_ini = fdt.replace(hour=0, minute=0, second=0, microsecond=0)
            dia_fin = fdt.replace(hour=23, minute=59, second=59, microsecond=999999)
            _c = session.exec(
                select(Consulta)
                .where((Consulta.patient_id==patient_id) & (Consulta.fecha>=dia_ini) & (Consulta.fecha<=dia_fin))
                .order_by(Consulta.fecha.desc())
            ).first()
            if _c:
                consulta_id = _c.id
    except Exception:
        pass

    hist = RecetaHistory(patient_id=patient_id, consulta_id=consulta_id, fecha=fdt,
                         items_json=items_json, recomendaciones=recomendaciones, proxima_cita=proxima_cita)
    session.add(hist); session.commit()

    headers = {"Content-Disposition": 'inline; filename="receta_calibrada.pdf"'}
    return Response(content=pdf, media_type="application/pdf", headers=headers)