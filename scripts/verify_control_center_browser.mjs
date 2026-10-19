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

  console.log('VERIFICACIÓN EN NAVEGADOR REAL EXITOSA: Datos reales leídos y validados sin credencial CEO.');
} finally {
  ws.close();
  chrome.kill();
  server.kill();
}
