
(function(){
  // =========================
  // Utilidades
  // =========================
  function pad(n){ return String(n).padStart(2,'0'); }

  // Convierte entradas locales a ISO "YYYY-MM-DDTHH:MM"
  function normalizeFechaToISO(raw){
    if (!raw) return raw;
    if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(raw)) return raw; // ya ISO

    // dd/mm/yyyy, hh:mm a.m./p.m.
    var m = raw.match(/(\d{2})\/(\d{2})\/(\d{4}).*?(\d{2}):(\d{2}).*?(a\.m\.|p\.m\.)/i);
    if (m){
      var dd = +m[1], mm = +m[2], yyyy = +m[3];
      var hh = +m[4], mi = +m[5];
      var ampm = m[6].toLowerCase();
      if (ampm.includes('p.m.') && hh < 12) hh += 12;
      if (ampm.includes('a.m.') && hh === 12) hh = 0;
      return `${yyyy}-${pad(mm)}-${pad(dd)}T${pad(hh)}:${pad(mi)}`;
    }

    // dd/mm/yyyy HH:MM
    var m2 = raw.match(/(\d{2})\/(\d{2})\/(\d{4}).*?(\d{2}):(\d{2})/);
    if (m2){
      var dd2 = +m2[1], mm2 = +m2[2], yyyy2 = +m2[3];
      var hh2 = +m2[4], mi2 = +m2[5];
      return `${yyyy2}-${pad(mm2)}-${pad(dd2)}T${pad(hh2)}:${pad(mi2)}`;
    }
    return raw; // fallback
  }

  // =========================
  // Receta: agregar/eliminar medicamento
  // =========================
  function addMedicine(prefill){
    prefill = prefill || {nombre:"", indicacion:""};
    var tbody = document.querySelector("#meds-body");
    if (!tbody){
      var items = document.getElementById("items");
      if (!items) return;
      var table = document.createElement("table");
      table.className = "table";
      var thead = document.createElement("thead");
      thead.innerHTML = "<tr><th>Medicamento</th><th>Indicaciones</th><th></th></tr>";
      tbody = document.createElement("tbody");
      tbody.id = "meds-body";
      table.appendChild(thead);
      table.appendChild(tbody);
      items.appendChild(table);
    }
    var tr = document.createElement("tr");
    tr.innerHTML =
      '<td><input name="medicamentos_nombre[]" required></td>' +
      '<td><textarea name="medicamentos_indicacion[]" rows="2"></textarea></td>' +
      '<td><button type="button" class="button" aria-label="Eliminar">✖</button></td>';
    tbody.appendChild(tr);
    var inputs = tr.querySelectorAll("input,textarea");
    inputs[0].value = prefill.nombre || "";
    inputs[1].value = prefill.indicacion || "";
    tr.querySelector("button").addEventListener("click", function(){ tr.remove(); });
  }
  var addBtn = document.getElementById("btn-add-medicine");
  if (addBtn) addBtn.addEventListener("click", function(){ addMedicine(); });

  // =========================

  // Evita doble POST al mismo click
let _savingCita = false;
// Próxima cita: guardar con feedback y refresco de calendario (con fix 422)
// =========================
async function guardarCita(){
  const btn  = document.getElementById("btn-guardar-cita");
  const form = document.getElementById("form-cita");
  const msg  = document.getElementById("cita_msg");
  if (!form){ console.warn("No existe #form-cita"); return; }
  // Evita dobles envíos si ya está en curso o el botón está deshabilitado
if (_savingCita || (btn && btn.disabled)) return;
_savingCita = true;


  if (btn){ btn.disabled = true; var prev = btn.textContent; btn.textContent = "Guardando…"; }
  if (msg){ msg.textContent = ""; }

  // Construir FormData
  const fd = new FormData(form);

  // Normaliza fecha -> ISO YYYY-MM-DDTHH:MM
  const fechaEl = form.querySelector('[name="fecha"]');
  if (fechaEl){
    const iso = normalizeFechaToISO(fechaEl.value);
    if (iso) fd.set("fecha", iso);
  }

  // 🔧 FIX 422: si consulta_id está vacío, NO lo envíes
  const cid = fd.get("consulta_id");
  if (cid == null || String(cid).trim() === "") {
    fd.delete("consulta_id");
  }

  // Asegura patient_id como entero (texto)
  const pid = fd.get("patient_id");
  if (pid != null) fd.set("patient_id", String(parseInt(pid, 10)));

  try{
    const r = await fetch("/api/appointments", { method:"POST", body: fd });
    // Log de respuesta cruda si no es OK (para depurar)
    if (!r.ok) {
      const txt = await r.text().catch(()=> "");
      console.error("Guardar cita: HTTP", r.status, txt);
    }
    const data = await r.json().catch(()=> ({}));

    if (data && data.ok){
      if (btn) btn.textContent = "✅ Guardada";
      try {
        var inputFecha = document.getElementById("cita_fecha");
        var inputNota  = document.getElementById("cita_nota");
        var hiddenPC   = document.getElementById("proxima_cita");
        if (hiddenPC && inputFecha){
          var raw = inputFecha.value;
          var d = new Date(raw);
          var pad = function(n){ return String(n).padStart(2,"0"); };
          var human = isNaN(d.getTime()) ? raw : (d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate())+" "+pad(d.getHours())+":"+pad(d.getMinutes()));
          var nota = inputNota ? inputNota.value.trim() : "";
          hiddenPC.value = human + (nota ? (" — " + nota) : "");
        }
      } catch(e) { /* no-op */ }

      if (msg) msg.textContent = "Cita guardada correctamente.";
      // Solo refrescar si la página tiene calendario visible
if (window.cargarCalendario && document.getElementById("calendar-list")) {
  await window.cargarCalendario();
}
    } else {
      if (btn) btn.textContent = "⚠️ Error";
      if (msg) msg.textContent = (data && (data.error || data.detail))
        ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.error || data.detail))
        : "No se pudo guardar la cita.";
    }
  } catch(e){
    if (btn) btn.textContent = "⚠️ Error";
    if (msg) msg.textContent = "Error de red o servidor.";
    console.error("Guardar cita: excepción", e);
  } finally {
  if (btn) setTimeout(()=>{ btn.textContent = prev; btn.disabled = false; }, 1500);
  _savingCita = false; // <-- libera bloqueo
}
}

// Exponer al global y listener por id (si quitas el onclick)
window.guardarCita = guardarCita;

  // Quitar cualquier onclick inline y asegurar que sólo haya un listener
(function(){
  const btn = document.getElementById("btn-guardar-cita");
  if (!btn) return;

  // Si la plantilla tiene onclick="guardarCita()", lo anulamos en runtime
  try { btn.removeAttribute("onclick"); btn.onclick = null; } catch(e){}

  // Enlazar una sola vez
  if (!btn.dataset.bound) {
    btn.addEventListener("click", guardarCita);
    btn.dataset.bound = "1";
  }
})();

// Evitar doble registro del listener y neutralizar cualquier onclick inline
(function(){
  const btn = document.getElementById("btn-guardar-cita");
  if (!btn) return;

  // 1) Si la plantilla tiene onclick, lo desactivamos
  try {
    btn.removeAttribute("onclick");
    btn.onclick = null;
  } catch (_) {}

  // 2) Asegurarnos de no enlazar dos veces
  if (!btn.dataset.bound) {
    btn.addEventListener("click", guardarCita);
    btn.dataset.bound = "1";
  }
})();



  // =========================
  // Calendario
  // =========================
  async function cargarCalendario(dayISO){
    var input = document.getElementById("calendar-day");
    var list  = document.getElementById("calendar-list");
if (!input && !list) return; // <-- si no hay UI, no pedimos al backend
    var day = dayISO || (input ? input.value : null);
    if (!day){
      var d = new Date(); day = d.toISOString().slice(0,10);
      if (input) input.value = day;
    }
    try{
      var r = await fetch("/api/calendar?day="+encodeURIComponent(day));
      var data = await r.json();
      list.innerHTML = "";
      (data.items || []).forEach(function(ap){
        var li = document.createElement("li");
        li.textContent = ap.hora + " — " + ap.paciente + (ap.nota ? " · " + ap.nota : "");
        list.appendChild(li);
      });
    } catch(e){ /* no-op */ }
  }
  window.cargarCalendario = cargarCalendario;

  document.addEventListener("DOMContentLoaded", function(){
    if (document.getElementById("calendar-list")) cargarCalendario();
  });

  // =========================
  // Recomendaciones (checkboxes → textarea)
  // =========================
  window.toggleRecom = function(cb){
    try{
      var ta = document.getElementById("recomendaciones");
      if (!ta) return;
      var label = cb.closest("label");
      var txt = (label ? label.textContent : "").trim();
      txt = txt.replace(/^\s*[\u2610\u2611]\s*/,'').trim();

      var lines = ta.value.split("\n").map(function(l){return l.trim();}).filter(Boolean);
      var idx = lines.indexOf(txt);
      if (cb.checked){
        if (idx === -1) lines.push(txt);
      } else {
        if (idx !== -1) lines.splice(idx, 1);
      }
      ta.value = lines.join("\n");
    } catch(e){ /* no-op */ }
  };

})();
