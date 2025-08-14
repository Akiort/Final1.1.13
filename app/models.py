
from datetime import datetime, date
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class PatientBase(SQLModel):
    nombre: str
    edad: Optional[int] = None
    sexo: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    alergias: Optional[str] = None

class Patient(PatientBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    consultas: List["Consulta"] = Relationship(back_populates="patient")

class PatientExtra(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    fecha_nacimiento: Optional[date] = None
    app: Optional[str] = None
    cirugias_previas: Optional[str] = None

class ConsultaBase(SQLModel):
    fecha: datetime = Field(default_factory=datetime.utcnow)
    motivo: Optional[str] = None
    dx: Optional[str] = None
    tratamiento: Optional[str] = None
    notas: Optional[str] = None

class Consulta(ConsultaBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    patient: "Patient" = Relationship(back_populates="consultas")

class RecetaItem(SQLModel):
    nombre: str
    indicacion: str

class Medicine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Dosificacion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    texto: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Appointment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    fecha: datetime
    notas: Optional[str] = None

class Ajustes(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    clinica_nombre: Optional[str] = None
    clinica_direccion: Optional[str] = None
    clinica_telefono: Optional[str] = None
    medico_nombre: Optional[str] = None
    cedula: Optional[str] = None
    cedula_especialista: Optional[str] = None


class RecetaHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    consulta_id: Optional[int] = Field(default=None, foreign_key="consulta.id")
    fecha: datetime = Field(default_factory=datetime.utcnow)
    items_json: str  # JSON con [{'nombre','indicacion'}]
    recomendaciones: Optional[str] = None
    proxima_cita: Optional[str] = None
