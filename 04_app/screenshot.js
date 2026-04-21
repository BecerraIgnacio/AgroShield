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
  await page.evaluate(() => window.scrollTo(0, 0));

  await capture(page, 'home-desktop-full.png');

  await page.setViewport({ width: 1440, height: 1600, deviceScaleFactor: 1 });
  await page.evaluate(() => {
    const hero = document.querySelector('.hero-section');
    if (hero) {
      hero.scrollIntoView({ behavior: 'instant', block: 'start' });
    }
  });
  await wait(400);
  await capture(page, 'home-desktop-hero.png');

  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 2, isMobile: true });
  await page.goto(APP_URL, { waitUntil: 'networkidle0', timeout: 60000 });
  await wait(1200);
  await capture(page, 'home-mobile-full.png');

  await browser.close();
})();
