const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const test = require('node:test');
const path = require('node:path');

function harness() {
  const elements = new Map();
  const make = () => ({ style: {}, classList: { add() {}, remove() {} }, children: [], value: '', addEventListener() {}, appendChild(el) { this.children.push(el); }, replaceChildren() { this.children = []; }, remove() {}, focus() {} });
  const document = { getElementById(id) { if (!elements.has(id)) elements.set(id, make()); return elements.get(id); }, createElement: make, querySelectorAll: () => [] };
  const requests = [];
  const Chart = function () {};
  Chart.defaults = { font: {} };
  Chart.getChart = () => null;
  const context = vm.createContext({ document, Chart, AbortController, FormData: class { append() {} }, setTimeout, clearTimeout, setInterval, clearInterval, fetch(url, options) { return new Promise(resolve => requests.push({ url, options, resolve })); } });
  vm.runInContext(fs.readFileSync(path.join(__dirname, 'public/app.js'), 'utf8'), context);
  return { context, elements, requests };
}
function analysis(revenue) {
  const series = { labels: ['A'], data: [revenue] };
  return { kpis: { totalRevenue: revenue, totalOrders: 5, growthRate: 1, avgOrderValue: revenue / 5, topProduct: 'A' }, forecast: { nextWeek: 1, nextMonth: 4, growthTrend: 'Stable' }, insights: [{ type: 'good', text: '<img onerror=alert(1)>' }], recommendations: [], charts: { salesOverTime: series, revenueByProduct: series, revenueByRegion: series } };
}
test('latest upload wins and charts/dashboard are populated', async () => {
  const h = harness();
  const first = vm.runInContext("uploadAndAnalyze({name:'first.csv'})", h.context);
  const second = vm.runInContext("uploadAndAnalyze({name:'second.csv'})", h.context);
  assert.equal(h.requests[0].options.signal.aborted, true);
  h.requests[1].resolve({ ok: true, json: async () => ({ success: true, data: analysis(200) }) });
  await second;
  h.requests[0].resolve({ ok: true, json: async () => ({ success: true, data: analysis(100) }) });
  await first;
  assert.equal(h.elements.get('kpiRevenue').textContent, '$200');
  assert.ok(h.elements.get('insightsList').innerHTML.includes('&lt;img'));
});
test('chat sends history, prevents duplicates, and resets on new dataset', async () => {
  const h = harness();
  h.context.data = analysis(200);
  vm.runInContext('analysisResult = data; initChat(data)', h.context);
  const input = h.elements.get('chatInput');
  input.value = 'Which product leads?';
  const pending = vm.runInContext('handleChatSend()', h.context);
  await vm.runInContext('handleChatSend()', h.context);
  assert.equal(h.requests.length, 1);
  h.requests[0].resolve({ ok: true, json: async () => ({ reply: 'A leads.' }) });
  await pending;
  input.value = 'How much?';
  const followup = vm.runInContext('handleChatSend()', h.context);
  assert.equal(JSON.parse(h.requests[1].options.body).history.length, 2);
  vm.runInContext('initChat(data)', h.context);
  h.requests[1].resolve({ ok: true, json: async () => ({ reply: 'Stale reply' }) });
  await followup;
  assert.equal(h.elements.get('chatMessages').children.length, 1);
  assert.equal(vm.runInContext('chatHistory.length', h.context), 0);
  assert.equal(input.disabled, false);
});
