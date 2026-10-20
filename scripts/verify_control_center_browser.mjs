import { spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';

const PORT = 8765;
const tokenPath = '/run/user/1000/aao-self-development-agent.token';
const agentToken = readFileSync(tokenPath, 'utf-8').trim();

console.log('1. Iniciando servidor FastAPI con uvicorn en puerto', PORT);
const server = spawn('python', ['-m', 'uvicorn', 'aao.work_management_api:app', '--port', String(PORT), '--host', '127.0.0.1'], {
  env: { ...process.env, PYTHONPATH: 'src:.' },
  stdio: ['ignore', 'pipe', 'pipe']
});

server.stderr.on('data', d => process.stderr.write('[server] ' + d));

// Esperar a que el servidor responda /ready
async function waitServer() {
  for (let i = 0; i < 30; i++) {
    try {
      const res = await fetch(`http://127.0.0.1:${PORT}/ready`);
      if (res.ok) return;
    } catch (_) {}
    await new Promise(r => setTimeout(r, 200));
  }
  throw new Error('Servidor FastAPI no respondió en /ready');
}

await waitServer();
console.log('2. Servidor FastAPI listo y conectado a PostgreSQL.');

console.log('3. Lanzando Google Chrome headless con puerto de depuración CDP (9222)...');
const chrome = spawn('google-chrome', [
  '--headless=new',
  '--remote-debugging-port=9222',
  '--disable-gpu',
  '--no-sandbox',
  '--disable-dev-shm-usage',
  'about:blank'
], { stdio: 'ignore' });

async function getWsUrl() {
  for (let i = 0; i < 30; i++) {
    try {
      const res = await fetch('http://127.0.0.1:9222/json/version');
      if (res.ok) {
        const data = await res.json();
        return data.webSocketDebuggerUrl;
      }
    } catch (_) {}
    await new Promise(r => setTimeout(r, 200));
  }
  throw new Error('No se pudo conectar a Chrome CDP');
}

const wsUrl = await getWsUrl();
console.log('4. Conectado a Chrome DevTools Protocol:', wsUrl);

const ws = new WebSocket(wsUrl);
let msgId = 1;
const pending = new Map();

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(msg.error);
    else resolve(msg.result);
  }
};

await new Promise((res, rej) => {
  ws.onopen = res;
  ws.onerror = rej;
});

function send(method, params = {}) {
  const id = msgId++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

try {
  // Crear nueva página target
  const { targetId } = await send('Target.createTarget', { url: `http://127.0.0.1:${PORT}/` });
  const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });

  function sendPage(method, params = {}) {
    const id = msgId++;
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, sessionId, method, params }));
    });
  }

  await sendPage('Page.enable');
  await sendPage('Runtime.enable');

  console.log('5. Navegando a http://127.0.0.1:' + PORT + '/ en Google Chrome...');
  await sendPage('Page.navigate', { url: `http://127.0.0.1:${PORT}/` });
  await new Promise(r => setTimeout(r, 1000));

  console.log('6. Introduciendo credencial AGENT en memoria en el formulario de la interfaz...');
  const authExpr = `
    (function() {
      const input = document.querySelector('#auth-token');
      input.value = '${agentToken}';
      document.querySelector('#auth-form button[type=submit]').click();
      return true;
    })()
  `;
  await sendPage('Runtime.evaluate', { expression: authExpr });

  console.log('7. Esperando carga y renderizado de datos reales de PostgreSQL...');
  await new Promise(r => setTimeout(r, 2000));

  const checkExpr = `
    (function() {
      return {
        projectValue: document.querySelector('#project').value,
        projectText: document.querySelector('#project option:checked')?.textContent || '',
        sessionAgent: document.querySelector('#session-agent-id')?.textContent || '',
        statusMessage: document.querySelector('#message')?.textContent || '',
        boardColumns: document.querySelectorAll('.kanban-col').length,
        taskCards: document.querySelectorAll('.task-card').length,
        taskTitles: Array.from(document.querySelectorAll('.task-card-title')).map(el => el.textContent),
        capabilitiesCount: document.querySelectorAll('#capabilities .catalog-card').length,
        firstCapability: document.querySelector('#capabilities strong')?.textContent || '',
        authBannerVisible: document.querySelector('#auth-panel').style.display !== 'none'
      };
    })()
  `;

  const { result } = await sendPage('Runtime.evaluate', { expression: checkExpr, returnByValue: true });
  const data = result.value;

  console.log('--- RESULTADOS DE VERIFICACIÓN EN NAVEGADOR REAL ---');
  console.log('Proyecto seleccionado:', data.projectText);
  console.log('Identidad en sesión:', data.sessionAgent);
  console.log('Mensaje de estado:', data.statusMessage);
  console.log('Columnas Kanban:', data.boardColumns);
  console.log('Tarjetas de tareas renderizadas:', data.taskCards);
  console.log('Títulos de tareas:', data.taskTitles);
  console.log('Capacidades renderizadas:', data.capabilitiesCount, `(${data.firstCapability})`);
  console.log('Auth banner ocultado tras login:', !data.authBannerVisible);

  if (!data.sessionAgent.includes('aao-selfdev-d60cd366b26d')) {
    throw new Error('La identidad del agente no coincide en el navegador: ' + data.sessionAgent);
  }
  if (!data.projectText.includes('AAO — Self Development')) {
    throw new Error('El proyecto no se cargó correctamente: ' + data.projectText);
  }
  if (data.taskCards !== 3) {
    throw new Error('Se esperaban 3 tareas reales, obtenidas: ' + data.taskCards);
  }
  if (!data.firstCapability.includes('aao.repository-checker')) {
    throw new Error('No se renderizó la capacidad real: ' + data.firstCapability);
  }

  console.log('8. Cambiando a la pestaña "Ciclo Git e Integración" en el navegador...');
  const switchTabExpr = `
    (function() {
      const gitTab = document.querySelector('.nav-tab[data-tab="tab-git-lifecycle"]');
      if (gitTab) gitTab.click();
      return true;
    })()
  `;
  await sendPage('Runtime.evaluate', { expression: switchTabExpr });
  await new Promise(r => setTimeout(r, 500));

  console.log('9. Verificando renderizado del ciclo Git, candidatos, SHAs exactos y gate de promoción...');
  const gitLifecycleExpr = `
    (function() {
      const gitPanel = document.querySelector('#tab-git-lifecycle');
      const promoteBtn = document.querySelector('#btn-promote-candidate');
      const candidateRows = document.querySelectorAll('#git-candidates-table-body tr');
      const promotionRows = document.querySelectorAll('#git-promotion-history-table-body tr');
      const unaccreditedRows = document.querySelectorAll('#git-unaccredited-candidates-table-body tr');
      const gatePill = document.querySelector('#gate-pill');
      const metricCandidates = document.querySelector('#metric-candidate-count');
      const metricVeto = document.querySelector('#metric-veto-status');
      const metricPromotions = document.querySelector('#metric-promotions-count');

      return {
        tabActive: gitPanel ? gitPanel.classList.contains('active') : false,
        promoteBtnDisabled: promoteBtn ? promoteBtn.disabled : false,
        promoteBtnText: promoteBtn ? promoteBtn.textContent.trim() : '',
        gatePillText: gatePill ? gatePill.textContent.trim() : '',
        metricCandidates: metricCandidates ? metricCandidates.textContent.trim() : '',
        metricVeto: metricVeto ? metricVeto.textContent.trim() : '',
        metricPromotions: metricPromotions ? metricPromotions.textContent.trim() : '',
        candidateRowsCount: candidateRows.length,
        candidateSampleText: candidateRows[0] ? candidateRows[0].textContent.trim() : '',
        promotionRowsCount: promotionRows.length,
        promotionEmptyText: promotionRows[0] ? promotionRows[0].textContent.trim() : '',
        unaccreditedRowsCount: unaccreditedRows.length,
        unaccreditedFirstRow: unaccreditedRows[0] ? unaccreditedRows[0].textContent.trim() : ''
      };
    })()
  `;

  const { result: gitResult } = await sendPage('Runtime.evaluate', { expression: gitLifecycleExpr, returnByValue: true });
  const gitData = gitResult.value;

  console.log('--- RESULTADOS CICLO GIT E INTEGRACIÓN EN NAVEGADOR REAL ---');
  console.log('Pestaña activa:', gitData.tabActive);
  console.log('Botón de promoción deshabilitado (fail-closed):', gitData.promoteBtnDisabled);
  console.log('Texto del botón de promoción:', gitData.promoteBtnText);
  console.log('Estado del gate pill:', gitData.gatePillText);
  console.log('Métrica de propuestas y checks evaluados:', gitData.metricCandidates);
  console.log('Métrica de veto:', gitData.metricVeto);
  console.log('Métrica de promociones acreditadas:', gitData.metricPromotions);
  console.log('Filas de comprobaciones históricas:', gitData.candidateRowsCount);
  console.log('Texto de comprobación histórica 1:', gitData.candidateSampleText);
  console.log('Filas en registro de promociones acreditadas:', gitData.promotionRowsCount);
  console.log('Texto registro de promociones:', gitData.promotionEmptyText);
  console.log('Filas de ramas candidatas no acreditadas:', gitData.unaccreditedRowsCount);
  console.log('Registro 1 de rama no acreditada:', gitData.unaccreditedFirstRow);

  if (!gitData.tabActive) {
    throw new Error('La pestaña tab-git-lifecycle no se activó');
  }
  if (!gitData.promoteBtnDisabled) {
    throw new Error('VIOLACIÓN DE GOBERNANZA: El botón de promoción debe estar estrictamente deshabilitado');
  }
  if (!gitData.gatePillText.includes('PROMOCIÓN BLOQUEADA')) {
    throw new Error('El estado del gate no indica PROMOCIÓN BLOQUEADA: ' + gitData.gatePillText);
  }
  if (!gitData.promotionEmptyText.includes('Cero Promociones Acreditadas')) {
    throw new Error('El registro de promociones debe acreditar 0 promociones: ' + gitData.promotionEmptyText);
  }
  if (!gitData.candidateSampleText.includes('Check Histórico') || !gitData.candidateSampleText.includes('No aplica')) {
    throw new Error('Las comprobaciones sobre commits históricos deben indicar que no aplica Base SHA: ' + gitData.candidateSampleText);
  }
  if (gitData.unaccreditedRowsCount !== 4) {
    throw new Error('Se esperaban 4 ramas candidatas en desarrollo no acreditadas, obtenidas: ' + gitData.unaccreditedRowsCount);
  }

  console.log('VERIFICACIÓN EN NAVEGADOR REAL EXITOSA: Candidatos históricos y promociones no acreditadas presentados fielmente según GOV-REV-001.');
} finally {
  ws.close();
  chrome.kill();
  server.kill();
}
