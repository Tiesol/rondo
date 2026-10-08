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

// Avisos flotantes: los de éxito se van solos; los que piden atención (data-queda), al cerrarlos.
function ocultarAvisos(raiz) {
  raiz.querySelectorAll("[data-aviso]:not([data-queda])").forEach((aviso) => {
    setTimeout(() => aviso.remove(), 5000);
  });
}
document.addEventListener("click", (evento) => {
  evento.target.closest("[data-cerrar-aviso]")?.closest("[data-aviso]")?.remove();
});
ocultarAvisos(document);
document.addEventListener("htmx:load", (evento) => ocultarAvisos(evento.target));

// Contadores: los botones − y + junto a un campo numérico (data-paso="-1" o "1").
document.addEventListener("click", (evento) => {
  const boton = evento.target.closest("[data-paso]");
  const campo = boton?.parentElement.querySelector("input[type=number]");
  if (!campo) return;
  if (campo.value === "") campo.value = campo.min || 0;
  else if (boton.dataset.paso === "1") campo.stepUp();
  else campo.stepDown();
  campo.dispatchEvent(new Event("change", { bubbles: true }));
});

// Selector de categoría: la elegida queda a la vista aunque la lista sea larga.
function mostrarCategoriaActual(raiz) {
  raiz.querySelector?.(".categorias [aria-current]")?.scrollIntoView({ block: "nearest", inline: "center" });
}
mostrarCategoriaActual(document);
document.addEventListener("htmx:load", (evento) => mostrarCategoriaActual(evento.target));

// Vista previa de los colores de la escuela: el campo con data-token pinta la pantalla al
// instante. El texto sobre el acento se recalcula en el servidor al guardar.
document.addEventListener("input", (evento) => {
  const token = evento.target.dataset?.token;
  if (token) document.documentElement.style.setProperty(token, evento.target.value);
});

// Instalación en el celular: el service worker no guarda datos (la app funciona con conexión).
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
