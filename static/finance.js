// HOME FINANCE & UTILITIES // Production Logic
(function() {
  const metricBalance = document.getElementById('metricBalance');
  const metricExpense = document.getElementById('metricExpense');
  const metricUtility = document.getElementById('metricUtility');
  const goalsContainer = document.getElementById('goalsContainer');
  const utilitiesTableBody = document.getElementById('utilitiesTableBody');
  const txTableBody = document.getElementById('txTableBody');

  const viewTabs = document.querySelectorAll('.v-tab');
  const tabPanes = document.querySelectorAll('.tab-pane');

  // Modals
  const txModal = document.getElementById('txModal');
  const btnOpenTxModal = document.getElementById('btnOpenTxModal');
  const btnCloseTxModal = document.getElementById('btnCloseTxModal');
  const btnSubmitTx = document.getElementById('btnSubmitTx');
  const txType = document.getElementById('txType');
  const txCategory = document.getElementById('txCategory');
  const txAmount = document.getElementById('txAmount');
  const txDate = document.getElementById('txDate');
  const txNote = document.getElementById('txNote');

  const metersModal = document.getElementById('metersModal');
  const btnOpenMetersModal = document.getElementById('btnOpenMetersModal');
  const btnCloseMetersModal = document.getElementById('btnCloseMetersModal');
  const btnSubmitMeters = document.getElementById('btnSubmitMeters');
  const meterPeriod = document.getElementById('meterPeriod');
  const mElecDay = document.getElementById('mElecDay');
  const mElecNight = document.getElementById('mElecNight');
  const mColdWater = document.getElementById('mColdWater');
  const mHotWater = document.getElementById('mHotWater');
  const mGas = document.getElementById('mGas');

  const goalModal = document.getElementById('goalModal');
  const btnOpenGoalModal = document.getElementById('btnOpenGoalModal');
  const btnCloseGoalModal = document.getElementById('btnCloseGoalModal');
  const btnSubmitGoal = document.getElementById('btnSubmitGoal');
  const goalTitle = document.getElementById('goalTitle');
  const goalTarget = document.getElementById('goalTarget');

  // Tab switching
  viewTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      viewTabs.forEach(t => t.classList.remove('active'));
      tabPanes.forEach(p => p.classList.add('hidden'));

      tab.classList.add('active');
      const pane = document.getElementById('pane' + tab.dataset.tab.charAt(0).toUpperCase() + tab.dataset.tab.slice(1));
      if (pane) pane.classList.remove('hidden');

      if (tab.dataset.tab === 'transactions') fetchTransactions();
      if (tab.dataset.tab === 'utilities') fetchUtilities();
    });
  });

  // Fetch Summary
  async function fetchSummary() {
    try {
      const res = await fetch('/api/summary');
      const data = await res.json();
      metricBalance.textContent = `${Math.round(data.net_balance).toLocaleString()} ₽`;
      metricExpense.textContent = `${Math.round(data.total_expense).toLocaleString()} ₽`;
      metricUtility.textContent = `${Math.round(data.latest_utility_bill).toLocaleString()} ₽`;
    } catch (e) {
      console.error(e);
    }
  }

  // Fetch Goals
  async function fetchGoals() {
    try {
      const res = await fetch('/api/goals');
      const data = await res.json();
      goalsContainer.innerHTML = '';

      data.goals.forEach(g => {
        const card = document.createElement('div');
        card.className = 'goal-card';
        card.innerHTML = `
          <div class="goal-top">
            <span>${escapeHtml(g.title)}</span>
            <span class="text-jade font-mono">${g.progress_pct}%</span>
          </div>
          <div class="goal-bar-track">
            <div class="goal-bar-fill" style="width: ${g.progress_pct}%;"></div>
          </div>
          <div class="goal-nums font-mono">
            <span>${Math.round(g.current_amount).toLocaleString()} ₽</span>
            <span class="text-muted">Цель: ${Math.round(g.target_amount).toLocaleString()} ₽</span>
          </div>
          <button class="goal-btn-deposit" data-id="${g.id}">+ 1 000 ₽ ВЗНОС</button>
        `;

        card.querySelector('.goal-btn-deposit').addEventListener('click', async () => {
          await fetch(`/api/goals/${g.id}/contribute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ amount: 1000.0 })
          });
          fetchGoals();
          fetchSummary();
        });

        goalsContainer.appendChild(card);
      });
    } catch (e) {
      console.error(e);
    }
  }

  // Fetch Utilities
  async function fetchUtilities() {
    try {
      const res = await fetch('/api/utilities');
      const data = await res.json();
      utilitiesTableBody.innerHTML = '';

      data.readings.forEach(u => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td style="font-weight:700;" class="font-mono">${u.period_month}</td>
          <td>День: ${u.elec_day_val} кВт⋅ч (${u.elec_day_cost} ₽)<br>Ночь: ${u.elec_night_val} кВт⋅ч (${u.elec_night_cost} ₽)</td>
          <td>Хол: ${u.cold_water_val} м³ (${u.cold_water_cost} ₽)<br>Гор: ${u.hot_water_val} м³ (${u.hot_water_cost} ₽)</td>
          <td>${u.gas_val} м³ (${u.gas_cost} ₽)</td>
          <td>Инет: ${u.fixed_internet} ₽<br>Тепло: ${u.fixed_heating} ₽</td>
          <td style="font-weight:700;font-size:13px;" class="text-jade font-mono">${u.total_bill.toLocaleString()} ₽</td>
        `;
        utilitiesTableBody.appendChild(tr);
      });
    } catch (e) {
      console.error(e);
    }
  }

  // Fetch Transactions
  async function fetchTransactions() {
    try {
      const res = await fetch('/api/transactions');
      const data = await res.json();
      txTableBody.innerHTML = '';

      data.transactions.forEach(t => {
        const tr = document.createElement('tr');
        const isExp = t.type === 'EXPENSE';
        tr.innerHTML = `
          <td class="font-mono text-muted">${t.tx_date}</td>
          <td><span class="type-badge ${isExp ? 'badge-expense' : 'badge-income'}">${isExp ? 'РАСХОД' : 'ДОХОД'}</span></td>
          <td style="font-weight:600;">${escapeHtml(t.category)}</td>
          <td class="font-mono ${isExp ? 'text-red' : 'text-jade'}" style="font-weight:700;">${isExp ? '-' : '+'}${t.amount.toLocaleString()} ₽</td>
          <td style="color:#A1A1AA;">${escapeHtml(t.note || '')}</td>
          <td><button class="mini-btn text-muted del-tx-btn" data-id="${t.id}">✕</button></td>
        `;

        tr.querySelector('.del-tx-btn').addEventListener('click', async () => {
          await fetch(`/api/transactions/${t.id}`, { method: 'DELETE' });
          fetchTransactions();
          fetchSummary();
        });

        txTableBody.appendChild(tr);
      });
    } catch (e) {
      console.error(e);
    }
  }

  // Modals Actions
  btnOpenTxModal.addEventListener('click', () => {
    txDate.value = new Date().toISOString().split('T')[0];
    txModal.classList.remove('hidden');
  });
  btnCloseTxModal.addEventListener('click', () => txModal.classList.add('hidden'));

  btnSubmitTx.addEventListener('click', async () => {
    const amt = parseFloat(txAmount.value);
    if (!amt || amt <= 0) {
      alert("Укажите сумму транзакции");
      return;
    }

    const payload = {
      type: txType.value,
      category: txCategory.value,
      amount: amt,
      note: txNote.value.trim(),
      tx_date: txDate.value
    };

    const res = await fetch('/api/transactions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      txModal.classList.add('hidden');
      fetchTransactions();
      fetchSummary();
    }
  });

  btnOpenMetersModal.addEventListener('click', () => {
    const now = new Date();
    const curMonth = `${now.getFullYear()}-${(now.getMonth() + 1).toString().padStart(2, '0')}`;
    meterPeriod.value = curMonth;
    metersModal.classList.remove('hidden');
  });
  btnCloseMetersModal.addEventListener('click', () => metersModal.classList.add('hidden'));

  btnSubmitMeters.addEventListener('click', async () => {
    const payload = {
      period_month: meterPeriod.value,
      elec_day_val: parseFloat(mElecDay.value) || 0,
      elec_night_val: parseFloat(mElecNight.value) || 0,
      cold_water_val: parseFloat(mColdWater.value) || 0,
      hot_water_val: parseFloat(mHotWater.value) || 0,
      gas_val: parseFloat(mGas.value) || 0
    };

    const res = await fetch('/api/utilities', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      metersModal.classList.add('hidden');
      fetchUtilities();
      fetchSummary();
    }
  });

  btnOpenGoalModal.addEventListener('click', () => goalModal.classList.remove('hidden'));
  btnCloseGoalModal.addEventListener('click', () => goalModal.classList.add('hidden'));

  btnSubmitGoal.addEventListener('click', async () => {
    const title = goalTitle.value.trim();
    const target = parseFloat(goalTarget.value);
    if (!title || !target) {
      alert("Заполните название и целевую сумму");
      return;
    }

    const res = await fetch('/api/goals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title, target_amount: target, deadline_date: '' })
    });
    if (res.ok) {
      goalModal.classList.add('hidden');
      fetchGoals();
    }
  });

  function escapeHtml(str) {
    return String(str).replace(/[&<>'"]/g, tag => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
    }[tag] || tag));
  }

  // Boot
  fetchSummary();
  fetchGoals();
  fetchUtilities();

})();
