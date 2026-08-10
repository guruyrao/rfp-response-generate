/**
 * html2pdf.js — Render an HTML file to PDF using headless Chromium.
 *
 * Uses puppeteer-core that ships with @mermaid-js/mermaid-cli, so no
 * extra install needed. Auto-discovers Chromium in the Puppeteer cache
 * or from the CHROME_PATH env var / installed Chrome / Edge.
 *
 * Usage:
 *   node html2pdf.js <input.html> <output.pdf> [--header file] [--footer file]
 */

const fs   = require('fs');
const os   = require('os');
const path = require('path');

// ---- args ------------------------------------------------------------------
const argv = process.argv.slice(2);
if (argv.length < 2) {
    console.error('Usage: node html2pdf.js <input.html> <output.pdf> [--header file] [--footer file]');
    process.exit(2);
}
const inputHtml = path.resolve(argv[0]);
const outputPdf = path.resolve(argv[1]);
let headerFile = null;
let footerFile = null;
for (let i = 2; i < argv.length; i++) {
    if (argv[i] === '--header') headerFile = path.resolve(argv[++i]);
    if (argv[i] === '--footer') footerFile = path.resolve(argv[++i]);
}

// ---- locate puppeteer-core (bundled with mermaid-cli) ----------------------
function findPuppeteer() {
    const candidates = [];
    // npm global
    try {
        const npmRoot = require('child_process')
            .execSync('npm root -g', { encoding: 'utf8' }).trim();
        candidates.push(path.join(npmRoot, '@mermaid-js', 'mermaid-cli', 'node_modules', 'puppeteer-core'));
        candidates.push(path.join(npmRoot, 'puppeteer-core'));
        candidates.push(path.join(npmRoot, 'puppeteer'));
    } catch (_) {}
    // local
    candidates.push(path.resolve(__dirname, 'node_modules', 'puppeteer-core'));
    candidates.push(path.resolve(__dirname, 'node_modules', 'puppeteer'));

    for (const p of candidates) {
        if (fs.existsSync(path.join(p, 'package.json'))) return p;
    }
    throw new Error('puppeteer-core not found. Install with:\n' +
        '  npm install -g @mermaid-js/mermaid-cli\n' +
        'or add puppeteer locally.');
}

// ---- locate Chromium executable --------------------------------------------
function findChrome() {
    if (process.env.CHROME_PATH && fs.existsSync(process.env.CHROME_PATH)) {
        return process.env.CHROME_PATH;
    }
    // Puppeteer cache in user profile
    const homeCache = path.join(os.homedir(), '.cache', 'puppeteer', 'chrome');
    if (fs.existsSync(homeCache)) {
        const versions = fs.readdirSync(homeCache).sort().reverse();
        for (const v of versions) {
            const exe = path.join(homeCache, v, 'chrome-win64', 'chrome.exe');
            if (fs.existsSync(exe)) return exe;
            const exeLinux = path.join(homeCache, v, 'chrome-linux64', 'chrome');
            if (fs.existsSync(exeLinux)) return exeLinux;
            const exeMac = path.join(homeCache, v, 'chrome-mac-x64', 'Google Chrome for Testing.app', 'Contents', 'MacOS', 'Google Chrome for Testing');
            if (fs.existsSync(exeMac)) return exeMac;
        }
    }
    // Installed browsers
    const wellKnown = [
        'C:/Program Files/Google/Chrome/Application/chrome.exe',
        'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
        'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
        'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
        '/usr/bin/google-chrome',
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    ];
    for (const p of wellKnown) if (fs.existsSync(p)) return p;

    throw new Error('Could not find Chrome/Edge. Set CHROME_PATH env var to your browser executable.');
}

// ---- main ------------------------------------------------------------------
const puppeteerRoot = findPuppeteer();
const puppeteer     = require(puppeteerRoot);
const chromePath    = findChrome();
console.log('    chromium: ' + chromePath);

const headerTemplate = headerFile ? fs.readFileSync(headerFile, 'utf8') : '<span></span>';
const footerTemplate = footerFile ? fs.readFileSync(footerFile, 'utf8') : '<span></span>';

(async () => {
    console.log('==> Launching Chromium ...');
    const browser = await puppeteer.launch({
        executablePath: chromePath,
        headless: 'new',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-web-security',
            '--allow-file-access-from-files',
        ],
    });

    try {
        const page = await browser.newPage();

        console.log('==> Loading HTML: ' + inputHtml);
        const fileUrl = 'file:///' + inputHtml.replace(/\\/g, '/');
        await page.goto(fileUrl, { waitUntil: 'networkidle0', timeout: 180000 });

        await page.evaluateHandle('document.fonts.ready');
        await new Promise(r => setTimeout(r, 1000));

        console.log('==> Generating PDF: ' + outputPdf);
        await page.pdf({
            path: outputPdf,
            format: 'A4',
            printBackground: true,
            displayHeaderFooter: true,
            headerTemplate,
            footerTemplate,
            margin: { top: '22mm', bottom: '22mm', left: '15mm', right: '15mm' },
            preferCSSPageSize: false,
        });

        const size = fs.statSync(outputPdf).size;
        console.log('==> SUCCESS  size=' + Math.round(size / 1024) + ' KB');
    } finally {
        await browser.close();
    }
})().catch((e) => {
    console.error('ERROR: ' + e.stack);
    process.exit(1);
});
