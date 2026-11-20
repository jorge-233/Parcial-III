/* Reproduce los pasos del turno que envia el servidor en #datos-combate:
 * { inicial: escena, pasos: [{ texto, anim, escena }] }, o null si no hay nada nuevo. */
(function () {
  'use strict';

  var reducir = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var TIEMPO = reducir
    ? { letra: 0, pausa: 650, sinTexto: 150, anim: 0 }
    : { letra: 22, pausa: 850, sinTexto: 350, anim: 1 };
  var ETIQUETA_ESTADO = { quemadura: 'QUE', paralisis: 'PAR', sueno: 'DOR', congelado: 'CON' };
  var ETIQUETA_STAT = { ataque: 'Atq', defensa: 'Def', atq_esp: 'AtqEsp', def_esp: 'DefEsp',
                        velocidad: 'Vel', precision: 'Prec', evasion: 'Eva' };
  var OTRO = { jugador: 'rival', rival: 'jugador' };

  var $ = function (id) { return document.getElementById(id); };
  var cuadro = $('cuadro-texto');
  var texto = $('texto');
  var menu = $('menu');
  var acelerar = false;
  var despertar = null;
  var reproduciendo = false;
  var MINIMO_ANIM = 120;

  // ------------------------------------------------------------ esperas
  function esperar(ms) {
    return new Promise(function (resolver) {
      if (acelerar || ms <= 0) { resolver(); return; }
      var t = setTimeout(fin, ms);
      function fin() { clearTimeout(t); if (despertar === fin) despertar = null; resolver(); }
      despertar = fin;
    });
  }

  function esperarFijo(ms) {    // las animaciones se acortan, no se saltan
    return new Promise(function (resolver) {
      var t = setTimeout(fin, acelerar ? Math.min(ms, MINIMO_ANIM) : ms);
      function fin() { clearTimeout(t); if (despertar === cortar) despertar = null; resolver(); }
      function cortar() { clearTimeout(t); t = setTimeout(fin, MINIMO_ANIM); }
      despertar = cortar;
    });
  }

  // Tocar la pantalla o pulsar Enter/Espacio/Z adelanta el mensaje actual
  function avanzar() {
    if (!reproduciendo) return;
    acelerar = true;
    if (despertar) despertar();
  }
  document.addEventListener('click', function (e) {
    if (e.target.closest('a, button, input, select, summary, dialog')) return;
    avanzar();
  });
  document.addEventListener('keydown', function (e) {
    if (!reproduciendo || e.target.closest('input, textarea, dialog')) return;
    if (e.key === 'Enter' || e.key === ' ' || e.key === 'z' || e.key === 'Z') {
      e.preventDefault();
      avanzar();
    }
  });

  document.querySelectorAll('[data-abrir]').forEach(function (b) {
    b.addEventListener('click', function () {
      var d = $(b.dataset.abrir);
      if (d && d.showModal) d.showModal();
    });
  });
  document.querySelectorAll('dialog').forEach(function (d) {
    d.addEventListener('click', function (e) {
      if (e.target === d || e.target.closest('[data-cerrar]')) d.close();
    });
  });

  // ------------------------------------------------------------ texto
  function escribir(mensaje) {
    texto.textContent = '';
    cuadro.classList.remove('esperando');
    if (TIEMPO.letra === 0) { texto.textContent = mensaje; return Promise.resolve(); }
    var i = 0;
    return new Promise(function (resolver) {
      (function siguiente() {
        if (acelerar || i >= mensaje.length) { texto.textContent = mensaje; resolver(); return; }
        i += 1;
        texto.textContent = mensaje.slice(0, i);
        setTimeout(siguiente, TIEMPO.letra);
      })();
    });
  }

  // ------------------------------------------------------------ escena
  function colorVida(pct) { return pct > 50 ? 'verde' : (pct > 20 ? 'amarillo' : 'rojo'); }

  function contarPS(el, desde, hasta) {
    if (!el) return;
    if (reducir || desde === hasta) { el.textContent = hasta; return; }
    var inicio = null, duracion = 800;
    function paso(t) {
      if (inicio === null) inicio = t;
      var p = Math.min(1, (t - inicio) / duracion);
      el.textContent = Math.round(desde + (hasta - desde) * p);
      if (p < 1) requestAnimationFrame(paso);
    }
    requestAnimationFrame(paso);
  }

  function aplicarLado(lado, f, inicial) {
    var info = $('info-' + lado);
    var poke = $('poke-' + lado);
    if (!info || !poke) return;
    var img = poke.querySelector('.sprite');

    if (img.dataset.slug !== f.slug) {
      img.src = '/static/' + f.sprite;
      img.alt = f.nombre;
      img.dataset.slug = f.slug;
      img.style.visibility = '';
    }
    info.querySelector('.nombre').textContent = f.nombre;
    info.classList.toggle('oculto', !f.en_campo);
    poke.classList.toggle('oculto', !f.en_campo);
    if (inicial) poke.classList.toggle('caido', f.debilitado);

    var pct = Math.max(0, f.hp / f.hp_max * 100);
    var relleno = info.querySelector('.relleno');
    relleno.style.width = pct.toFixed(1) + '%';
    relleno.className = 'relleno ' + colorVida(pct);
    var hp = info.querySelector('.hp');
    if (hp) {
      var antes = parseInt(hp.textContent, 10);
      info.querySelector('.hp-max').textContent = f.hp_max;
      contarPS(hp, isNaN(antes) || inicial ? f.hp : antes, f.hp);
    }

    var etq = info.querySelector('.estado-etq');
    etq.hidden = !f.estado;
    etq.textContent = f.estado ? ETIQUETA_ESTADO[f.estado] : '';
    etq.className = 'estado-etq' + (f.estado ? ' estado-' + f.estado : '');
    var claseEstado = f.estado ? ' estado-' + f.estado : '';
    poke.querySelector('.tinte').className = 'tinte' + claseEstado;
    poke.querySelector('.capa-estado').className = 'capa-estado' + claseEstado;

    info.querySelector('.bolas').innerHTML = f.equipo.map(function (x) {
      return '<span class="bola' + (x.debilitado ? ' caida' : '') + '"></span>';
    }).join('');
    info.querySelector('.etapas').innerHTML = Object.keys(f.etapas).map(function (s) {
      var v = f.etapas[s];
      return '<span class="chip">' + ETIQUETA_STAT[s] + ' ' + (v > 0 ? '+' : '') + v + '</span>';
    }).join('');
  }

  function aplicarEscena(escena, inicial) {
    aplicarLado('jugador', escena.jugador, inicial);
    aplicarLado('rival', escena.rival, inicial);
  }

  // ------------------------------------------------------------ animaciones
  function claseTemporal(el, clase, ms) {
    if (!el || !TIEMPO.anim) return Promise.resolve();
    el.classList.remove(clase);
    void el.offsetWidth;                         // reinicia la animacion
    el.classList.add(clase);
    return esperarFijo(ms).then(function () { el.classList.remove(clase); });
  }

  function efecto(lado, clase, tipo, contenido, ms) {
    var capa = $('efectos-' + lado);
    if (!capa || !TIEMPO.anim) return null;
    var el = document.createElement('div');
    el.className = clase;
    if (tipo) el.dataset.tipo = tipo;
    if (contenido) el.textContent = contenido;
    capa.appendChild(el);
    setTimeout(function () { el.remove(); }, ms || 1200);
    return el;
  }

  function animar(anim) {
    if (!anim) return Promise.resolve();
    var lado = anim.lado;
    var poke = lado ? $('poke-' + lado) : null;

    switch (anim.tipo) {
      case 'presentacion':
        ['rival', 'jugador'].forEach(function (l) {
          var e = $('ent-' + l);
          e.classList.remove('oculto', 'sale');
          e.classList.add('entra');
        });
        return esperarFijo(600);

      case 'entrada':
        var entrenador = $('ent-' + lado);
        if (entrenador && !entrenador.classList.contains('oculto')) {
          entrenador.classList.add('sale');
          setTimeout(function () { entrenador.classList.add('oculto'); }, 600);
        }
        poke.classList.remove('caido', 'retirada');
        return claseTemporal(poke, 'entrada', 500);

      case 'retirada':
        poke.classList.add('retirada');
        return esperarFijo(500).then(function () {
          poke.classList.add('oculto');
          poke.classList.remove('retirada');
        });

      case 'ataque':
        if (anim.categoria === 'estado') {
          efecto(lado, 'halo', anim.mov_tipo, null, 800);
          return esperarFijo(650);
        }
        var embestida = claseTemporal(poke, 'embestida-' + lado, 450);
        setTimeout(function () { efecto(OTRO[lado], 'destello', anim.mov_tipo, null, 700); }, 220);
        return embestida.then(function () { return esperarFijo(150); });

      case 'dano':
        efecto(lado, 'numero' + (anim.critico ? ' critico' : ''), null, '-' + anim.cantidad, 1100);
        return claseTemporal(poke, 'golpeado', 450).then(function () { return esperarFijo(450); });

      case 'fallo':
        return claseTemporal(poke, 'esquive', 500);

      case 'estado':
        efecto(lado, 'halo', anim.estado, null, 800);
        return esperarFijo(600);

      case 'stat':
        efecto(lado, 'flecha ' + (anim.sube ? 'sube' : 'baja'), null, anim.sube ? '▲' : '▼', 1000);
        return esperarFijo(700);

      case 'cura':
        for (var i = 0; i < 6; i++) {
          var c = efecto(lado, 'chispa-cura', null, null, 1200);
          if (c) { c.style.left = (20 + i * 11) + '%'; c.style.animationDelay = (i * 0.08) + 's'; }
        }
        return esperarFijo(800);

      case 'debilitado':
        poke.classList.add('caido');
        return esperarFijo(600);

      default:
        return Promise.resolve();
    }
  }

  // ------------------------------------------------------------ menu
  function bloquear(si) {
    if (!menu) return;
    menu.classList.toggle('bloqueado', si);
    menu.querySelectorAll('button').forEach(function (b) {
      if (si) { b.dataset.antes = b.disabled ? '1' : ''; b.disabled = true; }
      else if (b.dataset.antes !== undefined) { b.disabled = b.dataset.antes === '1'; delete b.dataset.antes; }
    });
  }

  function prepararMenu() {
    var principal = $('menu-principal');
    var paneles = [$('panel-movs'), $('panel-cambio')].filter(Boolean);
    if (!principal) return;
    principal.hidden = false;
    paneles.forEach(function (p) { p.hidden = true; });
    principal.querySelectorAll('[data-panel]').forEach(function (b) {
      b.addEventListener('click', function () {
        principal.hidden = true;
        paneles.forEach(function (p) { p.hidden = p.id !== b.dataset.panel; });
      });
    });
    paneles.forEach(function (p) {
      var atras = p.querySelector('.atras');
      if (!atras) return;
      atras.hidden = false;
      atras.addEventListener('click', function () {
        p.hidden = true;
        principal.hidden = false;
      });
    });
  }

  // Evita el doble envio
  document.querySelectorAll('.menu form').forEach(function (f) {
    f.addEventListener('submit', function () {
      setTimeout(function () { bloquear(true); }, 0);
    });
  });

  // ------------------------------------------------------------ reproduccion
  function reproducir(datos) {
    var cartel = $('cartel');
    if (cartel) cartel.hidden = true;
    reproduciendo = true;
    bloquear(true);
    aplicarEscena(datos.inicial, true);

    var cadena = Promise.resolve();
    datos.pasos.forEach(function (paso) {
      cadena = cadena.then(function () {
        acelerar = false;
        var antes = paso.anim && (paso.anim.tipo === 'presentacion' || paso.anim.tipo === 'entrada');
        var mover = function () { aplicarEscena(paso.escena, false); return animar(paso.anim); };
        var primero = antes ? mover() : (paso.texto ? escribir(paso.texto) : Promise.resolve());
        return primero
          .then(function () {
            if (antes) return paso.texto ? escribir(paso.texto) : null;
            return mover();
          })
          .then(function () {
            if (paso.texto) cuadro.classList.add('esperando');
            return esperar(paso.texto ? TIEMPO.pausa : TIEMPO.sinTexto);
          })
          .then(function () { cuadro.classList.remove('esperando'); });
      });
    });

    return cadena.then(function () {
      acelerar = false;
      reproduciendo = false;
      bloquear(false);
      if (cartel) { cartel.hidden = false; cartel.classList.add('aparece'); }
      var pregunta = $('menu-principal');
      if (pregunta && !cartel) texto.textContent = pregunta.querySelector('p').textContent;
    });
  }

  prepararMenu();
  var nodo = $('datos-combate');
  var datos = nodo ? JSON.parse(nodo.textContent) : null;
  if (datos && datos.pasos && datos.pasos.length) reproducir(datos);
})();
