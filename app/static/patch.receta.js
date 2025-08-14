(function(){
  function qs(sel){ return document.querySelector(sel); }
  async function guardarRecetaClick(ev){
    ev.preventDefault();
    var btn = ev.currentTarget;
    var form = qs("form.form");
    if (!form){ alert("No encontré el formulario de receta"); return; }

    try{ if (window.syncItems) window.syncItems(); }catch(e){}

    var fd = new FormData(form);
    var fecha = (qs("#rx_fecha") && qs("#rx_fecha").value) || "";
    if (fecha) fd.set("fecha", fecha);

    var cid = (fd.get("consulta_id") || "").trim();
    if (!cid) fd.delete("consulta_id");

    try{
      var items = JSON.parse(fd.get("items_json") || "[]");
      if (!Array.isArray(items) || items.length === 0){
        alert("Agrega al menos un medicamento e indicaciones.");
        return;
      }
    }catch(e){
      alert("No pude leer los medicamentos.");
      return;
    }

    btn.disabled = true;
    var original = btn.textContent;
    btn.textContent = "Guardando…";

    try{
      var res = await fetch("/receta/guardar", { method:"POST", body: fd });
      var data = await res.json().catch(()=>({}));
      if (!res.ok || !data.ok){
        throw new Error((data && data.error) || ("HTTP " + res.status));
      }
      btn.textContent = "✅ Receta guardada";
      var linkP = qs("#link-consulta-previa");
      if (linkP && data.consulta_id){
        linkP.classList.remove("hidden");
        linkP.innerHTML = 'Se guardó la receta. <a href="/consulta/' + data.consulta_id + '">Ver en consulta previa →</a>';
      }
    }catch(err){
      console.error("Guardar receta error:", err);
      alert("No pude guardar la receta: " + err.message);
      btn.textContent = original;
    }finally{
      btn.disabled = false;
    }
  }
  function ready(fn){ if (document.readyState !== "loading") fn(); else document.addEventListener("DOMContentLoaded", fn); }
  ready(function(){
    var btn = document.getElementById("btn-guardar-receta");
    if (btn){
      btn.addEventListener("click", guardarRecetaClick);
      if (!btn.classList.contains("primary")) btn.classList.add("primary");
    }
    var btnCita = document.getElementById("btn-guardar-cita");
    if (btnCita && !btnCita.classList.contains("primary")) btnCita.classList.add("primary");
  });
})();