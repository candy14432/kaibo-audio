(function () {
  'use strict';
  var header   = document.querySelector('header');
  var scenes   = document.querySelectorAll('.scene');
  var lastBand = scenes.length ? scenes[scenes.length - 1] : null;  // 4th full-screen band
  var themed   = document.querySelectorAll('[data-theme]');
  var heroMedia = document.querySelector('.kb-hero-media');
  var heroCopy  = document.querySelector('.kb-hero-copy');
  var ticking = false;

  // Parallax and the header state are written straight to the nodes inside a rAF.
  // Scroll events outrun the display; touching the video wrapper's transform on
  // every event re-rasterises the video layer and makes it flicker.
  function frame() {
    ticking = false;
    var y = window.scrollY || 0;
    var vh = window.innerHeight || 900;
    var p = Math.min(1, y / vh);
    if (heroMedia) heroMedia.style.transform = 'scale(' + (1 + p * 0.14).toFixed(4) + ')';
    if (heroCopy)  heroCopy.style.opacity = (1 - Math.min(1, p * 1.35)).toFixed(3);
    if (header && lastBand) {
      var h = header.offsetHeight;
      var past = lastBand.getBoundingClientRect().bottom <= h;
      var v = past ? '1' : '0';
      if (header.dataset.solid !== v) header.dataset.solid = v;
      if (past) {
        var probe = h * 0.6;                       // a point just inside the bar
        var theme = 'dark';
        for (var i = 0; i < themed.length; i++) {
          var r = themed[i].getBoundingClientRect();
          if (r.top <= probe && r.bottom > probe) { theme = themed[i].dataset.theme; break; }
        }
        if (header.dataset.theme !== theme) header.dataset.theme = theme;
      }
    }
  }
  window.addEventListener('scroll', function () {
    if (!ticking) { ticking = true; requestAnimationFrame(frame); }
  }, { passive: true });
  frame();

  // Each film runs only while its own band is on screen, and opens on frame one.
  // The observer below watches the media box inside each band, not the band
  // itself, so this list has to hold the same nodes or indexOf will not find
  // them. Getting that wrong warms bands[0] and resets the hero mid-play.
  var bands = [].slice.call(document.querySelectorAll('[data-play-in-view]'))
    .map(function (el) { return el.querySelector('.scene-media, .kb-hero-media') || el; });
  var conn = navigator.connection || {};
  var thrifty = !!conn.saveData;

  // The films are large enough that a band which only starts downloading when
  // the visitor reaches it sits on its poster for seconds. Warm the next one
  // while the current one plays — by then it is the film they are about to see
  // anyway. Skipped when the visitor has asked the browser to save data.
  function warmNext(band) {
    if (thrifty) return;
    var idx = bands.indexOf(band);
    if (idx < 0) return;
    var next = bands[idx + 1];
    if (!next) return;
    var nv = next.querySelector('video');
    if (!nv || nv.dataset.warmed) return;
    nv.dataset.warmed = '1';
    nv.preload = 'auto';
    nv.load();
  }

  if (typeof IntersectionObserver !== 'undefined') {
    var films = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        var wasIn = e.target.dataset.inView === '1';
        e.target.dataset.inView = e.isIntersecting ? '1' : '0';
        var v = e.target.querySelector('video');
        if (!v) return;
        if (e.isIntersecting) {
          warmNext(e.target);
          if (wasIn) return;                       // already running mid-band
          v.muted = true; v.playsInline = true;
          // data-start holds back a clip whose opening seconds are not the shot.
          // Native loop would wrap to 0 and expose them, so those clips loop here.
          var from = parseFloat(v.dataset.start) || 0;
          if (from > 0 && !v.dataset.startBound) {
            v.dataset.startBound = '1';
            v.loop = false;
            v.addEventListener('ended', function () {
              try { v.currentTime = from; } catch (err) {}
              var again = v.play(); if (again && again.catch) again.catch(function () {});
            });
          }
          // the seek has to wait for the data — currentTime set on an empty
          // element is dropped, which silently ignores data-start
          var go = function () {
            try { v.currentTime = from; } catch (err) {}
            var q = v.play(); if (q && q.catch) q.catch(function () {});
          };
          if (v.readyState >= 2) go(); else v.addEventListener('canplay', go, { once: true });
        } else if (!v.paused) {
          v.pause();
        }
      });
    }, { threshold: 0.5 });
    document.querySelectorAll('[data-play-in-view]').forEach(function (el) {
      films.observe(el.querySelector('.scene-media, .kb-hero-media') || el);
    });
  }

  // Product cards rise in once, then stop being watched.
  var reveal = document.querySelectorAll('[data-reveal]');
  if (typeof IntersectionObserver !== 'undefined') {
    var entrance = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.dataset.in = '1';
        entrance.unobserve(e.target);
      });
    }, { threshold: 0.15 });
    reveal.forEach(function (el) { entrance.observe(el); });
  } else {
    reveal.forEach(function (el) { el.dataset.in = '1'; });   // never leave them hidden
  }

  // Mobile menu
  var burger = document.querySelector('.kb-burger');
  if (burger && header) {
    var setMenu = function (open) {
      header.dataset.menu = open ? '1' : '0';
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    };
    burger.addEventListener('click', function () { setMenu(header.dataset.menu !== '1'); });
    document.addEventListener('click', function (ev) {
      if (ev.target.closest && ev.target.closest('.kb-menu a')) setMenu(false);
    });
    document.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') setMenu(false); });
    window.addEventListener('resize', function () { if (window.innerWidth > 960) setMenu(false); });
    setMenu(false);
  }

  // Signal rings follow the cursor across the contact band. The position rides on
  // custom properties set on <html> so nothing has to touch the section's own style.
  var contact = document.getElementById('contact');
  if (contact) {
    var root = document.documentElement;
    contact.addEventListener('pointermove', function (ev) {
      var r = contact.getBoundingClientRect();
      root.style.setProperty('--kb-x', (ev.clientX - r.left) + 'px');
      root.style.setProperty('--kb-y', (ev.clientY - r.top) + 'px');
    }, { passive: true });
    contact.addEventListener('pointerenter', function () { contact.dataset.hover = '1'; });
    contact.addEventListener('pointerleave', function () { contact.dataset.hover = '0'; });
  }

  // TODO(shopify): this only swaps the panel — it posts nothing anywhere yet.
  // Wire to Shopify's /contact form or a form app before going live.
  var submit = document.getElementById('kb-submit');
  var formPanel = document.getElementById('kb-form');
  var sentPanel = document.getElementById('kb-sent');
  if (submit && formPanel && sentPanel) {
    submit.addEventListener('click', function () {
      formPanel.hidden = true;
      sentPanel.hidden = false;
    });
  }
})();
