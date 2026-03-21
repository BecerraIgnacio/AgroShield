const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const APP_URL = process.env.APP_URL || 'http://127.0.0.1:4173';
const OUTPUT_DIR = process.env.SCREENSHOT_DIR || '/tmp/agroshield-site';

async function wait(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function capture(page, filename) {
  const target = path.join(OUTPUT_DIR, filename);
  await page.screenshot({ path: target, fullPage: true });
  console.log(`Saved ${target}`);
}

(async () => {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1600, height: 900, deviceScaleFactor: 1 });
  await page.goto(APP_URL, { waitUntil: 'networkidle0', timeout: 60000 });
  await wait(1200);

  await capture(page, 'landing.png');

  await page.click('[data-action="generate"]');
  await wait(900);
  await capture(page, 'results.png');

  await page.click('[data-tab="analysis"]');
  await wait(350);
  await capture(page, 'analysis.png');

  await page.click('[data-tab="structure"]');
  await wait(350);
  await capture(page, 'structure.png');

  await page.click('[data-tab="about"]');
  await wait(350);
  await capture(page, 'about.png');

  await browser.close();
})();
