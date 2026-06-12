/* ══════════════════════════════════════════════════════
   main.js — MindUp Bootstrap 5
   ══════════════════════════════════════════════════════ */

/* 1. Confirmation Modals
   Usage: <button data-confirm-url="/path/" data-confirm-message="Delete X?">Delete</button>
   ─────────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {

  document.querySelectorAll('[data-confirm-url]').forEach(btn => {
    btn.addEventListener('click', e => {
      e.preventDefault();
      const modal  = document.getElementById('confirmModal');
      const form   = document.getElementById('confirmModalForm');
      const body   = document.getElementById('confirmModalBody');
      const title  = document.getElementById('confirmModalTitle');
      const action = btn.dataset.confirmAction || 'Delete';
      body.textContent  = btn.dataset.confirmMessage || 'Are you sure?';
      title.textContent = action;
      form.action = btn.dataset.confirmUrl;
      bootstrap.Modal.getOrCreateInstance(modal).show();
    });
  });

  /* 2. AJAX Cascade: Topic → Category → Subcategory
     ─────────────────────────────────────────────────────── */
  const topicSelect    = document.getElementById('id_topic');
  const categorySelect = document.getElementById('id_category');
  const subcatSelect   = document.getElementById('id_subcategory');

  function enableSelect(el, placeholder) {
    el.disabled = false;
    el.innerHTML = `<option value="">${placeholder}</option>`;
  }
  function disableSelect(el, placeholder) {
    el.disabled = true;
    el.innerHTML = `<option value="">${placeholder}</option>`;
  }

  if (topicSelect) {
    topicSelect.addEventListener('change', async () => {
      const topicId = topicSelect.value;
      disableSelect(categorySelect, '— Select Category —');
      disableSelect(subcatSelect,   '— Select Subcategory —');
      if (!topicId) return;

      const res  = await fetch(`/ajax/categories/?topic_id=${topicId}`,
                               {headers: {'X-Requested-With': 'XMLHttpRequest'}});
      const data = await res.json();
      enableSelect(categorySelect, '— Select Category —');
      data.categories.forEach(c => {
        categorySelect.insertAdjacentHTML('beforeend',
          `<option value="${c.id}">${c.name}</option>`);
      });
      updateSubmitButton();
    });
  }

  if (categorySelect) {
    categorySelect.addEventListener('change', async () => {
      const catId = categorySelect.value;
      disableSelect(subcatSelect, '— Select Subcategory —');
      if (!catId) return;

      const res  = await fetch(`/ajax/subcategories/?category_id=${catId}`,
                               {headers: {'X-Requested-With': 'XMLHttpRequest'}});
      const data = await res.json();
      enableSelect(subcatSelect, '— Select Subcategory —');
      data.subcategories.forEach(s => {
        subcatSelect.insertAdjacentHTML('beforeend',
          `<option value="${s.id}">${s.name}</option>`);
      });
      updateSubmitButton();
    });
  }

  if (subcatSelect) {
    subcatSelect.addEventListener('change', updateSubmitButton);
  }

  /* 3. Character counter for bulk textarea
     ─────────────────────────────────────────────────────── */
  const rawText   = document.getElementById('id_raw_text');
  const charCount = document.getElementById('charCount');
  if (rawText && charCount) {
    rawText.addEventListener('input', () => {
      const chars = rawText.value.length;
      charCount.textContent = `${chars.toLocaleString()} characters`;
      updateSubmitButton();
    });
  }

  /* 4. Enable preview/submit button only when all fields filled
     ─────────────────────────────────────────────────────── */
  function updateSubmitButton() {
    const previewBtn = document.getElementById('previewBtn');
    if (!previewBtn) return;
    const ready = subcatSelect && subcatSelect.value
               && rawText && rawText.value.trim().length > 20;
    previewBtn.disabled = !ready;
  }

  /* 5. Preview modal — show estimated pair count before upload
     ─────────────────────────────────────────────────────── */
  const previewBtn = document.getElementById('previewBtn');
  const bulkForm   = document.getElementById('bulkUploadForm');
  if (previewBtn && bulkForm) {
    previewBtn.addEventListener('click', () => {
      const text  = rawText ? rawText.value : '';
      const count = estimatePairCount(text);
      const el    = document.getElementById('previewCount');
      const sub   = document.getElementById('previewSubcat');
      if (el) el.textContent = count;
      if (sub) sub.textContent =
        subcatSelect.options[subcatSelect.selectedIndex]?.text || '?';
      bootstrap.Modal.getOrCreateInstance(
        document.getElementById('uploadConfirmModal')).show();
    });
  }

  const confirmUploadBtn = document.getElementById('confirmUploadBtn');
  if (confirmUploadBtn && bulkForm) {
    confirmUploadBtn.addEventListener('click', () => {
      bootstrap.Modal.getInstance(
        document.getElementById('uploadConfirmModal')).hide();
      bulkForm.submit();
    });
  }

  function estimatePairCount(text) {
    // Quick client-side estimate using Q: markers or numbered lines
    const explicit = (text.match(/\bQ\s*[\d]*\s*[:\.\)]/gi) || []).length;
    if (explicit > 0) return explicit;
    const numbered = (text.match(/^\s*\d+[\.\)]\s+\S/gm) || []).length;
    if (numbered > 0) return Math.floor(numbered / 1);
    const paras = text.split(/\n{2,}/).filter(p => p.trim().length > 10);
    return Math.floor(paras.length / 2);
  }

  /* 6. Auto-dismiss flash messages after 4s
     ─────────────────────────────────────────────────────── */
  document.querySelectorAll('.alert-dismissible').forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 4000);
  });

  /* 7. Prevent back-button cache (belt + suspenders with server headers)
     ─────────────────────────────────────────────────────── */
  window.addEventListener('pageshow', e => {
    if (e.persisted) window.location.reload();
  });

});