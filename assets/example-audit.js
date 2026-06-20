/* example-audit.html — progressive-enhancement animations only.
   Loaded solely on /example-audit.html, under a scoped script-src 'self' CSP.
   The page is fully readable and complete WITHOUT this file: if it does not run,
   every stage, value, and coverage card is already present as static content.
   No external dependencies. Respects prefers-reduced-motion. */
document.documentElement.className += ' js';

(function () {
  function init() {
    var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var els = Array.prototype.slice.call(document.querySelectorAll('.reveal-up'));

    function runCount(span) {
      var target = parseFloat(span.getAttribute('data-count'));
      if (isNaN(target)) return;
      if (reduce) { span.textContent = String(Math.round(target)); return; }
      var dur = 850, t0 = null;
      function step(ts) {
        if (!t0) t0 = ts;
        var p = Math.min((ts - t0) / dur, 1);
        span.textContent = String(Math.round(target * p));
        if (p < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    }

    function reveal(el) {
      el.classList.add('in');
      var span = el.querySelector('[data-count]');
      if (span) runCount(span);
    }
    function revealAll() { els.forEach(reveal); }

    if (reduce || !('IntersectionObserver' in window)) { revealAll(); return; }

    // start the counters at zero so they animate up when scrolled into view
    Array.prototype.slice.call(document.querySelectorAll('[data-count]'))
      .forEach(function (s) { s.textContent = '0'; });

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { reveal(en.target); io.unobserve(en.target); }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -6% 0px' });
    els.forEach(function (e) { io.observe(e); });

    // safety net: never leave content hidden if the observer never fires
    setTimeout(revealAll, 2600);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
