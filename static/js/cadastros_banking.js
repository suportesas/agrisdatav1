// Shared PIX show/hide behavior for banking forms
document.addEventListener('DOMContentLoaded', function () {
  function togglePixFieldsFor(checkbox) {
    if (!checkbox) return;
    // Try to scope to closest form first
    let form = checkbox.closest('form') || document;
    let tipo = form.querySelector('#tipo_chave_pix_field') || document.getElementById('tipo_chave_pix_field');
    let chave = form.querySelector('#chave_pix_field') || document.getElementById('chave_pix_field');
    if (!tipo || !chave) return;
    if (checkbox.checked) {
      tipo.classList.remove('d-none');
      chave.classList.remove('d-none');
    } else {
      tipo.classList.add('d-none');
      chave.classList.add('d-none');
      const inTipo = form.querySelector('[name="tipo_chave_pix"]');
      const inChave = form.querySelector('[name="chave_pix"]');
      if (inTipo) inTipo.value = '';
      if (inChave) inChave.value = '';
    }
  }

  // Initialize all PIX toggles on page
  const pixCheckboxes = Array.from(document.querySelectorAll('[name="pix_habilitado"]'));
  pixCheckboxes.forEach(chk => {
    chk.addEventListener('change', function () { togglePixFieldsFor(chk); });
    togglePixFieldsFor(chk);
  });
});