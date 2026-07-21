// Generic section-nav tab switching for complex form pages.
// Extracted from templates/faturamento/nota_fiscal/form.html — same behavior,
// generalized to work on any page with a single `.section-nav` + `.form-section[data-tab-panel]` set.
//
// Also exposes `window.SectionNav` so a template's own business-rule JS can hide/show a
// nav tab together with its conditional section (e.g. a "Fornecedor Internacional" switch
// that only makes the "Dados Internacionais" tab relevant when checked). A hidden tab link
// gets `.d-none`; if it was the active tab when hidden, the nav falls back to the first
// still-visible tab instead of leaving an empty panel showing.
(function () {
  var navLinks = Array.prototype.slice.call(document.querySelectorAll('.section-nav a[data-tab]'));
  var panels = Array.prototype.slice.call(document.querySelectorAll('.form-section[data-tab-panel]'));
  if (!navLinks.length || !panels.length) return;

  function firstVisibleTabId() {
    var link = navLinks.find(function (a) { return !a.classList.contains('d-none'); });
    return (link || navLinks[0]).getAttribute('data-tab');
  }

  // If the page reloaded after a failed submit, a validation error may have
  // landed on a panel that isn't the first tab — e.g. a required field that
  // only becomes invalid in the model's clean() rather than the HTML form.
  // Since .tab-hidden is display:none, that error would otherwise be
  // completely invisible to the user. Prefer the first tab with an error.
  function firstErrorTabId() {
    var panel = panels.find(function (p) {
      return !!p.querySelector('.error-msg, .invalid-feedback, .is-invalid');
    });
    return panel ? panel.getAttribute('data-tab-panel') : null;
  }

  function activateTab(tabId) {
    panels.forEach(function (p) {
      p.classList.toggle('tab-hidden', p.getAttribute('data-tab-panel') !== tabId);
    });
    navLinks.forEach(function (a) {
      a.classList.toggle('active', a.getAttribute('data-tab') === tabId);
    });
  }

  navLinks.forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      if (a.classList.contains('d-none')) return;
      activateTab(a.getAttribute('data-tab'));
    });
  });

  activateTab(firstErrorTabId() || firstVisibleTabId());

  window.SectionNav = {
    activate: activateTab,
    setTabVisible: function (tabId, visible) {
      var link = navLinks.find(function (a) { return a.getAttribute('data-tab') === tabId; });
      if (!link) return;
      var wasActive = link.classList.contains('active');
      link.classList.toggle('d-none', !visible);
      if (!visible && wasActive) {
        activateTab(firstVisibleTabId());
      }
    },
  };
})();
