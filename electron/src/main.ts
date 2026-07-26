import { app, BrowserWindow } from 'electron';
import { ChildProcess, spawn } from 'node:child_process';
import { createReadStream, existsSync, statSync } from 'node:fs';
import { createServer, Server } from 'node:http';
import path from 'node:path';

const isDev = process.env.NODE_ENV !== 'production';
const BACKEND_PORT = 8000;
const BACKEND_HEALTH_URL = `http://127.0.0.1:${BACKEND_PORT}/health`;

const MIME_TYPES: Record<string, string> = {
  '.html': 'text/html',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.json': 'application/json',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain',
};

let backendProcess: ChildProcess | null = null;
let frontendServer: Server | null = null;

function backendExecutablePath(): string {
  // Bundled as an extraResource by electron-builder (see electron/package.json's "build.extraResources", D21).
  return path.join(process.resourcesPath, 'backend', 'avas-backend.exe');
}

function startBackend(): void {
  backendProcess = spawn(backendExecutablePath(), [], {
    windowsHide: true,
    env: { ...process.env, AVAS_BACKEND_PORT: String(BACKEND_PORT) },
  });
  backendProcess.stdout?.on('data', (chunk) => console.log(`[backend] ${chunk}`));
  backendProcess.stderr?.on('data', (chunk) => console.error(`[backend] ${chunk}`));
  backendProcess.on('error', (err) => console.error('[backend] failed to start:', err));
}

async function waitForBackend(timeoutMs = 20000, intervalMs = 300): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(BACKEND_HEALTH_URL);
      if (response.ok) {
        return true;
      }
    } catch {
      // Backend not accepting connections yet — keep polling.
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  return false;
}

/**
 * Serves the Next.js static export over a real HTTP origin instead of
 * `file://`. `window.loadFile()` resolves root-relative paths (every
 * `<Link href="/dashboard">`) against the filesystem root, not the app's own
 * directory — that's not a corner case, it breaks every root-relative link
 * in the packaged app. A local static server sidesteps the whole class of
 * bug the same way a real deployment would.
 */
function startFrontendServer(rootDir: string): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = createServer((req, res) => {
      const urlPath = decodeURIComponent((req.url ?? '/').split('?')[0]);
      const candidates = urlPath === '/' ? ['/index.html'] : [urlPath, `${urlPath}.html`];

      for (const candidate of candidates) {
        const filePath = path.join(rootDir, candidate);
        if (!filePath.startsWith(rootDir)) {
          continue; // path traversal guard
        }
        if (existsSync(filePath) && statSync(filePath).isFile()) {
          res.setHeader('Content-Type', MIME_TYPES[path.extname(filePath)] ?? 'application/octet-stream');
          createReadStream(filePath).pipe(res);
          return;
        }
      }
      res.statusCode = 404;
      res.end('Not found');
    });

    server.on('error', reject);
    server.listen(0, '127.0.0.1', () => {
      frontendServer = server;
      const address = server.address();
      resolve(typeof address === 'object' && address ? address.port : 0);
    });
  });
}

async function createWindow(): Promise<void> {
  const window = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    window.loadURL('http://localhost:3000');
    return;
  }

  const backendReady = await waitForBackend();
  if (!backendReady) {
    window.loadURL(
      'data:text/html,<h1>AVAS failed to start</h1>' +
        '<p>The backend service did not respond in time. Please restart the application.</p>'
    );
    return;
  }

  const frontendPort = await startFrontendServer(
    path.join(process.resourcesPath, 'frontend', 'out')
  );
  window.loadURL(`http://127.0.0.1:${frontendPort}/`);
}

app.whenReady().then(() => {
  if (!isDev) {
    startBackend();
  }
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('before-quit', () => {
  backendProcess?.kill();
  frontendServer?.close();
});
