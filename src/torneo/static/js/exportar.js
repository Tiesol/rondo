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
    // 1920 × 1080, como pide el diseño 2026. El tamaño va explícito: en pantalla la pieza está
    // achicada con transform (ajustar, abajo) y modern-screenshot la mediría con
    // getBoundingClientRect, que da el tamaño achicado. Así salía recortada y agrandada (T13.13).
    // offsetWidth y offsetHeight no cambian con el transform.
    const blob = await window.modernScreenshot.domToBlob(elemento, {
      width: elemento.offsetWidth,
      height: elemento.offsetHeight,
      scale: 1,
      type: "image/png",
    });
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

  // Las piezas miden 1920 × 1080: en pantalla se achican para entrar en el ancho.
  const ANCHO = 1920;
  const ALTO = 1080;
  function ajustar(marco) {
    const escala = marco.firstElementChild;
    const k = Math.min(1, marco.clientWidth / ANCHO);
    escala.style.transform = `scale(${k})`;
    marco.style.height = `${ALTO * k}px`;
  }
  const observador = new ResizeObserver((entradas) => entradas.forEach((e) => ajustar(e.target)));
  document.querySelectorAll(".marco-png").forEach((marco) => observador.observe(marco));

  // Nombres largos (diseño 2026): se achica la letra hasta data-min; si igual no entra, el CSS
  // lo corta con "…". Se hace con la fuente ya cargada, antes de exportar.
  function achicar(texto) {
    const minimo = parseFloat(texto.dataset.min || "0");
    let tamano = parseFloat(getComputedStyle(texto).fontSize);
    while (texto.scrollWidth > texto.clientWidth && tamano > minimo) {
      tamano -= 1;
      texto.style.fontSize = `${tamano}px`;
    }
  }
  document.fonts.ready.then(() => document.querySelectorAll(".pieza .ajustar").forEach(achicar));
})();
