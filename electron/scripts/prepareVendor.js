/**
 * electron-builder beforeBuild hook (D23): stages Tesseract and Playwright's
 * Chromium from wherever they're actually installed on the BUILDING machine
 * into electron/vendor/ (gitignored), which extraResources then copies
 * verbatim into the packaged app. Bundling them means the client's machine
 * never needs to install anything itself.
 */
const fs = require('fs');
const path = require('path');
const os = require('os');

const VENDOR_DIR = path.join(__dirname, '..', 'vendor');

function findTesseractDir() {
  const candidates = ['C:\\Program Files\\Tesseract-OCR', 'C:\\Program Files (x86)\\Tesseract-OCR'];
  return candidates.find((dir) => fs.existsSync(path.join(dir, 'tesseract.exe')));
}

function findChromiumDir() {
  const base = path.join(os.homedir(), 'AppData', 'Local', 'ms-playwright');
  if (!fs.existsSync(base)) {
    return null;
  }
  const entries = fs
    .readdirSync(base)
    .filter((name) => name.startsWith('chromium-') && !name.includes('headless_shell'))
    .sort();
  return entries.length > 0 ? path.join(base, entries[entries.length - 1]) : null;
}

function copyDirRecursive(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      copyDirRecursive(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function stageTesseract() {
  const srcDir = findTesseractDir();
  if (!srcDir) {
    throw new Error(
      'Tesseract-OCR not found (checked Program Files). Install it before packaging — see README.'
    );
  }
  const destDir = path.join(VENDOR_DIR, 'tesseract');
  fs.mkdirSync(destDir, { recursive: true });
  fs.copyFileSync(path.join(srcDir, 'tesseract.exe'), path.join(destDir, 'tesseract.exe'));
  for (const entry of fs.readdirSync(srcDir)) {
    if (entry.toLowerCase().endsWith('.dll')) {
      fs.copyFileSync(path.join(srcDir, entry), path.join(destDir, entry));
    }
  }
  copyDirRecursive(path.join(srcDir, 'tessdata'), path.join(destDir, 'tessdata'));
  console.log(`[prepareVendor] staged Tesseract from ${srcDir}`);
}

function stageChromium() {
  const srcDir = findChromiumDir();
  if (!srcDir) {
    throw new Error(
      "Playwright's Chromium not found (checked %LOCALAPPDATA%\\ms-playwright). " +
        'Run `playwright install chromium` before packaging — see README.'
    );
  }
  const destDir = path.join(VENDOR_DIR, 'playwright-browsers', path.basename(srcDir));
  copyDirRecursive(srcDir, destDir);
  console.log(`[prepareVendor] staged Chromium from ${srcDir}`);
}

module.exports = async function prepareVendor() {
  fs.rmSync(VENDOR_DIR, { recursive: true, force: true });
  stageTesseract();
  stageChromium();
};
