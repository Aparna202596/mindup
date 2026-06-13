/* ══════════════════════════════════════════════════════════════════════════
  main.js — MindUp  (Bootstrap 5 + SweetAlert2)
   ══════════════════════════════════════════════════════════════════════════ */

// ── CSRF helper ────────────────────────────────────────────────────────────────
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return '';
}

// ── Toast notification ─────────────────────────────────────────────────────────
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container') || (() => {
    const c = document.createElement('div');
    c.id = 'toast-container';
    c.className = 'position-fixed bottom-0 end-0 p-3';
    c.style.zIndex = '9999';
    document.body.appendChild(c);
    return c;
  })();

  const icons = {
    success: 'bi-check-circle-fill text-success',
    danger:  'bi-x-circle-fill text-danger',
    warning: 'bi-exclamation-triangle-fill text-warning',
    info:    'bi-info-circle-fill text-info',
  };

  const id = `toast-${Date.now()}`;
  container.insertAdjacentHTML('beforeend', `
    <div id="${id}" class="toast align-items-center border-0 shadow" role="alert" aria-live="assertive">
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center gap-2">
          <i class="bi ${icons[type] || icons.info} flex-shrink-0"></i>
          <span>${message}</span>
        </div>
        <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    </div>
  `);

  const toastEl = document.getElementById(id);
  const toast   = new bootstrap.Toast(toastEl, { delay: 3500 });
  toast.show();
  toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

// ══════════════════════════════════════════════════════════════════════════════
// Document Ready
// ══════════════════════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {

  /* ── 1. Confirmation modal (data-confirm-url) ─────────────────────────── */
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
      form.action       = btn.dataset.confirmUrl;
      bootstrap.Modal.getOrCreateInstance(modal).show();
    });
  });

  /* ── 2. AJAX Cascade: Topic → Category → Subcategory ──────────────────── */
  const topicSelect    = document.getElementById('id_topic');
  const categorySelect = document.getElementById('id_category');
  const subcatSelect   = document.getElementById('id_subcategory');

  function enableSelect(el, placeholder) {
    el.disabled  = false;
    el.innerHTML = `<option value="">${placeholder}</option>`;
  }
  function disableSelect(el, placeholder) {
    el.disabled  = true;
    el.innerHTML = `<option value="">${placeholder}</option>`;
  }

  if (topicSelect) {
    topicSelect.addEventListener('change', async () => {
      const topicId = topicSelect.value;
      disableSelect(categorySelect, '— Select Category —');
      disableSelect(subcatSelect,   '— Select Subcategory —');
      updateSubmitButton();
      if (!topicId) return;

      const res  = await fetch(`/ajax/categories/?topic_id=${topicId}`,
                              { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
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
      updateSubmitButton();
      if (!catId) return;

      const res  = await fetch(`/ajax/subcategories/?category_id=${catId}`,
                              { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
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

  /* ── 3. Character counter + pair estimate for bulk textarea ───────────── */
  const rawText      = document.getElementById('id_raw_text');
  const charCount    = document.getElementById('charCount');
  const pairEstimate = document.getElementById('pairEstimate');

  if (rawText) {
    rawText.addEventListener('input', () => {
      const chars = rawText.value.length;
      if (charCount) charCount.textContent = `${chars.toLocaleString()} characters`;
      if (pairEstimate) {
        const est = estimatePairCount(rawText.value);
        pairEstimate.textContent = est > 0 ? `~${est} Q&A pair${est !== 1 ? 's' : ''} detected` : '';
      }
      updateSubmitButton();
    });
  }

  /* ── 4. Enable preview + submit only when all fields filled ──────────── */
  function updateSubmitButton() {
    const previewBtn = document.getElementById('previewBtn');
    const submitBtn  = document.getElementById('submitBtn');
    const ready = subcatSelect?.value
              && rawText?.value.trim().length > 20;

    if (previewBtn) previewBtn.disabled = !ready;
    if (submitBtn)  submitBtn.disabled  = !ready;
  }

  /* ── 5. Preview modal ─────────────────────────────────────────────────── */
  const previewBtn = document.getElementById('previewBtn');
  const bulkForm   = document.getElementById('bulkUploadForm');

  if (previewBtn && bulkForm) {
    previewBtn.addEventListener('click', () => {
      const text  = rawText ? rawText.value : '';
      const count = estimatePairCount(text);
      const el    = document.getElementById('previewCount');
      const sub   = document.getElementById('previewSubcat');
      if (el)  el.textContent  = count;
      if (sub) sub.textContent =
        subcatSelect?.options[subcatSelect.selectedIndex]?.text || '?';
      bootstrap.Modal.getOrCreateInstance(
        document.getElementById('uploadConfirmModal')).show();
    });
  }

  const confirmUploadBtn = document.getElementById('confirmUploadBtn');
  if (confirmUploadBtn && bulkForm) {
    confirmUploadBtn.addEventListener('click', () => {
      bootstrap.Modal.getInstance(
        document.getElementById('uploadConfirmModal'))?.hide();
      bulkForm.submit();
    });
  }

  function estimatePairCount(text) {
    const explicit = (text.match(/\bQ\s*\d*\s*[:\.\)]/gi) || []).length;
    if (explicit > 0) return explicit;
    const numbered = (text.match(/^\s*\d+[\.\)]\s+\S/gm) || []).length;
    if (numbered > 0) return numbered;
    const paras = text.split(/\n{2,}/).filter(p => p.trim().length > 10);
    return Math.floor(paras.length / 2);
  }

  /* ── 6. Favorites (AJAX) ─────────────────────────────────────────────── */
  document.querySelectorAll('.fav-btn').forEach(btn => {
    btn.addEventListener('click', async function(e) {
      e.preventDefault();
      const ct   = this.dataset.contentType;
      const oid  = this.dataset.objectId;
      const icon = this.querySelector('i');

      const resp = await fetch('/ajax/favorites/', {
        method: 'POST',
        headers: {
          'Content-Type':     'application/json',
          'X-CSRFToken':      getCookie('csrftoken'),
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({ content_type: ct, object_id: oid }),
      });
      const data = await resp.json();
      if (data.success) {
        if (data.favorited) {
          icon.className = icon.className.replace('bi-star', 'bi-star-fill');
          icon.classList.add('text-warning');
          this.classList.remove('btn-outline-warning');
          this.classList.add('btn-warning');
        } else {
          icon.className = icon.className.replace('bi-star-fill', 'bi-star');
          icon.classList.remove('text-warning');
          this.classList.remove('btn-warning');
          this.classList.add('btn-outline-warning');
        }
        showToast(data.message, data.favorited ? 'success' : 'info');
      }
    });
  });

  /* ── 7. AJAX Hide ────────────────────────────────────────────────────── */
  document.querySelectorAll('.ajax-hide').forEach(btn => {
    btn.addEventListener('click', async function() {
      const { type, id, name } = this.dataset;
      const result = await Swal.fire({
        title:              `Hide "${name}"?`,
        html:               'All child items will also be hidden from users.',
        icon:               'warning',
        showCancelButton:   true,
        confirmButtonColor: '#f59e0b',
        confirmButtonText:  '<i class="bi bi-eye-slash me-1"></i>Hide',
        cancelButtonText:   'Cancel',
      });
      if (!result.isConfirmed) return;

      const resp = await fetch(`/ajax/${type}s/${id}/hide/`, {
        method:  'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' },
      });
      const data = await resp.json();
      if (data.success) {
        showToast(data.message, 'warning');
        // Update button in place
        const row = document.getElementById(`row-${id}`) ||
                    document.getElementById(`cat-${id}`) ||
                    document.getElementById(`sub-${id}`) ||
                    document.getElementById(`q-${id}`);
        if (row) {
          const badge = row.querySelector('.hidden-badge') || (() => {
            const b = document.createElement('span');
            b.className = 'badge bg-secondary ms-1 hidden-badge';
            b.innerHTML = '<i class="bi bi-eye-slash"></i> Hidden';
            return b;
          })();
          const nameEl = row.querySelector('a, .fw-medium, .fw-semibold');
          if (nameEl) nameEl.after(badge);
          this.className = this.className.replace('ajax-hide btn-outline-warning', 'ajax-unhide btn-outline-success');
          this.innerHTML = '<i class="bi bi-eye"></i>';
          this.dataset.oldHandler = 'hide';
          // Re-bind unhide
          this.addEventListener('click', handleUnhideClick);
          this.removeEventListener('click', handleHideClick);
        } else {
          setTimeout(() => location.reload(), 700);
        }
      } else {
        showToast(data.error, 'danger');
      }
    });
  });

  /* ── 8. AJAX Unhide ──────────────────────────────────────────────────── */
  document.querySelectorAll('.ajax-unhide').forEach(btn => {
    btn.addEventListener('click', handleUnhideClick);
  });

  async function handleUnhideClick() {
    const { type, id } = this.dataset;
    const resp = await fetch(`/ajax/${type}s/${id}/unhide/`, {
      method:  'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' },
    });
    const data = await resp.json();
    if (data.success) {
      showToast(data.message, 'success');
      setTimeout(() => location.reload(), 700);
    } else {
      await Swal.fire('Cannot Unhide', data.error, 'error');
    }
  }

  async function handleHideClick() { /* handled inline above */ }

  /* ── 9. AJAX Delete ──────────────────────────────────────────────────── */
  document.querySelectorAll('.ajax-delete').forEach(btn => {
    btn.addEventListener('click', async function() {
      const { type, id, name } = this.dataset;
      const result = await Swal.fire({
        title:              `Delete "${name}"?`,
        html:               '<span class="text-danger">Permanent — all children will be deleted too.</span>',
        icon:               'error',
        showCancelButton:   true,
        confirmButtonColor: '#ef4444',
        confirmButtonText:  '<i class="bi bi-trash me-1"></i>Delete permanently',
        cancelButtonText:   'Cancel',
      });
      if (!result.isConfirmed) return;

      const urlMap = {
        topic:       `/ajax/topics/${id}/delete/`,
        category:    `/ajax/categories/${id}/delete/`,
        subcategory: `/ajax/subcategories/${id}/delete/`,
        question:    `/ajax/questions/${id}/delete/`,
      };
      const url = urlMap[type];
      if (!url) return;

      const resp = await fetch(url, {
        method:  'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' },
      });
      const data = await resp.json();
      if (data.success) {
        showToast(data.message, 'success');
        const row = document.getElementById(`row-${id}`) ||
                    document.getElementById(`cat-${id}`) ||
                    document.getElementById(`sub-${id}`) ||
                    document.getElementById(`q-${id}`);
        if (row) {
          row.style.transition = 'opacity 0.3s';
          row.style.opacity    = '0';
          setTimeout(() => row.remove(), 300);
        } else {
          setTimeout(() => location.reload(), 700);
        }
      } else {
        showToast(data.error || 'Delete failed', 'danger');
      }
    });
  });

  /* ── 10. CRUD Modal (Create/Edit) ────────────────────────────────────── */
  document.querySelectorAll('[data-crud-action]').forEach(btn => {
    btn.addEventListener('click', () =>
      openCrudModal(btn.dataset.crudAction, btn.dataset.crudType, btn.dataset.crudId));
  });

  /* ── 11. Auto-dismiss flash messages ────────────────────────────────── */
  document.querySelectorAll('.alert-dismissible').forEach(alert => {
    setTimeout(() => {
      bootstrap.Alert.getOrCreateInstance(alert)?.close();
    }, 5000);
  });

  /* ── 12. Prevent back-button cache ──────────────────────────────────── */
  window.addEventListener('pageshow', e => {
    if (e.persisted) window.location.reload();
  });

  /* ── 13. Table search for admin dashboard ────────────────────────────── */
  document.getElementById('tableSearch')?.addEventListener('input', function() {
    const q = this.value.toLowerCase();
    document.querySelectorAll('.content-row').forEach(row => {
      row.style.display = (row.dataset.name || '').includes(q) ? '' : 'none';
    });
  });

});  // end DOMContentLoaded


// ══════════════════════════════════════════════════════════════════════════════
// CRUD Modal — exposed globally so templates can call openCrudModal(...)
// ══════════════════════════════════════════════════════════════════════════════
window.openCrudModal = async function(action, type, id) {
  const modalEl  = document.getElementById('crudModal');
  if (!modalEl) return;
  const modal    = bootstrap.Modal.getOrCreateInstance(modalEl);
  const titleEl  = document.getElementById('crudModalTitleText');
  const bodyEl   = document.getElementById('crudModalBody');
  const saveBtn  = document.getElementById('crudModalSaveBtn');
  const spinner  = document.getElementById('crudSaveSpinner');
  const saveTxt  = document.getElementById('crudSaveBtnText');

  const label = type.charAt(0).toUpperCase() + type.slice(1);
  titleEl.textContent = `${action === 'edit' ? 'Edit' : 'Create'} ${label}`;
  bodyEl.innerHTML    = '<div class="text-center py-4"><div class="spinner-border text-primary"></div></div>';
  modal.show();

  let currentData = {};
  if (action === 'edit' && id) {
    try {
      const resp  = await fetch(`/ajax/${type}s/${id}/edit/`,
                                { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      currentData = await resp.json();
    } catch (e) { /* ignore */ }
  }

  bodyEl.innerHTML = buildCrudForm(type, currentData);
  await initDependentSelects(type, currentData);

  saveBtn.onclick = async () => {
    spinner.classList.remove('d-none');
    saveTxt.textContent = 'Saving…';
    saveBtn.disabled    = true;

    const formData = new FormData(document.getElementById('crudInlineForm'));
    const url = action === 'edit'
      ? `/ajax/${type}s/${id}/edit/`
      : `/ajax/${type}s/create/`;

    const resp = await fetch(url, {
      method:  'POST',
      headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' },
      body:    formData,
    });
    const data = await resp.json();

    spinner.classList.add('d-none');
    saveTxt.textContent = 'Save';
    saveBtn.disabled    = false;

    if (data.success) {
      modal.hide();
      showToast(data.message, 'success');
      setTimeout(() => location.reload(), 600);
    } else {
      // Show error inside modal
      const existing = bodyEl.querySelector('.crud-error');
      if (existing) existing.remove();
      bodyEl.insertAdjacentHTML('afterbegin',
        `<div class="alert alert-danger rounded-3 py-2 px-3 small crud-error">
           <i class="bi bi-exclamation-circle me-1"></i>${data.error || JSON.stringify(data)}
         </div>`);
    }
  };
};

function buildCrudForm(type, data) {
  const statusOptions = ['pending', 'approved', 'rejected']
    .map(s => `<option value="${s}" ${data.status === s ? 'selected' : ''}>${s.charAt(0).toUpperCase() + s.slice(1)}</option>`)
    .join('');

  let fields = '';

  if (type === 'topic') {
    fields = `
      <div class="mb-3">
        <label class="form-label fw-medium">Name <span class="text-danger">*</span></label>
        <input type="text" name="name" class="form-control" value="${escHtml(data.name || '')}" required>
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium">Description</label>
        <textarea name="description" class="form-control" rows="3">${escHtml(data.description || '')}</textarea>
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium">Status</label>
        <select name="status" class="form-select">${statusOptions}</select>
      </div>`;

  } else if (type === 'category') {
    fields = `
      <div class="mb-3">
        <label class="form-label fw-medium">Topic <span class="text-danger">*</span></label>
        <select name="topic" class="form-select" id="modal_topic_sel" required>
          <option value="">— Loading topics… —</option>
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium">Name <span class="text-danger">*</span></label>
        <input type="text" name="name" class="form-control" value="${escHtml(data.name || '')}" required>
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium">Description</label>
        <textarea name="description" class="form-control" rows="3">${escHtml(data.description || '')}</textarea>
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium">Status</label>
        <select name="status" class="form-select">${statusOptions}</select>
      </div>`;

  } else if (type === 'subcategory') {
    fields = `
      <div class="mb-3">
        <label class="form-label fw-medium">Category <span class="text-danger">*</span></label>
        <select name="category" class="form-select" id="modal_category_sel" required>
          <option value="">— Loading categories… —</option>
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium">Name <span class="text-danger">*</span></label>
        <input type="text" name="name" class="form-control" value="${escHtml(data.name || '')}" required>
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium">Status</label>
        <select name="status" class="form-select">${statusOptions}</select>
      </div>`;
  }

  return `<form id="crudInlineForm">${fields}</form>`;
}

async function initDependentSelects(type, data) {
  if (type === 'category') {
    // Populate topics
    const topicSel = document.getElementById('modal_topic_sel');
    if (!topicSel) return;
    // Grab topics from the page's own topic select, or fetch a list
    const pageSel = document.getElementById('id_topic') ||
                    document.querySelector('select[name="topic"]');
    if (pageSel && pageSel.options.length > 1) {
      topicSel.innerHTML = '<option value="">— Select Topic —</option>';
      Array.from(pageSel.options).slice(1).forEach(o => {
        topicSel.insertAdjacentHTML('beforeend',
          `<option value="${o.value}" ${o.value === data.topic_id ? 'selected' : ''}>${o.text}</option>`);
      });
    }

  } else if (type === 'subcategory') {
    // Need to populate all categories
    const catSel = document.getElementById('modal_category_sel');
    if (!catSel) return;
    // We'll fetch via a topic-agnostic approach: use page's own category selects
    const pageCatSel = document.getElementById('id_category') ||
                       document.querySelector('select[name="category"]');
    if (pageCatSel && pageCatSel.options.length > 1) {
      catSel.innerHTML = '<option value="">— Select Category —</option>';
      Array.from(pageCatSel.options).slice(1).forEach(o => {
        catSel.insertAdjacentHTML('beforeend',
          `<option value="${o.value}" ${o.value === data.category_id ? 'selected' : ''}>${o.text}</option>`);
      });
    } else {
      // Fetch from all approved topics' categories
      catSel.innerHTML = '<option value="">— Select Category —</option>';
      // Iterate known topics on dashboard rows
      const topicIds = [...new Set(
        Array.from(document.querySelectorAll('[data-topic-id]')).map(el => el.dataset.topicId)
      )];
      if (topicIds.length === 0) {
        // No topic ids available, try fetching categories for all topics
        // This is best-effort; in production supply a /ajax/all-categories/ endpoint
        catSel.innerHTML = '<option value="">— No categories available —</option>';
        return;
      }
      for (const tid of topicIds) {
        const r = await fetch(`/ajax/categories/?topic_id=${tid}`);
        const d = await r.json();
        d.categories.forEach(c => {
          catSel.insertAdjacentHTML('beforeend',
            `<option value="${c.id}" ${c.id === data.category_id ? 'selected' : ''}>${c.name}</option>`);
        });
      }
    }
  }
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}