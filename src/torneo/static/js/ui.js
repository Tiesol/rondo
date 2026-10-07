// Interacciones chicas de la interfaz (docs/DISENO.md): hojas inferiores y avisos flotantes.

// Hojas inferiores: <dialog class="hoja">. Se abren con data-abrir-hoja="<id>" y se cierran
// con data-cerrar-hoja, con Esc (lo da el navegador) o tocando el fondo.
document.addEventListener("click", (evento) => {
  const abrir = evento.target.closest("[data-abrir-hoja]");
  if (abrir) {
    document.getElementById(abrir.dataset.abrirHoja)?.showModal();
    return;
  }
  const cerrar = evento.target.closest("[data-cerrar-hoja]");
  if (cerrar) {
    cerrar.closest("dialog")?.close();
    return;
  }
  const hoja = evento.target;
  if (hoja instanceof HTMLDialogElement && hoja.classList.contains("hoja")) {
    const caja = hoja.getBoundingClientRect();
    const afuera =
      evento.clientY < caja.top || evento.clientY > caja.bottom ||
      evento.clientX < caja.left || evento.clientX > caja.right;
    if (afuera) hoja.close();
  }
});

// Avisos flotantes: se van solos.
function ocultarAvisos(raiz) {
  raiz.querySelectorAll("[data-aviso]").forEach((aviso) => {
    setTimeout(() => aviso.remove(), 5000);
  });
}
ocultarAvisos(document);
document.addEventListener("htmx:load", (evento) => ocultarAvisos(evento.target));
