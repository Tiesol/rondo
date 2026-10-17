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

// Un selector que se guarda solo al cambiarlo (data-enviar-al-cambiar), como el mejor jugador.
document.addEventListener("change", (evento) => {
  if (evento.target.matches("[data-enviar-al-cambiar]")) evento.target.form?.requestSubmit();
});

// T13.40: un botón con data-calculando (propuestas, programar) se bloquea y dice "Calculando…"
// mientras espera, y el mismo formulario no se manda dos veces: se tocaba de nuevo, y el
// celular reenviaba al volver de minimizar la app. Va en la captura, antes que HTMX.
document.addEventListener(
  "submit",
  (evento) => {
    const formulario = evento.target;
    if (formulario.dataset.enviando) {
      evento.preventDefault();
      evento.stopImmediatePropagation();
      return;
    }
    const boton = evento.submitter;
    if (!boton?.dataset.calculando) return;
    formulario.dataset.enviando = "1";
    // Después de que el navegador o HTMX tomaron los datos: desactivado, el botón no mandaría
    // su name y value (el "modo" de Programar).
    setTimeout(() => {
      formulario.querySelectorAll("button:not([disabled])").forEach((b) => {
        b.disabled = true;
        b.dataset.bloqueado = "1";
      });
      boton.dataset.texto = boton.textContent;
      boton.textContent = boton.dataset.calculando;
    });
  },
  true,
);

function liberar(formulario) {
  delete formulario.dataset.enviando;
  formulario.querySelectorAll("button[data-bloqueado]").forEach((b) => {
    b.disabled = false;
    delete b.dataset.bloqueado;
  });
  // Aparte: en Programar, hx-disabled-elt ya los había desactivado (y HTMX los reactiva).
  formulario.querySelectorAll("button[data-texto]").forEach((b) => {
    b.textContent = b.dataset.texto;
    delete b.dataset.texto;
  });
}
// Con HTMX el formulario sigue en la pantalla (Programar): vuelve a estar listo al terminar.
document.addEventListener("htmx:afterRequest", (evento) => {
  const formulario = evento.detail.elt.closest?.("form");
  if (formulario?.dataset.enviando) setTimeout(() => liberar(formulario));
});
// Al volver atrás, el navegador puede mostrar la página como quedó, con el botón bloqueado.
window.addEventListener("pageshow", (evento) => {
  if (evento.persisted) document.querySelectorAll("form[data-enviando]").forEach(liberar);
});
