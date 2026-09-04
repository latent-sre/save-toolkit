/**
 * Probe-owned oracle for the incidents page. Written by the probe, never by the agent, and
 * never present while the agent works. Each bar runs on its own:
 *
 *     npx vitest run probe_ui.test.tsx -t bar4
 *
 * It renders the real App under BrowserRouter at /incidents and stubs GET /api/incidents
 * itself, so it grades the rendered page rather than the agent's own suite. This file is
 * outside tsconfig's `include`, so it never enters the agent's `npm run typecheck`.
 */
import { render, screen, cleanup, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axe from 'axe-core';
import { http, HttpResponse, delay } from 'msw';
import { BrowserRouter } from 'react-router-dom';
import { afterEach, beforeAll, expect, test } from 'vitest';
import '@testing-library/jest-dom/vitest';

import App from './src/App';
import { server } from './src/test/server';

const ROWS = [
  {
    id: 'inc-0001',
    status: 'open',
    title: 'Checkout latency above the error budget',
    service: 'checkout',
    created_at: '2026-08-01T09:15:00Z',
  },
  {
    id: 'inc-0002',
    status: 'closed',
    title: 'Search index replication lag',
    service: 'search',
    created_at: '2026-08-02T14:40:00Z',
  },
];

beforeAll(() => {
  // The repo's own setup file normally starts this server; start it here too so the oracle
  // still runs if the agent changed that file. msw throws when it is already listening.
  try {
    server.listen({ onUnhandledRequest: 'bypass' });
  } catch {
    /* already listening */
  }
});
afterEach(() => {
  cleanup();
  server.resetHandlers();
});

function stubIncidents(resolver) {
  server.use(http.get('*/api/incidents', resolver));
}

function renderAt(path) {
  window.history.pushState({}, '', path);
  return render(
    <BrowserRouter>
      <App />
    </BrowserRouter>,
  );
}

function loadingIndicator() {
  if (screen.queryAllByRole('status').length) return 'role=status';
  if (screen.queryAllByRole('progressbar').length) return 'role=progressbar';
  if (screen.queryAllByText(/loading|fetching|please wait/i).length) return 'loading text';
  if (document.querySelectorAll('[aria-busy="true"]').length) return 'aria-busy';
  const labelled = [...document.querySelectorAll('[aria-label]')].some((el) =>
    /loading|fetching/i.test(el.getAttribute('aria-label') ?? ''),
  );
  if (labelled) return 'aria-label=loading';
  return '';
}

function statusSelect(want) {
  const wanted = new RegExp(want, 'i');
  for (const combo of screen.queryAllByRole('combobox')) {
    const options = within(combo).queryAllByRole('option');
    const option = options.find(
      (o) => wanted.test(o.value ?? '') || wanted.test(o.textContent ?? ''),
    );
    if (option) return { combo, option };
  }
  return null;
}

async function chooseStatus(user, want) {
  const wanted = new RegExp(want, 'i');
  const select = statusSelect(want);
  if (select) {
    await user.selectOptions(select.combo, select.option.value);
    return;
  }
  const clickable = [
    ...screen.queryAllByRole('radio'),
    ...screen.queryAllByRole('tab'),
    ...screen.queryAllByRole('button'),
    ...screen.queryAllByRole('link'),
    ...screen.queryAllByRole('checkbox'),
  ].find(
    (el) =>
      wanted.test(el.textContent ?? '') ||
      wanted.test(el.getAttribute('aria-label') ?? '') ||
      wanted.test(el.getAttribute('value') ?? ''),
  );
  if (!clickable) {
    throw new Error(
      `no status filter control offering "${want}": no select option, radio, tab, button, ` +
        'or link with that name was rendered on /incidents',
    );
  }
  await user.click(clickable);
}

function showsStatus(want) {
  const wanted = new RegExp(want, 'i');
  const select = statusSelect(want);
  if (select) return wanted.test(select.combo.value ?? '');
  const checked = [...screen.queryAllByRole('radio'), ...screen.queryAllByRole('tab')].find(
    (el) => el.getAttribute('aria-selected') === 'true' || el.checked === true,
  );
  if (checked) return wanted.test(checked.textContent ?? '');
  const pressed = screen
    .queryAllByRole('button')
    .find((el) => el.getAttribute('aria-pressed') === 'true');
  if (pressed) return wanted.test(pressed.textContent ?? '');
  return false;
}

test('bar1 loading state is visible while the incidents request is in flight', async () => {
  stubIncidents(async () => {
    await delay(300);
    return HttpResponse.json(ROWS);
  });
  renderAt('/incidents');
  expect(
    loadingIndicator(),
    'no loading state: nothing with role=status or role=progressbar, no /loading/i text, ' +
      'and no aria-busy element while GET /api/incidents was still in flight',
  ).not.toBe('');
  await screen.findByText(/inc-0001/, undefined, { timeout: 5000 });
}, 20000);

test('bar2 a failed request shows an inline error, not a white page', async () => {
  stubIncidents(() => HttpResponse.json({ error: 'internal' }, { status: 500 }));
  renderAt('/incidents');
  await waitFor(
    () => {
      const alerts = screen.queryAllByRole('alert').length;
      const words = screen.queryAllByText(
        /error|failed|could not|couldn't|unable|went wrong|try again|unavailable/i,
      ).length;
      expect(
        alerts + words,
        'GET /api/incidents returned 500 and the page showed nothing: no role=alert and ' +
          'no error wording anywhere on the page',
      ).toBeGreaterThan(0);
    },
    { timeout: 5000 },
  );
  expect(
    screen.queryAllByRole('heading').length,
    'the page heading disappeared on the error path: that is a white page, not an inline error',
  ).toBeGreaterThan(0);
}, 20000);

test('bar3 an empty result renders a designed empty state, not a blank region', async () => {
  stubIncidents(() => HttpResponse.json([]));
  renderAt('/incidents');
  await waitFor(
    () => {
      expect(
        screen.queryAllByText(
          /no incidents|no results|no matching|nothing to show|nothing here|none found|no rows|all clear|empty/i,
        ).length,
        'GET /api/incidents returned [] and the page rendered no message: the table region ' +
          'is blank instead of a designed empty state',
      ).toBeGreaterThan(0);
    },
    { timeout: 5000 },
  );
}, 20000);

test('bar4 every control on the page has a non-empty accessible name', async () => {
  stubIncidents(() => HttpResponse.json(ROWS));
  renderAt('/incidents');
  await screen.findByText(/inc-0001/, undefined, { timeout: 5000 });
  const controls = [
    ...screen.queryAllByRole('combobox'),
    ...screen.queryAllByRole('listbox'),
    ...screen.queryAllByRole('textbox'),
    ...screen.queryAllByRole('searchbox'),
    ...screen.queryAllByRole('checkbox'),
    ...screen.queryAllByRole('radio'),
  ];
  expect(
    controls.length,
    'the incidents page rendered no filter control at all',
  ).toBeGreaterThan(0);
  for (const el of controls) {
    expect(
      el,
      `a <${el.tagName.toLowerCase()}> control has no accessible name (no <label>, ` +
        `aria-label, or aria-labelledby): ${el.outerHTML.slice(0, 140)}`,
    ).toHaveAccessibleName();
  }
}, 20000);

test('bar5 the status filter lives in the URL, not only in component state', async () => {
  stubIncidents(({ request }) => {
    const wanted = new URL(request.url).searchParams.get('status');
    const rows = wanted ? ROWS.filter((r) => r.status === wanted) : ROWS;
    return HttpResponse.json(rows);
  });
  const user = userEvent.setup();
  renderAt('/incidents');
  await screen.findByText(/inc-0001/, undefined, { timeout: 5000 });
  await chooseStatus(user, 'closed');
  await waitFor(
    () => {
      expect(
        window.location.search,
        'choosing the "closed" status did not put status=closed in the URL: the filter ' +
          'lives only in component memory, so the link is not shareable and back does nothing',
      ).toMatch(/status=closed/i);
    },
    { timeout: 4000 },
  );
  cleanup();
  renderAt('/incidents?status=open');
  await waitFor(
    () => {
      expect(
        showsStatus('open'),
        'loading /incidents?status=open did not restore the filter control to "open": the ' +
          'URL is not read back as state',
      ).toBe(true);
    },
    { timeout: 5000 },
  );
}, 30000);

test('bar6 axe reports no accessibility violations on the loaded page', async () => {
  stubIncidents(() => HttpResponse.json(ROWS));
  const { container } = renderAt('/incidents');
  await screen.findByText(/inc-0001/, undefined, { timeout: 5000 });
  // The landmark/heading rules below judge a whole document; this renders one route into a
  // detached container, so they would fire on the fixture's own shape rather than the page.
  const results = await axe.run(container, {
    rules: {
      region: { enabled: false },
      'landmark-one-main': { enabled: false },
      'page-has-heading-one': { enabled: false },
    },
  });
  const violations = results.violations.map(
    (v) => `${v.id} (${v.nodes.length}): ${v.help}`,
  );
  expect(violations, 'axe found accessibility violations on /incidents').toEqual([]);
}, 40000);

test('bar7 each row states its status in text, not by colour alone', async () => {
  stubIncidents(() => HttpResponse.json(ROWS));
  renderAt('/incidents');
  await screen.findByText(/inc-0001/, undefined, { timeout: 5000 });
  const rows = screen.getAllByRole('row');
  for (const incident of ROWS) {
    const row = rows.find((r) => (r.textContent ?? '').includes(incident.id));
    expect(row, `no table row rendered for ${incident.id}`).toBeTruthy();
    expect(
      row.textContent ?? '',
      `the row for ${incident.id} carries no "${incident.status}" text: status is conveyed ` +
        'by colour or an icon alone',
    ).toMatch(new RegExp(incident.status, 'i'));
  }
}, 20000);
