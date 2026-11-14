/**
 * EmoSense – Detector en vivo (cámara y foto).
 *
 * Usa las funciones comunes de camara.js (window.EmoSense.camara):
 * - Cámara: ciclo de análisis contra /api/analizar/.
 * - Foto: valida tipo y tamaño en el navegador, la envía a /api/foto/ y
 *   dibuja los recuadros sobre la vista previa.
 *
 * Los datos de las emociones llegan desde Django con json_script
 * (#datos-emociones).
 */
(function () {
  "use strict";

  var raiz = document.getElementById("detector");
  if (!raiz || !window.EmoSense || !window.EmoSense.camara) return;

  var C = window.EmoSense.camara;
  var EMOCIONES = JSON.parse(document.getElementById("datos-emociones").textContent);
  var URL_ANALIZAR = raiz.dataset.urlAnalizar;
  var URL_FOTO = raiz.dataset.urlFoto;
  var TAMANO_MAX = 2 * 1024 * 1024;
  var TIPOS_FOTO = ["image/jpeg", "image/png", "image/webp"];

  function $(id) {
    return document.getElementById(id);
  }

  var el = {
    pestanas: Array.prototype.slice.call(raiz.querySelectorAll('[role="tab"]')),
    video: $("video"),
    lienzoCamara: $("lienzo-camara"),
    vacioCamara: $("vacio-camara"),
    botonIniciar: $("boton-iniciar"),
    botonDetener: $("boton-detener"),
    estadoCamara: $("estado-camara"),
    inputFoto: $("input-foto"),
    zonaSubida: $("zona-subida"),
    escenaFoto: $("escena-foto"),
    fotoPrevia: $("foto-previa"),
    lienzoFoto: $("lienzo-foto"),
    estadoFoto: $("estado-foto"),
    emoji: $("resultado-emoji"),
    nombre: $("resultado-nombre"),
    extra: $("resultado-extra"),
    descripcion: $("resultado-descripcion"),
    gif: $("resultado-gif"),
    puntajes: Array.prototype.slice.call(raiz.querySelectorAll("[data-puntaje]")),
    rostros: $("dato-rostros"),
    tiempo: $("dato-tiempo"),
    recomendaciones: $("lista-recomendaciones"),
    consejo: $("consejo-atencion"),
    consejoEtiqueta: $("consejo-etiqueta"),
    consejoTexto: $("consejo-texto"),
    consejoSituacion: $("consejo-situacion"),
    consejoSituacionTexto: $("consejo-situacion-texto"),
    guia: $("guia"),
  };

  var avisos = C.crearAvisos($("alertas"));
  var medidor = null; // se crea después de la cámara
  var ultimaEmocion;           // para animar solo cuando cambia
  var ultimoResultadoFoto = null;
  var urlPrevia = null;

  /** Cambia el texto solo si es distinto (evita anuncios repetidos). */
  function ponerTexto(nodo, texto) {
    if (nodo.textContent !== texto) nodo.textContent = texto;
  }

  // --- Panel de resultados -------------------------------------------------

  /** Cambia el emoji (con rebote) y el GIF cuando cambia la emoción. */
  function cambiarEmocion(clave) {
    if (clave === ultimaEmocion) return;
    ultimaEmocion = clave;
    var info = clave ? EMOCIONES[clave] : null;

    el.emoji.textContent = info ? info.emoji : "🔍";
    el.emoji.classList.remove("rebote");
    void el.emoji.offsetWidth; // reinicia la animación
    el.emoji.classList.add("rebote");

    if (info && info.gif) {
      el.gif.src = info.gif;
      el.gif.alt = "Ejemplo animado de " + info.nombre;
      el.gif.hidden = false;
    } else {
      el.gif.hidden = true;
      el.gif.removeAttribute("src");
    }
  }

  /** Actualiza las 7 barras con la lista [{emocion, puntuacion}]. */
  function pintarPuntajes(puntuaciones) {
    var mapa = {};
    puntuaciones.forEach(function (item) {
      mapa[item.emocion] = item.puntuacion;
    });
    var mejor = puntuaciones.length ? puntuaciones[0].emocion : null;
    el.puntajes.forEach(function (fila) {
      var clave = fila.dataset.puntaje;
      var porcentaje = Math.round((mapa[clave] || 0) * 100);
      fila.querySelector(".puntaje__relleno").style.width = porcentaje + "%";
      ponerTexto(fila.querySelector(".puntaje__valor"), porcentaje + "%");
      fila.classList.toggle("es-principal", clave === mejor);
    });
  }

  /** Reemplaza la lista de recomendaciones solo si cambió. */
  function pintarRecomendaciones(lista) {
    var firma = lista.join("|");
    if (el.recomendaciones.dataset.firma === firma) return;
    el.recomendaciones.dataset.firma = firma;
    el.recomendaciones.replaceChildren.apply(
      el.recomendaciones,
      lista.map(function (texto) {
        var item = document.createElement("li");
        item.textContent = texto;
        return item;
      })
    );
  }

  /**
   * Tarjeta "Consejo de atención" según el rol de la expresión:
   * - propia (alegría, neutral): cómo usarla frente al cliente;
   * - cliente: cómo responder, con una situación de ejemplo.
   */
  function pintarConsejo(clave) {
    var info = clave ? EMOCIONES[clave] : null;
    el.consejo.hidden = !info;
    if (!info) return;
    var esCliente = info.rol === "cliente";
    el.consejo.style.setProperty("--emo", info.color);
    ponerTexto(el.consejoEtiqueta, esCliente ? "Si un cliente muestra esta expresión" : "Tu expresión ante el cliente");
    ponerTexto(el.consejoTexto, info.consejo_atencion);
    el.consejoSituacion.hidden = !esCliente;
    ponerTexto(el.consejoSituacionTexto, esCliente ? info.situacion : "");
  }

  /** Muestra en el panel el resultado de la API (rostro principal). */
  function mostrarResultado(datos) {
    var principal = datos.principal;
    ponerTexto(el.rostros, String(datos.cantidad_rostros));
    ponerTexto(el.tiempo, Math.round(datos.tiempo_ms) + " ms");
    pintarRecomendaciones((datos.calidad && datos.calidad.recomendaciones) || []);

    if (!principal) {
      cambiarEmocion(null);
      ponerTexto(el.nombre, "Sin rostro detectado");
      ponerTexto(el.extra, "");
      ponerTexto(el.descripcion, "Colócate de frente, con buena luz y a una distancia cómoda.");
      pintarPuntajes([]);
      pintarConsejo(null);
      return;
    }

    var info = EMOCIONES[principal.emocion];
    cambiarEmocion(principal.emocion);
    ponerTexto(el.nombre, info.nombre);
    ponerTexto(el.extra, datos.cantidad_rostros > 1 ? "(rostro más grande)" : "");
    ponerTexto(el.descripcion, info.descripcion);
    pintarPuntajes(principal.puntuaciones || []);
    pintarConsejo(principal.emocion);
  }

  // --- Cámara --------------------------------------------------------------

  var camara = C.crearCamara({
    video: el.video,
    url: URL_ANALIZAR,
    avisos: avisos,
    alResultado: function (datos) {
      mostrarResultado(datos);
      C.dibujarRostros(el.lienzoCamara, datos, true, EMOCIONES);
      if (medidor) medidor.registrar(datos);
    },
    alCambiarEstado: function (estado) {
      el.botonIniciar.disabled = estado !== "detenida";
      el.botonDetener.disabled = estado !== "activa";
      el.estadoCamara.hidden = estado !== "activa";
      el.vacioCamara.hidden = estado === "activa";
      if (estado === "detenida") {
        C.limpiarLienzo(el.lienzoCamara);
        if (medidor) medidor.cancelar("se detuvo la cámara");
      }
    },
  });

  // --- Medidor de amabilidad (medidor.js) ----------------------------------

  if (window.EmoSense.crearMedidor) {
    medidor = window.EmoSense.crearMedidor({ camara: camara, avisos: avisos });
  }

  // --- Guía: se abre sola con /detector/#guia ------------------------------

  function abrirGuiaSiCorresponde() {
    if (el.guia && window.location.hash === "#guia") {
      el.guia.open = true;
      el.guia.scrollIntoView({ block: "start" });
    }
  }
  window.addEventListener("hashchange", abrirGuiaSiCorresponde);
  // Si el ancla ya era #guia, el enlace no dispara hashchange: se abre al hacer clic.
  Array.prototype.forEach.call(document.querySelectorAll('a[href$="#guia"]'), function (enlace) {
    enlace.addEventListener("click", function () {
      setTimeout(abrirGuiaSiCorresponde, 0);
    });
  });
  abrirGuiaSiCorresponde();

  // --- Foto ----------------------------------------------------------------

  function cargarPrevia(url) {
    return new Promise(function (resolver) {
      el.fotoPrevia.onload = resolver;
      el.fotoPrevia.onerror = resolver; // si falla la vista previa, igual se analiza
      el.fotoPrevia.src = url;
    });
  }

  /** Valida la foto en el navegador, la envía y dibuja los resultados. */
  function analizarFoto(archivo) {
    if (!archivo) return;
    avisos.quitar("foto");
    avisos.quitar("api");

    if (TIPOS_FOTO.indexOf(archivo.type) === -1) {
      avisos.avisar("error", "Formato no permitido. Elige una imagen JPG, PNG o WebP.", "foto");
      return;
    }
    if (archivo.size > TAMANO_MAX) {
      avisos.avisar(
        "error",
        "La foto pesa " + (archivo.size / (1024 * 1024)).toFixed(1) + " MB y el máximo es 2 MB.",
        "foto"
      );
      return;
    }

    if (urlPrevia) URL.revokeObjectURL(urlPrevia);
    urlPrevia = URL.createObjectURL(archivo);
    ultimoResultadoFoto = null;
    el.escenaFoto.hidden = false;
    C.limpiarLienzo(el.lienzoFoto);
    el.estadoFoto.hidden = false;

    Promise.all([C.enviarImagen(URL_FOTO, archivo, archivo.name || "foto"), cargarPrevia(urlPrevia)])
      .then(function (resultados) {
        var respuesta = resultados[0];
        if (!respuesta.ok) {
          C.manejarErrorApi(respuesta, avisos);
          return;
        }
        ultimoResultadoFoto = respuesta.datos;
        mostrarResultado(respuesta.datos);
        C.dibujarRostros(el.lienzoFoto, respuesta.datos, false, EMOCIONES);
        if (!respuesta.datos.cantidad_rostros) {
          avisos.avisar(
            "advertencia",
            "No encontramos rostros en la foto. Prueba con una imagen donde el rostro se vea de frente y bien iluminado.",
            "foto"
          );
        }
      })
      .catch(function () {
        avisos.avisar("error", "No se pudo conectar con el servidor. Inténtalo de nuevo.", "foto");
      })
      .finally(function () {
        el.estadoFoto.hidden = true;
        el.inputFoto.value = "";
      });
  }

  // --- Pestañas ------------------------------------------------------------

  function seleccionarPestana(pestana, enfocar) {
    el.pestanas.forEach(function (p) {
      var seleccionada = p === pestana;
      p.setAttribute("aria-selected", seleccionada ? "true" : "false");
      p.tabIndex = seleccionada ? 0 : -1;
      $(p.getAttribute("aria-controls")).hidden = !seleccionada;
    });
    if (enfocar) pestana.focus();
    if (pestana.dataset.modo !== "camara" && camara.estaEncendida()) camara.detener();
    if (pestana.dataset.modo === "foto" && ultimoResultadoFoto) {
      C.dibujarRostros(el.lienzoFoto, ultimoResultadoFoto, false, EMOCIONES);
    }
  }

  // --- Eventos -------------------------------------------------------------

  el.pestanas.forEach(function (pestana, indice) {
    pestana.addEventListener("click", function () {
      seleccionarPestana(pestana, false);
    });
    pestana.addEventListener("keydown", function (evento) {
      var total = el.pestanas.length;
      var destino = null;
      if (evento.key === "ArrowRight") destino = el.pestanas[(indice + 1) % total];
      if (evento.key === "ArrowLeft") destino = el.pestanas[(indice - 1 + total) % total];
      if (evento.key === "Home") destino = el.pestanas[0];
      if (evento.key === "End") destino = el.pestanas[total - 1];
      if (destino) {
        evento.preventDefault();
        seleccionarPestana(destino, true);
      }
    });
  });

  el.botonIniciar.addEventListener("click", function () {
    camara.iniciar();
  });
  el.botonDetener.addEventListener("click", function () {
    camara.detener();
  });

  el.inputFoto.addEventListener("change", function () {
    analizarFoto(el.inputFoto.files && el.inputFoto.files[0]);
  });

  // Arrastrar y soltar sobre la zona de subida.
  ["dragenter", "dragover"].forEach(function (tipo) {
    el.zonaSubida.addEventListener(tipo, function (evento) {
      evento.preventDefault();
      el.zonaSubida.classList.add("esta-arrastrando");
    });
  });
  ["dragleave", "drop"].forEach(function (tipo) {
    el.zonaSubida.addEventListener(tipo, function () {
      el.zonaSubida.classList.remove("esta-arrastrando");
    });
  });
  el.zonaSubida.addEventListener("drop", function (evento) {
    evento.preventDefault();
    var archivos = evento.dataTransfer && evento.dataTransfer.files;
    analizarFoto(archivos && archivos[0]);
  });

  el.gif.addEventListener("error", function () {
    el.gif.hidden = true;
  });

  // Redibuja los recuadros de la foto si cambia el tamaño de la escena.
  if ("ResizeObserver" in window) {
    new ResizeObserver(function () {
      if (ultimoResultadoFoto && !el.escenaFoto.hidden) {
        C.dibujarRostros(el.lienzoFoto, ultimoResultadoFoto, false, EMOCIONES);
      }
    }).observe(el.escenaFoto);
  }
})();
