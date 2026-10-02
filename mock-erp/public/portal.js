/* Globex AP Portal — the eight-step click path Lab 4 automates.
 * 1 Enter vendor invoice → 2 Vendor Name → 3 Search → 4 select vendor row (auto when one match) → 5 Next
 * → 6 Invoice Number / PO Number / Total Amount → 7 Next → 8 Post voucher and release for payment. */
(function () {
  const $ = (id) => document.getElementById(id);
  const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;',
  })[character]);
  const api = (path, init) => fetch(path.startsWith('/') ? path : '/' + path, init).then(async (r) => {
    const body = await r.json().catch(() => ({}));
    if (r.status === 401) showAuth('Your workshop session is missing or expired. Sign in with the shared training account.');
    if (!r.ok) throw new Error(body.error || r.statusText);
    return body;
  });

  const state = { vendor: null, invoiceNumber: '', poNumber: '', totalAmount: NaN, poCheck: null };
  const mockInvoices = [
    { id: 'NW-88214', vendor: 'Northwind Office Supplies Inc.', po: 'PO-2026-0431', invoiceDate: 'Sep 02, 2026', dueDate: 'Oct 02, 2026', amount: 4155.40, match: 'matched', matchLabel: '3-way matched', workflow: 'ready', workflowLabel: 'Ready to post' },
    { id: 'CL-9913', vendor: 'Contoso Logistics LLC', po: 'PO-2026-0447', invoiceDate: 'Aug 09, 2026', dueDate: 'Sep 23, 2026', amount: 12740.00, match: 'matched', matchLabel: '3-way matched', workflow: 'approval', workflowLabel: 'Awaiting approval', dueSoon: true },
    { id: 'AF-20318', vendor: 'Ableton Fabrication, Inc.', po: 'PO-2026-0452', invoiceDate: 'Sep 04, 2026', dueDate: 'Oct 04, 2026', amount: 4026.88, match: 'matched', matchLabel: '3-way matched', workflow: 'ready', workflowLabel: 'Ready to post' },
    { id: 'MCS-26-0901', vendor: 'Meridian Cloud Services Corp.', po: 'PO-2026-0399', invoiceDate: 'Aug 22, 2026', dueDate: 'Sep 21, 2026', amount: 16980.00, match: 'matched', matchLabel: '3-way matched', workflow: 'approval', workflowLabel: 'Awaiting approval', dueSoon: true },
    { id: 'BH-4419', vendor: 'Blue Harbor Catering Co.', po: 'PO-2026-0461', invoiceDate: 'Sep 05, 2026', dueDate: 'Sep 20, 2026', amount: 2954.00, match: 'failed', matchLabel: 'Vendor blocked', workflow: 'exception', workflowLabel: 'On hold', dueSoon: true },
    { id: 'GLS-87315', vendor: 'Great Lakes Steel Supply Inc.', po: 'PO-2026-0470', invoiceDate: 'Aug 24, 2026', dueDate: 'Sep 23, 2026', amount: 17988.20, match: 'failed', matchLabel: 'Price variance', workflow: 'exception', workflowLabel: 'Match exception', dueSoon: true },
    { id: 'LP-10422', vendor: 'Liberty Print & Signage LLC', po: 'PO-2026-0476', invoiceDate: 'Sep 08, 2026', dueDate: 'Oct 08, 2026', amount: 4946.40, match: 'matched', matchLabel: '3-way matched', workflow: 'ready', workflowLabel: 'Ready to post' },
    { id: 'SFG-77602', vendor: 'Summit Facilities Group', po: 'PO-2026-0468', invoiceDate: 'Sep 10, 2026', dueDate: 'Oct 10, 2026', amount: 3699.26, match: 'matched', matchLabel: '3-way matched', workflow: 'posted', workflowLabel: 'Posted' },
    { id: 'VA-8831', vendor: 'Vertex Analytics Corp.', po: 'PO-2026-0405', invoiceDate: 'Aug 11, 2026', dueDate: 'Sep 25, 2026', amount: 22700.00, match: 'matched', matchLabel: '3-way matched', workflow: 'approval', workflowLabel: 'Awaiting approval' },
    { id: 'PT-6604', vendor: 'Pacific Timber Company', po: 'PO-2026-0489', invoiceDate: 'Sep 06, 2026', dueDate: 'Oct 06, 2026', amount: 7840.00, match: 'failed', matchLabel: 'PO not found', workflow: 'exception', workflowLabel: 'Match exception' },
  ];
  let submittedInvoices = [];
  let activeFilter = 'all';
  let searchQuery = '';

  function show(step) {
    document.querySelectorAll('section.panel').forEach((s) => (s.hidden = s.dataset.step !== step));
    $('crumbs').hidden = step === 'home';
    document.querySelectorAll('#crumbs span').forEach((c) => c.classList.toggle('on', c.dataset.step === step));
    $('page-context').textContent = step === 'home' ? 'Overview' : step === 'confirmation' ? 'Voucher posted' : 'New vendor invoice';
    window.scrollTo(0, 0);
  }

  const money = (n, cur) => `${Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} ${cur || ''}`.trim();

  function showAuth(message = '') {
    $('portal-shell').hidden = true;
    $('auth-shell').hidden = false;
    $('auth-message').textContent = message;
    $('input-portal-username').focus();
  }

  function showPortal(session) {
    $('auth-shell').hidden = true;
    $('portal-shell').hidden = false;
    if (session.participantId && session.participantId !== 'local') {
      $('session').hidden = false;
      $('session-participant').textContent = session.displayName || (session.participantId.startsWith('portal-') ? 'ap_user' : session.participantId);
    }
  }

  async function signIn(username, password) {
    const response = await fetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || 'The training credentials were rejected.');
    return body;
  }

  async function exchangeToken(accessToken) {
    const response = await fetch('/auth/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ accessToken }),
    });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body.error || 'The access token was rejected.');
    return body;
  }

  async function bootstrapAuth() {
    const fragment = new URLSearchParams(window.location.hash.slice(1));
    const token = fragment.get('access_token');
    try {
      let session;
      if (token) {
        session = await exchangeToken(token);
        history.replaceState(null, document.title, `${window.location.pathname}${window.location.search}`);
      } else {
        const response = await fetch('/auth/status');
        session = await response.json().catch(() => ({}));
        if (!response.ok) {
          showAuth();
          return;
        }
      }
      showPortal(session);
      await loadPostings();
    } catch (error) {
      showAuth(error.message);
    }
  }

  $('auth-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = $('btn-sign-in');
    button.disabled = true;
    $('auth-message').textContent = '';
    try {
      const session = await signIn($('input-portal-username').value.trim(), $('input-portal-password').value);
      $('input-portal-password').value = '';
      showPortal(session);
      await loadPostings();
    } catch (error) {
      showAuth(error.message);
    } finally {
      button.disabled = false;
    }
  });

  $('btn-sign-out').addEventListener('click', async () => {
    await fetch('/auth/logout', { method: 'POST' });
    $('session').hidden = true;
    showAuth('Signed out. Use the shared training credentials to return.');
  });

  const currency = (n) => `$${Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

  function renderInvoices() {
    const body = $('postings-body');
    const all = [...submittedInvoices, ...mockInvoices];
    const rows = all.filter((invoice) => {
      const matchesFilter = activeFilter === 'all' || invoice.workflow === activeFilter;
      const haystack = `${invoice.id} ${invoice.vendor} ${invoice.po}`.toLowerCase();
      return matchesFilter && haystack.includes(searchQuery);
    });
    body.innerHTML = '';
    $('record-count').textContent = `${rows.length} record${rows.length === 1 ? '' : 's'}`;
    if (!rows.length) {
      body.innerHTML = '<tr class="empty"><td colspan="9">No invoices match this workbench view.</td></tr>';
      return;
    }
    for (const invoice of rows) {
      const tr = document.createElement('tr');
      tr.dataset.invoiceId = invoice.id;
      tr.dataset.workflow = invoice.workflow;
      const matchClass = invoice.match === 'failed' ? 'failed' : invoice.match === 'pending' ? 'pending' : '';
      tr.innerHTML =
        `<td><input type="checkbox" aria-label="Select invoice ${escapeHtml(invoice.id)}"></td>` +
        `<td class="invoice-cell"><strong>${escapeHtml(invoice.id)}</strong><small title="${escapeHtml(invoice.vendor)}">${escapeHtml(invoice.vendor)}</small></td>` +
        `<td class="po-cell">${escapeHtml(invoice.po)}</td><td class="date-cell">${escapeHtml(invoice.invoiceDate)}</td>` +
        `<td class="date-cell ${invoice.dueSoon ? 'due-soon' : ''}">${escapeHtml(invoice.dueDate)}</td>` +
        `<td class="num"><strong>${escapeHtml(currency(invoice.amount))}</strong></td>` +
        `<td><span class="match ${matchClass}">${escapeHtml(invoice.matchLabel)}</span></td>` +
        `<td><span class="status-badge ${escapeHtml(invoice.workflow)}">${escapeHtml(invoice.workflowLabel)}</span></td>` +
        `<td><button class="row-menu" type="button" aria-label="Actions for ${escapeHtml(invoice.id)}">•••</button></td>`;
      body.appendChild(tr);
    }
  }

  async function loadPostings() {
    const { postings } = await api('/api/postings');
    submittedInvoices = postings.map((p) => ({
      id: p.invoiceNumber,
      postingId: p.postingId,
      vendor: p.vendorName,
      po: p.poNumber,
      invoiceDate: new Date(p.submittedAt).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }),
      dueDate: 'Next payment run',
      amount: p.totalAmount,
      match: 'matched',
      matchLabel: 'PO validated',
      workflow: 'posted',
      workflowLabel: 'Posted',
    }));
    renderInvoices();
  }

  function resetFlow() {
    Object.assign(state, { vendor: null, invoiceNumber: '', poNumber: '', totalAmount: NaN, poCheck: null });
    $('input-vendor-name').value = '';
    $('vendor-results').hidden = true;
    $('vendor-results-body').innerHTML = '';
    $('vendor-search-message').textContent = 'Active and blocked supplier records are included in the master-data search.';
    $('btn-next-1').disabled = true;
    ['input-invoice-number', 'input-po-number', 'input-total-amount'].forEach((id) => ($(id).value = ''));
    $('invoice-message').textContent = '';
  }

  function selectVendor(v) {
    state.vendor = v;
    document.querySelectorAll('#vendor-results-body tr').forEach((tr) => {
      const on = tr.dataset.vendorId === v.vendorId;
      tr.classList.toggle('selected', on);
      tr.querySelector('input[type=radio]').checked = on;
    });
    $('btn-next-1').disabled = false;
  }

  // 1 · Enter vendor invoice
  $('btn-post-invoice').addEventListener('click', () => {
    resetFlow();
    show('vendor');
    $('input-vendor-name').focus();
  });

  // 3 · Search (2 is typing into #input-vendor-name)
  async function search() {
    const q = $('input-vendor-name').value.trim();
    const msg = $('vendor-search-message');
    const table = $('vendor-results');
    const body = $('vendor-results-body');
    body.innerHTML = '';
    state.vendor = null;
    $('btn-next-1').disabled = true;
    if (!q) {
      msg.textContent = 'Enter a vendor name to search.';
      table.hidden = true;
      return;
    }
    const { vendors } = await api(`/api/vendors?q=${encodeURIComponent(q)}`);
    if (!vendors.length) {
      msg.textContent = `No vendor matches "${q}".`;
      table.hidden = true;
      return;
    }
    msg.textContent = `${vendors.length} vendor${vendors.length === 1 ? '' : 's'} found.`;
    for (const v of vendors) {
      const tr = document.createElement('tr');
      tr.className = 'selectable';
      tr.dataset.vendorId = v.vendorId;
      tr.innerHTML =
        `<td><input type="radio" name="vendor" id="vendor-row-${escapeHtml(v.vendorId)}" value="${escapeHtml(v.vendorId)}" aria-label="Select ${escapeHtml(v.vendorName)}"></td>` +
        `<td>${escapeHtml(v.vendorId)}</td><td>${escapeHtml(v.vendorName)}</td><td>${escapeHtml(v.taxId)}</td>` +
        `<td>${escapeHtml(v.paymentTerms)}</td><td><span class="status ${v.status === 'ACTIVE' ? 'ok' : 'inactive'}">${escapeHtml(v.status)}</span></td>` +
        `<td>${escapeHtml(v.openPurchaseOrders.join(', ') || '—')}</td>`;
      tr.addEventListener('click', () => selectVendor(v));
      body.appendChild(tr);
    }
    table.hidden = false;
    // 4 · one match selects itself; the robot only has to click a row when several vendors match
    if (vendors.length === 1) selectVendor(vendors[0]);
  }
  $('btn-search').addEventListener('click', search);
  $('input-vendor-name').addEventListener('keydown', (e) => e.key === 'Enter' && search());
  $('btn-cancel-1').addEventListener('click', () => show('home'));

  // 5 · Next
  $('btn-next-1').addEventListener('click', () => {
    if (!state.vendor) return;
    $('invoice-vendor-name').textContent = state.vendor.vendorName;
    $('invoice-vendor-id').textContent = state.vendor.vendorId;
    show('invoice');
    $('input-invoice-number').focus();
  });
  $('btn-back-1').addEventListener('click', () => show('vendor'));

  // 7 · Next (6 is the three fields)
  $('btn-next-2').addEventListener('click', async () => {
    const invoiceNumber = $('input-invoice-number').value.trim();
    const poNumber = $('input-po-number').value.trim().toUpperCase();
    const totalAmount = Number(String($('input-total-amount').value).replace(/[^0-9.-]/g, ''));
    const msg = $('invoice-message');
    if (!invoiceNumber || !poNumber || !Number.isFinite(totalAmount) || totalAmount <= 0) {
      msg.textContent = 'Invoice Number, PO Number, and a positive Total Amount are required.';
      return;
    }
    msg.textContent = '';
    Object.assign(state, { invoiceNumber, poNumber, totalAmount });
    $('review-vendor').textContent = `${state.vendor.vendorName} (${state.vendor.vendorId})`;
    $('review-invoice-number').textContent = invoiceNumber;
    $('review-po-number').textContent = poNumber;
    $('review-total-amount').textContent = money(totalAmount, state.vendor.currency);
    $('journal-debit').textContent = currency(totalAmount);
    $('journal-credit').textContent = currency(totalAmount);
    const status = $('review-po-status');
    status.textContent = 'Checking purchase order…';
    status.className = 'control-status pending';
    show('review');
    try {
      const { po } = await api('/api/po-lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vendorName: state.vendor.vendorName, poNumber, invoiceTotal: totalAmount, currency: state.vendor.currency }),
      });
      state.poCheck = po;
      status.textContent = po.found
        ? `PO found · ${money(po.openAmount, po.currency)} open · vendor ${po.vendorActive ? 'active' : 'blocked'}`
        : 'PO not found · exception override permitted in training mode';
      status.className = `control-status ${po.found && po.vendorActive ? 'pass' : 'fail'}`;
      document.querySelector('#step-review .status-badge').textContent = po.found && po.vendorActive ? 'Controls passed' : 'Override required';
      document.querySelector('#step-review .status-badge').className = `status-badge ${po.found && po.vendorActive ? 'ready' : 'exception'}`;
    } catch (err) {
      status.textContent = `PO check unavailable: ${err.message}`;
      status.className = 'control-status fail';
    }
  });
  $('btn-back-2').addEventListener('click', () => show('invoice'));

  // 8 · Post voucher and release for payment
  $('btn-submit-payment').addEventListener('click', async () => {
    const btn = $('btn-submit-payment');
    btn.disabled = true;
    try {
      const posting = await api('/api/postings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vendorId: state.vendor.vendorId,
          invoiceNumber: state.invoiceNumber,
          poNumber: state.poNumber,
          totalAmount: state.totalAmount,
          currency: state.vendor.currency,
        }),
      });
      $('confirmation-id').textContent = posting.postingId;
      $('confirmation-status').textContent = 'Submitted for payment';
      $('confirmation-detail').textContent = `${posting.vendorName} · invoice ${posting.invoiceNumber} · ${posting.poNumber} · ${money(posting.totalAmount, posting.currency)}`;
      show('confirmation');
      loadPostings();
    } catch (err) {
      alert(`Could not submit: ${err.message}`);
    } finally {
      btn.disabled = false;
    }
  });

  $('btn-post-another').addEventListener('click', () => {
    resetFlow();
    show('vendor');
    $('input-vendor-name').focus();
  });
  $('btn-home').addEventListener('click', () => show('home'));

  function activateFilter(filter) {
    activeFilter = filter;
    document.querySelectorAll('.table-tabs button').forEach((button) => button.classList.toggle('active', button.dataset.filter === filter));
    renderInvoices();
    document.querySelector('.workbench-card').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  document.querySelectorAll('.table-tabs button').forEach((button) => button.addEventListener('click', () => activateFilter(button.dataset.filter)));
  document.querySelectorAll('[data-filter-jump]').forEach((button) => button.addEventListener('click', () => activateFilter(button.dataset.filterJump)));
  $('invoice-search').addEventListener('input', (event) => {
    searchQuery = event.target.value.trim().toLowerCase();
    renderInvoices();
  });

  let toastTimer;
  function toast(message) {
    const element = $('toast');
    element.textContent = message;
    element.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (element.hidden = true), 2600);
  }

  document.querySelectorAll('[data-nav]').forEach((button) => button.addEventListener('click', () => {
    const destination = button.dataset.nav;
    if (destination === 'home') {
      show('home');
      activateFilter('all');
      return;
    }
    if (destination === 'invoices') return activateFilter('all');
    if (destination === 'approvals') return activateFilter('approval');
    const label = button.textContent.trim().replace(/\d+$/, '').trim();
    toast(`${label} is read-only in this training tenant.`);
  }));

  document.querySelectorAll('[data-cancel-flow]').forEach((button) => button.addEventListener('click', () => show('home')));
  $('btn-export').addEventListener('click', () => {
    const rows = [...submittedInvoices, ...mockInvoices];
    const csv = [
      ['Invoice', 'Supplier', 'Purchase Order', 'Invoice Date', 'Due Date', 'Gross Amount', 'Match Status', 'Workflow Status'],
      ...rows.map((item) => [item.id, item.vendor, item.po, item.invoiceDate, item.dueDate, item.amount.toFixed(2), item.matchLabel, item.workflowLabel]),
    ].map((row) => row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(',')).join('\n');
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    link.download = 'globex-ap-invoice-register-sep-2026.csv';
    link.click();
    URL.revokeObjectURL(link.href);
    toast('Invoice register exported.');
  });

  bootstrapAuth();
})();
