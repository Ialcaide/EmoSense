/**
 * EmoSense – Medidor de amabilidad.
 *
 * Sesión de práctica de 60 s: cuenta en qué porcentaje de los análisis con
 * rostro la expresión principal fue amable (alegría o neutral). Los análisis
 * sin rostro no cuentan. Si no hubo ningún rostro o la sesión se cancela,
 * no se guarda nada.
 *
 * Al terminar envía los conteos a POST /api/practica/ (el servidor calcula
 * el porcentaje, lo guarda de forma anónima y devuelve mensaje y consejos)
 * y guarda las últimas 5 sesiones en localStorage, solo en este navegador.
 *
 * La configuración (duración, umbrales, mensajes y consejos) llega desde
 * detector/amabilidad.py con json_script (#datos-practica).
 *
 * Uso (desde detector.js):
 *   var medidor = EmoSense.crearMedidor({ camara: camara, avisos: avisos });
 *   medidor.registrar(datos);      // con cada resultado de la cámara
 *   medidor.cancelar("motivo");    // si se detiene la cámara
 */
(function (global) {
  "use strict";

  var CLAVE_HISTORIAL = "emosense-historial-practica";
  var MAX_HISTORIAL = 5;

  function $(id) {
    return document.getElementById(id);
  }

  // --- Historial (localStorage, opcional) ----------------------------------

  function leerHistorial() {
    try {
      var datos = JSON.parse(localStorage.getItem(CLAVE_HISTORIAL) || "[]");
      return Array.isArray(datos) ? datos.slice(0, MAX_HISTORIAL) : [];
    } catch (e) {
      return [];
    }
  }

  function guardarHistorial(lista) {
    try {
      localStorage.setItem(CLAVE_HISTORIAL, JSON.stringify(lista.slice(0, MAX_HISTORIAL)));
      return true;
    } catch (e) {
      return false; // almacenamiento bloqueado: la página sigue funcionando
    }
  }

  function borrarHistorial() {
    try {
      localStorage.removeItem(CLAVE_HISTORIAL);
    } catch (e) {
      /* sin almacenamiento */
    }
  }

  // --- Evaluación local (respaldo si no se puede guardar en el servidor) ----

  /** Mismo criterio que detector/amabilidad.py: evaluar_sesion(). */
  function evaluarLocal(config, porcentaje, predominante) {
    var nivel =
      porcentaje >= config.umbral_excelente ? "excelente" : porcentaje >= config.umbral_bueno ? "bueno" : "mejorar";
    var extra = config.consejo_por_expresion[predominante] || config.consejo_sin_predominante;
    return {
      nivel: nivel,
      mensaje: config.niveles[nivel].mensaje,
      consejos: config.niveles[nivel].consejos.concat([extra]),
    };
  }

  function obtenerCsrf() {
    var coincidencia = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return coincidencia ? decodeURIComponent(coincidencia[1]) : "";
  }

  /**
   * Crea el medidor de amabilidad.
   * @param {Object} opciones
   * @param {Object} opciones.camara controlador de camara.js (iniciar, estaEncendida)
   * @param {Object} opciones.avisos gestor de avisos de camara.js
   */
  function crearMedidor(opciones) {
    var raiz = $("medidor");
    if (!raiz) return { registrar: function () {}, cancelar: function () {} };

    var config = JSON.parse($("datos-practica").textContent);
    var camara = opciones.camara;
    var avisos = opciones.avisos;
    var amables = config.emociones_amables;

    var el = {
      inicio: $("medidor-inicio"),
      curso: $("medidor-curso"),
      resultado: $("medidor-resultado"),
      historial: $("medidor-historial"),
      botonPracticar: $("boton-practicar"),
      botonCancelar: $("boton-cancelar-practica"),
      botonRepetir: $("boton-repetir-practica"),
      botonBorrar: $("boton-borrar-historial"),
      restante: $("medidor-restante"),
      barra: $("medidor-barra"),
      vivo: $("medidor-vivo"),
      conteo: $("medidor-conteo"),
      porcentaje: $("resultado-porcentaje"),
      mensaje: $("resultado-mensaje"),
      consejos: $("resultado-consejos"),
      guardado: $("resultado-guardado"),
      listaHistorial: $("lista-historial"),
    };

    var estado = "inactivo"; // inactivo | esperando | midiendo
    var sesion = null;
    var intervalo = null;

    function mostrar(seccion) {
      el.inicio.hidden = seccion !== "inicio";
      el.curso.hidden = seccion !== "curso";
      el.resultado.hidden = seccion !== "resultado";
    }

    // --- Historial ---------------------------------------------------------

    function pintarHistorial() {
      var lista = leerHistorial();
      el.historial.hidden = lista.length === 0;
      var formato = new Intl.DateTimeFormat("es-EC", {
        day: "2-digit",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
      el.listaHistorial.replaceChildren.apply(
        el.listaHistorial,
        lista.map(function (item) {
          var fila = document.createElement("li");
          fila.className = "historial__item";
          var fecha = document.createElement("span");
          fecha.className = "historial__fecha";
          fecha.textContent = formato.format(new Date(item.fecha));
          var pista = document.createElement("span");
          pista.className = "historial__pista";
          pista.setAttribute("aria-hidden", "true");
          var relleno = document.createElement("span");
          relleno.className = "historial__relleno";
          relleno.style.width = Math.max(0, Math.min(100, item.porcentaje)) + "%";
          pista.append(relleno);
          var valor = document.createElement("span");
          valor.className = "historial__valor";
          valor.textContent = Math.round(item.porcentaje) + "%";
          fila.append(fecha, pista, valor);
          return fila;
        })
      );
    }

    function agregarAlHistorial(porcentaje) {
      var lista = leerHistorial();
      lista.unshift({ fecha: new Date().toISOString(), porcentaje: porcentaje });
      guardarHistorial(lista);
      pintarHistorial();
    }

    // --- Sesión ------------------------------------------------------------

    function actualizarVivo() {
      if (!sesion.total) {
        el.vivo.textContent = "—";
        el.conteo.textContent = "(esperando un rostro…)";
        return;
      }
      el.vivo.textContent = Math.round((sesion.amables * 100) / sesion.total) + "%";
      el.conteo.textContent = "(" + sesion.total + " análisis con rostro)";
    }

    function tic() {
      var transcurrido = (performance.now() - sesion.inicio) / 1000;
      var restante = Math.max(0, Math.ceil(config.duracion - transcurrido));
      el.restante.textContent = String(restante);
      el.barra.style.width = Math.min(100, (transcurrido * 100) / config.duracion) + "%";
      if (transcurrido >= config.duracion) terminar();
    }

    function empezar() {
      sesion = { inicio: performance.now(), total: 0, amables: 0, otras: {} };
      estado = "midiendo";
      avisos.quitar("practica");
      mostrar("curso");
      actualizarVivo();
      tic();
      intervalo = setInterval(tic, 250);
      el.botonCancelar.focus();
    }

    /** Inicia la práctica; enciende la cámara si hace falta. */
    function practicar() {
      if (estado !== "inactivo") return;
      if (camara.estaEncendida()) {
        empezar();
        return;
      }
      estado = "esperando";
      el.botonPracticar.disabled = true;
      camara.iniciar().then(function (encendida) {
        el.botonPracticar.disabled = false;
        if (estado !== "esperando") return;
        estado = "inactivo";
        if (encendida) empezar();
      });
    }

    function detenerReloj() {
      clearInterval(intervalo);
      intervalo = null;
    }

    /** Expresión no amable más frecuente, o null. */
    function predominante() {
      var mejor = null;
      Object.keys(sesion.otras).forEach(function (clave) {
        if (mejor === null || sesion.otras[clave] > sesion.otras[mejor]) mejor = clave;
      });
      return mejor;
    }

    function mostrarResultado(porcentaje, evaluacion, textoGuardado) {
      el.porcentaje.textContent = Math.round(porcentaje) + "% amable";
      el.porcentaje.className = "medidor__porcentaje es-" + evaluacion.nivel;
      el.mensaje.textContent = evaluacion.mensaje;
      el.consejos.replaceChildren.apply(
        el.consejos,
        evaluacion.consejos.map(function (texto) {
          var item = document.createElement("li");
          item.textContent = texto;
          return item;
        })
      );
      el.guardado.textContent = textoGuardado;
      mostrar("resultado");
      el.botonRepetir.focus();
    }

    function terminar() {
      detenerReloj();
      estado = "inactivo";

      if (!sesion.total) {
        mostrar("inicio");
        avisos.avisar(
          "advertencia",
          "No se detectó ningún rostro durante la práctica, así que no se guardó. Revisa la luz y colócate frente a la cámara.",
          "practica"
        );
        return;
      }

      var datos = {
        duracion: config.duracion,
        cantidad_analisis: sesion.total,
        amables: sesion.amables,
        predominante: predominante(),
      };
      var porcentajeLocal = Math.round((sesion.amables * 1000) / sesion.total) / 10;

      fetch(config.url, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": obtenerCsrf() },
        credentials: "same-origin",
        body: JSON.stringify(datos),
      })
        .then(function (respuesta) {
          return respuesta.json().then(function (cuerpo) {
            if (!respuesta.ok || !cuerpo.ok) throw new Error(cuerpo.mensaje || String(respuesta.status));
            return cuerpo;
          });
        })
        .then(function (cuerpo) {
          agregarAlHistorial(cuerpo.porcentaje);
          mostrarResultado(cuerpo.porcentaje, cuerpo, "Resultado guardado de forma anónima ✅");
        })
        .catch(function () {
          agregarAlHistorial(porcentajeLocal);
          mostrarResultado(
            porcentajeLocal,
            evaluarLocal(config, porcentajeLocal, datos.predominante),
            "No se pudo guardar en el servidor; el resultado quedó solo en tu historial."
          );
        });
    }

    /** Registra un resultado de la cámara si hay una sesión en curso. */
    function registrar(datos) {
      if (estado !== "midiendo" || !datos.principal) return;
      var emocion = datos.principal.emocion;
      sesion.total += 1;
      if (amables.indexOf(emocion) !== -1) {
        sesion.amables += 1;
      } else {
        sesion.otras[emocion] = (sesion.otras[emocion] || 0) + 1;
      }
      actualizarVivo();
    }

    /** Cancela la sesión en curso sin guardar nada. */
    function cancelar(motivo) {
      if (estado === "esperando") {
        estado = "inactivo";
        return;
      }
      if (estado !== "midiendo") return;
      detenerReloj();
      estado = "inactivo";
      sesion = null;
      mostrar("inicio");
      avisos.avisar("info", "Práctica cancelada" + (motivo ? " (" + motivo + ")" : "") + ". No se guardó ningún resultado.", "practica");
    }

    // --- Eventos -----------------------------------------------------------

    el.botonPracticar.addEventListener("click", practicar);
    el.botonRepetir.addEventListener("click", function () {
      mostrar("inicio");
      practicar();
    });
    el.botonCancelar.addEventListener("click", function () {
      cancelar("");
    });
    el.botonBorrar.addEventListener("click", function () {
      borrarHistorial();
      pintarHistorial();
    });

    pintarHistorial();

    return { registrar: registrar, cancelar: cancelar };
  }

  global.EmoSense = global.EmoSense || {};
  global.EmoSense.crearMedidor = crearMedidor;
})(window);
