/**
 * Probe-owned oracle for the incidents console. Written by the probe, never by the agent, and
 * never present while the agent works. Each bar runs on its own:
 *
 *     npx vitest run probe_ui.test.tsx -t bar8
 *
 * It renders the real App under BrowserRouter at /incidents and stubs GET /v1/incidents itself
 * (the house contract: `{ data, next_cursor }` pages, problem+json errors with a request_id), so
 * it grades the rendered page rather than the agent's own suite. This file is outside tsconfig's
 * `include`, so it never enters the agent's `npm run typecheck`.
 */
import { render, screen, cleanup, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axe from 'axe-core';
import { http, HttpResponse } from 'msw';
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

const page = (data, next_cursor = null) => HttpResponse.json({ data, next_cursor }, {
  headers: { 'X-Request-ID': 'req-fixture' },
});

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
  server.use(http.get('*/v1/incidents', resolver));
}

function renderAt(path) {
  window.history.pushState({}, '', path);
  return render(
    <BrowserRouter>
      <App />
    </BrowserRouter>,
  );
}

function pageFor(container) {
  return container.querySelector('main, [role="main"]') ?? container;
}

function isVisible(element) {
  try {
    expect(element).toBeVisible();
    return true;
  } catch {
    return false;
  }
}

function renderedText(element) {
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
  const parts = [];
  let node;
  while ((node = walker.nextNode())) {
    if (node.parentElement && isVisible(node.parentElement)) parts.push(node.textContent);
  }
  return parts.join(' ').replace(/\s+/g, ' ').trim();
}

// Compare visible meanings/counts, so an unchanged message remounting is not a state
// transition, while the same live-region node changing its text or ARIA state is valid.
function stateSignals(container, state) {
  const page = pageFor(container);
  const query = within(page);
  const signals = [];
  const add = (elements, kind, value = renderedText) => {
    for (const element of elements.filter(isVisible)) {
      const meaning = value(element);
      if (meaning) signals.push({ kind, value: meaning });
    }
  };
  const addRole = (role) => {
    const names = new Map();
    const elements = query.queryAllByRole(role, { name: (name, element) => {
      names.set(element, name);
      return true;
    } });
    add(elements, role, (element) =>
      [renderedText(element), names.get(element)].filter(Boolean).join('|'));
  };
  const matching = (selector) => [
    ...(page.matches(selector) ? [page] : []), ...page.querySelectorAll(selector),
  ];
  if (state === 'loading') {
    addRole('status');
    add(query.queryAllByRole('progressbar'), 'progressbar', (el) =>
      `${el.getAttribute('aria-valuenow')}|${el.getAttribute('aria-valuetext')}`);
    add(query.queryAllByText(/loading|fetching|please wait/i), 'text');
    add(matching('[aria-busy="true"]'), 'busy', () => 'true');
    add(matching('[aria-label]').filter((el) =>
      /loading|fetching/i.test(el.getAttribute('aria-label') ?? '')), 'label',
      (el) => el.getAttribute('aria-label'));
  } else if (state === 'error') {
    addRole('alert');
    add(query.queryAllByText(
      /error|failed|could not|couldn't|unable|went wrong|try again|unavailable/i,
    ), 'text');
  } else {
    add(query.queryAllByText(
      /no incidents|no results|no matching|nothing to show|nothing here|none found|no rows|all clear|empty/i,
    ), 'text');
  }
  return signals;
}

function sameSignal(left, right) {
  return left.kind === right.kind && left.value === right.value;
}

function addedSignal(before, after) {
  return after.some((signal) =>
    after.filter((other) => sameSignal(signal, other)).length >
      before.filter((other) => sameSignal(signal, other)).length);
}

function controlledIncidents(response) {
  let release;
  let calls = 0;
  const pending = new Promise<void>((resolve) => { release = resolve; });
  stubIncidents(async () => {
    calls += 1;
    await pending;
    return response();
  });
  return {
    release: () => release(),
    started: () => waitFor(() => expect(calls, 'GET /v1/incidents never started')
      .toBeGreaterThan(0), { timeout: 5000 }),
  };
}

function expectIncidentRows(container, included, excluded) {
  const rows = within(pageFor(container)).queryAllByRole('row', { hidden: true }).filter(isVisible);
  expect(rows.some((row) => row.textContent?.includes(included)),
    `filtered results have no visible row for ${included}`).toBe(true);
  expect(rows.some((row) => row.textContent?.includes(excluded)),
    `filtered results still show the nonmatching row ${excluded}`).toBe(false);
}

function statusSelect(want) {
  const wanted = new RegExp(want, 'i');
  for (const combo of screen.queryAllByRole('combobox')) {
    if (combo.tagName !== 'SELECT') continue;
    const options = within(combo).queryAllByRole('option');
    const option = options.find(
      (o) => wanted.test(o.value ?? '') || wanted.test(o.textContent ?? ''),
    );
    if (option) return { combo, option };
  }
  return null;
}

function controlledListbox(combo) {
  const ids = [combo.getAttribute('aria-controls'), combo.getAttribute('aria-owns')]
    .filter(Boolean).join(' ').split(/\s+/);
  for (const id of ids) {
    const target = document.getElementById(id);
    if (!target) continue;
    const listbox = target.getAttribute('role') === 'listbox'
      ? target : within(target).queryByRole('listbox');
    if (listbox && isVisible(listbox)) return listbox;
  }
  return null;
}

function comboDisplay(combo) {
  return combo.tagName === 'INPUT' ? combo.value
    : combo.getAttribute('aria-valuetext') || renderedText(combo);
}

function restoredName(initial, selected, displayed, want) {
  if (initial === selected) return initial;
  // Learn only the observed replacement of the displayed choice in the name.
  // Anchor and escape its surrounding text; arbitrary renaming is not identity.
  const escape = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const choice = new RegExp(escape(displayed), 'i');
  const match = displayed && choice.exec(initial);
  if (match && !choice.test(initial.slice(match.index + displayed.length))) {
    const prefix = initial.slice(0, match.index);
    const suffix = initial.slice(match.index + displayed.length);
    const changed = new RegExp(`^${escape(prefix)}${escape(want)}${escape(suffix)}$`, 'i');
    if (changed.test(selected)) {
      return new RegExp(`^${escape(prefix)}(?:all|open|closed)${escape(suffix)}$`, 'i');
    }
  }
  throw new Error('unsupported status combobox name change: cannot identify the restored control');
}

async function chooseStatus(user, want) {
  const wanted = new RegExp(want, 'i');
  const select = statusSelect(want);
  if (select) {
    await user.selectOptions(select.combo, select.option.value);
    return;
  }
  // Custom selects may render their options in a portal. Follow the trigger's ARIA
  // relationship rather than treating a combobox as a native select or clicking a
  // matching option from an unrelated control elsewhere in the document.
  const names = new Map();
  const combos = screen.queryAllByRole('combobox', { name: (name, element) => {
    names.set(element, name);
    return true;
  } }).filter((combo) => combo.tagName !== 'SELECT');
  for (const combo of combos) {
    const displayed = comboDisplay(combo).trim();
    await user.click(combo);
    let listbox;
    try {
      listbox = await waitFor(() => {
        const current = controlledListbox(combo);
        if (!current) throw new Error('combobox has no visible associated listbox');
        return current;
      });
    } catch {
      await user.keyboard('{Escape}');
      continue;
    }
    const option = within(listbox).queryAllByRole('option', { name: wanted }).find(isVisible);
    if (option) {
      await user.click(option);
      return await waitFor(() => {
        let selectedName;
        screen.queryAllByRole('combobox', { name: (name, element) => {
          if (element === combo) selectedName = name;
          return false;
        } });
        if (selectedName === undefined) {
          throw new Error('unsupported status combobox replacement: cannot identify the restored control');
        }
        expect(comboDisplay(combo), 'choosing status did not update the filter control').toMatch(wanted);
        return restoredName(names.get(combo), selectedName, displayed, want);
      });
    }
    await user.keyboard('{Escape}');
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
      `no status filter control offering "${want}": no native select option, associated ` +
        'combobox/listbox option, radio, tab, button, checkbox, or link was available on /incidents',
    );
  }
  await user.click(clickable);
}

function showsStatus(want, comboboxName) {
  const wanted = new RegExp(want, 'i');
  if (comboboxName !== undefined) {
    const matches = screen.queryAllByRole('combobox', { name: comboboxName }).filter(isVisible);
    if (matches.length > 1) {
      // A name is not a unique identity. Unsupported ambiguity is an oracle error
      // (INCONCLUSIVE in check_ui.py), not proof of a correct or incorrect filter.
      throw new Error('ambiguous status combobox name: cannot identify the restored control');
    }
    if (!matches.length) {
      throw new Error('unsupported status combobox identity: cannot identify the restored control');
    }
    const combo = matches[0];
    const displayed = comboDisplay(combo);
    return wanted.test(displayed);
  }
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
  const request = controlledIncidents(() => page(ROWS));
  const { container } = renderAt('/incidents');
  try {
    await request.started();
    const pending = stateSignals(container, 'loading');
    expect(pending.length, 'no visible loading state while GET /v1/incidents was pending')
      .toBeGreaterThan(0);
    request.release();
    await waitFor(() => {
      expect(within(pageFor(container)).getByText(/inc-0001/)).toBeVisible();
      const loaded = stateSignals(container, 'loading');
      expect(addedSignal(loaded, pending),
        'the loading signal never changed after incidents loaded; a permanent unrelated ' +
          'status is not an incidents loading state').toBe(true);
    }, { timeout: 5000 });
  } finally {
    request.release();
  }
}, 20000);

test('bar2 a failed request shows an inline error, not a white page', async () => {
  const request = controlledIncidents(() => HttpResponse.json({ error: 'internal' }, { status: 500 }));
  const { container } = renderAt('/incidents');
  try {
    await request.started();
    const pending = stateSignals(container, 'error');
    request.release();
    await waitFor(() => {
      const failed = stateSignals(container, 'error');
      expect(addedSignal(pending, failed),
        'GET /v1/incidents returned 500 without a new visible inline error in the page')
        .toBe(true);
      expect(within(pageFor(container)).queryAllByRole('heading').some(isVisible),
        'the page heading disappeared on the error path: that is a white page, not an inline error')
        .toBe(true);
    }, { timeout: 5000 });
  } finally {
    request.release();
  }
}, 20000);

test('bar3 an empty result renders a designed empty state, not a blank region', async () => {
  const request = controlledIncidents(() => page([]));
  const { container } = renderAt('/incidents');
  try {
    await request.started();
    const pending = stateSignals(container, 'empty');
    request.release();
    await waitFor(() => {
      const empty = stateSignals(container, 'empty');
      expect(addedSignal(pending, empty),
        'GET /v1/incidents returned an empty page without a new visible empty-state message')
        .toBe(true);
    }, { timeout: 5000 });
  } finally {
    request.release();
  }
}, 20000);

test('bar4 every control on the page has a non-empty accessible name', async () => {
  stubIncidents(() => page(ROWS));
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
    'the incidents page rendered no filter or form control at all',
  ).toBeGreaterThan(0);
  for (const el of controls) {
    expect(
      el,
      `a <${el.tagName.toLowerCase()}> control has no accessible name (no <label>, ` +
        `aria-label, or aria-labelledby): ${el.outerHTML.slice(0, 140)}`,
    ).toHaveAccessibleName();
  }
}, 20000);

test('bar5 the status filter round-trips through the URL and filters visible rows', async () => {
  stubIncidents(({ request }) => {
    const wanted = new URL(request.url).searchParams.get('status');
    const rows = wanted ? ROWS.filter((r) => r.status === wanted) : ROWS;
    return page(rows);
  });
  const user = userEvent.setup();
  const { container } = renderAt('/incidents');
  await screen.findByText(/inc-0001/, undefined, { timeout: 5000 });
  const comboboxName = await chooseStatus(user, 'closed');
  await waitFor(
    () => {
      expect(
        window.location.search,
        'choosing the "closed" status did not put status=closed in the URL: the filter ' +
          'lives only in component memory, so the link is not shareable and back does nothing',
      ).toMatch(/status=closed/i);
      expectIncidentRows(container, 'inc-0002', 'inc-0001');
    },
    { timeout: 4000 },
  );
  cleanup();
  const deepLink = renderAt('/incidents?status=open');
  await waitFor(
    () => {
      expect(
        showsStatus('open', comboboxName),
        'loading /incidents?status=open did not restore the filter control to "open": the ' +
          'URL is not read back as state',
      ).toBe(true);
      expectIncidentRows(deepLink.container, 'inc-0001', 'inc-0002');
    },
    { timeout: 5000 },
  );
}, 30000);

test('bar6 axe reports no accessibility violations on the loaded page', async () => {
  stubIncidents(() => page(ROWS));
  const { container } = renderAt('/incidents');
  await screen.findByText(/inc-0001/, undefined, { timeout: 5000 });
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
  stubIncidents(() => page(ROWS));
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

test('bar8 a problem+json 500 shows its request id so the operator can find the log line', async () => {
  stubIncidents(() =>
    HttpResponse.json(
      {
        type: 'https://errors.example.internal/internal-server-error',
        title: 'Internal server error',
        status: 500,
        detail: 'The incident store did not answer in time.',
        request_id: 'req-8f3a1c',
      },
      { status: 500, headers: { 'Content-Type': 'application/problem+json', 'X-Request-ID': 'req-8f3a1c' } },
    ));
  const { container } = renderAt('/incidents');
  await waitFor(
    () => {
      const shown = within(pageFor(container)).queryAllByText(/req-8f3a1c/).some(isVisible);
      expect(
        shown,
        'GET /v1/incidents answered 500 with request_id "req-8f3a1c" and the page never showed it: ' +
          'an operator cannot find the log line for this failure',
      ).toBe(true);
      expect(within(pageFor(container)).queryAllByRole('heading').some(isVisible),
        'the page heading disappeared on the error path').toBe(true);
    },
    { timeout: 5000 },
  );
}, 20000);

test('bar9 loading more follows next_cursor to the second page', async () => {
  const cursors = [];
  stubIncidents(({ request }) => {
    const cursor = new URL(request.url).searchParams.get('cursor');
    cursors.push(cursor);
    return cursor === 'cursor-page-2' ? page([ROWS[1]], null) : page([ROWS[0]], 'cursor-page-2');
  });
  const user = userEvent.setup();
  const { container } = renderAt('/incidents');
  await waitFor(
    () =>
      expect(
        within(pageFor(container)).queryAllByText(/inc-0001/).some(isVisible),
        'the first page of incidents never rendered, so there is nothing to load more of',
      ).toBe(true),
    { timeout: 5000 },
  );
  const more = [...screen.queryAllByRole('button'), ...screen.queryAllByRole('link')].find((el) =>
    /load more|show more|more|next|older/i.test(
      `${el.textContent ?? ''} ${el.getAttribute('aria-label') ?? ''}`,
    ));
  expect(
    more,
    'the first page said next_cursor is "cursor-page-2" and the page rendered no "load more" ' +
      '(or next/older) control: the rest of the collection is unreachable',
  ).toBeTruthy();
  await user.click(more);
  await waitFor(
    () => {
      expect(
        cursors,
        'the second request did not pass the cursor back as ?cursor=cursor-page-2',
      ).toContain('cursor-page-2');
      expect(
        within(pageFor(container)).queryAllByText(/inc-0002/).some(isVisible),
        'the second page of incidents never rendered after loading more',
      ).toBe(true);
    },
    { timeout: 5000 },
  );
}, 20000);
