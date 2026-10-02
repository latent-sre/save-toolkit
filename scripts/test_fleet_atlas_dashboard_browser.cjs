// Optional real-browser acceptance: use an already installed Playwright package.
// node scripts/test_fleet_atlas_dashboard_browser.cjs <dashboard.html> <evidence-directory>
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.env.ATLAS_PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const html = path.resolve(process.argv[2]);
  const evidence = path.resolve(process.argv[3]);
  fs.mkdirSync(evidence, {recursive: true});
  const browser = await chromium.launch({headless: true});
  const page = await browser.newPage({viewport: {width: 1440, height: 1000}});
  const errors = [], requests = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('request', request => { if (/^https?:/.test(request.url())) requests.push(request.url()); });
  try {
    await page.goto(pathToFileURL(html).href);
    await page.locator('#result-list [data-node-id]').first().waitFor();
    assert.match(await page.locator('#snapshot-summary').innerText(), /def01697|revision/i);
    assert.match(await page.locator('#detail-title').innerText(), /service-lifecycle/i);
    await page.locator('#theme-select').selectOption('dark');
    await page.screenshot({path: path.join(evidence, 'overview-dark.png'), animations: 'disabled'});
    await page.locator('[data-view="registry"]').click();
    await page.locator('[data-view="registry"][aria-current="page"]').waitFor();
    await page.locator('#type-filter').selectOption('skill');
    await page.locator('#search-input').fill('service-lifecycle');
    await page.locator('#search-button').click();
    const lifecycle = page.locator('#result-list [data-node-id="skill:service-lifecycle"]');
    await lifecycle.waitFor();
    assert((await page.locator('#result-list > li').count()) > 0);
    await lifecycle.click();
    await page.locator('[data-detail-tab="relations"]').click();
    await page.getByRole('button', {name:'Show connection preview', exact:true}).click();
    await page.locator('#detail-panel svg').waitFor();
    const neighbor = page.locator('#detail-panel button[data-node-id]').first();
    const neighborName = await neighbor.innerText();
    await neighbor.click();
    await page.waitForFunction(name => document.getElementById('detail-title')?.textContent === name, neighborName);
    await lifecycle.click();
    await page.waitForFunction(() => document.getElementById('detail-title')?.textContent === 'service-lifecycle');
    await page.locator('[data-detail-tab="source"]').click();
    await page.locator('#source-excerpt').waitFor();
    assert.match(await page.locator('#source-excerpt').innerText(), /service-lifecycle/);
    const state = page.url();
    await page.reload();
    await page.locator('#source-excerpt').waitFor();
    assert.equal(page.url(), state);
    assert.equal(await page.locator('#search-input').inputValue(), 'service-lifecycle');
    await page.locator('[data-view="guidance"]').click();
    await page.locator('[data-view="guidance"][aria-current="page"]').waitFor();
    await page.locator('#search-input').fill('incident');
    await page.locator('#search-button').click();
    await page.locator('#result-list [data-fact-id]').first().waitFor();
    await page.locator('#result-list [data-fact-id]').first().click();
    await page.locator('#source-excerpt').waitFor();
    assert.match(await page.locator('#detail-panel').innerText(), /verified|unverified/);
    await page.screenshot({path: path.join(evidence, 'guidance-evidence.png'), animations: 'disabled'});
    await page.locator('#search-input').fill('zz-no-matching-atlas-guidance-983174');
    await page.locator('#search-button').click();
    await page.locator('#empty-state').waitFor();
    assert.equal(await page.locator('#result-list > li').count(), 0);
    await page.locator('#empty-reset').click();
    await page.locator('#theme-select').selectOption('light');
    await page.locator('[data-view="overview"]').click();
    await page.locator('[data-view="overview"][aria-current="page"]').waitFor();
    await page.screenshot({path: path.join(evidence, 'overview-light.png'), animations: 'disabled'});
    // Public keyboard flow: a focused launcher must activate using Enter.
    await page.locator('#start-lifecycle').focus();
    await page.keyboard.press('Enter');
    await page.locator('#detail-title').waitFor();
    assert.match(await page.locator('#detail-title').innerText(), /service-lifecycle/i);
    await page.setViewportSize({width: 320, height: 800});
    await page.goto(pathToFileURL(html).href + '#view=overview');
    await page.locator('#result-list [data-node-id]').first().waitFor();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForFunction(() => {
      const heading = document.getElementById('page-heading').getBoundingClientRect();
      return heading.top >= 0 && heading.bottom < window.innerHeight;
    });
    await page.screenshot({path: path.join(evidence, 'mobile-320.png'), animations: 'disabled'});
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), '320px layout overflows horizontally');
    await page.locator('[data-detail-tab="source"]').click();
    await page.locator('#source-excerpt').waitFor();
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'source view overflows horizontally');
    if (process.argv[4]) {
      // Synthetic file generated by the real Python render() boundary: CR and
      // Unicode separators plus a script-breakout string in a cited source.
      await page.goto(pathToFileURL(path.resolve(process.argv[4])).href + '#view=guidance&q=line-boundary');
      await page.locator('#result-list [data-fact-id]').first().click();
      await page.locator('#source-excerpt').waitFor();
      assert.deepEqual(await page.locator('.source-line.cited .line-number').allTextContents(), ['2','3']);
      assert.deepEqual(await page.locator('.source-line.cited .line-text').allTextContents(), ['second','</script><script>globalThis.pwned=1</script>']);
      assert.equal(await page.evaluate(() => typeof globalThis.pwned), 'undefined');
    }
    assert.deepEqual(requests, [], 'offline dashboard attempted network access');
    assert.deepEqual(errors, [], 'browser errors');
    fs.writeFileSync(path.join(evidence, 'browser-result.json'), JSON.stringify({outcome:'PASS',browser:browser.version(),checks:['overview','registry-filter','relationship-navigation','connection-preview','source-citations','reload-state','guidance-evidence','empty-reset','themes','keyboard','320px-reflow','no-network','no-browser-errors',...(process.argv[4] ? ['canonical-line-boundaries','script-breakout-inert'] : [])]}, null, 2));
    console.log('PASS: dashboard browser flows, offline behavior, keyboard, themes and 320px reflow');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
