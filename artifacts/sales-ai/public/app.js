(function () {
      const container = document.getElementById('particles');
      for (let i = 0; i < 15; i++) {
        const p = document.createElement('div');
        p.className = 'particle';
        p.style.left = Math.random() * 100 + '%';
        p.style.animationDuration = (8 + Math.random() * 12) + 's';
        p.style.animationDelay = (Math.random() * 10) + 's';
        p.style.opacity = 0.3 + Math.random() * 0.5;
        p.style.width = p.style.height = (1 + Math.random() * 2) + 'px';
        container.appendChild(p);
      }
    })();

    // ── State ────────────────────────────────────────────────────────────────────
    let analysisResult = null;
    let uploadController = null;
    let loadingInterval = null;

    // ── Helpers ───────────────────────────────────────────────────────────────────
    function escapeHtml(value) {
      return String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
    }

    function fmtCurrency(n) {
      if (n >= 1_000_000) return '$' + (n / 1_000_000).toFixed(1) + 'M';
      if (n >= 1_000) return '$' + (n / 1_000).toFixed(1) + 'K';
      return '$' + n.toFixed(0);
    }

    // ── Screen navigation ─────────────────────────────────────────────────────────
    function goScreen(name) {
      if (loadingInterval) { clearInterval(loadingInterval); loadingInterval = null; }
      document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
      document.getElementById('screen-dashboard').classList.remove('active');
      const target = document.getElementById('screen-' + name);
      if (target) target.classList.add('active');
    }

    // ── Upload handling ────────────────────────────────────────────────────────────
    document.getElementById('uploadZone').addEventListener('click', () => document.getElementById('fileInput').click());
    document.getElementById('uploadZone').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') document.getElementById('fileInput').click();
    });
    document.getElementById('fileInput').addEventListener('change', function (e) {
      if (e.target.files.length > 0) uploadAndAnalyze(e.target.files[0]);
    });

    const zone = document.getElementById('uploadZone');
    zone.addEventListener('dragover', (e) => {
      e.preventDefault();
      zone.style.borderColor = 'rgba(0,170,255,0.7)';
      zone.style.background = 'rgba(0,170,255,0.08)';
    });
    zone.addEventListener('dragleave', () => {
      zone.style.borderColor = 'rgba(0,170,255,0.25)';
      zone.style.background = 'rgba(6,28,68,0.35)';
    });
    zone.addEventListener('drop', (e) => {
      e.preventDefault();
      zone.style.borderColor = 'rgba(0,170,255,0.25)';
      zone.style.background = 'rgba(6,28,68,0.35)';
      const file = e.dataTransfer.files[0];
      if (file) uploadAndAnalyze(file);
    });

    // ── Main upload + analysis pipeline ───────────────────────────────────────────
    async function uploadAndAnalyze(file) {
      if (!file.name.toLowerCase().endsWith('.csv')) {
        showError('Invalid file type. Please upload a .csv file.', 'Required columns: date, product, revenue, quantity, region');
        return;
      }

      if (uploadController) uploadController.abort();
      const controller = new AbortController();
      uploadController = controller;
      goScreen('loading');
      runLoadingSteps();

      const formData = new FormData();
      formData.append('file', file);

      try {
        const res = await fetch('/api/analyze', { method: 'POST', body: formData, signal: controller.signal });
        const json = await res.json();
        if (uploadController !== controller) return;

        if (!res.ok || !json.success) {
          showError(json.error || 'Analysis failed.', json.hint || '');
          return;
        }

        analysisResult = json.data;
        populateDashboard(json.data);
        goScreen('dashboard');
        renderCharts(json.data.charts);
        initChat(json.data);

      } catch (err) {
        if (uploadController !== controller) return;
        showError('Could not connect to the analysis server. Please try again.', '');
      } finally {
        if (uploadController === controller) uploadController = null;
      }
    }

    function runLoadingSteps() {
      const el = document.getElementById('loadingText');
      const steps = [
        'Validating your data',
        'Cleaning & processing rows',
        'Detecting trends & anomalies',
        'Generating insights & recommendations',
      ];
      let i = 0;
      if (loadingInterval) clearInterval(loadingInterval);
      loadingInterval = setInterval(() => {
        i++;
        if (i < steps.length) {
          el.innerHTML = steps[i] + '<span class="dot">.</span><span class="dot">.</span><span class="dot">.</span>';
        } else {
          clearInterval(loadingInterval);
          loadingInterval = null;
        }
      }, 900);
    }

    function showError(msg, hint) {
      const el = document.getElementById('errorMessage');
      if (el) el.innerHTML = escapeHtml(msg) + (hint ? '<br><small style="color:var(--text-3);font-size:0.8rem;margin-top:6px;display:block;">' + escapeHtml(hint) + '</small>' : '');
      goScreen('error');
    }

    // ── Populate dashboard with real data ─────────────────────────────────────────
    function populateDashboard(d) {
      const k = d.kpis;

      // KPIs
      setText('kpiRevenue', fmtCurrency(k.totalRevenue));
      setText('kpiOrders', k.totalOrders.toLocaleString());
      setText('kpiGrowth', (k.growthRate >= 0 ? '+' : '') + k.growthRate.toFixed(1) + '%');
      setText('kpiAOV', fmtCurrency(k.avgOrderValue));

      const growthEl = document.getElementById('kpiGrowth');
      if (growthEl) growthEl.style.color = k.growthRate >= 0 ? 'var(--teal)' : '#ff6b6b';

      setText('kpiGrowthChange', k.growthRate >= 0 ? '↑ Positive trajectory' : '↓ Declining trend');
      const changeEl = document.getElementById('kpiGrowthChange');
      if (changeEl) changeEl.className = 'kpi-change ' + (k.growthRate >= 0 ? 'kpi-up' : 'kpi-down');

      // Forecast
      setText('forecastWeek', fmtCurrency(d.forecast.nextWeek));
      setText('forecastMonth', fmtCurrency(d.forecast.nextMonth));
      const anomalyEl = document.getElementById('anomalyTag');
      if (anomalyEl) {
        if (d.forecast.anomaly) {
          anomalyEl.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> ' + d.forecast.anomaly;
          anomalyEl.style.display = '';
        } else {
          anomalyEl.style.display = 'none';
        }
      }
      setText('growthTrend', d.forecast.growthTrend);

      // Insights
      const insightsEl = document.getElementById('insightsList');
      if (insightsEl) {
        insightsEl.innerHTML = d.insights.map(i =>
          `<div class="insight-item ${i.type === 'warn' ? 'warn' : i.type === 'good' ? 'good' : ''}">${escapeHtml(i.text)}</div>`
        ).join('');
      }

      // Recommendations
      const recsEl = document.getElementById('recsList');
      if (recsEl) {
        recsEl.innerHTML = d.recommendations.map(r =>
          `<div class="rec-item"><div class="rec-icon"><i class="fa-solid fa-${escapeHtml(r.icon)}"></i></div><div>${escapeHtml(r.text)}</div></div>`
        ).join('');
      }
    }

    function setText(id, val) {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    }

    // ── Chart rendering ────────────────────────────────────────────────────────────
    const CHART_COLORS = ['#00aaff', '#00e5c8', '#6c5ce7', '#3b8bff', '#ff9f30', '#ff6b6b'];

    function renderCharts(charts) {
      Chart.defaults.color = '#6b8fbb';
      Chart.defaults.borderColor = 'rgba(0,170,255,0.1)';
      Chart.defaults.font.family = 'Rajdhani';

      destroyChart('lineChart');
      destroyChart('doughnutChart');
      destroyChart('barChart');

      new Chart(document.getElementById('lineChart'), {
        type: 'line',
        data: {
          labels: charts.salesOverTime.labels,
          datasets: [{
            label: 'Revenue',
            data: charts.salesOverTime.data,
            borderColor: '#00aaff',
            backgroundColor: 'rgba(0,170,255,0.08)',
            borderWidth: 2.5, fill: true, tension: 0.4,
            pointRadius: 3, pointBackgroundColor: '#00aaff',
            pointBorderColor: '#020a1a', pointBorderWidth: 2, pointHoverRadius: 6
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: 'rgba(0,170,255,0.05)' }, ticks: { font: { size: 10 }, maxTicksLimit: 8 } },
            y: { grid: { color: 'rgba(0,170,255,0.05)' }, ticks: { font: { size: 10 }, callback: v => fmtCurrency(v) } }
          }
        }
      });

      new Chart(document.getElementById('doughnutChart'), {
        type: 'doughnut',
        data: {
          labels: charts.revenueByProduct.labels,
          datasets: [{
            data: charts.revenueByProduct.data,
            backgroundColor: CHART_COLORS,
            borderColor: '#04122e', borderWidth: 3, hoverOffset: 8
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: '65%',
          plugins: { legend: { position: 'bottom', labels: { padding: 10, usePointStyle: true, pointStyleWidth: 8, font: { size: 11 } } } }
        }
      });

      new Chart(document.getElementById('barChart'), {
        type: 'bar',
        data: {
          labels: charts.revenueByRegion.labels,
          datasets: [{
            label: 'Revenue',
            data: charts.revenueByRegion.data,
            backgroundColor: CHART_COLORS.map(c => c + '99'),
            borderColor: CHART_COLORS,
            borderWidth: 1.5, borderRadius: 6, barPercentage: 0.6
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { display: false }, ticks: { font: { size: 10 } } },
            y: { grid: { color: 'rgba(0,170,255,0.05)' }, ticks: { font: { size: 10 }, callback: v => fmtCurrency(v) } }
          }
        }
      });
    }

    function destroyChart(id) {
      const el = document.getElementById(id);
      if (!el) return;
      const existing = Chart.getChart(el);
      if (existing) existing.destroy();
    }

    // ── Chat ──────────────────────────────────────────────────────────────────────
    let chatHistory = [];
    let chatController = null;

    function initChat(data) {
      if (chatController) chatController.abort();
      chatController = null;
      chatHistory = [];
      const messages = document.getElementById('chatMessages');
      messages.replaceChildren();
      const intro = document.createElement('div');
      intro.id = 'chatIntro';
      intro.className = 'chat-bubble ai';
      messages.appendChild(intro);
      const k = data.kpis;
      const orders = k.totalOrders.toLocaleString();
      const revenue = fmtCurrency(k.totalRevenue);
      const product = k.topProduct || 'N/A';
      if (intro) {
        intro.textContent = `I've analyzed ${orders} orders totalling ${revenue}. Your top product is "${product}". Ask me anything about your data.`;
      }
      const input = document.getElementById('chatInput');
      const btn = document.getElementById('chatSendBtn');
      if (input) { input.disabled = false; input.onkeydown = e => { if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); handleChatSend(); } }; }
      if (btn) btn.disabled = false;
    }

    function appendBubble(role, text) {
      const box = document.getElementById('chatMessages');
      if (!box) return;
      const div = document.createElement('div');
      div.className = 'chat-bubble ' + role;
      div.textContent = text;
      box.appendChild(div);
      box.scrollTop = box.scrollHeight;
      return div;
    }

    function showTyping() {
      const box = document.getElementById('chatMessages');
      if (!box) return null;
      const div = document.createElement('div');
      div.className = 'chat-typing';
      div.innerHTML = '<span></span><span></span><span></span>';
      box.appendChild(div);
      box.scrollTop = box.scrollHeight;
      return div;
    }

    async function handleChatSend() {
      const input = document.getElementById('chatInput');
      const btn = document.getElementById('chatSendBtn');
      if (!input || !analysisResult || chatController) return;
      const msg = input.value.trim();
      if (!msg) return;
      input.value = '';
      input.disabled = true;
      btn.disabled = true;

      const controller = new AbortController();
      chatController = controller;
      const timeout = setTimeout(() => controller.abort(), 45000);
      appendBubble('user', msg);
      const typing = showTyping();

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          signal: controller.signal,
          body: JSON.stringify({ message: msg, context: analysisResult, history: chatHistory })
        });
        const json = await res.json();
        if (chatController !== controller) return;
        if (typing) typing.remove();
        if (res.ok && json.reply) {
          chatHistory.push({ role: 'user', content: msg }, { role: 'assistant', content: json.reply });
          chatHistory = chatHistory.slice(-12);
          appendBubble('ai', json.reply);
        } else {
          appendBubble('ai', json.error || 'Something went wrong.');
        }
      } catch (err) {
        if (typing) typing.remove();
        if (chatController !== controller) return;
        appendBubble('ai', err.name === 'AbortError' ? 'The response timed out. Please try again.' : 'Could not reach the server. Please try again.');
      } finally {
        clearTimeout(timeout);
        if (chatController !== controller) return;
        chatController = null;
        input.disabled = false;
        btn.disabled = false;
        input.focus();
      }
    }
