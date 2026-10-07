// Convierte un elemento en PNG y lo comparte (celular) o lo descarga (PC).
// Usa modern-screenshot (vendor/modern-screenshot.js), que se expone como window.modernScreenshot.
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

  async function exportarPng(elemento, nombre, avisar) {
    avisar("Generando la imagen…");
    const blob = await window.modernScreenshot.domToBlob(elemento, {
      scale: 2,
      backgroundColor: "#ffffff",
      type: "image/png",
    });
    const archivo = new File([blob], nombre, { type: "image/png" });
    if (navigator.canShare && navigator.canShare({ files: [archivo] })) {
      try {
        await navigator.share({ files: [archivo], title: nombre });
        avisar("Listo.");
      } catch (error) {
        // El usuario cerró el menú de compartir: no es un error.
        avisar(error.name === "AbortError" ? "" : "No se pudo compartir; se descarga.");
        if (error.name !== "AbortError") descargar(blob, nombre);
      }
    } else {
      descargar(blob, nombre);
      avisar("Imagen descargada.");
    }
  }

  document.addEventListener("click", (evento) => {
    const boton = evento.target.closest("[data-exportar]");
    if (!boton) return;
    const elemento = document.getElementById(boton.dataset.exportar);
    const estado = document.getElementById(boton.dataset.estado);
    const avisar = (texto) => { if (estado) estado.textContent = texto; };
    boton.disabled = true;
    exportarPng(elemento, boton.dataset.nombre || "calendario.png", avisar)
      .catch(() => avisar("No se pudo generar la imagen."))
      .finally(() => { boton.disabled = false; });
  });
})();
