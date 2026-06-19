/* ══════════════════════════════════════════════════════════════════════════
   main.js — MindUp  (Bootstrap 5 + SweetAlert2)
   Centralized JS: no duplicate handlers across templates.
   ══════════════════════════════════════════════════════════════════════════ */

'use strict';

/* ── CSRF helper ──────────────────────────────────────────────────────────── */
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return '';
}

/* ── Global loading indicator ─────────────────────────────────────────────── */
const Loader = {
  el: null,
  init() {
    this.el = document.getElementById('global-loader');
  },
  show() {
    this.el?.classList.remove('d-none');
  },
  hide() {
    this.el?.classList.add('d-none');
  },
};

/* ── Toast notification ───────────────────────────────────────────────────── */
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container') || (() => {
    const c = document.createElement('div');
    c.id = 'toast-container';
    c.className = 'position-fixed bottom-0 end-0 p-3';
    c.style.zIndex = '9999';
    c.setAttribute('aria-live', 'polite');
    c.setAttribute('aria-atomic', 'true');
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
    <div id="${id}" class="toast align-items-center border-0 shadow" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center gap-2">
          <i class="bi ${icons[type] || icons.info} flex-shrink-0" aria-hidden="true"></i>
          <span>${message}</span>
        </div>
        <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `);
  const toastEl = document.getElementById(id);
  const toast   = new bootstrap.Toast(toastEl, { delay: 3500 });
  toast.show();
  toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
}

/* ══════════════════════════════════════════════════════════════════════════
   Unified Modal API
   Controls the single #unifiedModal for ALL CRUD / confirm operations.
   ══════════════════════════════════════════════════════════════════════════ */
const UnifiedModal = {
  // Icon map per operation type
  _icons: {
    create:   { cls: 'bi-plus-circle-fill text-primary',           btn: 'btn-primary',     confirmIcon: 'bi-check-lg',  confirmText: 'Create'  },
    edit:     { cls: 'bi-pencil-square text-primary',              btn: 'btn-primary',     confirmIcon: 'bi-check-lg',  confirmText: 'Save'    },
    delete:   { cls: 'bi-exclamation-triangle-fill text-danger',   btn: 'btn-danger',      confirmIcon: 'bi-trash',     confirmText: 'Delete'  },
    hide:     { cls: 'bi-eye-slash-fill text-warning',             btn: 'btn-warning',     confirmIcon: 'bi-eye-slash', confirmText: 'Hide'    },
    unhide:   { cls: 'bi-eye-fill text-success',                   btn: 'btn-success',     confirmIcon: 'bi-eye',       confirmText: 'Unhide'  },
    confirm:  { cls: 'bi-question-circle-fill text-primary',       btn: 'btn-primary',     confirmIcon: 'bi-check-lg',  confirmText: 'Confirm' },
    warning:  { cls: 'bi-exclamation-triangle-fill text-warning',  btn: 'btn-warning',     confirmIcon: 'bi-check-lg',  confirmText: 'Proceed' },
  },

  _modal: null,
  _confirmCallback: null,

  init() {
    const el = document.getElementById('unifiedModal');
    if (!el) return;
    this._modal = bootstrap.Modal.getOrCreateInstance(el);

    // Size control — large for forms, default for confirms
    el.addEventListener('show.bs.modal', () => {
      const dialog = document.getElementById('unifiedModalDialog');
      dialog.classList.toggle('modal-lg', !!this._isForm);
    });

    document.getElementById('unifiedModalConfirmBtn')
      ?.addEventListener('click', () => this._handleConfirm());
  },

  /** Show a simple confirmation modal (no form). */
  confirm({ title, message, type = 'confirm', onConfirm }) {
    this._isForm = false;
    this._confirmCallback = onConfirm;
    this._applyMeta(title, type);
    this._setContent(`<p class="mb-0">${message}</p>`);
    this._clearAlert();
    this._modal?.show();
  },

  /** Show a form-based modal for create / edit. */
  form({ title, html, type = 'create', onConfirm }) {
    this._isForm = true;
    this._confirmCallback = onConfirm;
    this._applyMeta(title, type);
    this._setContent(html);
    this._clearAlert();
    this._modal?.show();
  },

  /** Show the loading skeleton inside the body. */
  showLoader() {
    document.getElementById('unifiedModalLoader')?.classList.remove('d-none');
    document.getElementById('unifiedModalContent').innerHTML = '';
  },

  /** Hide loading skeleton, inject content. */
  hideLoader(html) {
    document.getElementById('unifiedModalLoader')?.classList.add('d-none');
    this._setContent(html);
  },

  showAlert(message, type = 'danger') {
    const el = document.getElementById('unifiedModalAlert');
    if (!el) return;
    el.className = `alert alert-${type} rounded-3 py-2 px-3 small mb-2`;
    el.innerHTML = `<i class="bi bi-exclamation-circle me-1" aria-hidden="true"></i>${message}`;
    el.classList.remove('d-none');
  },

  hide() {
    this._modal?.hide();
  },

  _applyMeta(title, type) {
    const cfg = this._icons[type] || this._icons.confirm;
    document.getElementById('unifiedModalTitleText').textContent = title;
    document.getElementById('unifiedModalIcon').innerHTML =
      `<i class="bi ${cfg.cls}" aria-hidden="true"></i>`;

    const btn = document.getElementById('unifiedModalConfirmBtn');
    btn.className = `btn ${cfg.btn}`;
    document.getElementById('unifiedModalConfirmIcon').className = `bi ${cfg.confirmIcon} me-1`;
    document.getElementById('unifiedModalConfirmText').textContent = cfg.confirmText;
  },

  _setContent(html) {
    document.getElementById('unifiedModalContent').innerHTML = html;
  },

  _clearAlert() {
    const el = document.getElementById('unifiedModalAlert');
    if (el) { el.className = 'd-none'; el.innerHTML = ''; }
  },

  _setLoading(loading) {
    const spinner = document.getElementById('unifiedModalSpinner');
    const btn     = document.getElementById('unifiedModalConfirmBtn');
    const txt     = document.getElementById('unifiedModalConfirmText');
    spinner?.classList.toggle('d-none', !loading);
    if (btn) btn.disabled = loading;
    if (txt) txt.textContent = loading ? 'Working…' : (this._icons[this._currentType]?.confirmText || 'Confirm');
  },

  async _handleConfirm() {
    if (typeof this._confirmCallback === 'function') {
      this._setLoading(true);
      try {
        await this._confirmCallback();
      } finally {
        this._setLoading(false);
      }
    }
  },
};

/* ══════════════════════════════════════════════════════════════════════════
   CRUD Modal — openCrudModal() exposed globally for inline template calls
   ══════════════════════════════════════════════════════════════════════════ */
window.openCrudModal = async function(action, type, id) {
  const label = type.charAt(0).toUpperCase() + type.slice(1);
  const title = `${action === 'edit' ? 'Edit' : 'Create'} ${label}`;

  UnifiedModal.form({ title, html: '', type: action === 'edit' ? 'edit' : 'create', onConfirm: null });
  UnifiedModal.showLoader();

  let currentData = {};
  if (action === 'edit' && id) {
    try {
      const r = await fetch(`/ajax/${type}s/${id}/edit/`,
        { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      currentData = await r.json();
    } catch (_) { /* ignore, proceed with empty */ }
  }

  const formHtml = buildCrudForm(type, currentData);
  UnifiedModal.hideLoader(formHtml);
  await initDependentSelects(type, currentData);

  // Wire up confirm button
  UnifiedModal._confirmCallback = async () => {
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

    if (data.success) {
      UnifiedModal.hide();
      showToast(data.message, 'success');
      setTimeout(() => location.reload(), 600);
    } else {
      UnifiedModal.showAlert(data.error || JSON.stringify(data));
    }
  };
};

/* ── Build CRUD form HTML ─────────────────────────────────────────────────── */
function buildCrudForm(type, data) {
  const statusOptions = ['pending', 'approved', 'rejected']
    .map(s => `<option value="${s}" ${data.status === s ? 'selected' : ''}>${s.charAt(0).toUpperCase() + s.slice(1)}</option>`)
    .join('');

  let fields = '';
  if (type === 'topic') {
    fields = `
      <div class="mb-3">
        <label class="form-label fw-medium" for="crudName">Name <span class="text-danger" aria-hidden="true">*</span></label>
        <input type="text" id="crudName" name="name" class="form-control" value="${escHtml(data.name || '')}" required aria-required="true">
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium" for="crudDesc">Description</label>
        <textarea id="crudDesc" name="description" class="form-control" rows="3">${escHtml(data.description || '')}</textarea>
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium" for="crudStatus">Status</label>
        <select id="crudStatus" name="status" class="form-select">${statusOptions}</select>
      </div>`;
  } else if (type === 'category') {
    fields = `
      <div class="mb-3">
        <label class="form-label fw-medium" for="modal_topic_sel">Topic <span class="text-danger" aria-hidden="true">*</span></label>
        <select id="modal_topic_sel" name="topic" class="form-select" required aria-required="true">
          <option value="">— Loading topics… —</option>
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium" for="crudName">Name <span class="text-danger" aria-hidden="true">*</span></label>
        <input type="text" id="crudName" name="name" class="form-control" value="${escHtml(data.name || '')}" required aria-required="true">
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium" for="crudDesc">Description</label>
        <textarea id="crudDesc" name="description" class="form-control" rows="3">${escHtml(data.description || '')}</textarea>
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium" for="crudStatus">Status</label>
        <select id="crudStatus" name="status" class="form-select">${statusOptions}</select>
      </div>`;
  } else if (type === 'subcategory') {
    fields = `
      <div class="mb-3">
        <label class="form-label fw-medium" for="modal_category_sel">Category <span class="text-danger" aria-hidden="true">*</span></label>
        <select id="modal_category_sel" name="category" class="form-select" required aria-required="true">
          <option value="">— Loading categories… —</option>
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium" for="crudName">Name <span class="text-danger" aria-hidden="true">*</span></label>
        <input type="text" id="crudName" name="name" class="form-control" value="${escHtml(data.name || '')}" required aria-required="true">
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium" for="crudStatus">Status</label>
        <select id="crudStatus" name="status" class="form-select">${statusOptions}</select>
      </div>`;
  } else if (type === 'question') {
    fields = `
      <div class="mb-3">
        <label class="form-label fw-medium" for="modal_subcat_sel">Subcategory <span class="text-danger" aria-hidden="true">*</span></label>
        <select id="modal_subcat_sel" name="subcategory" class="form-select" required aria-required="true">
          <option value="">— Loading… —</option>
        </select>
      </div>
      <div class="mb-3">
        <label class="form-label fw-medium" for="crudTitle">Question <span class="text-danger" aria-hidden="true">*</span></label>
        <textarea id="crudTitle" name="title" class="form-control" rows="4" required aria-required="true">${escHtml(data.title || '')}</textarea>
      </div>`;
  }

  return `<form id="crudInlineForm" novalidate>${fields}</form>`;
}

/* ── Populate dependent selects inside the modal ─────────────────────────── */
async function initDependentSelects(type, data) {
  if (type === 'category') {
    const topicSel = document.getElementById('modal_topic_sel');
    if (!topicSel) return;
    const pageSel = document.getElementById('id_topic') ||
                    document.querySelector('select[name="topic"]');
    if (pageSel && pageSel.options.length > 1) {
      topicSel.innerHTML = '<option value="">— Select Topic —</option>';
      Array.from(pageSel.options).slice(1).forEach(o => {
        topicSel.insertAdjacentHTML('beforeend',
          `<option value="${o.value}" ${o.value === String(data.topic_id) ? 'selected' : ''}>${escHtml(o.text)}</option>`);
      });
    }
  } else if (type === 'subcategory') {
    const catSel = document.getElementById('modal_category_sel');
    if (!catSel) return;
    catSel.innerHTML = '<option value="">— Select Category —</option>';
    // Try to pull from page's existing select
    const pageCatSel = document.getElementById('id_category') ||
                       document.querySelector('select[name="category"]');
    if (pageCatSel && pageCatSel.options.length > 1) {
      Array.from(pageCatSel.options).slice(1).forEach(o => {
        catSel.insertAdjacentHTML('beforeend',
          `<option value="${o.value}" ${o.value === String(data.category_id) ? 'selected' : ''}>${escHtml(o.text)}</option>`);
      });
    } else {
      // Fetch all categories from the server
      try {
        const r = await fetch('/ajax/all-categories/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
        const d = await r.json();
        (d.categories || []).forEach(c => {
          catSel.insertAdjacentHTML('beforeend',
            `<option value="${c.id}" ${c.id === data.category_id ? 'selected' : ''}>${escHtml(c.name)}</option>`);
        });
      } catch (_) { catSel.innerHTML = '<option value="">— No categories available —</option>'; }
    }
  } else if (type === 'question') {
    const subSel = document.getElementById('modal_subcat_sel');
    if (!subSel) return;
    try {
      const r = await fetch('/ajax/all-subcategories/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      const d = await r.json();
      subSel.innerHTML = '<option value="">— Select Subcategory —</option>';
      (d.subcategories || []).forEach(s => {
        subSel.insertAdjacentHTML('beforeend',
          `<option value="${s.id}" ${s.id === data.subcategory_id ? 'selected' : ''}>${escHtml(s.name)}</option>`);
      });
    } catch (_) { subSel.innerHTML = '<option value="">— Error loading subcategories —</option>'; }
  }
}

/* ── Escape HTML helper ──────────────────────────────────────────────────── */
function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

/* ══════════════════════════════════════════════════════════════════════════
   AJAX helpers — shared across all templates via class selectors
   ══════════════════════════════════════════════════════════════════════════ */

/** Generic AJAX POST, returns parsed JSON */
async function ajaxPost(url, extraHeaders = {}) {
  const resp = await fetch(url, {
    method:  'POST',
    headers: {
      'X-CSRFToken':      getCookie('csrftoken'),
      'X-Requested-With': 'XMLHttpRequest',
      ...extraHeaders,
    },
  });
  return resp.json();
}

/** Delete URL map — single source of truth */
function getDeleteUrl(type, id) {
  const map = {
    topic:        `/ajax/topics/${id}/delete/`,
    category:     `/ajax/categories/${id}/delete/`,
    subcategory:  `/ajax/subcategories/${id}/delete/`,
    question:     `/ajax/questions/${id}/delete/`,
    answer:       `/answers/${id}/delete/`,
    bulk_upload:  `/answers/${id}/delete/`,
  };
  return map[type] || '#';
}

/** Remove a row from DOM with fade */
function removeRow(id, type) {
  const selectors = [`#row-${id}`, `#cat-${id}`, `#sub-${id}`, `#q-${id}`, `#answer-${id}`];
  for (const sel of selectors) {
    const el = document.querySelector(sel);
    if (el) {
      el.style.transition = 'opacity 0.3s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 310);
      return true;
    }
  }
  return false;
}

/* ══════════════════════════════════════════════════════════════════════════
   DOMContentLoaded — wire up all global event handlers
   ══════════════════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {

  /* ── Init modules ─────────────────────────────────────────────────────── */
  Loader.init();
  UnifiedModal.init();

  /* ── 1. Auto-dismiss flash messages ──────────────────────────────────── */
  document.querySelectorAll('.auto-dismiss-alert').forEach(alert => {
    const delay = parseInt(alert.dataset.autoDismiss, 10) || 4000;
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert?.close();
    }, delay);
  });

  /* ── 2. Global loading indicator on navigation / form submit ─────────── */
  // Show on all standard <a> navigations (except targets, anchors, modals)
  document.addEventListener('click', e => {
    const anchor = e.target.closest('a[href]');
    if (
      anchor &&
      !anchor.href.startsWith('#') &&
      !anchor.target &&
      !anchor.dataset.bsToggle &&
      !e.ctrlKey && !e.metaKey && !e.shiftKey
    ) {
      Loader.show();
    }
  });
  // Show on form submit
  document.addEventListener('submit', e => {
    if (!e.target.dataset.noLoader) Loader.show();
  });
  // Hide on pageshow (back-button or bfcache restore)
  window.addEventListener('pageshow', e => {
    Loader.hide();
    if (e.persisted) window.location.reload();
  });

  /* ── 3. CRUD modal trigger buttons ───────────────────────────────────── */
  document.querySelectorAll('[data-crud-action]').forEach(btn => {
    btn.addEventListener('click', () =>
      openCrudModal(btn.dataset.crudAction, btn.dataset.crudType, btn.dataset.crudId));
  });

  /* ── 4. Confirmation modal (data-confirm-url, legacy support) ─────────── */
  document.querySelectorAll('[data-confirm-url]').forEach(btn => {
    btn.addEventListener('click', e => {
      e.preventDefault();
      UnifiedModal.confirm({
        title:    btn.dataset.confirmAction || 'Confirm',
        message:  btn.dataset.confirmMessage || 'Are you sure?',
        type:     'confirm',
        onConfirm: async () => {
          Loader.show();
          const form = document.createElement('form');
          form.method = 'POST';
          form.action = btn.dataset.confirmUrl;
          const csrf = document.createElement('input');
          csrf.type = 'hidden'; csrf.name = 'csrfmiddlewaretoken'; csrf.value = getCookie('csrftoken');
          form.appendChild(csrf);
          document.body.appendChild(form);
          form.submit();
        },
      });
    });
  });

  /* ── 5. Favorites (AJAX) ─────────────────────────────────────────────── */
  document.querySelectorAll('.fav-btn').forEach(btn => {
    btn.addEventListener('click', async function(e) {
      e.preventDefault();
      const ct   = this.dataset.contentType;
      const oid  = this.dataset.objectId;
      const icon = this.querySelector('i');

      try {
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
            icon.classList.remove('text-muted');
            this.classList.remove('btn-outline-warning');
            this.classList.add('btn-warning');
          } else {
            icon.className = icon.className.replace('bi-star-fill', 'bi-star');
            icon.classList.remove('text-warning');
            icon.classList.add('text-muted');
            this.classList.remove('btn-warning');
            this.classList.add('btn-outline-warning');
          }
          this.setAttribute('aria-pressed', data.favorited ? 'true' : 'false');
          showToast(data.message, data.favorited ? 'success' : 'info');
        }
      } catch (_) { showToast('Could not update favorite', 'danger'); }
    });
  });

  /* ── 6. AJAX Hide ────────────────────────────────────────────────────── */
  document.querySelectorAll('.ajax-hide').forEach(btn => {
    btn.addEventListener('click', async function() {
      const { type, id, name } = this.dataset;
      UnifiedModal.confirm({
        title:   `Hide "${name}"?`,
        message: 'All child items will also be hidden from users.',
        type:    'hide',
        onConfirm: async () => {
          Loader.show();
          try {
            const data = await ajaxPost(`/ajax/${type}s/${id}/hide/`);
            UnifiedModal.hide();
            Loader.hide();
            if (data.success) {
              showToast(data.message, 'warning');
              setTimeout(() => location.reload(), 700);
            } else {
              showToast(data.error || 'Hide failed', 'danger');
            }
          } catch (_) { Loader.hide(); showToast('Request failed', 'danger'); }
        },
      });
    });
  });

  /* ── 7. AJAX Unhide ──────────────────────────────────────────────────── */
  document.querySelectorAll('.ajax-unhide').forEach(btn => {
    btn.addEventListener('click', async function() {
      const { type, id, name } = this.dataset;
      UnifiedModal.confirm({
        title:   `Unhide "${name || type}"?`,
        message: 'This item will become visible to all users.',
        type:    'unhide',
        onConfirm: async () => {
          Loader.show();
          try {
            const data = await ajaxPost(`/ajax/${type}s/${id}/unhide/`);
            UnifiedModal.hide();
            Loader.hide();
            if (data.success) {
              showToast(data.message, 'success');
              setTimeout(() => location.reload(), 700);
            } else {
              showToast(data.error || 'Cannot unhide', 'danger');
            }
          } catch (_) { Loader.hide(); showToast('Request failed', 'danger'); }
        },
      });
    });
  });

  /* ── 8. AJAX Delete ──────────────────────────────────────────────────── */
  document.querySelectorAll('.ajax-delete').forEach(btn => {
    btn.addEventListener('click', async function() {
      const { type, id, name } = this.dataset;
      const redirect = this.dataset.redirect || null;
      const deleteUrl = this.dataset.deleteUrl || getDeleteUrl(type, id);

      UnifiedModal.confirm({
        title:   `Delete "${name}"?`,
        message: '<span class="text-danger fw-semibold">Permanent — all children will be deleted too. This cannot be undone.</span>',
        type:    'delete',
        onConfirm: async () => {
          Loader.show();
          try {
            const resp = await fetch(deleteUrl, {
              method:  'POST',
              headers: { 'X-CSRFToken': getCookie('csrftoken'), 'X-Requested-With': 'XMLHttpRequest' },
            });
            const data = await resp.json();
            UnifiedModal.hide();
            Loader.hide();
            if (data.success) {
              showToast(data.message, 'success');
              if (redirect) {
                setTimeout(() => { window.location.href = redirect; }, 700);
              } else if (!removeRow(id, type)) {
                setTimeout(() => location.reload(), 700);
              }
            } else {
              showToast(data.error || 'Delete failed', 'danger');
            }
          } catch (_) { Loader.hide(); showToast('Request failed', 'danger'); }
        },
      });
    });
  });

  /* ── 9. AJAX Admin approve/reject (pending approvals) ────────────────── */
  document.querySelectorAll('.ajax-hide, .ajax-unhide, .ajax-delete').forEach(() => {
    // handled above — no-op, just ensuring querySelectorAll doesn't chain
  });

  /* ── 10. Cascade: Topic → Category → Subcategory (bulk upload & forms) ── */
  const topicSelect    = document.getElementById('id_topic');
  const categorySelect = document.getElementById('id_category');
  const subcatSelect   = document.getElementById('id_subcategory');

  function enableSelect(el, placeholder) {
    if (!el) return;
    el.disabled  = false;
    el.innerHTML = `<option value="">${placeholder}</option>`;
  }
  function disableSelect(el, placeholder) {
    if (!el) return;
    el.disabled  = true;
    el.innerHTML = `<option value="">${placeholder}</option>`;
  }

  if (topicSelect) {
    topicSelect.addEventListener('change', async () => {
      disableSelect(categorySelect, '— Select Category —');
      disableSelect(subcatSelect,   '— Select Subcategory —');
      updateBulkSubmit();
      if (!topicSelect.value) return;
      const res  = await fetch(`/ajax/categories/?topic_id=${topicSelect.value}`,
                               { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      const data = await res.json();
      enableSelect(categorySelect, '— Select Category —');
      (data.categories || []).forEach(c => {
        categorySelect.insertAdjacentHTML('beforeend',
          `<option value="${c.id}">${escHtml(c.name)}</option>`);
      });
      updateBulkSubmit();
    });
  }

  if (categorySelect) {
    categorySelect.addEventListener('change', async () => {
      disableSelect(subcatSelect, '— Select Subcategory —');
      updateBulkSubmit();
      if (!categorySelect.value) return;
      const res  = await fetch(`/ajax/subcategories/?category_id=${categorySelect.value}`,
                               { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      const data = await res.json();
      enableSelect(subcatSelect, '— Select Subcategory —');
      (data.subcategories || []).forEach(s => {
        subcatSelect.insertAdjacentHTML('beforeend',
          `<option value="${s.id}">${escHtml(s.name)}</option>`);
      });
      updateBulkSubmit();
    });
  }

  if (subcatSelect) subcatSelect.addEventListener('change', updateBulkSubmit);

  /* ── 11. Bulk upload: char counter + pair estimate ──────────────────── */
  const rawText      = document.getElementById('id_raw_text');
  const charCount    = document.getElementById('charCount');
  const pairEstimate = document.getElementById('pairEstimate');

  if (rawText) {
    rawText.addEventListener('input', () => {
      const chars = rawText.value.length;
      if (charCount)    charCount.textContent    = `${chars.toLocaleString()} characters`;
      if (pairEstimate) pairEstimate.textContent =
        ((est) => est > 0 ? `~${est} Q&A pair${est !== 1 ? 's' : ''} detected` : '')(estimatePairCount(rawText.value));
      updateBulkSubmit();
    });
  }

  function updateBulkSubmit() {
    const ready = !!subcatSelect?.value && (rawText?.value.trim().length ?? 0) > 20;
    ['previewBtn', 'submitBtn'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.disabled = !ready;
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

  /* ── 12. Bulk upload preview modal ──────────────────────────────────── */
  const previewBtn = document.getElementById('previewBtn');
  const bulkForm   = document.getElementById('bulkUploadForm');
  if (previewBtn && bulkForm) {
    previewBtn.addEventListener('click', () => {
      const count = estimatePairCount(rawText?.value || '');
      document.getElementById('previewCount')?.textContent = count;
      document.getElementById('previewSubcat')?.textContent =
        subcatSelect?.options[subcatSelect.selectedIndex]?.text || '?';
      bootstrap.Modal.getOrCreateInstance(
        document.getElementById('uploadConfirmModal'))?.show();
    });
  }

  const confirmUploadBtn = document.getElementById('confirmUploadBtn');
  if (confirmUploadBtn && bulkForm) {
    confirmUploadBtn.addEventListener('click', () => {
      bootstrap.Modal.getInstance(
        document.getElementById('uploadConfirmModal'))?.hide();
      Loader.show();
      bulkForm.submit();
    });
  }

  /* ── 13. Admin table search filter ───────────────────────────────────── */
  document.getElementById('tableSearch')?.addEventListener('input', function() {
    const q = this.value.toLowerCase();
    document.querySelectorAll('.content-row').forEach(row => {
      row.style.display = (row.dataset.name || '').toLowerCase().includes(q) ? '' : 'none';
    });
  });

  /* ── 14. Login page: password show/hide toggle ──────────────────────── */
  const togglePw = document.getElementById('togglePw');
  const pwField  = document.getElementById('id_password');
  const eyeIcon  = document.getElementById('eyeIcon');
  if (togglePw && pwField && eyeIcon) {
    togglePw.addEventListener('click', () => {
      const isText = pwField.type === 'text';
      pwField.type = isText ? 'password' : 'text';
      eyeIcon.className = isText ? 'bi bi-eye' : 'bi bi-eye-slash';
    });
  }

  /* ── 15. Login form client-side validation ──────────────────────────── */
  document.getElementById('loginForm')?.addEventListener('submit', function(e) {
    let ok = true;
    ['id_email', 'id_password'].forEach(id => {
      const f = document.getElementById(id);
      if (f && !f.value.trim()) { f.classList.add('is-invalid'); ok = false; }
      else f?.classList.remove('is-invalid');
    });
    if (!ok) e.preventDefault();
  });

}); // end DOMContentLoaded