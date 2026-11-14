/**
 * EmoSense – Tema claro/oscuro y menú móvil.
 *
 * - Alterna entre tema claro y oscuro y lo guarda en localStorage.
 * - Abre y cierra el menú hamburguesa en pantallas pequeñas.
 *
 * El tema inicial se aplica con un script en el <head> de base.html
 * para evitar el parpadeo antes de pintar.
 */
(function () {
  "use strict";

  var CLAVE_TEMA = "emosense-tema";
  var raiz = document.documentElement;

  /** Guarda el tema; ignora errores (modo privado o almacenamiento bloqueado). */
  function guardarTema(tema) {
    try {
      localStorage.setItem(CLAVE_TEMA, tema);
    } catch (e) {
      /* sin almacenamiento: el tema solo dura esta visita */
    }
  }

  /** Devuelve el tema actual ("light" o "dark"). */
  function temaActual() {
    return raiz.getAttribute("data-theme") === "dark" ? "dark" : "light";
  }

  /** Actualiza el icono y la etiqueta accesible del botón de tema. */
  function actualizarBotonTema(boton) {
    var oscuro = temaActual() === "dark";
    boton.textContent = oscuro ? "☀️" : "🌙";
    boton.setAttribute("aria-label", oscuro ? "Cambiar a tema claro" : "Cambiar a tema oscuro");
    boton.setAttribute("aria-pressed", oscuro ? "true" : "false");
  }

  /** Configura el botón que alterna el tema. */
  function iniciarTema() {
    var boton = document.getElementById("boton-tema");
    if (!boton) return;
    actualizarBotonTema(boton);
    boton.addEventListener("click", function () {
      var nuevo = temaActual() === "dark" ? "light" : "dark";
      raiz.setAttribute("data-theme", nuevo);
      guardarTema(nuevo);
      actualizarBotonTema(boton);
    });
  }

  /** Configura el menú hamburguesa (abrir, cerrar con Escape o al cambiar de tamaño). */
  function iniciarMenu() {
    var boton = document.getElementById("boton-menu");
    var menu = document.getElementById("menu-principal");
    if (!boton || !menu) return;

    function cambiarMenu(abrir) {
      menu.classList.toggle("esta-abierto", abrir);
      boton.setAttribute("aria-expanded", abrir ? "true" : "false");
      boton.setAttribute("aria-label", abrir ? "Cerrar menú" : "Abrir menú");
      boton.textContent = abrir ? "✕" : "☰";
    }

    boton.addEventListener("click", function () {
      cambiarMenu(boton.getAttribute("aria-expanded") !== "true");
    });

    document.addEventListener("keydown", function (evento) {
      if (evento.key === "Escape" && menu.classList.contains("esta-abierto")) {
        cambiarMenu(false);
        boton.focus();
      }
    });

    // Cerrar al hacer clic fuera de la barra.
    document.addEventListener("click", function (evento) {
      if (menu.classList.contains("esta-abierto") && !evento.target.closest(".barra")) {
        cambiarMenu(false);
      }
    });

    // Al pasar a escritorio, el menú vuelve a su estado normal.
    window.matchMedia("(min-width: 640px)").addEventListener("change", function (consulta) {
      if (consulta.matches) cambiarMenu(false);
    });
  }

  /** Oculta con un fundido la pantalla de carga inicial (si la página la muestra). */
  function ocultarPantallaCarga() {
    var pantalla = document.getElementById("pantalla-carga");
    if (!pantalla || !pantalla.hasAttribute("data-inicial")) return;
    pantalla.removeAttribute("data-inicial");
    pantalla.classList.add("pantalla-carga--saliendo");
    window.setTimeout(function () {
      pantalla.hidden = true;
      pantalla.classList.remove("pantalla-carga--saliendo");
    }, 320);
  }

  document.addEventListener("DOMContentLoaded", function () {
    iniciarTema();
    iniciarMenu();
  });

  if (document.readyState === "complete") {
    ocultarPantallaCarga();
  } else {
    window.addEventListener("load", ocultarPantallaCarga);
  }
})();
