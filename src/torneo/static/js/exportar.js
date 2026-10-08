// Convierte piezas del calendario en PNG y las comparte (celular) o las descarga (PC).
// Usa modern-screenshot (vendor/modern-screenshot.js), que se expone como window.modernScreenshot.
//
// - data-exportar="<id>": una pieza; data-nombre es el nombre del archivo.
// - data-exportar-todas="<selector>": todas las piezas juntas (cada una con data-nombre).
(function () {
  "use strict";

  function descargar(blob, nombre) {
    const enlace = document.createElement("a");
    enlace.href = URL.createObjectURL(blob);
    enlace.download = nombre;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    setTimeout(() => URL.revokeObjectURL(enlace.href), 10000);
  }

  async function aArchivo(elemento) {
    const blob = await window.modernScreenshot.domToBlob(elemento, { scale: 2, type: "image/png" });
    return new File([blob], elemento.dataset.nombre || "calendario.png", { type: "image/png" });
  }

  async function compartir(elementos, avisar) {
    avisar(elementos.length > 1 ? "Generando las imágenes…" : "Generando la imagen…");
    const archivos = [];
    for (const elemento of elementos) archivos.push(await aArchivo(elemento));
    if (navigator.canShare && navigator.canShare({ files: archivos })) {
      try {
        await navigator.share({ files: archivos, title: archivos[0].name });
        avisar("Listo.");
        return;
      } catch (error) {
        // El usuario cerró el menú de compartir: no es un error.
        if (error.name === "AbortError") { avisar(""); return; }
        avisar("No se pudo compartir; se descargan.");
      }
    }
    archivos.forEach((archivo) => descargar(archivo, archivo.name));
    avisar(archivos.length > 1 ? "Imágenes descargadas." : "Imagen descargada.");
  }

  document.addEventListener("click", (evento) => {
    const boton = evento.target.closest("[data-exportar], [data-exportar-todas]");
    if (!boton) return;
    const elementos = boton.dataset.exportarTodas
      ? Array.from(document.querySelectorAll(boton.dataset.exportarTodas))
      : [document.getElementById(boton.dataset.exportar)];
    const estado = document.getElementById(boton.dataset.estado);
    const avisar = (texto) => { if (estado) estado.textContent = texto; };
    boton.disabled = true;
    compartir(elementos.filter(Boolean), avisar)
      .catch(() => avisar("No se pudo generar la imagen."))
      .finally(() => { boton.disabled = false; });
  });

  // Las piezas miden 1220 × 690: en pantalla se achican para entrar en el ancho.
  function ajustar(marco) {
    const escala = marco.firstElementChild;
    const k = Math.min(1, marco.clientWidth / 1220);
    escala.style.transform = `scale(${k})`;
    marco.style.height = `${690 * k}px`;
  }
  const observador = new ResizeObserver((entradas) => entradas.forEach((e) => ajustar(e.target)));
  document.querySelectorAll(".marco-png").forEach((marco) => observador.observe(marco));
})();
