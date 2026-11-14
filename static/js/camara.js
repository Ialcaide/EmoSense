/**
 * EmoSense – Funciones comunes de cámara y análisis.
 *
 * Lo usa el detector (detector.js). Expone
 * window.EmoSense.camara con:
 *
 *   - crearCamara(opciones): controla getUserMedia y el ciclo de análisis.
 *     Captura un fotograma a 640 px, lo envía como JPEG 0.8 y solo programa
 *     el siguiente envío (500 ms) cuando llega la respuesta.
 *   - enviarImagen(url, blob, nombre): POST multipart con el token CSRF.
 *   - crearAvisos(contenedor): avisos con clave en una zona aria-live.
 *   - manejarErrorApi(respuesta, avisos): avisos para errores de la API.
 *   - dibujarRostros(lienzo, datos, espejo, emociones): recuadros y etiquetas.
 *   - limpiarLienzo(lienzo).
 *
 * Ninguna imagen se guarda: solo se envía para analizarla en memoria.
 */
(function (global) {
  "use strict";

  var ANCHO_CAPTURA = 640;
  var CALIDAD_JPEG = 0.8;
  var PAUSA_MS = 500;
  var PAUSA_REINTENTO_MS = 2000;
  var LENTO_MS = 3000;
  var LIMITE_RESPUESTA_MS = 15000;

  // --- Utilidades ----------------------------------------------------------

  /** Lee el token CSRF de la cookie 'csrftoken'. */
  function obtenerCsrf() {
    var coincidencia = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return coincidencia ? decodeURIComponent(coincidencia[1]) : "";
  }

  /**
   * Envía una imagen en el campo 'imagen' y resuelve con
   * {estado, ok, datos, duracion}. Rechaza si no hay conexión o si se
   * supera el tiempo límite (AbortError).
   */
  function enviarImagen(url, blob, nombreArchivo) {
    var formulario = new FormData();
    formulario.append("imagen", blob, nombreArchivo);
    var control = new AbortController();
    var limite = setTimeout(function () {
      control.abort();
    }, LIMITE_RESPUESTA_MS);
    var inicio = performance.now();

    return fetch(url, {
      method: "POST",
      body: formulario,
      headers: { "X-CSRFToken": obtenerCsrf() },
      credentials: "same-origin",
      signal: control.signal,
    })
      .then(function (respuesta) {
        return respuesta
          .json()
          .catch(function () {
            return null;
          })
          .then(function (datos) {
            return {
              estado: respuesta.status,
              ok: respuesta.ok && !!datos && datos.ok === true,
              datos: datos,
              duracion: performance.now() - inicio,
            };
          });
      })
      .finally(function () {
        clearTimeout(limite);
      });
  }

  // --- Avisos --------------------------------------------------------------

  /**
   * Crea un gestor de avisos sobre un contenedor con aria-live.
   * Un aviso nuevo reemplaza al anterior con la misma clave.
   */
  function crearAvisos(contenedor) {
    function buscar(clave) {
      var encontrado = null;
      Array.prototype.forEach.call(contenedor.querySelectorAll(".aviso"), function (aviso) {
        if (aviso.dataset.clave === clave) encontrado = aviso;
      });
      return encontrado;
    }

    function quitar(clave) {
      var aviso = buscar(clave);
      if (aviso) aviso.remove();
    }

    /**
     * @param {string} tipo exito | advertencia | error | info
     * @param {string} mensaje texto del aviso
     * @param {string} clave identificador del aviso
     */
    function avisar(tipo, mensaje, clave) {
      var existente = buscar(clave);
      if (existente && existente.dataset.mensaje === mensaje) return;
      if (existente) existente.remove();

      var aviso = document.createElement("div");
      aviso.className = "alerta alerta--" + tipo + " aviso";
      aviso.dataset.clave = clave;
      aviso.dataset.mensaje = mensaje;
      var texto = document.createElement("p");
      texto.textContent = mensaje;
      var cerrar = document.createElement("button");
      cerrar.type = "button";
      cerrar.className = "aviso__cerrar";
      cerrar.setAttribute("aria-label", "Cerrar aviso");
      cerrar.textContent = "×";
      cerrar.addEventListener("click", function () {
        aviso.remove();
      });
      aviso.append(texto, cerrar);
      contenedor.append(aviso);
    }

    return { avisar: avisar, quitar: quitar };
  }

  /**
   * Muestra el aviso adecuado para una respuesta con error de la API.
   * @returns {boolean} true si el error impide seguir analizando (503, 403).
   */
  function manejarErrorApi(respuesta, avisos) {
    if (respuesta.estado === 503) {
      avisos.avisar(
        "error",
        "Faltan los modelos de visión en el servidor. Ejecuta «python descargar_modelos.py» y recarga la página.",
        "api"
      );
      return true;
    }
    if (respuesta.estado === 403) {
      avisos.avisar("error", "La sesión de seguridad expiró. Recarga la página e inténtalo de nuevo.", "api");
      return true;
    }
    var mensaje =
      respuesta.datos && respuesta.datos.mensaje
        ? respuesta.datos.mensaje
        : "Error del servidor (" + respuesta.estado + "). Inténtalo de nuevo.";
    avisos.avisar("advertencia", mensaje, "api");
    return false;
  }

  function mensajeErrorCamara(error) {
    switch (error && error.name) {
      case "NotAllowedError":
      case "SecurityError":
        return "Permiso denegado: permite el acceso a la cámara desde el icono junto a la barra de direcciones y vuelve a intentarlo.";
      case "NotReadableError":
      case "TrackStartError":
        return "La cámara está ocupada por otra aplicación (Zoom, Teams u otra pestaña). Ciérrala e inténtalo de nuevo.";
      case "NotFoundError":
      case "DevicesNotFoundError":
      case "OverconstrainedError":
        return "No encontramos ninguna cámara conectada.";
      default:
        return "No se pudo iniciar la cámara. Inténtalo de nuevo.";
    }
  }

  // --- Dibujo de recuadros -------------------------------------------------

  function trazarRectangulo(ctx, x, y, w, h, radio) {
    ctx.beginPath();
    if (ctx.roundRect) {
      ctx.roundRect(x, y, w, h, radio);
    } else {
      ctx.rect(x, y, w, h);
    }
  }

  /** Ajusta el tamaño interno del canvas a su tamaño en pantalla y lo limpia. */
  function prepararLienzo(lienzo) {
    var caja = lienzo.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    lienzo.width = Math.max(1, Math.round(caja.width * dpr));
    lienzo.height = Math.max(1, Math.round(caja.height * dpr));
    var ctx = lienzo.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, caja.width, caja.height);
    return { ctx: ctx, ancho: caja.width, alto: caja.height };
  }

  function limpiarLienzo(lienzo) {
    var ctx = lienzo.getContext("2d");
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, lienzo.width, lienzo.height);
  }

  /** Dibuja un recuadro redondeado con su etiqueta "😄 Alegría 87%". */
  function dibujarRecuadro(ctx, x, y, w, h, rostro, esPrincipal, anchoLienzo, emociones) {
    var info = emociones[rostro.emocion] || { emoji: "", nombre: rostro.emocion, color: "#6C5CE7" };
    var grosor = esPrincipal ? 4 : 2;

    ctx.lineWidth = grosor;
    ctx.strokeStyle = info.color;
    trazarRectangulo(ctx, x, y, w, h, 12);
    ctx.stroke();

    var texto = info.emoji + " " + info.nombre + " " + Math.round(rostro.puntuacion * 100) + "%";
    var tamanoFuente = esPrincipal ? 15 : 13;
    ctx.font = "700 " + tamanoFuente + 'px "Nunito Sans", system-ui, sans-serif';
    var relleno = 8;
    var altoEtiqueta = tamanoFuente + 12;
    var anchoEtiqueta = ctx.measureText(texto).width + relleno * 2;

    var ex = Math.min(Math.max(x - grosor / 2, 0), Math.max(0, anchoLienzo - anchoEtiqueta));
    var ey = y - altoEtiqueta - 4;
    if (ey < 0) ey = y + grosor + 2; // sin espacio arriba: dentro del recuadro

    ctx.fillStyle = info.color;
    trazarRectangulo(ctx, ex, ey, anchoEtiqueta, altoEtiqueta, 8);
    ctx.fill();

    ctx.fillStyle = "#FFFFFF";
    ctx.textBaseline = "middle";
    ctx.shadowColor = "rgba(0, 0, 0, 0.45)";
    ctx.shadowBlur = 2;
    ctx.fillText(texto, ex + relleno, ey + altoEtiqueta / 2 + 1);
    ctx.shadowColor = "transparent";
    ctx.shadowBlur = 0;
  }

  /**
   * Dibuja los rostros sobre el canvas, corrigiendo el ajuste "contain"
   * (bandas laterales o superiores) y, si se indica, el efecto espejo.
   * Las coordenadas de la API están en la escala de la imagen enviada.
   */
  function dibujarRostros(lienzo, datos, espejo, emociones) {
    var lienzoInfo = prepararLienzo(lienzo);
    if (!datos || !datos.rostros || !datos.rostros.length) return;

    var escala = Math.min(lienzoInfo.ancho / datos.ancho, lienzoInfo.alto / datos.alto);
    var desplX = (lienzoInfo.ancho - datos.ancho * escala) / 2;
    var desplY = (lienzoInfo.alto - datos.alto * escala) / 2;

    // Se dibujan primero los secundarios para que el principal quede encima.
    for (var i = datos.rostros.length - 1; i >= 0; i--) {
      var r = datos.rostros[i];
      var xOrigen = espejo ? datos.ancho - (r.x + r.w) : r.x;
      dibujarRecuadro(
        lienzoInfo.ctx,
        desplX + xOrigen * escala,
        desplY + r.y * escala,
        r.w * escala,
        r.h * escala,
        r,
        i === 0,
        lienzoInfo.ancho,
        emociones
      );
    }
  }

  // --- Cámara y ciclo de análisis ------------------------------------------

  /**
   * Crea un controlador de cámara con ciclo de análisis.
   *
   * @param {Object} opciones
   * @param {HTMLVideoElement} opciones.video
   * @param {string} opciones.url endpoint de análisis (/api/analizar/)
   * @param {Object} opciones.avisos gestor creado con crearAvisos()
   * @param {Function} opciones.alResultado recibe los datos de cada análisis correcto
   * @param {Function} [opciones.alCambiarEstado] recibe "iniciando" | "activa" | "detenida"
   * @returns {{iniciar: Function, detener: Function, estaEncendida: Function}}
   */
  function crearCamara(opciones) {
    var video = opciones.video;
    var avisos = opciones.avisos;
    var alCambiarEstado = opciones.alCambiarEstado || function () {};
    var flujo = null;
    var estado = "detenida";
    var generacion = 0; // invalida respuestas que llegan después de detener
    var temporizador = null;
    var lienzoCaptura = document.createElement("canvas");

    function cambiarEstado(nuevo) {
      estado = nuevo;
      alCambiarEstado(nuevo);
    }

    /** Captura el fotograma actual a 640 px de ancho como JPEG. */
    function capturarFotograma() {
      var escala = Math.min(1, ANCHO_CAPTURA / video.videoWidth);
      lienzoCaptura.width = Math.round(video.videoWidth * escala);
      lienzoCaptura.height = Math.round(video.videoHeight * escala);
      lienzoCaptura.getContext("2d").drawImage(video, 0, 0, lienzoCaptura.width, lienzoCaptura.height);
      return new Promise(function (resolver, rechazar) {
        lienzoCaptura.toBlob(
          function (blob) {
            if (blob) resolver(blob);
            else rechazar(new Error("No se pudo capturar el fotograma."));
          },
          "image/jpeg",
          CALIDAD_JPEG
        );
      });
    }

    function sigueVigente(gen) {
      return estado === "activa" && gen === generacion;
    }

    /** Un paso del ciclo: captura, envía y programa el siguiente al responder. */
    function ciclo(gen) {
      if (!sigueVigente(gen)) return;

      capturarFotograma()
        .then(function (blob) {
          return enviarImagen(opciones.url, blob, "fotograma.jpg");
        })
        .then(function (respuesta) {
          if (!sigueVigente(gen)) return;
          avisos.quitar("conexion");

          if (respuesta.duracion > LENTO_MS) {
            avisos.avisar(
              "advertencia",
              "El análisis va lento (" + (respuesta.duracion / 1000).toFixed(1) + " s por fotograma). Cierra otras aplicaciones o revisa tu conexión.",
              "lento"
            );
          } else {
            avisos.quitar("lento");
          }

          if (respuesta.ok) {
            avisos.quitar("api");
            opciones.alResultado(respuesta.datos);
          } else if (manejarErrorApi(respuesta, avisos)) {
            detener();
            return;
          }
          temporizador = setTimeout(function () {
            ciclo(gen);
          }, PAUSA_MS);
        })
        .catch(function (error) {
          if (!sigueVigente(gen)) return;
          avisos.avisar(
            "advertencia",
            error && error.name === "AbortError"
              ? "El servidor no respondió a tiempo. Reintentando…"
              : "No se pudo conectar con el servidor. Reintentando…",
            "conexion"
          );
          temporizador = setTimeout(function () {
            ciclo(gen);
          }, PAUSA_REINTENTO_MS);
        });
    }

    function esperarMetadatos() {
      if (video.readyState >= 1 && video.videoWidth) return Promise.resolve();
      return new Promise(function (resolver) {
        video.addEventListener("loadedmetadata", resolver, { once: true });
      });
    }

    /** Pide la cámara y arranca el ciclo. Resuelve con true si se encendió. */
    function iniciar() {
      if (estado !== "detenida") return Promise.resolve(estado === "activa");
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        avisos.avisar(
          "error",
          "Tu navegador no permite usar la cámara aquí. Abre la página en localhost o HTTPS con un navegador actualizado.",
          "camara"
        );
        return Promise.resolve(false);
      }
      avisos.quitar("camara");
      var gen = ++generacion;
      cambiarEstado("iniciando");

      return navigator.mediaDevices
        .getUserMedia({ video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } }, audio: false })
        .then(function (stream) {
          if (gen !== generacion) {
            // Se detuvo mientras se pedía el permiso.
            stream.getTracks().forEach(function (pista) {
              pista.stop();
            });
            return false;
          }
          flujo = stream;
          video.srcObject = stream;
          return Promise.resolve(video.play())
            .catch(function () {})
            .then(esperarMetadatos)
            .then(function () {
              if (gen !== generacion) return false;
              cambiarEstado("activa");
              ciclo(gen);
              return true;
            });
        })
        .catch(function (error) {
          if (gen !== generacion) return false;
          cambiarEstado("detenida");
          avisos.avisar("error", mensajeErrorCamara(error), "camara");
          return false;
        });
    }

    /** Detiene el análisis y libera la cámara. */
    function detener() {
      generacion++;
      clearTimeout(temporizador);
      if (flujo) {
        flujo.getTracks().forEach(function (pista) {
          pista.stop();
        });
        flujo = null;
      }
      video.srcObject = null;
      avisos.quitar("lento");
      avisos.quitar("conexion");
      if (estado !== "detenida") cambiarEstado("detenida");
    }

    // Libera la cámara al salir de la página.
    window.addEventListener("pagehide", detener);

    return {
      iniciar: iniciar,
      detener: detener,
      estaEncendida: function () {
        return estado !== "detenida";
      },
    };
  }

  global.EmoSense = global.EmoSense || {};
  global.EmoSense.camara = {
    crearCamara: crearCamara,
    enviarImagen: enviarImagen,
    crearAvisos: crearAvisos,
    manejarErrorApi: manejarErrorApi,
    dibujarRostros: dibujarRostros,
    limpiarLienzo: limpiarLienzo,
  };
})(window);
