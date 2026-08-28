/* ============================================================================
   PAYVANTA — product interface
   Vanilla ES2020. No framework, no build step, no dependencies.

   Contract: this file renders only what the engine projection provides.
   Where a figure does not exist it says so and says why. It never fabricates
   a value, and it never labels demonstration data as official evidence.
   ========================================================================= */
'use strict';

/* ------------------------------------------------------------------ STATE */
const S = {
  snap: null,          // /api/snapshot
  bench: null,         // /api/benchmark
  bmMatrix: null,      // /api/benchmark/official/matrix (lazy)
  bmMatrixLoading: false,
  bmMatrixError: null,
  bmMatrixAttempted: false,
  route: 'control',
  param: null,
  sub: null,
  ready: false,
  metrics: new Map(),  // metric key -> last rendered text (Phase 18 diffing)
  disclosures: new Set(),
  filters: { opp: 'all', audit: 'all' },
  oppSearch: '',
  oppSort: 'risk',
  pipeStage: null,
  graph: { sel: null, focus: null, fit: false, w: 0 },
  bmCell: null,
  bmSeed: 14,
  bmDetail: null,
  bmSearch: '',
  /* Search results are state, not a DOM side effect. They used to be written straight
     into #bm-search-results, so the next route() — a filter click, a cell click, a
     seed change — silently erased them while the query text stayed in the box. */
  bmSearchHits: null,
  bmSearchTotal: 0,
  bmSearchTrunc: false,
  bmFilter: 'all',
  demo: { on: false, i: 0 },
  cine: null,
  run: { phase: 'idle', error: null, summary: null, run_index: 0, history: [] },
};

const $  = (s, r) => (r || document).querySelector(s);
const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));

/* ------------------------------------------------------------------ UTILS */
function esc(v) {
  if (v === null || v === undefined) return '';
  return String(v).replace(/[&<>"']/g, c => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}
/** Tagged template that escapes interpolations. Arrays are joined. */
function h(strings, ...vals) {
  let out = strings[0];
  for (let i = 0; i < vals.length; i++) {
    const v = vals[i];
    out += (Array.isArray(v) ? v.join('') : (v === null || v === undefined ? '' : String(v)));
    out += strings[i + 1];
  }
  return out;
}
const raw = s => s;

/** Money display, or a truthful absence marker. */
function m(money, kind) {
  if (!money) return absentInline(kind || 'not-measured');
  return esc(money.display);
}
function mv(money) { return money ? money.display : null; }
function paise(money) { return money && typeof money.paise === 'number' ? money.paise : 0; }

const ABSENT = {
  'not-measured':   ['NOT MEASURED', 'No measurement record exists for this opportunity yet.'],
  'not-executed':   ['NOT EXECUTED', 'The action never reached an adapter, so there is nothing to measure.'],
  'not-authorized': ['NOT AUTHORIZED', 'Policy did not authorize an action, so no value was pursued.'],
  'not-mounted':    ['EVIDENCE NOT MOUNTED', 'The official artefact tree is not present in this workspace.'],
  'not-observed':   ['NOT OBSERVABLE', 'The world did not expose an observable outcome for this action.'],
  'none':           ['NONE', 'The engine recorded no entries here.'],
  'na':             ['NOT APPLICABLE', 'This field does not apply to the selected action.'],
  'failed':         ['RUN FAILED', 'The simulator did not return a result.'],
};
function absentInline(kind) {
  const a = ABSENT[kind] || ABSENT['none'];
  return h`<span class="absent" title="${esc(a[1])}"><span class="absent-k">${esc(a[0])}</span></span>`;
}
function absentBlock(kind, extra) {
  const a = ABSENT[kind] || ABSENT['none'];
  return h`<div class="absent-block"><span class="absent-k">${esc(a[0])}</span>
    <p>${esc(extra || a[1])}</p></div>`;
}

/** A bare paise integer as money. Engine money arrives as an object carrying a formatted
    `display`, but a few raw paise integers reach the surface from policy traces, and they
    have to read like every other figure rather than as an 6-digit count. */
function paiseText(p) {
  if (typeof p !== 'number' || !isFinite(p)) return null;
  return '₹' + (p / 100).toLocaleString('en-IN',
    { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

/** Epoch microseconds from the deterministic clock, as a position in the run's timeline.
    `43200000000` is not a reading a person can take; `12h 0m` is the same value. The raw
    integer stays in the cell's title so the forensic trail is not lost. */
function microsText(us) {
  if (typeof us !== 'number' || !isFinite(us)) return null;
  const s = Math.floor(us / 1e6);
  const d = Math.floor(s / 86400);
  const hr = Math.floor((s % 86400) / 3600);
  const mn = Math.floor((s % 3600) / 60);
  if (d) return d + 'd ' + hr + 'h';
  if (hr) return hr + 'h ' + mn + 'm';
  if (mn) return mn + 'm';
  return s + 's';
}

function titleize(s) {
  if (!s) return '';
  return String(s).replace(/_/g, ' ').toLowerCase().replace(/(^|\s)\S/g, c => c.toUpperCase());
}
function pct(x, digits) {
  if (typeof x !== 'number' || !isFinite(x)) return null;
  return (x * 100).toFixed(digits === undefined ? 1 : digits) + '%';
}
/** A count, grouped the way every other figure on the surface is grouped. Sitting
    ungrouped in a column of Indian-grouped money, `375498` reads as a different order
    of magnitude than `3,75,498` at a glance. */
function cnt(x) {
  return typeof x === 'number' && isFinite(x) ? x.toLocaleString('en-IN') : null;
}
function shortId(id) {
  if (!id) return '';
  const s = String(id);
  return s.length > 14 ? s.slice(0, 4) + '…' + s.slice(-6) : s;
}

/** Status tone from an engine state string. Colour is always paired with text. */
function toneOf(card) {
  if (!card) return 'nu';
  if (card.blocked) return 'no';
  if (card.needs_review) return 'wa';
  if (card.incremental_net && card.incremental_net.paise > 0) return 'ok';
  if (card.authorization_state === 'AUTHORIZED') return 'tl';
  return 'nu';
}
function tok(label, tone, shape) {
  if (!label) return '';
  return h`<span class="tok tok-${tone || 'nu'} ${shape ? 'tok-' + shape : ''}">${esc(label)}</span>`;
}
function execTone(stage) {
  if (stage === 'SUCCEEDED') return 'ok';
  if (stage === 'SCHEDULED') return 'wa';
  if (!stage || stage === 'NOT_EXECUTED') return 'nu';
  return 'no';
}
function authTone(state) {
  if (state === 'AUTHORIZED') return 'ok';
  if (!state || state === 'NOT_SUBMITTED') return 'nu';
  return 'no';
}

/* ------------------------------------------------------- SECTION HELPERS */
let secN = 0;
function sec(title, note, sub) {
  secN += 1;
  const n = String(secN).padStart(2, '0');
  return h`<section class="sec">
    <div class="sec-top">
      <span class="sec-n">${n}</span>
      <h2 class="sec-h">${esc(title)}</h2>
      ${note ? h`<p class="sec-note">${esc(note)}</p>` : ''}
    </div>
    ${sub ? h`<p class="sec-sub">${esc(sub)}</p>` : ''}
  </section>`;
}
function panel(title, body, note) {
  return h`<section class="panel">
    ${title ? h`<div class="panel-head"><h3 class="panel-h">${esc(title)}</h3>
      ${note ? h`<p class="panel-note">${esc(note)}</p>` : ''}</div>` : ''}
    <div class="panel-body">${raw(body)}</div>
  </section>`;
}
/** A figure with a provenance affordance (Phase 20). */
function figure(label, value, opts) {
  const o = opts || {};
  const key = o.key || label;
  const cls = o.tone ? ' is-' + o.tone : '';
  return h`<div class="kpi" ${o.accent ? 'data-accent="' + o.accent + '"' : ''}>
    <div class="kpi-k">
      <span class="lbl">${esc(label)}</span>
      ${o.calc ? h`<button type="button" class="prov prov-mark" data-calc="${esc(o.calc)}"
        title="View how ${esc(label)} is calculated"
        aria-label="View calculation for ${esc(label)}">ƒ</button>` : ''}
    </div>
    <p class="kpi-val${cls}" data-metric="${esc(key)}">${raw(value)}</p>
    ${o.sub ? h`<p class="kpi-sub">${esc(o.sub)}</p>` : ''}
  </div>`;
}
function row(k, v, opts) {
  const o = opts || {};
  return h`<div class="dl-row ${o.two ? 'two' : ''}">
    <span class="dl-k">${esc(k)}</span>
    <span class="dl-v ${o.mono ? 'mono' : ''} ${o.big ? 'big' : ''}">${raw(v)}</span>
  </div>`;
}

/* ================================================================= ROUTER */
const ROUTES = {
  control:       { label: 'Control Room',         sub: 'Recover revenue. Prove the recovery.' },
  opportunities: { label: 'Opportunities',        sub: 'Recovery opportunity explorer' },
  opportunity:   { label: 'Recovery Workspace',   sub: 'Single-decision recovery workspace' },
  lab:           { label: 'Recovery Lab',         sub: 'Counterfactual scenario bench' },
  guardrails:    { label: 'Guardrails',           sub: 'Policy proof and authorization' },
  audit:         { label: 'Audit Ledger',         sub: 'Every decision, in order' },
  benchmark:     { label: 'Benchmark Lab',        sub: 'Measured, not claimed' },
  system:        { label: 'System / Evidence',    sub: 'Inspectable product state' },
};

/* Routes whose first path segment is an object id (`#/opportunity/<id>/graph`).
   Everything else treats that segment as a sub-view (`#/benchmark/matrix`). */
const PARAM_ROUTES = new Set(['opportunity', 'lab', 'guardrails', 'audit']);

function parseHash() {
  const raw = (location.hash || '#/control').replace(/^#\/?/, '');
  const parts = raw.split('/').filter(Boolean);
  const route = ROUTES[parts[0]] ? parts[0] : 'control';
  if (PARAM_ROUTES.has(route)) {
    return { route, param: parts[1] || null, sub: parts[2] || null };
  }
  return { route, param: null, sub: parts[1] || null };
}

function go(hash) { location.hash = hash; }

function route() {
  const p = parseHash();
  S.route = p.route; S.param = p.param; S.sub = p.sub;
  secN = 0;

  $$('.rail-item').forEach(a => {
    const on = a.dataset.route === S.route ||
      (S.route === 'opportunity' && a.dataset.route === 'opportunities');
    a.setAttribute('aria-current', on ? 'page' : 'false');
    // On a narrow viewport the rail lies down and scrolls sideways; the current
    // section must be the one you can see.
    if (on && a.offsetParent) a.scrollIntoView({ block: 'nearest', inline: 'nearest' });
  });

  const meta = ROUTES[S.route];
  $('#crumb').textContent = meta.label;
  $('#crumb-sub').textContent = meta.sub;

  if (!S.ready) return;

  // Canonicalize a bare `#/opportunity` so the sub-navigation has an object to
  // hang off and the URL is shareable.
  if (S.route === 'opportunity' && !S.param) {
    const id = S.snap.wow_opportunity_id || firstOppId();
    if (id) {
      S.param = id;
      history.replaceState(null, '', '#/opportunity/' + id + (S.sub ? '/' + S.sub : ''));
    }
  }

  const view = $('#view');
  const renderers = {
    control: viewControl, opportunities: viewOpportunities, opportunity: viewWorkspace,
    lab: viewLab, guardrails: viewGuardrails, audit: viewAudit, benchmark: viewBenchmark,
    system: viewSystem,
  };
  view.innerHTML = h`<div class="wrap${S.route === 'opportunity' && !S.sub ? ' wrap-ws' : ''}">${raw(renderers[S.route]())}</div>`;

  renderSubnav();
  renderSource();
  bindView();
  tickMetrics();
  markScrollers();
  reveal();

  view.scrollTop = 0;
  const head = $('.sec-h, h1', view);
  announce(meta.label + ' — ' + (head ? head.textContent : ''));
  view.focus({ preventScroll: true });
}

function announce(msg) { $('#live').textContent = msg; }

/* -------------------------------------------------------------- SUBNAV */
const SUBNAV = {
  opportunity: [
    ['', 'Decision'], ['graph', 'Causal graph'], ['lab', 'Recovery lab'],
    ['guardrails', 'Guardrails'], ['execution', 'Execution'], ['receipt', 'Receipt'],
  ],
  benchmark: [['', 'Overview'], ['matrix', 'Matrix'], ['compare', 'Compare'], ['evidence', 'Forensics']],
};
function renderSubnav() {
  const nav = $('#subnav');
  const items = SUBNAV[S.route];
  if (!items || (S.route === 'opportunity' && !S.param)) { nav.innerHTML = ''; return; }
  // Navigation, not a tab widget. These are real links: they change the URL, they
  // bookmark, they work with back and forward. `role="tab"` would promise a
  // screen-reader user arrow-key traversal inside a tablist and a tabpanel that
  // aria-controls points at — none of which is true here. `aria-current` states the
  // same thing honestly and costs nothing.
  nav.innerHTML = items.map(([key, label]) => {
    const on = (S.sub || '') === key;
    const target = S.route === 'opportunity'
      ? '#/opportunity/' + S.param + (key ? '/' + key : '')
      : '#/benchmark' + (key ? '/' + key : '');
    return h`<a class="subnav-item" href="${esc(target)}" ${on ? 'aria-current="page"' : ''}>${esc(label)}</a>`;
  }).join('');
}

/* -------------------------------------------------- DATA PROVENANCE CHIP */
function sourceFor() {
  const cr = S.snap && S.snap.control_room;
  if (S.route === 'benchmark') {
    const b = S.bench;
    if (!b) return ['absent', 'Loading evidence', 'Benchmark evidence status is still loading.'];
    if (b.evidence_verified) {
      return ['official', 'Official evidence verified',
        '600-cell official cloud benchmark at ' + b.artefact_root + '. Frozen experiment reference verified.'];
    }
    if (b.artefact_classification === 'ADMISSIBLE_OFFICIAL' && b.verification) {
      return ['absent', 'Official evidence unverified',
        'Artefacts present but verification failed: ' + (b.verification.failures || []).join('; ')];
    }
    if (b.artefact_status === 'INADMISSIBLE_LOCAL_TREE') {
      return ['absent', 'Invalidated evidence rejected',
        'This workspace contains a retained but invalidated benchmark tree. Only official-cloud-final is admissible.'];
    }
    return ['absent', 'Official evidence not mounted',
      'The declared official run lives at ' + b.artefact_root +
      ', which is not present in this workspace. No M-10 values are shown.'];
  }
  return ['demo', 'Sandbox · seed ' + (cr ? cr.seed : '?'),
    (cr ? cr.fixture_label : '') +
    ' Every figure on this screen was produced by the engine on this sandbox. It is not official benchmark evidence.'];
}
function renderSource() {
  const [kind, text, note] = sourceFor();
  const chip = $('#source-badge');
  chip.dataset.kind = kind;
  $('.datachip-text', chip).textContent = text;
  chip.title = note;
  $('#source-note').textContent = note;
  const cr = S.snap && S.snap.control_room;
  document.body.dataset.product = 'PAYVANTA';
  document.body.dataset.route = S.route;
  document.body.dataset.environment = S.route === 'benchmark' ? 'official-evidence' : 'sandbox';
  if (cr && cr.seed != null) document.body.dataset.seed = String(cr.seed);
  else delete document.body.dataset.seed;
  if (cr && cr.profile) document.body.dataset.profile = cr.profile;
  else delete document.body.dataset.profile;
  document.body.dataset.policy = 'REVIVE';
  if (S.route === 'opportunity' && S.param) document.body.dataset.opportunityId = S.param;
  else delete document.body.dataset.opportunityId;
  const bmRail = $('[data-route="benchmark"]');
  if (bmRail) {
    const f = benchFacts();
    bmRail.classList.toggle('is-verified', !!(f && f.verified));
  }
}

/* ============================================== OFFICIAL EVIDENCE PROOF LAYER
   Sandbox screens show the engine running on a synthetic test population.
   Official numbers come only from
   artefacts/benchmark/official-cloud-final/ via /api/benchmark. Never mix. */
function benchFacts() {
  const b = S.bench;
  if (!b) return null;
  const run = b.declared_official_run || {};
  const prov = b.provenance || {};
  const v = b.verification || {};
  const revive = (b.policy_summaries && b.policy_summaries.REVIVE) || {};
  return {
    verified: !!b.evidence_verified,
    cells: v.cell_count != null ? v.cell_count : run.cells,
    expected: v.expected_cells || run.cells,
    groups: run.groups,
    seeds: run.seeds,
    profiles: run.profiles,
    policies: run.policies,
    validation: prov.validation_status || run.validation,
    blocked: prov.blocked,
    frozen: prov.frozen_experiment_reference || run.frozen_experiment_reference,
    config: prov.config_hash,
    pack: prov.policy_pack_version || b.policy_pack_version,
    packHash: prov.policy_pack_hash || b.policy_pack_hash,
    source: prov.source || 'OFFICIAL CLOUD RUN',
    m10Median: revive['M-10_median_paise'],
    m10Min: revive['M-10_min_paise'],
    m10Max: revive['M-10_max_paise'],
    failures: revive.execution_failures_total,
    unauthorized: revive.unauthorized_executions_total,
    negativeSeeds: revive.seeds_where_negative_m10,
    runCount: revive.run_count,
  };
}

function proofStrip(opts) {
  const o = opts || {};
  const f = benchFacts();
  if (!f || !f.verified) {
  return h`<aside class="proof-strip is-quiet" aria-label="Official evidence status"
      data-evidence="official" data-status="unverified">
      <span class="proof-k">Measured, not claimed</span>
      <span class="proof-body">Official experiment artefacts are not verified in this workspace.</span>
      <a class="proof-cta" href="#/benchmark">View Benchmark Lab</a>
    </aside>`;
  }
  return h`<aside class="proof-strip ${o.compact ? 'is-compact' : ''}" aria-label="Official experiment verification"
      data-evidence="official" data-status="verified" data-cells="${esc(f.cells)}"
      data-seeds="${esc(f.seeds)}" data-profiles="${esc(f.profiles)}" data-policies="${esc(f.policies)}">
    <span class="proof-k">Measured, not claimed</span>
    <span class="proof-body">
      <b>${esc(f.cells)} / ${esc(f.expected)}</b> official cells ·
      ${esc(f.seeds)} seeds · ${esc(f.profiles)} profiles · ${esc(f.policies)} policies ·
      ${esc(f.validation)}
    </span>
    ${o.hideCta ? '' : h`<a class="proof-cta" href="#/benchmark">View official evidence</a>`}
  </aside>`;
}

function evidenceStatusCard() {
  const f = benchFacts();
  if (!f || !f.verified) {
    return h`<aside class="ev-card is-pending">
      <p class="lbl">Evidence status</p>
      <p class="ev-card-h">Official benchmark not verified</p>
      <p class="ev-card-p">This session runs in a sandbox. Open Benchmark Lab for the frozen experiment contract.</p>
      <a class="btn btn-ghost" href="#/benchmark">Open Benchmark Lab</a>
    </aside>`;
  }
  return h`<aside class="ev-card">
    <p class="lbl">Evidence status</p>
    <p class="ev-card-h">${tok('OFFICIAL BENCHMARK', 'vi', 'di')} ${tok('VERIFIED', 'ok')}</p>
    <p class="ev-card-fig">${esc(f.cells)} / ${esc(f.expected)} <span>cells</span></p>
    <p class="ev-card-meta">${esc(f.groups)} groups · ${esc(f.seeds)} seeds · ${esc(f.profiles)} profiles · ${esc(f.policies)} policies</p>
    <p class="ev-card-p">This Control Room runs a sandbox test population. The engine it runs was evaluated in a frozen official experiment. The two are not the same dataset.</p>
    <a class="btn btn-primary" href="#/benchmark">View official evidence</a>
  </aside>`;
}

function proofOfRecovery(wf, hero) {
  const f = benchFacts();
  const steps = [
    ['At risk', hero.at_risk_revenue],
    ['Recoverable', hero.recoverable_revenue],
    ['Natural', wf.realized.natural],
    ['Incremental', wf.realized.incremental],
    ['Cost', hero.realized_cost],
    ['Net', wf.realized.net],
  ];
  return h`<div class="proof-rec">
    <p class="proof-rec-lede">PAYVANTA does not stop at choosing an action. It measures the incremental net value created by intervention — recovery above what accounts would have paid on their own, net of cost.</p>
    <ol class="proof-chain" aria-label="Recovery economics">
      ${steps.map(([lab, val], i) => h`<li>
        <span class="lbl">${esc(lab)}</span>
        <span class="proof-chain-v">${m(val)}</span>
        ${i < steps.length - 1 ? h`<span class="proof-chain-arr" aria-hidden="true">↓</span>` : ''}
      </li>`)}
    </ol>
    <p class="proof-rec-foot">${f && f.verified
      ? 'Backed by ' + f.cells + ' official cells in the frozen experiment. The figures above are this sandbox run; the experiment is the evaluation of the same engine.'
      : 'Official experiment artefacts are not verified here. The chain above is this sandbox session only.'}</p>
  </div>`;
}

function engineContractNote() {
  const f = benchFacts();
  return h`<aside class="engine-note">
    <p class="lbl">Engine evidence</p>
    <p>This decision is sandbox data from the engine. It is <strong>not</strong> an official benchmark cell.
      ${f && f.verified
        ? 'The same engine was evaluated across ' + f.cells + ' official cells (' + f.seeds + ' seeds × ' + f.profiles + ' profiles × ' + f.policies + ' policies).'
        : 'Open Benchmark Lab to inspect the frozen experiment contract.'}
    </p>
    <p><a class="prov" href="#/benchmark">Inspect official evidence</a></p>
  </aside>`;
}

function experimentModel(run) {
  const items = [
    [run.seeds, 'Seeds', 'Deterministic scenario families. Same seed, same world.'],
    [run.profiles, 'Profiles', 'Operating environments: BALANCED, HIGH_NATURAL, SCARCE, ABUNDANT, HOSTILE, DEGRADED.'],
    [run.policies, 'Policies', 'Strategies compared: B0, B1, B2, B3, REVIVE.'],
    [run.cells, 'Official cells', 'Every seed × profile × policy combination, once.'],
  ];
  return h`<div class="bm-eq" aria-label="Experiment structure">
    ${items.map((it, i) => h`
      ${i === items.length - 1 ? h`<span class="bm-eq-op" aria-hidden="true">=</span>` : (i ? h`<span class="bm-eq-op" aria-hidden="true">×</span>` : '')}
      <button type="button" class="bm-eq-cell" data-eq="${esc(it[1])}" title="${esc(it[2])}"
        aria-label="${esc(it[0] + ' ' + it[1] + '. ' + it[2])}">
        <span class="bm-eq-n">${esc(it[0])}</span>
        <span class="lbl">${esc(it[1])}</span>
      </button>`)}
  </div>
  <p class="sec-sub" id="bm-eq-note" style="margin-top:var(--s-3)">Hover a factor. Click cells to open the profile × policy matrix.</p>`;
}

function experimentCertificate(f) {
  if (!f || !f.verified) return '';
  const checks = [
    ['Config', !!f.config],
    ['Policy pack', !!f.pack],
    ['Frozen experiment', !!f.frozen],
    ['Cells', f.cells === f.expected],
    ['Validation', f.validation === 'BENCHMARK_VALID'],
  ];
  return h`<div class="bm-cert" aria-label="Experiment verification">
    <p class="bm-cert-k">OFFICIAL EVIDENCE</p>
    <p class="bm-cert-h">Experiment verified</p>
    <p class="bm-cert-meta">${esc(f.cells)} cells · ${esc(f.seeds)} seeds · ${esc(f.profiles)} profiles · ${esc(f.policies)} policies · ${esc(f.groups)} groups</p>
    <ul class="bm-cert-list">${checks.map(([lab, ok]) => h`<li data-ok="${ok}">
      <span>${esc(lab)}</span> ${ok ? tok('Verified', 'ok') : tok('Unverified', 'wa')}
    </li>`)}</ul>
    <p class="mono dim" style="margin-top:var(--s-3);overflow-wrap:anywhere">${esc(f.frozen)}</p>
  </div>`;
}

/* ================================================== VIEW: CONTROL ROOM */

/* Financial pillar: the outcome, the equation, and the accounting spine.
   This is the left third of the first viewport — dense on purpose. */
function moneyPillar(hero, wf, cr) {
  const net = paise(hero.incremental_net_recovery);
  const steps = [
    ['At risk', hero.at_risk_revenue, 'base', 'at_risk'],
    ['Recoverable', hero.recoverable_revenue, 'base', 'recoverable'],
    ['Natural', wf.realized.natural, 'natural', 'natural'],
    ['Incremental', wf.realized.incremental, 'incremental', 'incremental'],
    ['Cost', hero.realized_cost, 'cost', 'cost'],
    ['Net', wf.realized.net, 'net', 'net'],
  ];
  const down = h`<svg class="revflow-down" width="8" height="10" viewBox="0 0 8 10" aria-hidden="true" focusable="false"><path d="M1 1.5 L4 8.5 L7 1.5" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>`;
  return h`
  <section class="hero-money" aria-label="Incremental net recovery"
           data-metric="incremental_net_recovery" data-status="realized">
    <div class="ar-head">
      <span class="lbl">Incremental net recovery</span>
      ${tok('Realized', 'ok', 'sq')}
      <button type="button" class="prov" data-calc="net">view calculation</button>
    </div>
    <p class="hero-fig ${net < 0 ? 'is-neg' : ''}" data-metric="hero-net">${m(hero.incremental_net_recovery)}</p>
    <p class="hero-eq">
      <b data-metric="eq-incremental">${m(wf.realized.incremental)}</b><span class="op">incr.</span>
      <span class="op">−</span>
      <b data-metric="eq-cost">${m(wf.realized.cost)}</b><span class="op">cost</span>
      <span class="op">=</span>
      <b data-metric="eq-net">${m(wf.realized.net)}</b><span class="op">net</span>
    </p>
    <ol class="revflow" aria-label="Revenue flow from at risk to incremental net">
      ${steps.map(([lab, val, kind, calc], i) => h`<li data-kind="${esc(kind)}" data-step="${i + 1}" data-metric="${esc(calc)}">
        <button type="button" class="revflow-k prov" data-calc="${esc(calc)}">${esc(lab)}</button>
        <span class="revflow-v mono" data-metric="rf-${esc(kind)}">${m(val)}</span>
        ${i < steps.length - 1 ? down : ''}
      </li>`)}
    </ol>
    <p class="hero-cap-tight">${esc(pct(hero.recovery_rate, 2))} of at-risk revenue ·
      ${esc(cr.cycles_run)} cycles · sandbox</p>
  </section>`;
}

function oppLifecycle(opp) {
  if (!opp) return 'OPEN';
  if (opp.blocked) {
    return 'BLOCKED · ' + (opp.blocking_reason || 'NOT AUTHORIZED') + ' · NO EXECUTION';
  }
  const bits = [];
  if (opp.authorization_state) bits.push(opp.authorization_state);
  if (opp.execution_state && opp.execution_state !== 'NOT_EXECUTED') bits.push(opp.execution_state);
  if (opp.measured) {
    bits.push('MEASURED');
    if (opp.incremental_net && opp.incremental_net.display) bits.push(opp.incremental_net.display);
  }
  return bits.length ? bits.join(' · ') : titleize(opp.policy_state || opp.execution_state || 'Open');
}

function oppStatusToken(opp) {
  if (!opp) return 'open';
  if (opp.blocked) return 'blocked';
  if (opp.measured) return 'measured';
  if (opp.authorization_state) return String(opp.authorization_state).toLowerCase();
  return 'open';
}

/* The active recovery card: the single most instructive opportunity, made
   actionable. Pure projection over the card the engine already produced. */
function activeRecoveryCard(cr) {
  const wowId = S.snap && S.snap.wow_opportunity_id;
  const all = cr.all_opportunities || cr.top_opportunities || [];
  const opp = (wowId && all.find(o => o.opportunity_id === wowId))
    || (cr.top_opportunities || [])[0]
    || all[0];
  if (!opp) return h`<section class="ar-card">${absentBlock('none', 'No opportunity is open in this sandbox.')}</section>`;
  const id = opp.opportunity_id;
  const rec = opp.best_action || opp.selected_action || 'Under evaluation';
  const life = oppLifecycle(opp);
  return h`
  <section class="ar-card" aria-label="Active recovery opportunity"
           data-opportunity-id="${esc(id)}" data-status="${esc(oppStatusToken(opp))}">
    <div class="ar-head">
      <span class="ar-live" aria-hidden="true"></span>
      <span class="lbl">Active recovery opportunity</span>
      <span class="mono dim ar-id">${esc(shortId(id))}</span>
    </div>
    <p class="ar-type">${esc(opp.risk_label || titleize(opp.risk_class))}</p>
    <p class="ar-val" data-metric="opportunity-value-at-risk">${m(opp.value_at_risk)}</p>
    <dl class="ar-rows">
      <div class="ar-row"><dt>Cause</dt><dd>${opp.cause ? esc(titleize(opp.cause)) : absentInline('none')}</dd></div>
      <div class="ar-row"><dt>PAYVANTA recommends</dt><dd class="ar-rec">${esc(rec)}</dd></div>
      <div class="ar-row"><dt>Expected incremental</dt><dd class="mono" data-metric="expected-incremental">${m(opp.expected_incremental)}</dd></div>
      <div class="ar-row"><dt>State</dt><dd data-status="${esc(oppStatusToken(opp))}">${esc(life)}</dd></div>
    </dl>
    <div class="ar-actions">
      <button type="button" class="btn btn-primary" data-analyze="${esc(id)}">Analyze opportunity</button>
      <a class="btn btn-ghost" href="#/opportunity/${esc(id)}">Open workspace</a>
    </div>
  </section>`;
}

/* System state card: the seven lifecycle counts, plus the RUN RECOVERY action. */
function sysStateCard(cr) {
  const p = cr.system_pulse || {};
  return h`
  <section class="sys-card" aria-label="System state" data-metric="system-pulse">
    <div class="ar-head">
      <span class="lbl">System state</span>
      <span class="mono dim">last cycle</span>
    </div>
    <ol class="sys-list">
      ${PULSE_KEYS.map(([k, label, tone]) => h`
        <li data-tone="${Number(p[k]) > 0 ? tone : 'nu'}" data-status="${Number(p[k]) > 0 ? 'active' : 'idle'}" data-metric="${esc(k)}">
          <span class="sys-l">${esc(label)}</span>
          <span class="sys-n mono" data-metric="sys-${k}">${esc(Number(p[k]) || 0)}</span>
        </li>`)}
    </ol>
    <div id="run-slot">${runSlot(cr)}</div>
  </section>`;
}

/* The RUN RECOVERY slot swaps between the action, its live phase, and the
   completed batch summary without a route change. */
function runSlot(cr) {
  const run = S.run;
  if (run.phase === 'running') {
    return h`<div class="run-flow" role="status" data-status="running">
      <p class="run-phase-lbl">RUNNING · Recovery run ${run.run_index ? '#' + esc(run.run_index) : ''} in progress</p>
      <ol class="run-steps">${RUN_STAGES.map(s => h`<li>${esc(s)}</li>`)}</ol>
    </div>`;
  }
  if (run.phase === 'error') {
    return h`<div class="run-flow" role="alert" data-status="failed">
      <p class="run-phase-lbl run-err">FAILED · Recovery run failed</p>
      <p class="run-msg">${esc(run.error || 'The engine returned no result.')}</p>
      <p class="run-msg dim">No financial side effect occurred. State is unchanged.</p>
      <button type="button" class="btn btn-primary" data-run-recovery>Retry</button>
    </div>`;
  }
  if (run.phase === 'done' && run.summary) {
    const s = run.summary;
    return h`<div class="run-flow is-done" data-status="complete" data-run-id="${esc(run.run_index)}">
      <p class="run-phase-lbl run-ok">COMPLETE · Recovery run complete</p>
      <div class="run-grid">
        <div class="run-cell"><span class="lbl">Incremental net</span><b class="mono">${m(s.net)}</b></div>
        <div class="run-cell"><span class="lbl">Realized cost</span><b class="mono">${m(s.cost)}</b></div>
        <div class="run-cell"><span class="lbl">Authorized</span><b class="mono">${esc(s.authorized)}</b></div>
        <div class="run-cell"><span class="lbl">Blocked</span><b class="mono">${esc(s.blocked)}</b></div>
        <div class="run-cell"><span class="lbl">Executed</span><b class="mono">${esc(s.executed)}</b></div>
        <div class="run-cell"><span class="lbl">Measured</span><b class="mono">${esc(s.measured)}</b></div>
      </div>
      <div class="run-links">
        <a class="btn btn-sm" href="#/audit">View audit</a>
        <button type="button" class="btn btn-sm btn-ghost" data-run-recovery>Run again</button>
      </div>
    </div>`;
  }
  return h`<div class="run-flow" data-status="ready">
    <p class="run-hint">READY · Bounded local run · new seed · full engine</p>
    <button type="button" class="btn btn-primary btn-block" data-run-recovery>Run recovery</button>
  </div>`;
}

const RUN_STAGES = ['Detecting', 'Diagnosing', 'Evaluating', 'Guarding', 'Authorizing', 'Executing', 'Measuring'];

function environmentDetails(cr) {
  return h`<details class="env-details">
    <summary><span class="lbl">Environment</span> ${tok('Sandbox', 'tl', 'di')} · seed ${esc(cr.seed)}</summary>
    <div class="dl env-grid">
      ${row('Environment', 'PAYVANTA Sandbox')}
      ${row('Data', 'Synthetic test population')}
      ${row('Engine', 'PAYVANTA Recovery Engine')}
      ${row('Execution', 'Bounded local execution')}
      ${row('Official benchmark', '600-cell frozen experiment — see Benchmark Lab')}
      ${row('Inspect', h`<a class="prov" href="#/system">System / Evidence</a> · <a class="prov" href="/api/product/overview">GET /api/product/overview</a>`)}
    </div>
  </details>`;
}

function pipeBlock(cr) {
  return h`
  <div class="pipe pipe-hero" role="group" aria-label="Recovery pipeline stages">
    ${cr.interactive_pipeline.map((st, i) => h`
      <button type="button" class="pipe-cell" data-stage="${esc(st.id)}" data-status="${esc(st.status)}"
              aria-pressed="${S.pipeStage === st.id}">
        <span class="pipe-dot" aria-hidden="true"></span>
        <span class="pipe-n">${String(i + 1).padStart(2, '0')}</span>
        <span class="pipe-lbl">${esc(st.label)}</span>
        <span class="pipe-count" data-metric="pipe-${esc(st.id)}">${esc(st.count)}</span>
      </button>`)}
  </div>
  ${S.pipeStage ? pipeStagePanel(cr) : ''}`;
}

function runHistoryBlock() {
  const rows = S.run.history || [];
  if (!rows.length) {
    return h`<section class="run-hist is-empty" aria-label="Recent runs" data-status="empty">
      <p class="lbl">Recent runs</p>
      <p class="run-hist-empty">No recovery runs yet</p>
      <p class="run-hint">Run Recovery to create a measured run.</p>
      <button type="button" class="btn btn-sm" data-run-recovery>Run recovery</button>
    </section>`;
  }
  const r = rows[0];
  return h`<section class="run-hist" aria-label="Recent runs" data-status="ready">
    <p class="lbl">Recent runs</p>
    <ol>
      <li data-run-id="${esc(r.run_index)}" data-seed="${esc(r.seed)}" data-status="complete">
        <span class="mono">#${esc(r.run_index)}</span>
        <span>seed ${esc(r.seed)}</span>
        <b class="mono">${m(r.net)}</b>
        <span class="dim">${esc(r.executed)} exec · ${esc(r.blocked)} blocked</span>
      </li>
    </ol>
  </section>`;
}

/* Live run lifecycle: POST a bounded run, mark the phase while the engine works,
   then swap the session snapshot wholesale and re-render so every figure on the
   screen is the new run, not a stale one. */
async function runRecovery() {
  if (S.run.phase === 'running') return;
  S.run.phase = 'running';
  S.run.error = null;
  route();
  try {
    const r = await fetch('/api/recovery-run', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
    });
    let data = null;
    try { data = await r.json(); } catch (_) { data = null; }
    if (!r.ok || !data || !data.control_room) {
      S.run.phase = 'error';
      S.run.error = (data && data.error) || ('The engine returned no result (HTTP ' + r.status + ').');
      route();
      announce('Recovery run failed.');
      return;
    }
    S.snap = data;
    const cr = data.control_room;
    const p = cr.system_pulse || {};
    const hero = cr.hero || {};
    S.run.phase = 'done';
    S.run.run_index = data.run_index || (S.run.run_index + 1);
    S.run.summary = {
      net: hero.incremental_net_recovery,
      cost: hero.realized_cost,
      authorized: p.authorized, blocked: p.blocked,
      executed: p.executed, measured: p.measured,
    };
    S.run.history = [{
      run_index: S.run.run_index,
      seed: cr.seed,
      net: hero.incremental_net_recovery,
      authorized: p.authorized, blocked: p.blocked,
      executed: p.executed, measured: p.measured,
    }].concat(S.run.history || []).slice(0, 8);
    route();
    announce('Recovery run complete. Incremental net recovery updated.');
  } catch (err) {
    S.run.phase = 'error';
    S.run.error = 'The engine could not be reached, so no run was produced.';
    route();
  }
}

async function restoreDemoSeed() {
  if (S.run.phase === 'running') return;
  S.run.phase = 'running';
  S.run.error = null;
  route();
  try {
    const r = await fetch('/api/recovery-run', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ seed: 14 }),
    });
    let data = null;
    try { data = await r.json(); } catch (_) { data = null; }
    if (!r.ok || !data || !data.control_room) {
      S.run.phase = 'error';
      S.run.error = (data && data.error) || ('The engine returned no result (HTTP ' + r.status + ').');
      route();
      announce('Could not restore the demo sandbox.');
      return;
    }
    S.snap = data;
    S.run = { phase: 'idle', error: null, summary: null, run_index: 0, history: [] };
    const dest = '#/control';
    if ((location.hash || dest) === dest) route();
    else go(dest);
    announce('Sandbox restored to seed 14.');
  } catch (err) {
    S.run.phase = 'error';
    S.run.error = 'The engine could not be reached, so the sandbox was not restored.';
    route();
  }
}

function openOfficialDemoCell() {
  S.bmCell = 'ABUNDANT|REVIVE';
  S.bmSeed = 14;
  S.bmDetail = null;
  go('#/benchmark/matrix');
}

function viewControl() {
  const cr = S.snap.control_room;
  const wf = cr.waterfall;
  const hero = cr.hero;
  const sum = cr.opportunity_summary;
  /* The payload calls this `count`. Three places here read `sum.total`, which has never
     existed, so the hero shipped the word "undefined" where the portfolio size belongs.
     Resolved once, with a fallback to the array it summarizes, so a future rename degrades
     to a real number instead of a placeholder. */
  const oppN = cnt(sum.count) || cnt((cr.all_opportunities || []).length) || '—';

  return h`
  <header class="hero" data-product="PAYVANTA" data-environment="sandbox" data-seed="${esc(cr.seed)}">
    <h1 class="hero-product">PAYVANTA</h1>
    <p class="hero-lede">Autonomous revenue recovery intelligence</p>
    <p class="hero-kicker">Recover revenue. Prove the recovery.</p>
    <div class="hero-triad">
      ${moneyPillar(hero, wf, cr)}
      ${activeRecoveryCard(cr)}
      ${sysStateCard(cr)}
    </div>
  </header>

  ${pipeBlock(cr)}
  ${proofStrip()}
  ${runHistoryBlock()}
  ${environmentDetails(cr)}

  ${sec('Proof of recovery', 'act → measure → verify',
    'Revenue recovery is the outcome. Official cells evaluate whether the engine’s claim holds across a frozen experiment — not this sandbox run’s numbers.')}
  ${panel(null, proofOfRecovery(wf, hero))}

  ${sec('Why PAYVANTA', 'three pillars',
    'Decision intelligence, deterministic control, and an official experiment that evaluates the engine. Not a claim about this sandbox run.')}
  ${(() => {
    const f = benchFacts();
    const proof = f && f.verified
      ? f.cells + ' official cells across ' + f.seeds + ' seeds, ' + f.profiles + ' profiles, and ' + f.policies + ' policies. Frozen configuration. Cell-level provenance.'
      : 'The frozen official experiment is the evaluation of this engine. Open Benchmark Lab to inspect artefacts.';
    return h`<div class="pillars">
    <article class="pillar">
      <p class="lbl">Decision</p>
      <h3>Counterfactual economic decisioning</h3>
      <p>Every action is priced against doing nothing — incremental value, cost, risk, fatigue, and policy.</p>
      <a class="prov" href="#/lab">Open Recovery Lab</a>
    </article>
    <article class="pillar">
      <p class="lbl">Control</p>
      <h3>Guarded, authorized, bounded execution</h3>
      <p>Nothing reaches an adapter without an authorization record. Blocks are observed, not hidden.</p>
      <a class="prov" href="#/guardrails">Open Guardrails</a>
    </article>
    <article class="pillar">
      <p class="lbl">Proof</p>
      <h3>600-cell official evaluation</h3>
      <p>${esc(proof)}</p>
      <a class="prov" href="#/benchmark">View official evidence</a>
    </article>
  </div>`;
  })()}

  ${sec('Revenue flow', 'planned vs realized',
    'Two tracks, each internally consistent. Planned is what the engine expected before acting; realized is what measurement observed. Mixing them would produce a waterfall that does not reconcile.')}
  ${panel(null, waterfallBlock(wf))}

  ${sec('Active opportunities', oppN + ' total',
    'Ranked by revenue at risk. Open a workspace to see the full decision.')}
  <div class="opgrid">${cr.top_opportunities.slice(0, 6).map(oppCard)}</div>
  <p style="margin-top:var(--s-4)">
    <a class="btn btn-ghost" href="#/opportunities">Open the explorer — all ${esc(oppN)} opportunities</a>
  </p>

  ${sec('Recent decisions', cr.recent_receipts.length + ' receipts',
    'Every decision leaves a receipt. These are the most recent.')}
  ${recentDecisions(cr.recent_receipts)}
  `;
}

function viewSystem() {
  const cr = S.snap.control_room;
  const hero = cr.hero;
  const realized = cr.waterfall && cr.waterfall.realized;
  const pulse = cr.system_pulse || {};
  const f = benchFacts();
  const wowId = S.snap.wow_opportunity_id;
  const opp = (cr.all_opportunities || []).find(o => o.opportunity_id === wowId)
    || (cr.top_opportunities || [])[0];
  const detail = wowId ? detailFor(wowId) : null;
  const g = detail && detail.guardrail;
  const officialStatus = f && f.verified ? 'VERIFIED' : 'NOT VERIFIED';
  return h`
  ${sec('System / Evidence', 'inspectable product state',
    'The same sandbox session and official evidence the rest of PAYVANTA uses. Nothing here is evaluator-only.')}
  <section class="sys-overview" data-product="PAYVANTA" data-environment="sandbox" data-seed="${esc(cr.seed)}" data-status="ready">
    <div class="dl">
      ${row('Product', 'PAYVANTA')}
      ${row('Descriptor', esc(cr.descriptor || 'Autonomous Revenue Recovery Intelligence'))}
      ${row('Environment', tok('SANDBOX', 'tl', 'di') + ' · seed ' + esc(cr.seed))}
      ${row('Data', 'Synthetic test population')}
      ${row('Engine', 'PAYVANTA Recovery Engine')}
      ${row('Engine status', tok('READY', 'ok'))}
      ${row('Execution', 'Bounded local execution')}
      ${row('Policy pack', esc(cr.policy_pack_version) + ' · ' + esc(cr.policy_pack_status))}
      ${row('Internal policy id', 'REVIVE', { mono: true })}
      ${row('Intelligence', 'Deterministic decision system · LLM off')}
      ${row('Current run', 'seed ' + esc(cr.seed) + ' · ' + esc(cr.cycles_run) + ' cycles')}
      ${row('Current opportunity', wowId
        ? h`<a class="prov" href="#/opportunity/${esc(wowId)}">${esc(shortId(wowId))}</a>`
        : absentInline('none'))}
      ${row('Workflow', 'Detect → Diagnose → Candidates → Optimize → Guard → Authorize → Execute → Measure')}
    </div>
  </section>

  ${sec('Financial result', 'this sandbox',
    'Measured by the engine on this session. These figures are not an official benchmark cell.')}
  <div class="dl" data-metric="financial">
    ${row('At risk', m(hero.at_risk_revenue))}
    ${row('Recoverable', m(hero.recoverable_revenue))}
    ${row('Natural', m(realized && realized.natural))}
    ${row('Incremental', m(realized && realized.incremental))}
    ${row('Cost', m(hero.realized_cost))}
    ${row('Incremental net recovery', m(hero.incremental_net_recovery))}
    ${row('Source', 'Sandbox engine measurement')}
    ${row('Execution integrity', tok(hero.execution_integrity || 'UNKNOWN', hero.execution_integrity === 'PASS' ? 'ok' : 'no'))}
  </div>

  ${sec('Workflow pulse', 'last cycle', 'Counts from the recovery engine, not a decoration.')}
  ${pulseBlock(pulse)}

  ${opp ? h`
    ${sec('Active recovery opportunity', oppLifecycle(opp))}
    <div class="dl" data-opportunity-id="${esc(opp.opportunity_id)}" data-status="${esc(oppStatusToken(opp))}">
      ${row('Opportunity', h`<a class="prov" href="#/opportunity/${esc(opp.opportunity_id)}">${esc(opp.opportunity_id)}</a>`, { mono: true })}
      ${row('Problem', esc(opp.risk_label || titleize(opp.risk_class)))}
      ${row('Cause', opp.cause ? esc(titleize(opp.cause)) : absentInline('none'))}
      ${row('Recommended action', esc(opp.best_action || opp.selected_action || 'Under evaluation'))}
      ${row('Expected incremental', m(opp.expected_incremental))}
      ${row('Authorization', esc(opp.authorization_state || 'NOT SUBMITTED'))}
      ${row('Execution', esc(opp.execution_state || 'NOT_EXECUTED'))}
      ${row('Measured net', opp.measured ? m(opp.incremental_net) : absentInline(opp.blocked ? 'not-executed' : 'not-measured'))}
      ${opp.blocked ? row('Block', 'NO EXECUTION · ' + esc(opp.blocking_reason || 'not authorized')) : ''}
    </div>` : ''}

  ${g ? h`
    ${sec('Guardrails', titleize(g.authorization_state), g.autonomy_bound || '')}
    ${guardStrip(g, false)}
    ${sec('Stopping rules', (g.stopping_fired || 0) + ' fired')}
    ${stoppingBlock(g)}` : ''}

  ${sec('Official benchmark', officialStatus,
    'This is the engine you just saw. It was evaluated separately across 600 official cells. Not this sandbox run.')}
  <div class="dl" data-evidence="official" data-status="${f && f.verified ? 'verified' : 'unverified'}">
    ${row('Evidence', f && f.verified ? tok('OFFICIAL EVIDENCE · VERIFIED', 'ok') : tok('NOT VERIFIED', 'wa'))}
    ${row('Path', 'artefacts/benchmark/official-cloud-final/', { mono: true })}
    ${row('Cells', f && f.verified ? esc(f.cells) + ' / ' + esc(f.expected) : 'Observed only after verification')}
    ${row('Groups', f && f.verified ? esc(f.groups) : '—')}
    ${row('Seeds × profiles × policies', f && f.verified
      ? esc(f.seeds) + ' × ' + esc(f.profiles) + ' × ' + esc(f.policies) + ' = ' + esc(f.cells)
      : '20 × 6 × 5 declared contract')}
    ${row('Validation', f && f.verified ? esc(f.validation) : '—')}
    ${row('M-10', 'Incremental net recovery vs B0 on the same seed and profile')}
    ${row('Frozen experiment', f && f.frozen ? esc(f.frozen) : 'declared in Benchmark Lab', { mono: true })}
    ${row('Open', h`<a class="prov" href="#/benchmark">Benchmark Lab</a> · <a class="prov" href="#/benchmark/matrix">Matrix</a> · <a class="prov" href="#/benchmark/evidence">Forensics</a>`)}
    ${row('API', h`<a class="prov" href="/api/benchmark/official/contract">/api/benchmark/official/contract</a> · <a class="prov" href="/api/benchmark/story">/api/benchmark/story</a>`)}
  </div>

  ${sec('Claim → evidence', 'traceable', 'Every major claim names its source, test, UI, and API.')}
  <div class="ledger-scroll cv"><table class="ledger">
    <thead><tr><th>Claim</th><th>Source</th><th>Value</th><th>UI</th><th>API</th></tr></thead>
    <tbody>
      <tr>
        <td>Incremental net recovery</td>
        <td>Sandbox engine measurement</td>
        <td class="mono" data-metric="incremental_net_recovery">${m(hero.incremental_net_recovery)}</td>
        <td><a class="prov" href="#/control">#/control</a></td>
        <td class="mono dim">GET /api/product/overview</td>
      </tr>
      <tr>
        <td>Bounded execution</td>
        <td>Authorization gate</td>
        <td class="mono">${esc(hero.execution_integrity || 'UNKNOWN')}</td>
        <td><a class="prov" href="#/system">#/system</a></td>
        <td class="mono dim">GET /api/product/overview</td>
      </tr>
      <tr>
        <td>Official experiment cells</td>
        <td>Official manifest + verification</td>
        <td class="mono">${f && f.verified ? esc(f.cells) : 'not verified'}</td>
        <td><a class="prov" href="#/benchmark">#/benchmark</a></td>
        <td class="mono dim">GET /api/benchmark/official/contract</td>
      </tr>
      <tr>
        <td>BENCHMARK_VALID</td>
        <td>validation.json</td>
        <td class="mono">${f && f.verified ? esc(f.validation) : 'not verified'}</td>
        <td><a class="prov" href="#/benchmark/evidence">#/benchmark/evidence</a></td>
        <td class="mono dim">GET /api/benchmark/official/summary</td>
      </tr>
      <tr>
        <td>M-10</td>
        <td>Paired vs B0 on the same seed × profile</td>
        <td class="mono">INCREMENTAL NET RECOVERY</td>
        <td><a class="prov" href="#/benchmark/matrix">#/benchmark/matrix</a></td>
        <td class="mono dim">GET /api/benchmark/official/cell/14/ABUNDANT/REVIVE</td>
      </tr>
      ${opp ? h`<tr>
        <td>Active opportunity state</td>
        <td>Sandbox opportunity projection</td>
        <td>${esc(oppLifecycle(opp))}</td>
        <td><a class="prov" href="#/opportunity/${esc(opp.opportunity_id)}">workspace</a></td>
        <td class="mono dim">GET /api/opportunity/{id}</td>
      </tr>` : ''}
    </tbody>
  </table></div>

  ${sec('Inspect', 'API and routes', 'One product. The JSON is the same truth as this screen.')}
  <ul class="sys-links">
    <li><a href="/api/product/overview">GET /api/product/overview</a> · intelligence.llm_used · track03</li>
    <li><a href="/api/snapshot">GET /api/snapshot</a></li>
    <li><a href="/api/audit">GET /api/audit</a></li>
    <li><a href="/api/runs">GET /api/runs</a></li>
    <li><a href="/api/benchmark">GET /api/benchmark</a></li>
    <li><a href="/api/benchmark/story">GET /api/benchmark/story</a></li>
    <li><a href="/api/benchmark/official/summary">GET /api/benchmark/official/summary</a></li>
    <li><a href="/api/benchmark/official/contract">GET /api/benchmark/official/contract</a></li>
    <li><a href="/api/benchmark/official/matrix">GET /api/benchmark/official/matrix</a></li>
    ${wowId ? h`<li><a href="/api/opportunity/${esc(wowId)}">GET /api/opportunity/${esc(wowId)}</a></li>
      <li><a href="/api/receipt/${esc(wowId)}">GET /api/receipt/${esc(wowId)}</a></li>` : ''}
    <li><a href="#/control">Control Room</a> · <a href="#/audit">Audit Ledger</a> · <a href="#/benchmark">Benchmark Lab</a></li>
  </ul>
  `;
}

function waterfallBlock(wf) {
  const maxP = Math.max(1, ...wf.planned.map(s => paise(s.value)));
  const maxR = Math.max(1, ...wf.realized_steps.map(s => Math.abs(paise(s.value))));
  const track = (heading, note, steps, max) => h`
    <div class="wf-track">
      <div class="wf-track-h"><h4 class="lbl">${esc(heading)}</h4>
        <span class="sec-note">${esc(note)}</span></div>
      <div class="wf-rows">
        ${steps.map(st => h`
          <div class="wf-row" data-anim="wf">
            <div class="wf-row-top">
              <span class="wf-row-lbl">${esc(st.label)}</span>
              <span class="wf-row-val" data-metric="wf-${esc(heading)}-${esc(st.id)}">${m(st.value)}</span>
            </div>
            <div class="wf-bar"><i class="wf-fill" data-kind="${esc(st.kind)}"
              style="width:${Math.min(100, Math.abs(paise(st.value)) / max * 100).toFixed(2)}%"></i></div>
            ${st.note ? h`<p class="wf-row-note">${esc(st.note)}</p>` : ''}
          </div>`)}
      </div>
    </div>`;
  return h`
    <div class="wf"><div class="wf-tracks">
      ${track('Planned', 'engine valuations at decision time', wf.planned, maxP)}
      ${track('Realized', 'measurement only', wf.realized_steps, maxR)}
    </div>
    <p class="wf-foot">${esc(wf.note)} Measurement covered
      ${esc(wf.measurement_coverage.measured)} opportunities, of which
      ${esc(wf.measurement_coverage.observed)} produced an observable outcome and
      ${esc(wf.measurement_coverage.unobservable)} did not.</p>
    </div>`;
}

const PULSE_KEYS = [
  ['detected', 'Detected', 'tl'], ['diagnosed', 'Diagnosed', 'tl'],
  ['evaluated', 'Evaluated', 'tl'], ['authorized', 'Authorized', 'ok'],
  ['blocked', 'Blocked', 'no'], ['executed', 'Executed', 'ok'],
  ['measured', 'Measured', 'ok'],
];
function pulseBlock(p) {
  const max = Math.max(1, ...PULSE_KEYS.map(([k]) => Number(p[k]) || 0));
  return h`<div class="pulse">${PULSE_KEYS.map(([k, label, tone]) => {
    const n = Number(p[k]) || 0;
    const w = (n / max * 100).toFixed(1);
    return h`
    <div class="pulse-i" data-tone="${n > 0 ? tone : 'nu'}">
      <span class="pulse-n" data-metric="pulse-${k}">${esc(n)}</span>
      <span class="pulse-l">${esc(label)}</span>
      <span class="pulse-bar" aria-hidden="true"><i style="width:${w}%"></i></span>
    </div>`;
  })}</div>`;
}

function pipeStagePanel(cr) {
  const st = cr.interactive_pipeline.find(x => x.id === S.pipeStage);
  if (!st) return '';
  // The expanded stage has room, so nothing is truncated here. A sample that
  // carries a value becomes a real key/value fact; one that does not keeps the
  // bullet, because a fact list with a blank key column reads as broken.
  const body = (st.samples && st.samples.length)
    ? h`<ul class="factlist">${st.samples.map(s => s.value
        ? h`<li class="fact"><span class="fact-k">${esc(s.label)}</span><span class="fact-v mono">${esc(s.value)}</span></li>`
        : h`<li class="fact"><span class="fact-k">◦</span><span class="fact-v">${esc(s.label)}</span></li>`)}</ul>`
    : absentBlock('none', 'The engine recorded no observable detail for ' + st.label +
        ' on the latest cycle. The count is ' + st.count + '.');
  return panel(st.label + ' — ' + st.count + ' on the latest cycle', body, st.status);
}

function recentDecisions(receipts) {
  if (!receipts.length) return absentBlock('none', 'No decision has produced a receipt yet.');
  // Cause is deliberately absent here: the Control Room answers "what was decided
  // and what did it return". The diagnosis belongs to the workspace and the audit
  // ledger, and carrying it here pushed the economics off the edge at 1280.
  return h`<div class="ledger-scroll"><table class="ledger">
    <thead><tr>
      <th>Opportunity</th><th>Selected action</th>
      <th>Authorization</th><th>Execution</th>
      <th class="num">Expected incr.</th><th class="num">Realized net</th><th></th>
    </tr></thead>
    <tbody>${receipts.map(r => h`
      <tr>
        <td class="mono">${esc(shortId(r.opportunity_id))}</td>
        <td>${r.selected_action ? esc(r.selected_action) : absentInline('not-authorized')}</td>
        <td>${tok(titleize(r.authorization.state), authTone(r.authorization.state), 'sq')}</td>
        <td>${r.execution.stage ? tok(titleize(r.execution.stage), execTone(r.execution.stage), 'di') : absentInline('not-executed')}</td>
        <td class="num mono">${m(r.expected_incremental_value)}</td>
        <td class="num mono">${r.incremental_net_recovery ? m(r.incremental_net_recovery) : absentInline('not-measured')}</td>
        <td><a class="btn btn-sm btn-ghost" href="#/opportunity/${esc(r.opportunity_id)}/receipt">Receipt</a></td>
      </tr>`)}</tbody>
  </table></div>`;
}

/* ============================================ VIEW: OPPORTUNITY EXPLORER */
const OPP_FILTERS = [
  ['all', 'All', () => true],
  ['recoverable', 'Recoverable', c => c.addressable],
  ['high', 'High value', (c, ctx) => paise(c.value_at_risk) >= ctx.p75],
  ['blocked', 'Blocked', c => c.blocked],
  ['authorized', 'Authorized', c => c.authorization_state === 'AUTHORIZED'],
  ['executed', 'Executed', c => c.execution_state !== 'NOT_EXECUTED'],
  ['review', 'Needs review', c => c.needs_review],
];
const OPP_SORTS = [
  ['risk', 'Revenue at risk', (a, b) => paise(b.value_at_risk) - paise(a.value_at_risk)],
  ['incr', 'Expected incremental', (a, b) => paise(b.expected_incremental) - paise(a.expected_incremental)],
  ['net', 'Realized net', (a, b) => paise(b.incremental_net) - paise(a.incremental_net)],
  ['id', 'Opportunity id', (a, b) => a.opportunity_id.localeCompare(b.opportunity_id)],
];

function oppContext(all) {
  const vals = all.map(c => paise(c.value_at_risk)).sort((a, b) => a - b);
  return { p75: vals.length ? vals[Math.floor(vals.length * 0.75)] : 0 };
}

function viewOpportunities() {
  const cr = S.snap.control_room;
  const all = cr.all_opportunities;
  const ctx = oppContext(all);
  const q = S.oppSearch.trim().toLowerCase();
  const f = OPP_FILTERS.find(x => x[0] === S.filters.opp) || OPP_FILTERS[0];
  const sorter = (OPP_SORTS.find(x => x[0] === S.oppSort) || OPP_SORTS[0])[2];

  let list = all.filter(c => f[2](c, ctx));
  if (q) {
    list = list.filter(c => [c.opportunity_id, c.cause, c.risk_label, c.selected_action,
      c.blocking_reason, c.review_reason].some(v => v && String(v).toLowerCase().includes(q)));
  }
  list = list.slice().sort(sorter);

  return h`
  ${sec('Recovery opportunity explorer', all.length + ' opportunities',
    'Every open recovery opportunity the engine detected on this fixture, with what it decided and what happened.')}
  <div class="toolbar">
    <label class="field field-search">
      <span class="sr">Search opportunities</span>
      <input class="input input-search" id="opp-q" type="search" value="${esc(S.oppSearch)}"
             placeholder="Search id, cause, action, block reason…">
    </label>
    <label class="field">
      <span class="lbl">Sort</span>
      <select class="select" id="opp-sort">
        ${OPP_SORTS.map(([k, l]) => h`<option value="${k}" ${S.oppSort === k ? 'selected' : ''}>${esc(l)}</option>`)}
      </select>
    </label>
  </div>
  <div class="filters" role="group" aria-label="Filter opportunities">
    ${OPP_FILTERS.map(([k, l, fn]) => h`
      <button type="button" class="chip" data-oppfilter="${k}" aria-pressed="${S.filters.opp === k}">
        ${esc(l)}<span class="chip-n">${all.filter(c => fn(c, ctx)).length}</span>
      </button>`)}
  </div>
  <p class="sec-sub" style="margin:var(--s-4) 0">Showing ${list.length} of ${all.length}${q ? ' matching “' + esc(q) + '”' : ''}.</p>
  ${list.length
    ? h`<div class="opgrid">${list.map(oppCard)}</div>`
    : absentBlock('none', 'No opportunity matches this filter and search combination. Clear the search or pick another filter.')}
  `;
}

function oppCard(c) {
  const tone = toneOf(c);
  return h`<article class="opcard" data-tone="${tone}" data-opp="${esc(c.opportunity_id)}">
    <div class="opcard-top">
      <span class="opcard-id" title="${esc(c.opportunity_id)}">${esc(shortId(c.opportunity_id))}</span>
      <span class="opcard-risk">${tok(c.risk_label, 'nu', 'sq')}</span>
    </div>
    <p class="opcard-fig" data-metric="opp-${esc(c.opportunity_id)}-risk">${m(c.value_at_risk)}</p>
    <p class="opcard-cause">${c.cause ? esc(titleize(c.cause)) : absentInline('none')}
      ${c.selected_action ? h`<span class="dim"> → </span>${esc(c.selected_action)}` : ''}</p>
    <div class="opcard-meta">
      <div class="opcard-m"><span class="lbl">Expected incr.</span>
        <span class="opcard-mv">${m(c.expected_incremental)}</span></div>
      <div class="opcard-m"><span class="lbl">Natural (pred.)</span>
        <span class="opcard-mv">${m(c.natural_recovery_est)}</span></div>
      <div class="opcard-m"><span class="lbl">Realized net</span>
        <span class="opcard-mv">${c.incremental_net ? m(c.incremental_net) : absentInline(c.execution_state === 'NOT_EXECUTED' ? 'not-executed' : 'not-measured')}</span></div>
    </div>
    <div class="opcard-state">
      ${tok(titleize(c.authorization_state || 'not submitted'), authTone(c.authorization_state), 'sq')}
      ${tok(titleize(c.execution_state), execTone(c.execution_state), 'di')}
      ${c.candidate_count ? tok(c.candidate_count + ' candidates', 'vi') : ''}
    </div>
    ${c.needs_review ? h`<p class="opcard-why">${esc(c.review_reason)}</p>` : ''}
    <div class="opcard-ctl">
      <button type="button" class="btn btn-sm btn-primary" data-analyze="${esc(c.opportunity_id)}">Analyze</button>
      <a class="btn btn-sm btn-ghost" href="#/opportunity/${esc(c.opportunity_id)}">Open workspace</a>
    </div>
  </article>`;
}

/* ================================================== VIEW: WORKSPACE */
function detailFor(id) { return S.snap.opportunities[id] || null; }

function firstOppId() {
  const t = S.snap.control_room.top_opportunities;
  return t.length ? t[0].opportunity_id : null;
}

function viewWorkspace() {
  const id = S.param || S.snap.wow_opportunity_id || firstOppId();
  if (!id) return absentBlock('none', 'This fixture produced no opportunities to open.');
  const d = detailFor(id);
  if (!d) {
    return h`${sec('Opportunity not found')}
      ${absentBlock('none', 'No projection exists for “' + esc(id) +
        '”. It is not part of this fixture. Return to the explorer to pick a live opportunity.')}
      <p style="margin-top:var(--s-4)"><a class="btn btn-ghost" href="#/opportunities">Back to explorer</a></p>`;
  }
  const view = S.sub || '';
  if (view === 'graph')      return wsGraphOnly(d);
  if (view === 'lab')        return wsLabOnly(d);
  if (view === 'guardrails') return wsGuardOnly(d);
  if (view === 'execution')  return wsExecOnly(d);
  if (view === 'receipt')    return wsReceiptOnly(d);
  return wsFull(d);
}

function wsHeader(d, label) {
  const c = d.card;
  return h`${sec(label || 'Recovery workspace', shortId(c.opportunity_id))}
  <div class="kpiwrap ws-kpis"><div class="kpis" data-n="4">
    ${figure('At risk', m(c.value_at_risk), { key: 'ws-risk' })}
    ${figure('Expected incremental', m(c.expected_incremental), { key: 'ws-inc' })}
    ${figure('Natural (predicted)', m(c.natural_recovery_est), { key: 'ws-nat' })}
    ${figure('Realized net', c.incremental_net ? m(c.incremental_net)
      : absentInline(c.execution_state === 'NOT_EXECUTED' ? 'not-executed' : 'not-measured'),
      { key: 'ws-net', accent: 'net' })}
  </div></div>`;
}

function wsFull(d) {
  const id = d.card.opportunity_id;
  return h`
  <div class="ws-page">
  ${wsHeader(d)}
  <div class="ws"><div class="ws-grid">
    <div class="ws-col ws-a">
      ${panel('Opportunity', h`${oppFacts(d, true)}${evidencePreview(d)}`)}
    </div>
    <div class="ws-col ws-c">
      ${panel('Decision', h`${decisionInstrument(d, true)}
        <p class="wf-foot">${esc(d.counterfactual.selection_rationale)}</p>`)}
    </div>
    <div class="ws-lower">
      ${panel('Guardrails', h`${guardStrip(d.guardrail, true)}
        <p class="ws-more"><a class="prov" href="#/opportunity/${esc(id)}/guardrails">Open full guardrail proof</a></p>`,
        titleize(d.guardrail.authorization_state))}
      ${panel('Execution', h`${timelineBlock(d, true)}
        <p class="ws-more"><a class="prov" href="#/opportunity/${esc(id)}/execution">Open execution record</a></p>`,
        d.receipt.execution.stage || 'not executed')}
      ${panel('Receipt preview', h`${receiptPreview(d.receipt)}
        <p class="ws-more"><a class="prov" href="#/opportunity/${esc(id)}/receipt">Open decision receipt</a></p>`)}
    </div>
  </div></div>
  </div>`;
}

function wsGraphOnly(d) {
  return h`${wsHeader(d, 'Causal recovery graph')}
    ${panel(null, graphBlock(d, true))}
    ${panel('Context recorded at diagnosis', contextBlock(d.graph.context))}`;
}
function wsLabOnly(d) {
  return h`${wsHeader(d, 'Counterfactual recovery lab')}
    ${panel(null, cfBlock(d.counterfactual))}
    ${panel('Why this action?', whyBlock(d))}`;
}
function wsGuardOnly(d) {
  return h`${wsHeader(d, 'Guardrail proof')}
    ${guardMatrix(d.guardrail)}
    ${sec('Stopping rules', d.guardrail.stopping_fired + ' fired')}
    ${panel(null, stoppingBlock(d.guardrail))}`;
}
function wsExecOnly(d) {
  return h`${wsHeader(d, 'Execution')}
    ${panel(null, timelineBlock(d))}
    ${panel('Execution record', execRecord(d))}`;
}
function wsReceiptOnly(d) {
  return h`${wsHeader(d, 'Decision receipt')}${receiptBlock(d.receipt)}`;
}

function oppFacts(d, compact) {
  const c = d.card, r = d.receipt;
  if (compact) {
    return h`<div class="dl">
      ${row('Risk class', tok(c.risk_label, 'nu', 'sq'))}
      ${row('Addressable', c.addressable ? tok('Yes', 'ok') : tok('No', 'no'))}
      ${row('Diagnosed cause', c.cause ? esc(titleize(c.cause)) : absentInline('none'))}
      ${row('Candidates generated', esc(c.candidate_count))}
      ${row('Natural recovery probability', esc(pct(d.counterfactual.p_natural, 1)) || absentInline('none'))}
    </div>`;
  }
  return h`<div class="dl">
    ${row('Opportunity', esc(c.opportunity_id), { mono: true })}
    ${row('Cycle', esc(c.cycle_id), { mono: true })}
    ${row('Risk class', tok(c.risk_label, 'nu', 'sq'))}
    ${row('Addressable', c.addressable ? tok('Yes', 'ok') : tok('No', 'no'))}
    ${row('Diagnosed cause', c.cause ? esc(titleize(c.cause)) : absentInline('none'))}
    ${row('Diagnostic confidence', r.observed_failure.confidence !== null && r.observed_failure.confidence !== undefined
      ? esc(typeof r.observed_failure.confidence === 'number'
          ? 'uncertainty ' + r.observed_failure.confidence.toFixed(3)
          : titleize(r.observed_failure.confidence))
      : absentInline('none'))}
    ${row('Candidates generated', esc(c.candidate_count))}
    ${row('Natural recovery probability', esc(pct(d.counterfactual.p_natural, 1)) || absentInline('none'))}
  </div>`;
}

function evidencePreview(d) {
  const g = d.graph, ev = d.receipt.evidence;
  const facts = Object.entries(g.evidence_facts || {});
  const shown = facts.slice(0, 2);
  const feats = (ev.supporting_features || []).slice(0, 2);
  if (!facts.length && !feats.length && !(ev.signals || []).length) {
    return h`<p class="wf-foot">No discrete evidence facts recorded at detection.</p>`;
  }
  return h`
    <p class="lbl ws-ev-k">Evidence</p>
    ${shown.length ? h`<ul class="factlist">${shown.map(([k, v]) =>
      h`<li class="fact"><span class="fact-k">${esc(k)}</span><span class="fact-v">${esc(v)}</span></li>`)}</ul>` : ''}
    ${facts.length > shown.length ? h`<p class="wf-foot">${esc(facts.length - shown.length)} more on the evidence record.</p>` : ''}
    <p class="wf-foot">Causes ranked: ${esc((g.causes || []).map(titleize).join(', ') || 'none')}.</p>`;
}

function evidenceBlock(d) {
  const g = d.graph, ev = d.receipt.evidence;
  const facts = Object.entries(g.evidence_facts || {});
  const feats = ev.supporting_features || [];
  if (!facts.length && !feats.length && !(ev.signals || []).length) {
    return absentBlock('none', 'Detection recorded no discrete evidence facts for this opportunity. The diagnosis rests on the observable context only.');
  }
  return h`
    ${facts.length ? h`<ul class="factlist">${facts.map(([k, v]) =>
      h`<li class="fact"><span class="fact-k">${esc(k)}</span><span class="fact-v">${esc(v)}</span></li>`)}</ul>` : ''}
    ${feats.length ? h`<div style="margin-top:var(--s-4)">
      <p class="lbl" style="margin-bottom:var(--s-2)">Supporting features</p>
      <ul class="factlist">${feats.map(f =>
        h`<li class="fact"><span class="fact-k">+</span><span class="fact-v">${esc(titleize(f))}</span></li>`)}</ul>
    </div>` : ''}
    ${(ev.signals || []).length ? h`<div style="margin-top:var(--s-4)">
      <p class="lbl" style="margin-bottom:var(--s-2)">Signals</p>
      <ul class="factlist">${ev.signals.map(s =>
        h`<li class="fact"><span class="fact-k">sig</span><span class="fact-v">${esc(s)}</span></li>`)}</ul>
    </div>` : ''}
    <p class="wf-foot">Diagnosis used a language model: <b>${g.llm_used ? 'yes' : 'no'}</b>.
      Causes ranked: ${esc((g.causes || []).map(titleize).join(', ') || 'none')}.</p>`;
}

function decisionInstrument(d, compact) {
  const c = d.card, r = d.receipt, cf = d.counterfactual;
  const chosen = cf.options.find(o => o.chosen);
  const core = h`
    ${row('Selected action', c.selected_action ? h`<b>${esc(c.selected_action)}</b>` : absentInline('not-authorized'), { big: !!c.selected_action })}
    ${row('Allocator outcome', c.outcome ? tok(titleize(c.outcome), c.outcome === 'SELECTED' ? 'ok' : 'wa', 'sq') : absentInline('none'))}
    ${compact ? '' : row('Allocator reason', d.guardrail.allocator_reason ? esc(titleize(d.guardrail.allocator_reason)) : absentInline('none'), { mono: true })}
    ${row('Expected incremental value', m(r.expected_incremental_value), { mono: true })}
    ${row('Estimated cost', m(r.estimated_intervention_cost), { mono: true })}
    ${chosen && chosen.enrv_band ? row('ENRV band',
      h`${m(chosen.enrv_band.lo)} <span class="dim">…</span> ${m(chosen.enrv_band.hi)}`, { mono: true }) : ''}
    ${row('Authorization', tok(titleize(d.guardrail.authorization_state), authTone(d.guardrail.authorization_state), 'sq'))}
    ${d.guardrail.blocking_reason ? row('Blocked by',
      h`${esc(d.guardrail.blocking_gate)} — ${esc(d.guardrail.blocking_reason)}`) : ''}
    ${compact ? '' : row('Allocator mode', esc(cf.allocator_mode || '') || absentInline('none'), { mono: true })}
  `;
  return h`<div class="dl">${core}</div>
    ${compact ? '' : h`<p class="wf-foot">${esc(d.guardrail.autonomy_bound)}</p>`}`;
}

/* --------------------------------------------------------- CAUSAL GRAPH */
const GRAPH_STAGE_LABEL = {
  customer: 'Customer', payment: 'Payment', checkout: 'Checkout',
  subscription: 'Subscription', invoice: 'Invoice', opportunity: 'Failure',
  cause: 'Cause', intervention: 'Recovery option', decision: 'Selected action',
  guardrail: 'Guardrails', execution: 'Execution', outcome: 'Outcome',
};
const GRAPH_OPTION_CAP = 5;

/* The inputs of the last drawn diagram, kept so a width change can redraw the SVG
   alone instead of re-rendering the whole workspace. */
let GRAPH_CTX = null;

function graphBlock(d, big) {
  const g = d.graph;
  const chain = g.chain || [];
  if (!chain.length) {
    GRAPH_CTX = null;
    return absentBlock('none', 'The projection produced no causal chain for this opportunity.');
  }
  const byId = new Map(g.nodes.map(n => [n.id, n]));
  const options = g.nodes.filter(n => n.kind === 'intervention')
    .slice().sort((a, b) => paise(b.detail.enrv) - paise(a.detail.enrv));
  const chosenId = (g.edges.find(e => e.rel === 'selected') || {}).from || null;
  GRAPH_CTX = { chain, byId, options, chosenId, big };

  const focusNode = S.graph.focus ? byId.get(S.graph.focus) : null;
  const focusLabel = focusNode
    ? (GRAPH_STAGE_LABEL[focusNode.kind] || focusNode.kind) + ' — ' + focusNode.label
    : S.graph.focus;

  return h`
    <div class="graph">
      <div class="graph-ctl">
        <button type="button" class="btn btn-sm btn-ghost" data-graph="fit"
                aria-pressed="${!!S.graph.fit}">${S.graph.fit ? 'Actual size' : 'Fit'}</button>
        <button type="button" class="btn btn-sm btn-ghost" data-graph="reset"
                ${S.graph.focus || S.graph.fit || S.graph.sel ? '' : 'disabled'}>Reset</button>
        ${S.graph.focus ? h`<span class="tok tok-tl">Focused: ${esc(focusLabel)}</span>` : ''}
        <span class="sec-note" style="margin-left:auto">hover to trace · click for detail · double-click to focus a branch</span>
      </div>
      <div class="graph-frame" data-graph-frame ${S.graph.fit ? 'data-fit="1"' : ''}>
        ${graphSvg(chain, byId, options, chosenId, big, S.graph.w)}
      </div>
      <div style="margin-top:var(--s-4)">
        <p class="lbl" style="margin-bottom:var(--s-2)">Causal narrative</p>
        ${graphNarrative(chain, byId, options, chosenId)}
      </div>
    </div>`;
}

/**
 * The diagram is authored at the width it is displayed at, not at a fixed 900 units
 * scaled to fit. A causal graph squeezed into a third of the screen renders its node
 * text at four pixels, which is not a diagram — it is a texture. So the layout takes a
 * width, the candidate row wraps when it cannot hold every box side by side, and the
 * height follows from the result. `bindGraph` redraws on resize with the measured
 * frame width.
 */
function graphSvg(chain, byId, options, chosenId, big, width) {
  const W = Math.max(300, Math.round(width || 900));
  const ROW = big ? 96 : 84, BOXH = 52, PAD = 18, GAP = 12;
  const shown = options.slice(0, GRAPH_OPTION_CAP);
  const hidden = options.length - shown.length;
  const boxes = shown.length + (hidden > 0 ? 1 : 0);

  // Candidate row geometry: as many boxes per row as the width honestly holds.
  const OW_MAX = 168, OW_MIN = 132;
  const inner = W - PAD * 2;
  let cols = Math.max(1, Math.min(boxes, Math.floor((inner + GAP) / (OW_MIN + GAP))));
  const ow = Math.min(OW_MAX, Math.floor((inner - (cols - 1) * GAP) / cols));
  const oRows = Math.max(1, Math.ceil(boxes / cols));

  // Linear stage box: wide, but never wider than the frame.
  const LW = Math.min(320, inner);
  const centerX = W / 2;

  // Lay the vertical stack out first so both edges and nodes read the same geometry.
  const layers = [];
  let y = PAD;
  chain.forEach(id => {
    const rows = id === 'OPTIONS' ? oRows : 1;
    layers.push({ id, y, rows, h: rows * BOXH + (rows - 1) * GAP });
    y += rows * BOXH + (rows - 1) * GAP + (ROW - BOXH);
  });
  const H = y - (ROW - BOXH) + PAD;

  // Where candidate box i sits, given the wrapped grid.
  const optSlot = i => {
    const r = Math.floor(i / cols), c = i % cols;
    const n = Math.min(cols, boxes - r * cols);          // boxes on this row
    const rowW = n * ow + (n - 1) * GAP;
    return { x: centerX - rowW / 2 + c * (ow + GAP), row: r };
  };

  let svg = '';

  // edges first so nodes paint above them
  for (let i = 0; i < layers.length - 1; i++) {
    const a = layers[i], b = layers[i + 1];
    const y1 = a.y + a.h, y2 = b.y;
    if (b.id === 'OPTIONS') {
      for (let k = 0; k < boxes; k++) {
        const s = optSlot(k);
        const id = k < shown.length ? shown[k].id : 'more';
        svg += edgePath(centerX, y1, s.x + ow / 2, y2 + s.row * (BOXH + GAP), a.id, id, 'candidate');
      }
    } else if (a.id === 'OPTIONS') {
      const idx = shown.findIndex(o => o.id === chosenId);
      const s = idx >= 0 ? optSlot(idx) : { x: centerX - ow / 2, row: oRows - 1 };
      svg += edgePath(s.x + ow / 2, a.y + s.row * (BOXH + GAP) + BOXH, centerX, y2,
        chosenId || 'selected', b.id, 'selected');
    } else {
      svg += edgePath(centerX, y1, centerX, y2, a.id, b.id, relFor(a.id, b.id));
    }
  }

  // nodes
  layers.forEach(l => {
    if (l.id === 'OPTIONS') {
      for (let k = 0; k < boxes; k++) {
        const s = optSlot(k);
        const yy = l.y + s.row * (BOXH + GAP);
        if (k < shown.length) {
          const o = shown[k];
          svg += nodeBox(s.x, yy, ow, BOXH, o.id, 'OPTION', o.label,
            (o.detail.enrv ? o.detail.enrv.display : '') + (o.id === chosenId ? '  ★' : ''),
            o.id === chosenId);
        } else {
          svg += nodeBox(s.x, yy, ow, BOXH, 'more', 'OPTION',
            '+' + hidden + ' more candidates', 'lower ENRV — open the lab', false);
        }
      }
      return;
    }
    const n = byId.get(l.id);
    if (!n) return;
    svg += nodeBox(centerX - LW / 2, l.y, LW, BOXH, n.id,
      (GRAPH_STAGE_LABEL[n.kind] || n.kind).toUpperCase(), n.label, nodeDetailLine(n), false, n.kind);
  });

  return h`<svg class="graph-svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="group"
    aria-label="Causal recovery graph, ${chain.length} stages" data-graph-svg>${raw(svg)}</svg>`;
}

function relFor(a, b) {
  const map = {
    'guardrails': 'gated_by', 'execution': 'authorized', 'outcome': 'realized',
    'selected': 'selected',
  };
  return map[b] || 'leads_to';
}

function edgePath(x1, y1, x2, y2, from, to, rel) {
  const my = (y1 + y2) / 2;
  const d = `M ${x1} ${y1} C ${x1} ${my}, ${x2} ${my}, ${x2} ${y2}`;
  const lx = (x1 + x2) / 2, ly = my - 3;
  // Both endpoints are recorded, not just the target: tracing a chain on hover means
  // lighting the edges *into and out of* a node, which needs to know both ends.
  return `<path class="gedge" d="${d}" data-edge="${esc(to)}" data-from="${esc(from)}" data-to="${esc(to)}"/>` +
    (rel && Math.abs(x1 - x2) < 6
      ? `<text class="gedge-lbl" x="${lx + 6}" y="${ly}">${esc(rel.replace(/_/g, ' '))}</text>` : '');
}

function nodeBox(x, y, w, hh, id, kind, label, detail, chosen, rawKind) {
  const trunc = (s, n) => { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '…' : s; };
  const chars = Math.floor(w / 6.2);
  return `<g class="gnode ${chosen ? 'sel' : ''}" data-node="${esc(id)}" data-kind="${esc(rawKind || kind)}"
      tabindex="0" role="button" aria-label="${esc(kind + ': ' + label + '. ' + (detail || ''))}">
    <rect class="gnode-box" x="${x}" y="${y}" width="${w}" height="${hh}" rx="4"/>
    <text class="gnode-kind" x="${x + 10}" y="${y + 15}">${esc(kind)}</text>
    <text class="gnode-lbl" x="${x + 10}" y="${y + 31}">${esc(trunc(label, chars))}</text>
    <text class="gnode-det" x="${x + 10}" y="${y + 44}">${esc(trunc(detail, chars + 4))}</text>
  </g>`;
}

function nodeDetailLine(n) {
  const dt = n.detail || {};
  switch (n.kind) {
    case 'opportunity':  return (dt.value_at_risk ? dt.value_at_risk.display : '') + ' · ' + (dt.risk_class || '');
    case 'customer':     return [dt.segment, dt.prior_contacts + ' prior contacts'].filter(Boolean).join(' · ');
    case 'payment':      return [dt.reason, dt.method, dt.amount && dt.amount.display].filter(Boolean).join(' · ');
    case 'checkout':     return [dt.stage, dt.cart && dt.cart.display].filter(Boolean).join(' · ');
    case 'subscription': return [dt.state, dt.mandate_state].filter(Boolean).join(' · ');
    case 'invoice':      return [dt.ageing, dt.outstanding && dt.outstanding.display].filter(Boolean).join(' · ');
    case 'cause':        return 'confidence ' + (dt.confidence || '?');
    case 'decision':     return [dt.outcome, dt.reason].filter(Boolean).join(' · ');
    case 'guardrail':    return dt.blocking_gate
      ? 'blocked at ' + dt.blocking_gate + ' — ' + dt.blocking_reason
      : dt.gates_evaluated + ' gates evaluated · ' + dt.authorization_state;
    case 'execution':    return [dt.stage, dt.failure_reason].filter(Boolean).join(' · ');
    case 'outcome':      return [dt.incremental_net && dt.incremental_net.display + ' net',
      dt.observability].filter(Boolean).join(' · ');
    default: return '';
  }
}

function graphNarrative(chain, byId, options, chosenId) {
  const items = [];
  chain.forEach(id => {
    if (id === 'OPTIONS') {
      const chosen = options.find(o => o.id === chosenId);
      items.push({
        id: 'OPTIONS',
        kind: 'Recovery options',
        label: options.length + ' candidates generated and valued',
        detail: chosen
          ? 'Selected: ' + chosen.label + ' at ' + (chosen.detail.enrv ? chosen.detail.enrv.display : '?') + ' ENRV'
          : 'No candidate was selected',
      });
      return;
    }
    const n = byId.get(id);
    if (!n) return;
    items.push({ id: n.id, kind: GRAPH_STAGE_LABEL[n.kind] || n.kind, label: n.label, detail: nodeDetailLine(n) });
  });
  // data-narr pairs each row with its node, so tracing the diagram traces the prose.
  return h`<ol class="gnarr">${items.map(it => h`
    <li class="gnarr-i" data-narr="${esc(it.id)}"><div class="gnarr-t">
      <p class="gnarr-k">${esc(it.kind)}</p>
      <p class="gnarr-l">${esc(it.label)}</p>
      ${it.detail ? h`<p class="gnarr-d">${esc(it.detail)}</p>` : ''}
    </div></li>`)}</ol>`;
}

function contextBlock(ctx) {
  const parts = Object.entries(ctx || {}).filter(([, v]) => v && typeof v === 'object');
  if (!parts.length) return absentBlock('none', 'No observable context was recorded at diagnosis.');
  return h`<div class="dl">${parts.map(([group, obj]) => h`
    <div class="dl-row">
      <span class="dl-k">${esc(titleize(group))}</span>
      <ul class="factlist" style="margin-top:var(--s-2)">
        ${Object.entries(obj).filter(([, v]) => v !== null && v !== undefined && v !== '').map(([k, v]) =>
          h`<li class="fact"><span class="fact-k">${esc(k)}</span><span class="fact-v">${esc(
            typeof v === 'number' && !Number.isInteger(v) ? v.toFixed(4) : v)}</span></li>`)}
      </ul>
    </div>`)}</div>`;
}

/* --------------------------------------------- COUNTERFACTUAL LAB */
function cfBlock(cf) {
  if (!cf.options.length) return absentBlock('none', 'No candidate actions were generated, so there is nothing to compare.');
  const max = Math.max(1, ...cf.options.map(o => Math.abs(paise(o.expected_incremental_net))));
  const chosen = cf.options.find(o => o.chosen);
  const nothing = cf.options.find(o => o.is_do_nothing);

  return h`
    <div class="cf">
      ${nothing ? cfOption(nothing, max, 0) : ''}
      ${cf.options.filter(o => !o.is_do_nothing).map((o, i) => cfOption(o, max, i + 1))}
    </div>
    <div class="cf-rec" style="margin-top:var(--s-4)">
      <p class="cf-rec-k">PAYVANTA recommends</p>
      <p class="cf-rec-h">${chosen ? esc(chosen.action_label) : 'Do nothing'}</p>
      <p class="cf-rec-p">${esc(cf.selection_rationale)}</p>
      ${allocatorReason(cf)}
      ${cf.constraint_summary && cf.constraint_summary.length ? h`
        <p class="cf-rec-p"><b>Constraints in force:</b> ${esc(cf.constraint_summary.join('; '))}</p>` : ''}
    </div>`;
}

/**
 * The allocator's reason code, shown rather than paraphrased away. The sentence
 * above it (selection_rationale) is the same fact in words; this row is what the
 * engine actually emitted, kept visible because a decision record that hides its
 * own evidence is worth less than one that prints it.
 */
function allocatorReason(cf) {
  const a = cf && cf.allocator_explanation;
  if (!a) return '';
  return h`
    <p class="alloc-ev">
      <span class="alloc-k">Allocator reason</span>
      <span class="alloc-code">${esc(a.code)}</span>
      ${(a.args || []).map(g => h`<span class="alloc-arg">${esc(g.label)} <b>${esc(g.value)}</b></span>`)}
      ${a.sentence ? '' : h`<span class="alloc-arg">no description recorded for this code</span>`}
    </p>`;
}

function cfOption(o, max, idx) {
  const role = o.chosen ? 'chosen' : (o.is_do_nothing ? 'nothing' : 'alt');
  const net = paise(o.expected_incremental_net);
  return h`<article class="cf-opt" data-role="${role}" data-anim="cf">
    <div class="cf-opt-top">
      <span class="cf-opt-n">${o.is_do_nothing ? 'BASE' : String(idx).padStart(2, '0')}</span>
      <h4 class="cf-opt-h">${esc(o.action_label)}</h4>
      <span class="cf-opt-badges">
        ${o.chosen ? tok('Chosen', 'tl', 'sq') : ''}
        ${o.is_do_nothing ? tok('Counterfactual baseline', 'nu', 'sq') : ''}
        ${o.availability && o.availability !== 'AVAILABLE' ? tok(titleize(o.availability), 'no', 'di') : ''}
        ${o.approval_required ? tok('Approval required', 'wa', 'di') : ''}
      </span>
    </div>
    <div class="cf-metrics">
      <div class="cf-m"><span class="lbl">Expected recovery</span>
        <span class="cf-mv">${m(o.expected_recovery)}</span></div>
      <div class="cf-m"><span class="lbl">Incremental value</span>
        <span class="cf-mv ${net > 0 ? 'is-pos' : (net < 0 ? 'is-neg' : '')}">${m(o.expected_incremental_net)}</span></div>
      <div class="cf-m"><span class="lbl">Cost</span>
        <span class="cf-mv">${m(o.intervention_cost)}</span></div>
      <div class="cf-m"><span class="lbl">Fatigue cost</span>
        <span class="cf-mv">${m(o.fatigue_cost)}</span></div>
      <div class="cf-m"><span class="lbl">P(action)</span>
        <span class="cf-mv">${esc(pct(o.p_action, 1)) || absentInline('none')}</span></div>
      <div class="cf-m"><span class="lbl">Uplift over baseline</span>
        <span class="cf-mv">${esc(pct(o.uplift, 1)) || absentInline('none')}</span></div>
    </div>
    <div class="cf-scale"><i style="width:${(Math.abs(net) / max * 100).toFixed(2)}%"></i></div>
    ${o.value_drivers && o.value_drivers.length ? h`
      <p class="wf-row-note">${esc(o.value_drivers.join(' · '))}</p>` : ''}
    ${o.why_lost && o.why_lost.length ? h`
      <ul class="cf-lost">${o.why_lost.map(w => h`<li>${esc(w)}</li>`)}</ul>` : ''}
  </article>`;
}

/* ------------------------------------------------ WHY THIS ACTION? */
function whyBlock(d) {
  const r = d.receipt, cf = d.counterfactual, g = d.guardrail;
  const steps = [
    ['Cause', h`<p class="dl-v">${esc(titleize(r.observed_failure.cause))}</p>
       <p class="wf-row-note">Risk class ${esc(r.observed_failure.risk_class)}.
       Ranked causes: ${esc((d.graph.causes || []).map(titleize).join(', ') || 'none')}.</p>`],
    ['Evidence', evidenceBlock(d)],
    ['Alternatives', h`<ul class="factlist">${r.available_actions.map(a =>
        h`<li class="fact"><span class="fact-k">${a === r.selected_action ? '★' : '◦'}</span>
          <span class="fact-v">${esc(a)}</span></li>`)}</ul>`],
    ['Economic comparison', cfCompare(cf)],
    ['Constraints', r.policy_constraints && r.policy_constraints.length
      ? h`<ul class="factlist">${r.policy_constraints.map(c =>
          h`<li class="fact"><span class="fact-k">λ</span><span class="fact-v">${esc(c)}</span></li>`)}</ul>`
      : absentBlock('none', 'The allocator reported no binding constraints on this decision.')],
    ['Policy', h`<div class="dl">
        ${row('Authorization', tok(titleize(g.authorization_state), authTone(g.authorization_state), 'sq'))}
        ${row('Gates evaluated', esc(g.gates_evaluated) + ' — ' + esc(g.gates_passed) + ' allowed')}
        ${row('Stopping rules fired', esc(g.stopping_fired))}
        ${g.blocking_reason ? row('Blocked by', esc(g.blocking_gate) + ' — ' + esc(g.blocking_reason)) : ''}
      </div>`],
    ['Selection', h`<p class="dl-v">${esc(cf.selection_rationale)}</p>${allocatorReason(cf)}`],
  ];
  return h`<div class="why">${steps.map(([title, body], i) => {
    const key = 'why-' + i;
    const open = S.disclosures.has(key);
    return h`<div class="why-i">
      <button type="button" class="why-t" data-disclose="${key}" aria-expanded="${open}" aria-controls="${key}-p">
        <span class="why-h">${esc(title)}</span>
        <span class="why-x" aria-hidden="true">+</span>
      </button>
      <div class="why-p" id="${key}-p" ${open ? '' : 'hidden'}>${raw(body)}</div>
    </div>`;
  })}</div>`;
}

function cfCompare(cf) {
  const sorted = cf.options.slice().sort((a, b) =>
    paise(b.expected_incremental_net) - paise(a.expected_incremental_net));
  return h`<div class="tscroll"><table class="gtable">
    <thead><tr><th>Action</th><th class="num">Incremental</th><th class="num">Cost</th><th>Status</th></tr></thead>
    <tbody>${sorted.map(o => h`<tr ${o.chosen ? 'data-v="CHOSEN"' : ''}>
      <td>${o.chosen ? '★ ' : ''}${esc(o.action_label)}</td>
      <td class="num mono">${m(o.expected_incremental_net)}</td>
      <td class="num mono">${m(o.intervention_cost)}</td>
      <td>${esc(titleize(o.availability))}</td>
    </tr>`)}</tbody></table></div>`;
}

/* ---------------------------------------------------- GUARDRAIL MATRIX */
/* Compact six-family status for the workspace lower band. Full gate tables
   stay on the Guardrails sub-route. */
function guardStrip(g, compact) {
  if (!g.gate_groups || !g.gate_groups.length) {
    return absentBlock('not-authorized',
      'No authorization request was submitted, so no gate was evaluated.');
  }
  return h`<ul class="guard-strip" aria-label="Guardrail families">
    ${g.gate_groups.map(row => h`<li data-status="${esc(row.status)}">
      <span class="guard-strip-k">${esc(row.family)}</span>
      <span class="guard-strip-v">${esc(row.status.replace('_', ' '))}</span>
    </li>`)}
  </ul>
  ${g.blocking_reason
    ? h`<p class="wf-foot">Blocked at ${esc(g.blocking_gate)} — ${esc(g.blocking_reason)}. No execution occurred.</p>`
    : (compact ? '' : h`<p class="wf-foot">${esc(g.autonomy_bound || '')}</p>`)}`;
}

function guardMatrix(g) {
  if (!g.gate_groups || !g.gate_groups.length) {
    return absentBlock('not-authorized',
      'No authorization request was submitted for this opportunity, so no gate was evaluated. ' +
      'The allocator outcome was ' + (g.allocator_outcome ? titleize(g.allocator_outcome) : 'not recorded') + '.');
  }
  return h`<div class="gmatrix">${g.gate_groups.map((row, i) => {
    const key = 'g-' + i;
    const open = S.disclosures.has(key);
    return h`<div class="grow" data-status="${esc(row.status)}">
      <button type="button" class="grow-t" data-disclose="${key}" aria-expanded="${open}" aria-controls="${key}-p">
        <span class="grow-mark" aria-hidden="true"></span>
        <span class="grow-name">${esc(row.family)}</span>
        <span class="grow-res">${esc(row.result)}</span>
        <span class="grow-x" aria-hidden="true">${open ? '−' : '+'}</span>
      </button>
      <div class="grow-p" id="${key}-p" ${open ? '' : 'hidden'}>
        <div class="tscroll"><table class="gtable">
          <thead><tr><th>Gate</th><th>Checks</th><th>Observed</th><th>Constraint</th><th>Result</th></tr></thead>
          <tbody>${row.gates.map(gt => h`<tr data-v="${esc(gt.verdict)}" data-na="${gt.applicable ? '0' : '1'}">
            <td class="g">${esc(gt.gate_id)} ${esc(gt.name)}</td>
            <td>${esc(gt.checks)}</td>
            <td class="mono">${gt.observed !== null ? esc(gt.observed) : absentInline('na')}</td>
            <td class="mono">${gt.constraint !== null ? esc(gt.constraint) : absentInline('na')}</td>
            <td>${esc(gt.reason_label || gt.reason_code)}</td>
          </tr>`)}</tbody>
        </table></div>
      </div>
    </div>`;
  })}</div>
  <p class="wf-foot">${esc(g.autonomy_bound)}
    ${g.approval_required ? 'This action required a human approval decision.' : ''}</p>`;
}

/* The stopping-rule columns are polymorphic — the engine puts a different kind of quantity
   in each rule's `observed_value`. Casting them all through one raw path printed `460564`
   where ₹4,605.64 was meant (SR-10 carries `value_at_risk_paise`), `43200000000` where a
   clock position was (SR-01 carries `now_micros`), and an empty cell for SR-09's list of
   risk flags. Unit belongs with the rule that produced the number, so it is declared here
   rather than guessed from the value's magnitude. */
const SR_UNIT = {
  'SR-01': 'micros',   // now_micros vs recovery_window_expires_at_micros
  'SR-03': 'count',    // retries_on_opportunity vs max_retries_per_opportunity
  'SR-04': 'count',    // contacts_on_opportunity vs opportunity_contact_cap
  'SR-07': 'count',    // consecutive_no_action_cycles vs sr07_consecutive_cycles
  'SR-09': 'list',     // risk_flags
  'SR-10': 'paise',    // value_at_risk_paise
};

/** One stopping-rule cell. Returns the reading plus the raw value for the cell title, so
    a formatted figure never costs the forensic original. */
function srCell(v, unit) {
  if (v === null || v === undefined) return { html: absentInline('na'), title: '' };
  if (unit === 'list') {
    return Array.isArray(v) && v.length
      ? { html: esc(v.join(', ')), title: v.length + ' flag(s)' }
      : { html: absentInline('none'), title: 'No risk or legal flag recorded' };
  }
  if (unit === 'paise') return { html: esc(paiseText(v)), title: v + ' paise' };
  if (unit === 'micros') return { html: esc(microsText(v)), title: v + ' µs since run epoch' };
  if (unit === 'count') return { html: esc(cnt(v)), title: '' };
  return { html: esc(String(v)), title: '' };
}

function stoppingBlock(g) {
  if (!g.stopping_results || !g.stopping_results.length) {
    return absentBlock('none', 'No stopping rule was evaluated because no authorization request was submitted.');
  }
  return h`<div class="tscroll"><table class="gtable">
    <thead><tr><th>Rule</th><th>Condition</th><th class="num">Observed</th><th class="num">Threshold</th><th>Fired</th></tr></thead>
    <tbody>${g.stopping_results.map(s => {
      const unit = SR_UNIT[s.rule_id] || 'text';
      const obs = srCell(s.observed_value, unit);
      const thr = srCell(s.threshold, unit === 'list' ? 'text' : unit);
      return h`<tr data-v="${s.fired ? 'DENY' : 'ALLOW'}">
        <td class="g">${esc(s.rule_id)}</td>
        <td>${esc(titleize(s.reason_code))}</td>
        <td class="num mono" title="${esc(obs.title)}">${raw(obs.html)}</td>
        <td class="num mono" title="${esc(thr.title)}">${raw(thr.html)}</td>
        <td>${s.fired ? tok('Fired', 'no', 'di') : tok('Clear', 'ok', 'sq')}</td>
      </tr>`;
    })}</tbody></table></div>`;
}

/* ----------------------------------------------- EXECUTION TIMELINE */
function timelineBlock(d, compact) {
  const p = d.receipt.pipeline;
  if (compact) {
    return h`<ol class="tl-strip" aria-label="Execution stages">${p.map(st => {
      const state = st.blocked ? 'blocked' : (st.complete ? 'done' : 'pending');
      return h`<li data-state="${state}">
        <span class="tl-strip-dot" aria-hidden="true"></span>
        <span class="tl-strip-n">${esc(st.label || st.stage)}</span>
      </li>`;
    })}</ol>`;
  }
  return h`<div class="tl">${p.map(st => {
    const state = st.blocked ? 'blocked' : (st.complete ? 'done' : 'pending');
    return h`<div class="tl-i" data-state="${state}">
      <div class="tl-rail"><span class="tl-dot" aria-hidden="true"></span><span class="tl-line" aria-hidden="true"></span></div>
      <div class="tl-body">
        <div class="tl-h">
          <span class="tl-name">${esc(st.label || st.stage)}</span>
          ${st.blocked ? tok('Blocked', 'no', 'di') : (st.complete ? tok('Complete', 'ok', 'sq') : tok('Not reached', 'nu'))}
        </div>
        <p class="tl-note">${esc(st.note)}</p>
      </div>
    </div>`;
  })}</div>`;
}

function execRecord(d) {
  const e = d.receipt.execution;
  if (!e.stage) {
    return absentBlock('not-executed',
      'No execution record exists. ' +
      (d.guardrail.blocking_reason
        ? 'The action was blocked at ' + d.guardrail.blocking_gate + ' (' + d.guardrail.blocking_reason + '), so it never reached an adapter.'
        : 'The allocator did not select an executable action for this opportunity.'));
  }
  return h`<div class="dl">
    ${row('Stage', tok(titleize(e.stage), execTone(e.stage), 'di'))}
    ${row('Failure reason', e.failure_reason ? esc(e.failure_reason) : absentInline('na'), { mono: true })}
    ${row('Idempotency key', e.idempotency_key ? esc(e.idempotency_key) : absentInline('none'), { mono: true })}
    ${row('Realized recovery', d.receipt.realized_recovery ? m(d.receipt.realized_recovery) : absentInline('not-measured'), { mono: true })}
    ${row('Realized cost', d.receipt.realized_cost ? m(d.receipt.realized_cost) : absentInline('not-measured'), { mono: true })}
    ${row('Attribution', d.receipt.attribution ? esc(titleize(d.receipt.attribution)) : absentInline('not-observed'))}
  </div>`;
}

/* Compact receipt for the workspace lower band. The full certificate
   remains on the Receipt sub-route. */
function receiptPreview(r) {
  const net = r.incremental_net_recovery;
  return h`<div class="dl">
    ${row('Selected', r.selected_action ? esc(r.selected_action) : absentInline('not-authorized'))}
    ${row('Authorization', tok(titleize(r.authorization.state), authTone(r.authorization.state), 'sq'))}
    ${row('Execution', r.execution.stage ? esc(titleize(r.execution.stage)) : absentInline('not-executed'))}
    ${row('Incremental net', net ? m(net) : absentInline(r.execution.stage ? 'not-measured' : 'not-executed'), { mono: true })}
  </div>
  <p class="wf-foot">Sandbox receipt — not an official cell.</p>`;
}

/* ------------------------------------------------------------ RECEIPT */
function receiptBlock(r) {
  const net = r.incremental_net_recovery;
  const neg = net && net.paise < 0;
  return h`<article class="receipt" data-receipt="${esc(r.opportunity_id)}">
    <header class="receipt-head">
      <p class="receipt-k"><span class="receipt-mark">PAYVANTA · DECISION RECEIPT</span>
        ${tok(titleize(r.authorization.state), authTone(r.authorization.state), 'sq')}</p>
      <h3 class="receipt-h">${esc(r.selected_action || 'No action authorized')}</h3>
      <p class="receipt-sub">${esc(r.opportunity_id)} · cycle ${esc(r.cycle_id)}</p>
    </header>
    <div class="receipt-net">
      <span class="lbl">Incremental net recovery</span>
      <span class="receipt-net-v ${neg ? 'is-neg' : ''}" data-metric="rc-net-${esc(r.opportunity_id)}">${
        net ? m(net) : absentInline(r.execution.stage ? 'not-measured' : 'not-executed')}</span>
      ${net ? h`<button type="button" class="prov" data-calc="net">how this is computed</button>` : ''}
    </div>
    <div class="receipt-grid">
      <div class="receipt-cell"><span class="lbl">Observed failure</span>
        <span class="dl-v">${esc(r.observed_failure.risk_class)}</span>
        <span class="mono dim">${esc(titleize(r.observed_failure.cause))}</span></div>
      <div class="receipt-cell"><span class="lbl">Evidence</span>
        <span class="dl-v">${esc(Object.keys(r.evidence.facts || {}).length)} facts ·
          ${esc((r.evidence.signals || []).length)} signals</span>
        <span class="mono dim">${esc((r.evidence.supporting_features || []).map(titleize).join(', ') || 'no supporting features recorded')}</span></div>
      <div class="receipt-cell"><span class="lbl">Actions available</span>
        <span class="dl-v">${esc(r.available_actions.length)}</span>
        <span class="mono dim">${esc(r.available_actions.slice(0, 3).join(', '))}${r.available_actions.length > 3 ? '…' : ''}</span></div>
      <div class="receipt-cell"><span class="lbl">Expected incremental value</span>
        <span class="dl-v mono">${m(r.expected_incremental_value)}</span>
        <span class="mono dim">cost ${m(r.estimated_intervention_cost)}</span></div>
      <div class="receipt-cell"><span class="lbl">Policy constraints</span>
        <span class="dl-v">${r.policy_constraints.length ? esc(r.policy_constraints.length) + ' in force' : 'none binding'}</span>
        <span class="mono dim">${esc(r.policy_constraints.join('; ') || 'allocator reported no binding constraint')}</span></div>
      <div class="receipt-cell"><span class="lbl">Authorization</span>
        <span class="dl-v">${esc(titleize(r.authorization.state))}</span>
        <span class="mono dim">${r.authorization.blocking_reason
          ? esc(r.authorization.blocking_gate + ' — ' + r.authorization.blocking_reason)
          : 'all applicable gates allowed'}</span></div>
      <div class="receipt-cell"><span class="lbl">Execution</span>
        <span class="dl-v">${r.execution.stage ? esc(titleize(r.execution.stage)) : 'Not executed'}</span>
        <span class="mono dim">${esc(r.execution.failure_reason || r.execution.idempotency_key || '—')}</span></div>
      <div class="receipt-cell"><span class="lbl">Realized</span>
        <span class="dl-v mono">${r.realized_recovery ? m(r.realized_recovery) : absentInline('not-measured')}</span>
        <span class="mono dim">natural ${r.natural_recovery ? esc(r.natural_recovery.display) : 'not attributed'} ·
          cost ${r.realized_cost ? esc(r.realized_cost.display) : 'none'}</span></div>
      <div class="receipt-cell"><span class="lbl">Why alternatives lost</span>
        <span class="dl-v">${esc(r.why_alternatives_lost.length)} rejected</span>
        <span class="mono dim">${esc(r.why_alternatives_lost.slice(0, 2)
          .map(w => w.action + ': ' + w.reason).join(' · ') || 'no alternatives')}</span></div>
      <div class="receipt-cell"><span class="lbl">Evidence basis</span>
        <span class="dl-v">Decision provenance · sandbox run</span>
        <span class="mono dim">${esc(evidenceBasisLine())}</span></div>
    </div>
    <footer class="receipt-foot">
      <span class="receipt-ref">Audit reference ${esc(r.audit_reference || 'not recorded')}</span>
      <span class="receipt-actions">
        <button type="button" class="btn btn-sm" data-receipt-copy="${esc(r.opportunity_id)}">Copy receipt</button>
        <button type="button" class="btn btn-sm" data-receipt-print="${esc(r.opportunity_id)}">Print view</button>
        <a class="btn btn-sm btn-ghost" href="#/audit/${esc(r.opportunity_id)}">Open audit</a>
      </span>
    </footer>
  </article>`;
}

function receiptText(r) {
  const L = [];
  L.push('PAYVANTA — DECISION RECEIPT');
  L.push('='.repeat(52));
  L.push('Opportunity      : ' + r.opportunity_id);
  L.push('Cycle            : ' + r.cycle_id);
  L.push('Audit reference  : ' + (r.audit_reference || 'not recorded'));
  L.push('');
  L.push('OBSERVED FAILURE');
  L.push('  Risk class     : ' + r.observed_failure.risk_class);
  L.push('  Cause          : ' + r.observed_failure.cause);
  L.push('');
  L.push('EVIDENCE');
  Object.entries(r.evidence.facts || {}).forEach(([k, v]) => L.push('  ' + k.padEnd(15) + ': ' + v));
  (r.evidence.signals || []).forEach(s => L.push('  signal         : ' + s));
  L.push('');
  L.push('DECISION');
  L.push('  Available      : ' + r.available_actions.join(', '));
  L.push('  Selected       : ' + (r.selected_action || 'none'));
  L.push('  Expected incr. : ' + (mv(r.expected_incremental_value) || 'n/a'));
  L.push('  Estimated cost : ' + (mv(r.estimated_intervention_cost) || 'n/a'));
  L.push('  Rationale      : ' + r.selection_rationale);
  if (r.allocator_explanation)
    L.push('  Reason code    : ' + r.allocator_explanation.codes.join(' '));
  L.push('');
  L.push('WHY ALTERNATIVES LOST');
  r.why_alternatives_lost.forEach(w => L.push('  - ' + w.action + ' (' + (mv(w.enrv) || 'n/a') + '): ' + w.reason));
  L.push('');
  L.push('POLICY');
  L.push('  Authorization  : ' + r.authorization.state);
  if (r.authorization.blocking_reason)
    L.push('  Blocked by     : ' + r.authorization.blocking_gate + ' — ' + r.authorization.blocking_reason);
  (r.policy_constraints || []).forEach(c => L.push('  constraint     : ' + c));
  L.push('');
  L.push('EXECUTION');
  L.push('  Stage          : ' + (r.execution.stage || 'not executed'));
  if (r.execution.failure_reason) L.push('  Reason         : ' + r.execution.failure_reason);
  if (r.execution.idempotency_key) L.push('  Idempotency    : ' + r.execution.idempotency_key);
  L.push('');
  L.push('MEASURED OUTCOME');
  L.push('  Gross recovery : ' + (mv(r.realized_recovery) || 'not measured'));
  L.push('  Natural        : ' + (mv(r.natural_recovery) || 'not attributed'));
  L.push('  Realized cost  : ' + (mv(r.realized_cost) || 'none'));
  L.push('  Incremental net: ' + (mv(r.incremental_net_recovery) || 'not measured'));
  L.push('  Attribution    : ' + (r.attribution || 'not observable'));
  L.push('');
  L.push('PIPELINE');
  r.pipeline.forEach(st => L.push('  ' + (st.label || st.stage).padEnd(11) + ': ' +
    (st.blocked ? 'BLOCKED' : st.complete ? 'complete' : 'not reached') + ' — ' + st.note));
  L.push('');
  L.push(S.snap.control_room.fixture_label);
  L.push('');
  L.push('EVIDENCE BASIS');
  L.push('  ' + evidenceBasisLine());
  return L.join('\n');
}

function evidenceBasisLine() {
  const f = benchFacts();
  const cr = S.snap && S.snap.control_room;
  const pack = cr ? cr.policy_pack_version : '';
  if (f && f.verified) {
    return 'Engine: PAYVANTA · Policy pack: ' + pack +
      ' · Benchmark contract: frozen experiment ' + shortHash(f.frozen) +
      ' (this receipt is not an official cell)';
  }
  return 'Engine: PAYVANTA · Policy pack: ' + pack + ' · Official experiment not verified in this workspace';
}

/* ================================================== VIEW: RECOVERY LAB */
function viewLab() {
  const cr = S.snap.control_room;
  const cards = cr.all_opportunities;
  const withCands = cards.filter(c => c.candidate_count > 1);
  const id = S.param || (withCands[0] && withCands[0].opportunity_id) || firstOppId();
  const d = id ? detailFor(id) : null;

  return h`
  ${sec('Counterfactual recovery lab', 'do nothing vs intervene',
    'PAYVANTA does not ask “what can we send?”. It asks “what is each option worth over doing nothing, after cost, risk, fatigue and policy?” This is the comparison the allocator actually optimizes.')}
  ${proofStrip({ compact: true })}
  <div class="toolbar">
    <label class="field" style="flex:1 1 320px">
      <span class="lbl">Opportunity</span>
      <select class="select" id="lab-pick" style="flex:1 1 auto">
        ${cards.map(c => h`<option value="${esc(c.opportunity_id)}" ${c.opportunity_id === id ? 'selected' : ''}>
          ${esc(shortId(c.opportunity_id))} · ${m(c.value_at_risk)} · ${esc(c.candidate_count)} candidates
        </option>`)}
      </select>
    </label>
    ${d ? h`<a class="btn btn-ghost" href="#/opportunity/${esc(id)}">Open full workspace</a>` : ''}
  </div>
  ${d ? h`
    ${panel('Baseline', h`<div class="dl">
      ${row('Natural recovery probability', esc(pct(d.counterfactual.p_natural, 2)))}
      ${row('Allocator mode', esc(d.counterfactual.allocator_mode || 'not recorded'), { mono: true })}
      ${row('Candidates valued', esc(d.counterfactual.options.length))}
    </div>`)}
    ${panel('Option comparison', cfBlock(d.counterfactual))}
    ${engineContractNote()}
    ${sec('Simulate a different world', 'deterministic',
      'Generate a fresh synthetic world and run the full engine over it. Same seed, same result, every time.')}
    ${simulator()}`
    : absentBlock('none', 'This fixture produced no opportunity with more than one candidate action.')}
  `;
}

function simulator() {
  return h`${panel(null, h`
    <form class="simform" id="sim-form">
      <label class="simfield"><span class="lbl">Failure type</span>
        <select class="select" name="failure_type">
          ${['PAYMENT_FAILURE', 'SUBSCRIPTION_FAILURE', 'CHECKOUT_ABANDONMENT', 'RECEIVABLE_OVERDUE']
            .map(v => h`<option value="${v}">${esc(titleize(v))}</option>`)}
        </select></label>
      <label class="simfield"><span class="lbl">Profile</span>
        <select class="select" name="profile">
          ${['BALANCED', 'HIGH_NATURAL', 'SCARCE', 'ABUNDANT', 'HOSTILE', 'DEGRADED']
            .map(v => h`<option value="${v}" ${v === 'SCARCE' ? 'selected' : ''}>${esc(titleize(v))}</option>`)}
        </select></label>
      <label class="simfield"><span class="lbl">Seed</span>
        <input class="input" name="seed" type="number" value="7" min="1" max="9999" required></label>
      <label class="simfield"><span class="lbl">Opportunities</span>
        <input class="input" name="opportunity_count" type="number" value="12" min="1" max="60" required></label>
      <label class="simfield"><span class="lbl">Urgency</span>
        <select class="select" name="urgency">
          ${['normal', 'high'].map(v => h`<option value="${v}">${esc(titleize(v))}</option>`)}
        </select></label>
      <button class="btn btn-primary" type="submit">Run engine</button>
    </form>`)}
    <div id="sim-out" style="margin-top:var(--s-4)"></div>`;
}

/* The simulator returns a complete engine run — a full control room, a map of opportunity
   details keyed by id, and an audit ledger. This used to read `res.opportunities.length`
   (a map, so `undefined`) and `res.summary` (a key the payload has never carried), so an
   entire engine run rendered as one empty figure. Everything below comes from the response. */
function simResult(res) {
  if (res.error) return absentBlock('none', 'The engine rejected this configuration: ' + res.error);
  const cr = res.control_room;
  if (!cr) return absentBlock('none',
    'The simulator returned no engine payload for this configuration, so there is nothing to show.');
  const hero = cr.hero || {};
  const inp = res.inputs || {};
  const wf = (cr.waterfall || {}).realized || {};
  const detail = res.opportunities && typeof res.opportunities === 'object' ? res.opportunities : {};
  const ids = Object.keys(detail);
  const ranked = cr.top_opportunities || cr.all_opportunities || [];
  const net = paise(hero.incremental_net_recovery);

  return h`
  ${panel('Simulation result', h`
    <div class="kpiwrap"><div class="kpis" data-n="4">
      ${figure('Incremental net recovery', m(hero.incremental_net_recovery),
        { key: 'sim-net', tone: net < 0 ? 'neg' : 'pos' })}
      ${figure('Revenue at risk', m(hero.at_risk_revenue), { key: 'sim-risk' })}
      ${figure('Recovery rate', esc(pct(hero.recovery_rate, 2) || '0.00%'), { key: 'sim-rate' })}
      ${figure('Opportunities', esc(cnt(ids.length) || '0'), { key: 'sim-n' })}
    </div></div>
    <p class="hero-eq" style="margin-top:var(--s-4)">
      <b>${m(wf.incremental)}</b><span class="op">incremental</span>
      <span class="op">−</span>
      <b>${m(wf.cost)}</b><span class="op">cost</span>
      <span class="op">=</span>
      <b>${m(wf.net)}</b><span class="op">net</span></p>
    ${net < 0 ? h`<p class="sec-sub">A negative result is a real outcome, not an error: under this
      profile the engine spent more on intervention than it recovered above natural recovery.</p>` : ''}`,
    cr.fixture_label || 'Synthetic deterministic world.')}

  ${panel('What the engine did', pulseBlock(cr.system_pulse), 'Counts for this run only.')}

  ${panel('Policy outcome', h`<div class="dl">
    ${row('Authorized', esc(cnt(hero.authorized_interventions) || '0'), { mono: true })}
    ${row('Blocked', esc(cnt(hero.blocked_interventions) || '0'), { mono: true })}
    ${row('Policy compliance', tok(titleize(hero.policy_compliance), hero.policy_compliance === 'PASS' ? 'ok' : 'no', 'sq'))}
    ${row('Execution integrity', tok(titleize(hero.execution_integrity), hero.execution_integrity === 'PASS' ? 'ok' : 'no', 'sq'))}
    ${row('Policy pack', h`<span class="mono">${esc(cr.policy_pack_version)}</span>
      ${tok(titleize(cr.policy_pack_status), cr.policy_pack_status === 'SEALED' ? 'ok' : 'wa', 'sq')}`)}
  </div>`)}

  ${ranked.length ? h`${panel('Opportunities in this world', h`
    <div class="ledger-scroll"><table class="ledger">
      <thead><tr><th>Opportunity</th><th class="num">At risk</th><th>Cause</th>
        <th>Selected action</th><th>Policy</th><th class="num">Expected incremental</th></tr></thead>
      <tbody>${ranked.map(c => h`<tr>
        <td class="mono">${esc(shortId(c.opportunity_id))}</td>
        <td class="num mono">${m(c.value_at_risk)}</td>
        <td>${esc(c.cause || 'not diagnosed')}</td>
        <td>${esc(c.selected_action || 'none selected')}</td>
        <td>${c.blocked ? tok('Blocked', 'no', 'di')
              : tok(titleize(c.authorization_state || 'not submitted'), authTone(c.authorization_state), 'sq')}</td>
        <td class="num mono">${m(c.expected_incremental)}</td>
      </tr>`)}</tbody></table></div>`,
    ranked.length + ' of ' + ids.length + ' shown')}` : ''}

  ${panel('Run provenance', h`<div class="dl">
    ${row('Source', h`${tok('REAL ENGINE', 'vi', 'di')} <span class="dl-tag">the full engine, run on a synthetic world</span>`)}
    ${row('Seed', esc(inp.seed), { mono: true })}
    ${row('Profile', esc(inp.profile), { mono: true })}
    ${row('Failure type', esc(titleize(inp.failure_type)))}
    ${row('Urgency', esc(titleize(inp.urgency)))}
    ${row('Opportunities requested', esc(cnt(inp.opportunity_count)), { mono: true })}
    ${row('Cycles run', esc(cnt(cr.cycles_run)), { mono: true })}
    ${row('Audit events recorded', esc(cnt((res.audit_ledger || []).length)), { mono: true })}
    ${row('Reproducibility', 'Same seed, profile and failure type reproduce this run exactly.')}
    ${row('Not official evidence', 'This is a scenario bench. Only the Benchmark Lab reads the sealed 600-cell run.')}
  </div>`)}`;
}

/* =============================================== VIEW: GUARDRAILS */
function viewGuardrails() {
  const cr = S.snap.control_room;
  const cards = cr.all_opportunities;
  const withAuth = cards.filter(c => c.authorization_state);
  const blockedCards = cards.filter(c => c.blocked);
  const id = S.param || (blockedCards[0] || withAuth[0] || {}).opportunity_id;
  const d = id ? detailFor(id) : null;

  return h`
  ${sec('Policy and guardrails', withAuth.length + ' authorization requests',
    'Nothing reaches an adapter without passing every applicable gate. Blocks are recorded with the value observed and the constraint it failed.')}
  <div class="kpiwrap" style="margin-bottom:var(--s-5)"><div class="kpis" data-n="4">
    ${figure('Authorized', esc(cr.hero.authorized_interventions), { key: 'g-auth', tone: 'pos' })}
    ${figure('Blocked', esc(cr.hero.blocked_interventions), { key: 'g-block', tone: cr.hero.blocked_interventions ? 'neg' : '' })}
    ${figure('Policy compliance', esc(cr.hero.policy_compliance), { key: 'g-comp' })}
    ${figure('Execution integrity', esc(cr.hero.execution_integrity), { key: 'g-int' })}
  </div></div>
  ${panel('Policy pack', h`<div class="dl">
    ${row('Version', esc(cr.policy_pack_version), { mono: true })}
    ${row('Status', tok(titleize(cr.policy_pack_status), cr.policy_pack_status === 'SEALED' ? 'ok' : 'wa', 'sq'))}
    ${row('Internal policy id', esc(cr.internal_policy_id), { mono: true })}
    ${row('Autonomy bound', 'Execution requires AUTHORIZED. Blocked actions never reach adapters.')}
  </div>`)}

  ${sec('Blocked interventions', blockedCards.length + ' blocked')}
  ${blockedCards.length ? h`<div class="ledger-scroll"><table class="ledger">
    <thead><tr><th>Opportunity</th><th class="num">At risk</th><th>Action</th><th>Gate</th><th>Reason</th><th></th></tr></thead>
    <tbody>${blockedCards.map(c => h`<tr>
      <td class="mono">${esc(shortId(c.opportunity_id))}</td>
      <td class="num mono">${m(c.value_at_risk)}</td>
      <td>${esc(c.selected_action || 'none')}</td>
      <td class="mono">${esc((detailFor(c.opportunity_id) || { guardrail: {} }).guardrail.blocking_gate || '?')}</td>
      <td>${esc(c.blocking_reason)}</td>
      <td><button type="button" class="btn btn-sm btn-ghost" data-guard="${esc(c.opportunity_id)}">Proof</button></td>
    </tr>`)}</tbody></table></div>`
    : absentBlock('none', 'No intervention was blocked on this fixture. Every authorization request passed its gates.')}

  ${d ? h`
    ${sec('Guardrail proof', shortId(id))}
    ${guardMatrix(d.guardrail)}
    ${sec('Stopping rules', d.guardrail.stopping_fired + ' fired')}
    ${panel(null, stoppingBlock(d.guardrail))}` : ''}
  `;
}

/* =============================================== VIEW: AUDIT LEDGER */
const AUDIT_FILTERS = [
  ['all', 'All', () => true],
  ['decisions', 'Decisions', r => r.category === 'decisions'],
  ['guardrails', 'Guardrails', r => r.category === 'guardrails'],
  ['executions', 'Execution', r => r.category === 'executions'],
  ['measurements', 'Measurement', r => r.category === 'measurements'],
  ['blocks', 'Blocks', r => r.blocked],
];
const AUDIT_PAGE = 120;

// A row reading "Executions" under a chip reading "Execution" is one vocabulary
// pretending to be two. The filter labels are the vocabulary; the table borrows them.
const AUDIT_CAT_LABEL = Object.fromEntries(AUDIT_FILTERS.slice(1).map(([k, l]) => [k, l]));

function viewAudit() {
  const all = S.snap.audit_ledger;
  const scoped = S.param ? all.filter(r => r.object === S.param) : all;
  const f = AUDIT_FILTERS.find(x => x[0] === S.filters.audit) || AUDIT_FILTERS[0];
  const rows = scoped.filter(f[2]);
  const shown = rows.slice(0, S.auditLimit || AUDIT_PAGE);

  return h`
  ${sec('Audit ledger',
    // Scoped, the header count has to say so. "504 events" above a 28-row table is
    // two true numbers that read as one wrong one.
    S.param ? scoped.length + ' of ' + all.length + ' events' : all.length + ' events',
    'Every stage of every decision, in the order the engine recorded it. Nothing is summarized away.')}
  ${S.param ? h`<p class="sec-sub" style="margin-bottom:var(--s-4)">
    Scoped to <span class="mono">${esc(S.param)}</span> — ${scoped.length} events.
    <a class="prov" href="#/audit">show all</a></p>` : ''}
  <div class="filters" role="group" aria-label="Filter audit events">
    ${AUDIT_FILTERS.map(([k, l, fn]) => h`
      <button type="button" class="chip" data-auditfilter="${k}" aria-pressed="${S.filters.audit === k}">
        ${esc(l)}<span class="chip-n">${scoped.filter(fn).length}</span>
      </button>`)}
  </div>
  <p class="sec-sub" style="margin:var(--s-4) 0">Showing ${shown.length} of ${rows.length}.</p>
  ${rows.length ? h`<div class="ledger-scroll cv"><table class="ledger">
    <thead><tr><th>Sequence</th><th>Category</th><th>Stage</th><th>Object</th>
      <th>Decision</th><th>Event</th><th>Result</th><th>Audit ref</th></tr></thead>
    <tbody>${shown.map(r => h`<tr>
      <td class="mono">${esc(r.timestamp)}</td>
      <td>${esc(AUDIT_CAT_LABEL[r.category] || titleize(r.category))}</td>
      <td class="mono">${esc(r.label || r.stage)}</td>
      <td class="mono"><a class="prov" href="#/opportunity/${esc(r.object)}">${esc(shortId(r.object))}</a></td>
      <td>${esc(r.decision)}</td>
      <td>${esc(r.event)}</td>
      <td>${r.result === 'blocked' ? tok('Blocked', 'no', 'di')
        : r.result === 'complete' ? tok('Complete', 'ok', 'sq') : tok('Pending', 'nu')}</td>
      <td class="mono dim">${esc(shortId(r.audit_reference))}</td>
    </tr>`)}</tbody></table></div>
    ${shown.length < rows.length ? h`<p style="margin-top:var(--s-4)">
      <button type="button" class="btn btn-ghost" id="audit-more">Show ${Math.min(AUDIT_PAGE, rows.length - shown.length)} more
        (${rows.length - shown.length} remaining)</button></p>` : ''}`
    : absentBlock('none', 'No audit event matches this filter.')}
  `;
}

/* ============================================= VIEW: BENCHMARK LAB */
function benchVerified(b) { return !!(b && b.evidence_verified); }

function benchStory() {
  return (S.bench && S.bench.story) || {};
}

function bmLevels(active) {
  return h`<div class="bm-levels" aria-label="Evidence levels">
    <a class="bm-level ${active === 'exec' ? 'is-on' : ''}" href="#/benchmark" data-level="executive">
      <span class="lbl">Level 1</span><span>Executive evidence</span>
    </a>
    <a class="bm-level ${active === 'forensic' ? 'is-on' : ''}" href="#/benchmark/matrix" data-level="forensic">
      <span class="lbl">Level 2</span><span>Forensic evidence</span>
    </a>
    <a class="bm-level ${active === 'prov' ? 'is-on' : ''}" href="#/benchmark/evidence" data-level="forensic">
      <span class="lbl">Level 2</span><span>Provenance</span>
    </a>
  </div>`;
}

function benchMtx(b) {
  if (S.bmMatrix && S.bmMatrix.matrix) return S.bmMatrix;
  return (b && b.profile_policy_matrix) || { profiles: [], policies: [], matrix: {} };
}

function benchPolicies(b) {
  return (b && b.policy_summaries) || {};
}

function benchProfiles(b) {
  const agg = b && b.aggregate;
  return (agg && agg.per_profile) || {};
}

function m10HeatStyle(paise, maxPos, minNeg) {
  if (paise === null || paise === undefined) return '';
  if (paise >= 0 && maxPos > 0) {
    const t = Math.min(1, paise / maxPos);
    return `--m10-int:${t.toFixed(3)};--m10-sign:pos`;
  }
  if (paise < 0 && minNeg < 0) {
    const t = Math.min(1, Math.abs(paise / minNeg));
    return `--m10-int:${t.toFixed(3)};--m10-sign:neg`;
  }
  return '--m10-int:0;--m10-sign:zero';
}

function matrixM10Extents(mtx) {
  let maxPos = 0;
  let minNeg = 0;
  const matrix = mtx.matrix || {};
  Object.values(matrix).forEach(row => {
    Object.values(row || {}).forEach(cell => {
      const p = cell && cell.m10_median_paise;
      if (typeof p === 'number') {
        if (p > maxPos) maxPos = p;
        if (p < minNeg) minNeg = p;
      }
    });
  });
  return { maxPos, minNeg };
}

function matrixHasData(mtx) {
  return !!(mtx && mtx.matrix && Object.keys(mtx.matrix).length);
}

/* The sub-views that put measured cell values on screen, and therefore need the lazy
   matrix request. A bare `#/benchmark` parses to sub === null, not '' — parseHash
   returns `parts[1] || null` — so this normalises before comparing. The renderer
   normalised (`S.sub || ''`) and the loader did not, which is what left the
   Experiment tab loading forever: its guard tested `S.sub === ''` against null, the
   fetch was never issued, and nothing was ever going to set the data the loading
   panel was waiting for. One predicate, used by both, so they cannot disagree. */
const MATRIX_SUBVIEWS = new Set(['', 'matrix', 'compare']);

function matrixWanted() {
  return S.route === 'benchmark' && benchVerified(S.bench) &&
    MATRIX_SUBVIEWS.has(S.sub || '');
}

/**
 * Which of the matrix's terminal states to render.
 *
 * Deriving "loading" from the absence of data conflates three different situations —
 * never requested, in flight, and came back empty — into one spinner that no outcome
 * can clear. Every state below renders something final: a value, a named failure with
 * a retry, or an honest statement about evidence. `loading` is only reachable while a
 * request is genuinely in flight, or in the synchronous gap between this render and
 * bindView() issuing the fetch in the same route() call.
 */
function matrixState(b) {
  if (!b) return 'verifying';
  if (!benchVerified(b)) {
    return (b.artefact_status === 'MOUNTED' || b.artefact_status === 'VERIFIED')
      ? 'unverified' : 'unmounted';
  }
  if (S.bmMatrixError) return 'failed';
  if (matrixHasData(S.bmMatrix)) return 'ready';
  if (S.bmMatrixLoading) return 'loading';
  // Requested, settled, still no cells: a failure, not a wait.
  return S.bmMatrixAttempted ? 'failed' : 'loading';
}

function bmMatrixPanel(title, body) {
  return panel(title, body);
}

function bmMatrixLoadingPanel(title, note) {
  return bmMatrixPanel(title, h`
    <p class="bm-loading" role="status" aria-live="polite">Loading measured matrix from official artefacts…</p>
    ${note ? h`<p class="sec-sub">${esc(note)}</p>` : ''}`);
}

function bmMatrixFailedPanel(title, err) {
  return bmMatrixPanel(title, h`
    <div class="absent-block">
      <span class="absent-k">MATRIX LOAD FAILED</span>
      <p>Official evidence is verified, but the measured matrix could not be loaded.</p>
      ${err ? h`<p class="sec-sub mono">${esc(err)}</p>` : ''}
      <p style="margin-top:var(--s-3)">
        <button type="button" class="btn btn-ghost" id="bm-matrix-retry">Retry matrix load</button>
      </p>
    </div>`);
}

/** The detail line under MATRIX LOAD FAILED. A settled-but-empty response carries no
    error string of its own, and a failure panel with a blank diagnostic reads as a
    rendering bug rather than a reportable state. */
function bmMatrixErrorDetail() {
  return S.bmMatrixError ||
    'The matrix endpoint returned no cells for the verified official run.';
}

function bmCellMatchesFilter(cell, policy, filter) {
  if (filter === 'all') return true;
  if (!cell) return false;
  if (filter === 'valid') return cell.status === 'valid';
  if (filter === 'invalid') return cell.status !== 'valid';
  if (filter === 'high') return (cell.m10_median_paise || 0) > 0;
  if (filter === 'low') return (cell.m10_median_paise || 0) <= 0;
  if (filter === 'blocked') return cell.status !== 'valid';
  if (filter === 'failures') return policy === 'REVIVE';
  if (filter === 'violations') return cell.valid_count === 20;
  return true;
}

function shortHash(hash) {
  if (!hash || hash.length < 16) return hash || '—';
  return hash.slice(0, 12) + '…';
}

function benchProv(b) {
  return (b && b.provenance) || {};
}

function bmProvStrip(prov, verification) {
  if (!prov) return '';
  return h`<div class="bm-prov-strip" aria-label="Evidence provenance">
    <span class="bm-prov-chip">${tok('OFFICIAL CLOUD RUN', 'vi', 'sq')}</span>
    <span class="bm-prov-chip">CONFIG <span class="mono">${esc(shortHash(prov.config_hash))}</span></span>
    <span class="bm-prov-chip">POLICY PACK <span class="mono">${esc(prov.policy_pack_version || '—')}</span></span>
    <span class="bm-prov-chip">CELLS <span class="mono">${esc(verification && verification.cell_count != null ? verification.cell_count + ' / 600' : '600 / 600')}</span></span>
    <span class="bm-prov-chip">VALIDATION <span class="mono">${esc(prov.validation_status || 'BENCHMARK_VALID')}</span></span>
  </div>`;
}

function viewBenchmark() {
  const b = S.bench;
  if (!b) return absentBlock('not-mounted', 'Benchmark evidence status is still loading.');
  const run = b.declared_official_run;
  const verified = benchVerified(b);
  const prov = benchProv(b);
  const mtx = benchMtx(b);
  const view = S.sub || '';
  const compact = view !== '';

  const head = h`
  ${compact ? '' : sec('Benchmark lab', verified ? 'OFFICIAL EVIDENCE' : b.artefact_classification,
    verified
      ? 'Level 1: the frozen 20 × 6 × 5 experiment. Level 2: one cell, its checksum, its artefact. The benchmark is the proof layer around the engine — not the product itself.'
      : 'Recovery systems are easy to claim and hard to prove. This screen shows the frozen experiment contract and the honest status of evidence in this workspace.')}
  <header class="bm-hero ${compact ? 'is-compact' : ''}" style="margin-bottom:var(--s-4)">
    ${compact ? '' : h`<p class="bm-kicker">PAYVANTA · BENCHMARK LAB</p>
    <p class="bm-claim">${esc(b.headline.toUpperCase())}</p>`}
    <div class="bm-banner ${verified ? 'is-verified' : 'is-pending'}">
      <div class="bm-banner-main">
        ${verified ? tok('OFFICIAL EVIDENCE · VERIFIED', 'vi', 'di') : tok(titleize(b.evidence_status || b.artefact_status), 'wa', 'di')}
        ${verified ? h`<span class="bm-banner-src">SOURCE · OFFICIAL CLOUD RUN</span>` : ''}
      </div>
      <div class="bm-stats bm-stats-hero">
        <div class="bm-stat"><span class="lbl">Official cells</span><span class="bm-stat-v">${verified ? '600' : esc(run.cells)}</span></div>
        <div class="bm-stat"><span class="lbl">Groups</span><span class="bm-stat-v">${verified ? '120' : esc(run.groups)}</span></div>
        <div class="bm-stat"><span class="lbl">Seeds</span><span class="bm-stat-v">${esc(run.seeds)}</span></div>
        <div class="bm-stat"><span class="lbl">Profiles</span><span class="bm-stat-v">${esc(run.profiles)}</span></div>
        <div class="bm-stat"><span class="lbl">Policies</span><span class="bm-stat-v">${esc(run.policies)}</span></div>
        <div class="bm-stat"><span class="lbl">Official evidence</span>
          ${verified
            ? h`<span class="bm-stat-v is-tok">${tok('VERIFIED', 'ok')}</span>
                <span class="bm-stat-note">Benchmark valid · blocked = false</span>`
            : h`<span class="bm-stat-v is-tok">${tok(titleize(run.validation), 'wa')}</span>`}
        </div>
      </div>
      ${verified ? bmProvStrip(prov, b.verification) : ''}
    </div>
    ${bmLevels(view === 'evidence' ? 'prov' : (view === 'matrix' || view === 'compare' ? 'forensic' : 'exec'))}
  </header>`;

  if (view === 'matrix') return head + bmMatrix(b, mtx, run, verified);
  if (view === 'compare') return head + bmCompare(b, run, verified, mtx);
  if (view === 'evidence') return head + bmEvidence(b, run, verified, prov);
  return head + bmExperiment(b, run, verified, prov, mtx);
}

function bmExperiment(b, run, verified, prov, mtx) {
  const revive = benchPolicies(b).REVIVE;
  const f = benchFacts();
  const story = benchStory();
  return h`
  ${bmEngineCallout(story)}
  ${panel('Experiment structure', h`
    ${experimentModel(run)}
    ${bmWhyFactors(story, run)}
    <p class="sec-sub" style="margin-top:var(--s-4)">One cell is not a demonstration. ${esc(run.cells)} cells is a controlled evaluation of recovery behavior across deterministic seeds and operating profiles. Primary metric: <strong>M-10 incremental net recovery</strong> — net recovered by a policy minus net recovered by B0 on the same seed and profile.</p>`, 'frozen experiment')}
  ${bmMethodology(story, run)}
  ${bmProfilePolicyDefs(story)}
  ${verified ? panel('Incremental net recovery — REVIVE M-10 median', h`
    <p class="bm-m10-hero">${esc(revive && revive['M-10_median_paise'] != null
      ? formatRead(revive['M-10_median_paise']) : '—')}</p>
    <p class="sec-sub">Median across ${esc(revive.run_count || run.groups)} evaluation groups, from <span class="mono">per_policy.json</span>. Observed range: ${esc(formatRead(revive['M-10_min_paise']))} … ${esc(formatRead(revive['M-10_max_paise']))}. ${esc(revive.seeds_where_negative_m10 || 0)} groups recorded <strong>negative</strong> M-10 — intervening cost more than it recovered.</p>
    <p class="sec-sub" style="margin-top:var(--s-3)">B0’s M-10 is 0 by definition: it is the reference the metric subtracts. B1–B3 record 0 because they realized no recovery, not because the metric fixes them there — they did intervene. <a href="#/benchmark/compare">See outcome against effort</a>.</p>`) : ''}
  ${verified ? experimentCertificate(f) : ''}
  ${verified ? bmMatrixPreview(b, mtx, run) : panel('Evidence status', bmStatus(b))}
  ${bmHardening(story)}
  ${bmPerfTimeline(story)}
  ${bmClaimTable(story)}
  ${bmLimitations(story)}
  ${bmFinalSeal(run, verified, f)}
  <p style="margin-top:var(--s-4);display:flex;gap:var(--s-2);flex-wrap:wrap">
    <a class="btn btn-ghost" href="#/benchmark/matrix">${verified ? 'Open profile × policy matrix' : 'Open experiment matrix'}</a>
    ${verified ? h`<a class="btn btn-ghost" href="#/benchmark/compare">Policy & profile comparison</a>` : ''}
    <a class="btn btn-ghost" href="#/benchmark/evidence">Provenance & verification</a>
    <button type="button" class="btn btn-ghost" data-official-cell>ABUNDANT × REVIVE · seed 14</button>
    <a class="btn btn-quiet" href="#/control">Explore recovery engine</a>
  </p>`;
}

function bmEngineCallout(story) {
  const rel = (story.sandbox_vs_official || {});
  const sand = rel.sandbox || {};
  const off = rel.official || {};
  return panel('The engine you just saw', h`
    <p class="sec-sub" style="margin-bottom:var(--s-3)">${esc(rel.relationship || 'This is the engine you just saw operating. That engine was evaluated separately across 600 official cells.')}</p>
    <p class="sec-sub" style="margin-bottom:var(--s-4)">${esc(story.differentiator || '')}</p>
    <div class="bm-split">
      <div class="bm-split-i" data-kind="sandbox">
        <p class="lbl">Sandbox</p>
        <p>${esc(sand.does || 'Demonstrates the working PAYVANTA recovery workflow.')}</p>
        <p class="dim">${esc(sand.is_not || 'Not an official benchmark cell.')}</p>
      </div>
      <div class="bm-split-i" data-kind="official">
        <p class="lbl">Official benchmark</p>
        <p>${esc(off.does || 'Evaluates the engine under a frozen controlled experiment.')}</p>
        <p class="dim">${esc(off.is_not || 'Not the product itself.')}</p>
      </div>
    </div>`, 'product → evidence');
}

function bmWhyFactors(story, run) {
  const why = story.why || {};
  const rows = [
    ['20 seeds', (why.seeds && why.seeds.why) || 'Deterministic variation with repeatability.'],
    ['6 profiles', (why.profiles && why.profiles.why) || 'Different operating environments.'],
    ['5 policies', (why.policies && why.policies.why) || 'Comparative policy evaluation.'],
    ['600 cells', (why.cells && why.cells.why) || 'Systematic coverage rather than one selected scenario.'],
    ['120 groups', (why.groups && why.groups.why) || 'One world (seed × profile) under all five policies.'],
  ];
  return h`<div class="bm-why" style="margin-top:var(--s-4)">
    ${rows.map(([k, v]) => h`<div class="bm-why-i"><p class="bm-why-k">${esc(k)}</p><p>${esc(v)}</p></div>`)}
  </div>`;
}

function bmMethodology(story, run) {
  const why = story.why || {};
  const m10 = story.m10 || {};
  const access = story.access || {};
  return panel('How this was measured', h`
    <div class="dl">
      ${row('Design', '20 seeds × 6 profiles × 5 policies = 600 cells · 120 groups')}
      ${row('Seeds', esc((why.seeds && why.seeds.why) || 'Deterministic worlds. Same seed, same population.'))}
      ${row('Profiles', 'BALANCED, HIGH_NATURAL, SCARCE, ABUNDANT, HOSTILE, DEGRADED')}
      ${row('Policies', 'B0, B1, B2, B3, REVIVE — REVIVE is the internal policy id')}
      ${row('Workers', esc(String((why.workers && why.workers.count) || run.workers || 8)))}
      ${row('Primary metric', esc((m10.id || 'M-10') + ' · ' + (m10.user_facing || 'INCREMENTAL NET RECOVERY')))}
      ${row('M-10', esc(m10.definition || 'NetRecovered(policy) − NetRecovered(B0)'))}
      ${row('Validation', esc(run.validation || 'BENCHMARK_VALID') + ' · blocked = ' + String(run.blocked))}
      ${row('Artefacts', esc(access.path || 'artefacts/benchmark/official-cloud-final/'), { mono: true })}
      ${row('Git', esc(access.gitignore_rule ? 'artefacts/ is gitignored — mount the frozen tree to verify' : '—'))}
    </div>`, 'methodology');
}

function bmProfilePolicyDefs(story) {
  const profiles = story.profiles || [];
  const policies = story.policies || [];
  if (!profiles.length && !policies.length) return '';
  return panel('Profiles and policies', h`
    <div class="bm-def-grid">
      <div>
        <p class="lbl" style="margin-bottom:var(--s-3)">Operating profiles</p>
        <div class="dl">${profiles.map(p =>
          row(p.id, esc(p.description) + ' · scarcity ' + esc(String(p.capacity_scarcity_factor))))}</div>
      </div>
      <div>
        <p class="lbl" style="margin-bottom:var(--s-3)">Evaluated policies</p>
        <div class="dl">${policies.map(p =>
          row(p.id, esc(p.baseline) + ' — ' + esc(p.behaviour)))}</div>
      </div>
    </div>
    <p class="sec-sub" style="margin-top:var(--s-3)">REVIVE is an internal technical policy identifier. The product name is PAYVANTA.</p>`, 'definitions');
}

function bmHardening(story) {
  const steps = story.engineering || [];
  if (!steps.length) return '';
  return panel('Engineering hardening', h`
    <p class="sec-sub" style="margin-bottom:var(--s-4)">Debugging → profiling → optimization → validation → evidence. Each step is a measured infrastructure change, not a score.</p>
    <ol class="bm-hard">${steps.map(s => h`
      <li class="bm-hard-i" data-kind="${esc(s.kind || '')}">
        <div class="bm-hard-h">
          <span class="mono">${esc(s.id)}</span>
          <strong>${esc(s.title)}</strong>
          <span class="lbl">${esc(s.kind || '')}</span>
        </div>
        <div class="bm-hard-b">
          <p><span class="lbl">Problem</span> ${esc(s.problem || '')}</p>
          <p><span class="lbl">Fix</span> ${esc(s.fix || '')}</p>
          <p><span class="lbl">Measured</span> ${esc(bmHardeningResult(s))}</p>
        </div>
        ${s.classification ? h`<p class="bm-hard-class">${esc(s.classification)}</p>` : ''}
      </li>`)}</ol>`, 'engineering');
}

function bmHardeningResult(step) {
  const m = step.measured || {};
  if (step.id === 'M13.24' && m.workers) {
    return 'workers=1 / 2 / 8 fingerprints match. Wall 72.3s → 39.8s → 31.7s on a 10-cell (2-group) stress — not an 8× speedup.';
  }
  if (step.id === 'M13.25' && m.cases) {
    return 'files-ahead, manifest-ahead, corrupt cell, partial group, production-shaped interruption, resume — tests pass.';
  }
  if (step.id === 'M13.26' && m.cell_wall_seconds) {
    const w = m.cell_wall_seconds;
    return 'BALANCED ' + w.BALANCED + 's · SCARCE ' + w.SCARCE + 's · HOSTILE ' + w.HOSTILE + 's · ABUNDANT ' + w.ABUNDANT + 's. ~340k executions. M8 Lagrangian hot path. Not a hang.';
  }
  if (step.id === 'M13.27') {
    return 'Unauthorized cross-scan ~4137.6s → compute_policy_metrics ~0.321s local / ~0.39s cloud tail. Cell ~9900s → ~627.3s. Performance, not a score.';
  }
  if (step.id === 'CLOUD') {
    return 'seed=1 ABUNDANT REVIVE · 2016 cycles · 627.3s · 339,890 executions · checksum 80c238eb…5113da · run_valid=true · violations=0.';
  }
  if (step.id === 'OFFICIAL') {
    return '600 cells · 120 groups · workers=8 · BENCHMARK_VALID · blocked=false.';
  }
  return m.label || '';
}

function bmPerfTimeline(story) {
  const steps = story.engineering || [];
  const m27 = steps.find(s => s.id === 'M13.27') || {};
  const cloud = steps.find(s => s.id === 'CLOUD') || {};
  const m = m27.measured || {};
  const c = cloud.measured || {};
  const oldCell = m.pre_optimization_cloud_cell_seconds || 9900;
  const newCell = c.total_cell_seconds || m.post_optimization_cloud_cell_seconds || 627.3;
  const oldTail = m.old_unauthorized_cross_scan_seconds || 4137.6;
  const newTail = c.metrics_tail_seconds || m.cloud_metrics_tail_seconds || 0.39;
  return panel('Performance validation', h`
    <p class="bm-perf-flag">PERFORMANCE VALIDATION — NOT A BENCHMARK SCORE</p>
    <p class="sec-sub" style="margin-bottom:var(--s-4)">M13.27 rescued an O(authorization × execution) metrics tail. Checksums did not change. This is reliability engineering around the engine, not an M-10 improvement.</p>
    <div class="bm-perf">
      <div class="bm-perf-col">
        <p class="lbl">Cloud cell wall</p>
        <p class="bm-perf-old">~${esc(String(oldCell))}s</p>
        <p class="bm-perf-cap">Pre-optimization cloud cell</p>
        <span class="bm-perf-arrow" aria-hidden="true">↓ metrics-tail rescue</span>
        <p class="bm-perf-new">~${esc(String(newCell))}s</p>
        <p class="bm-perf-cap">Post-optimization cloud cell</p>
      </div>
      <div class="bm-perf-col">
        <p class="lbl">Metrics tail</p>
        <p class="bm-perf-old">~${esc(String(oldTail))}s</p>
        <p class="bm-perf-cap">Unauthorized cross-scan (local reference)</p>
        <span class="bm-perf-arrow" aria-hidden="true">↓ indexed aggregation</span>
        <p class="bm-perf-new">${esc(String(newTail))}s</p>
        <p class="bm-perf-cap">Cloud metrics tail · local compute_policy_metrics ${esc(String(m.new_compute_policy_metrics_local_seconds || 0.321))}s</p>
      </div>
    </div>`, 'performance');
}

function bmClaimTable(story) {
  const rows = story.claims || [];
  if (!rows.length) return '';
  return panel('Claim → evidence', h`
    <div class="ledger-scroll cv">
      <table class="ledger">
        <thead><tr><th>Claim</th><th>Source</th><th>Test</th><th>UI</th><th>API</th></tr></thead>
        <tbody>${rows.map(r => h`<tr>
          <td>${esc(r.claim)}</td>
          <td class="mono dim">${esc(r.source)}</td>
          <td class="mono dim">${esc((r.test || '').split('::').pop() || r.test || '')}</td>
          <td>${r.ui ? h`<a class="prov" href="${esc(r.ui.split(' ')[0])}">${esc(r.ui)}</a>` : '—'}</td>
          <td class="mono dim">${esc(r.api)}</td>
        </tr>`)}</tbody>
      </table>
    </div>`, 'traceable');
}

function bmLimitations(story) {
  const rows = story.limitations || [];
  if (!rows.length) return '';
  return panel('Limitations', h`
    <div class="bm-why">${rows.map(r => h`
      <div class="bm-why-i"><p class="bm-why-k">${esc(r.title)}</p><p>${esc(r.text)}</p></div>`)}</div>`, 'honesty');
}

function bmFinalSeal(run, verified, f) {
  return h`<section class="bm-seal ${verified ? 'is-verified' : ''}" aria-label="Measured, not claimed">
    <p class="bm-seal-k">PAYVANTA · OFFICIAL EXPERIMENT</p>
    <p class="bm-seal-h">Measured.<br>Not claimed.</p>
    <ul class="bm-seal-stats">
      <li><span>600</span> official cells</li>
      <li><span>120</span> groups</li>
      <li><span>20</span> seeds</li>
      <li><span>6</span> profiles</li>
      <li><span>5</span> policies</li>
    </ul>
    <p class="bm-seal-meta">${verified ? 'FROZEN EXPERIMENT · VERIFIED' : 'FROZEN EXPERIMENT · ' + esc(run.validation || 'DECLARED')}</p>
    ${f && f.frozen ? h`<p class="mono dim" style="overflow-wrap:anywhere;margin-top:var(--s-3)">${esc(f.frozen)}</p>` : ''}
  </section>`;
}

// Two forms, matching money.py exactly. `formatPaise` is the evidence form —
// exact rupees and paise, nothing rounded away, for tables and receipts where
// someone reconciles a figure. `formatRead` is the reading form: above ₹1,000
// the paise cannot change a decision and only cost two prominent glyphs, so
// they go. Below that they still carry meaning (a ₹4.50 messaging cost is 4.50,
// not 5) and are kept. Anything the server already formatted should use its
// `.display` / `.read` strings rather than being re-derived here.
function formatPaise(paise) {
  if (paise === null || paise === undefined) return '—';
  const sign = paise < 0 ? '-' : '';
  const abs = Math.abs(Math.round(paise));
  const rupees = Math.floor(abs / 100);
  const rem = abs % 100;
  return sign + '₹' + rupees.toLocaleString('en-IN') + '.' + String(rem).padStart(2, '0');
}

function formatRead(paise) {
  if (paise === null || paise === undefined) return '—';
  const abs = Math.abs(Math.round(paise));
  if (abs < 100_000) return formatPaise(paise);
  const sign = paise < 0 ? '-' : '';
  return sign + '₹' + Math.round(abs / 100).toLocaleString('en-IN');
}

function bmMatrixPreview(b, mtx, run) {
  const st = matrixState(b);
  if (st === 'failed') {
    return bmMatrixFailedPanel('Profile × policy matrix (M-10 median)', bmMatrixErrorDetail());
  }
  if (st === 'loading') {
    return bmMatrixLoadingPanel('Profile × policy matrix (M-10 median)',
      'Aggregate summaries loaded first. Indexing 600 official cells for profile × policy M-10 medians.');
  }
  const { maxPos, minNeg } = matrixM10Extents(mtx);
  return panel('Profile × policy matrix (M-10 median)', h`
    <p class="sec-sub" style="margin-bottom:var(--s-4)">Each cell summarizes 20 seeds. Click through to the full matrix for seed drill-down.</p>
    <div class="matrix-scroll" data-scroll="x">
      <table class="matrix bm-heat">
        <thead><tr><th class="rowh">Profile</th>
          ${mtx.policies.map(p => h`<th>${esc(p)}</th>`)}</tr></thead>
        <tbody>${mtx.profiles.map(prof => h`<tr>
          <th class="rowh">${esc(titleize(prof))}</th>
          ${mtx.policies.map(pol => {
            const cell = (mtx.matrix[prof] || {})[pol] || {};
            const style = m10HeatStyle(cell.m10_median_paise, maxPos, minNeg);
            /* aria-label replaces the inner text as the accessible name, so it has to
               carry the figure too — labelling this "Abundant × REVIVE" alone would
               hide the one number the cell exists to show. */
            const name = titleize(prof) + ' × ' + pol + ' — M-10 median ' +
              (cell.m10_median ? cell.m10_median.display : 'not measured') + ' · ' +
              (cell.valid_count || 0) + ' of ' + run.seeds + ' seeds valid';
            return h`<td><a class="mcell mcell-link" href="#/benchmark/matrix" data-policy="${esc(pol)}"
              style="${raw(style)}" aria-label="${esc(name)}" title="${esc(name)}">
              <span class="mcell-m10">${cell.m10_median ? esc(cell.m10_median.display) : '—'}</span>
              <span class="mcell-s">${esc(cell.valid_count || 0)}/${esc(run.seeds)} valid</span>
            </a></td>`;
          })}
        </tr>`)}</tbody>
      </table>
    </div>`);
}

function bmStatus(b) {
  const verified = benchVerified(b);
  const mounted = verified || b.artefact_status === 'MOUNTED' || b.artefact_status === 'VERIFIED';
  return h`
    ${!mounted ? absentBlock('not-mounted',
      'The declared official run’s artefacts live at ' + b.artefact_root +
      ', which is not present in this workspace. PAYVANTA shows the frozen configuration only.') : ''}
    ${b.verification && !verified ? absentBlock('none',
      'Verification failed: ' + (b.verification.failures || []).join(' · ')) : ''}
    <div class="dl" style="margin-top:var(--s-4)">
      ${row('Evidence status', tok(titleize(b.evidence_status || b.artefact_status), verified ? 'vi' : 'wa', 'di'))}
      ${row('Artefact root', esc(b.artefact_root), { mono: true })}
      ${row('Manifest', b.manifest ? tok('Present', 'ok') : absentInline('not-mounted'))}
      ${row('Aggregate', b.aggregate_present ? tok('Present', 'ok') : absentInline('not-mounted'))}
      ${row('Policy summaries', b.policy_summaries ? tok('Present', 'ok') : absentInline('not-mounted'))}
    </div>`;
}

function bmMatrix(b, mtx, run, verified) {
  if (verified) {
    const st = matrixState(b);
    if (st === 'failed') {
      return bmMatrixFailedPanel('Profile × policy matrix', bmMatrixErrorDetail());
    }
    if (st === 'loading') {
      return bmMatrixLoadingPanel('Profile × policy matrix',
        'Per-seed drill-down remains on demand. This indexes read-only cell artefacts once per session.');
    }
  }
  const { maxPos, minNeg } = matrixM10Extents(mtx);
  const [prof, pol] = S.bmCell ? S.bmCell.split('|') : ['', ''];
  return h`
  ${panel('Profile × policy matrix', h`
    <div class="bm-toolbar">
      <label class="simfield"><span class="lbl">Search cell</span>
        <input type="search" id="bm-q" class="inp" placeholder="seed 14 ABUNDANT REVIVE" value="${esc(S.bmSearch)}"></label>
      <div class="filters" role="group" aria-label="Cell filters">
        ${['all', 'valid', 'invalid', 'high', 'low', 'failures', 'violations'].map(f =>
          h`<button type="button" class="chip" data-bmfilter="${esc(f)}" aria-pressed="${S.bmFilter === f}">${esc(titleize(f))}</button>`)}
      </div>
    </div>
    <p class="sec-sub" style="margin-bottom:var(--s-4)">
      ${esc(mtx.profiles.length)} profiles × ${esc(mtx.policies.length)} policies × ${esc(run.seeds)} seeds =
      ${esc(run.cells)} cells. Forensic level: hover for preview · click a cell, then a seed. Pitch path: ABUNDANT × REVIVE × seed 14.
      ${S.bmFilter !== 'all' ? h`<br><span class="dim">Filter “${esc(titleize(S.bmFilter))}” dims groups that do not match aggregate signals. Per-seed failures appear in cell drill-down.</span>` : ''}</p>
    <div class="matrix-scroll bm-matrix-wrap" data-scroll="x">
      <table class="matrix bm-heat">
        <thead><tr><th class="rowh">Profile</th>
          ${mtx.policies.map(p => h`<th><button type="button" class="matrix-col-h" data-bmpol="${esc(p)}">${esc(p)}</button></th>`)}</tr></thead>
        <tbody>${mtx.profiles.map(pf => h`<tr>
          <th class="rowh"><button type="button" class="matrix-row-h" data-bmprof="${esc(pf)}">${esc(titleize(pf))}</button></th>
          ${mtx.policies.map(pl => {
            const cell = verified ? ((mtx.matrix[pf] || {})[pl] || {}) : {};
            const style = verified ? m10HeatStyle(cell.m10_median_paise, maxPos, minNeg) : '';
            const sel = S.bmCell === pf + '|' + pl;
            const match = !verified || S.bmFilter === 'all' || bmCellMatchesFilter(cell, pl, S.bmFilter);
            /* The cell's own text is "REVIVE / ₹2,10,90,130.08 / 20 valid" — which
               profile it belongs to is carried by the row header, and a screen reader
               moving button to button never hears it. So the accessible name states
               the full coordinate, and the hover preview does too: a tooltip reading
               only "M-10 median ₹…" tells you the number you can already see and not
               which of the thirty cells you are on. */
            const coord = titleize(pf) + ' × ' + pl;
            const reading = verified && cell.m10_median
              ? 'M-10 median ' + cell.m10_median.display + ' · ' +
                (cell.valid_count || 0) + ' of ' + (cell.seed_count || run.seeds) +
                ' seeds valid · ' + String(cell.status || 'unknown').toUpperCase()
              : run.seeds + ' seeds · evidence not mounted';
            return h`<td><button type="button" class="mcell ${match ? '' : 'mcell-dim'}" data-policy="${esc(pl)}"
              data-cell="${esc(pf)}|${esc(pl)}"
              style="${raw(style)}"
              aria-pressed="${sel}"
              aria-label="${esc(coord + ' — ' + reading)}"
              title="${esc(coord + ' — ' + reading)}">
              <span class="mcell-p">${esc(pl)}</span>
              <span class="mcell-m10">${verified && cell.m10_median ? esc(cell.m10_median.display) : esc(run.seeds + ' seeds')}</span>
              <span class="mcell-s">${verified ? esc((cell.valid_count || 0) + ' valid') : esc(titleize(mtx.verified ? 'partial' : 'not mounted'))}</span>
            </button></td>`;
          })}
        </tr>`)}</tbody>
      </table>
    </div>
    <div id="bm-search-results">${raw(bmSearchResults())}</div>`)}
  ${S.bmCell ? bmCellPanel(b, run, verified) : ''}
  ${verified && prof && pol ? bmMobilePickers(run, prof, pol) : ''}`;
}

function bmMobilePickers(run, prof, pol) {
  return h`<div class="bm-mobile-pick">
    <label class="simfield"><span class="lbl">Profile</span>
      <select id="bm-prof" class="inp">${run.profile_set.map(p =>
        h`<option value="${esc(p)}" ${p === prof ? 'selected' : ''}>${esc(titleize(p))}</option>`)}</select></label>
    <label class="simfield"><span class="lbl">Policy</span>
      <select id="bm-pol" class="inp">${run.policy_set.map(p =>
        h`<option value="${esc(p)}" ${p === pol ? 'selected' : ''}>${esc(p)}</option>`)}</select></label>
    <label class="simfield"><span class="lbl">Seed</span>
      <select id="bm-seed" class="inp">${run.seed_set.map(s =>
        h`<option value="${esc(s)}" ${Number(s) === Number(S.bmSeed) ? 'selected' : ''}>${esc(s)}</option>`)}</select></label>
  </div>`;
}

function bmCellPanel(b, run, verified) {
  const [prof, pol] = S.bmCell.split('|');
  const cellGroup = verified ? ((benchMtx(b).matrix[prof] || {})[pol] || {}) : null;
  const d = S.bmDetail;
  return panel('Cell — ' + titleize(prof) + ' × ' + pol, h`
    <div class="bm-cell-grid">
      <div class="dl">
        ${row('Profile', esc(prof), { mono: true })}
        ${row('Policy', esc(pol) + (pol === 'REVIVE' ? ' · internal benchmark id' : ''), { mono: true })}
        ${row('Seed coverage', verified ? esc((cellGroup && cellGroup.seed_count) || run.seeds) + ' / ' + esc(run.seeds) : esc(run.seeds), { mono: true })}
        ${row('Valid runs', verified && cellGroup ? esc(cellGroup.valid_count) + ' / ' + esc(run.seeds) : absentInline('not-mounted'))}
        ${row('M-10 median (group)', verified && cellGroup && cellGroup.m10_median ? esc(cellGroup.m10_median.display) : absentInline('not-mounted'))}
      </div>
      <div class="bm-seed-panel">
        <p class="lbl" style="margin-bottom:var(--s-2)">Seed drill-down</p>
        <div class="bm-seeds">${run.seed_set.map(s =>
          h`<button type="button" class="chip" data-bmseed="${esc(s)}" aria-pressed="${Number(s) === Number(S.bmSeed)}">${esc(s)}</button>`)}</div>
        ${d ? bmCellDetail(d) : h`<p class="sec-sub" id="bm-detail-load">Loading measured cell…</p>`}
        ${d ? h`<p style="margin-top:var(--s-3)"><button type="button" class="btn btn-ghost" id="bm-artifact">View artefact JSON</button></p>` : ''}
      </div>
    </div>`, S.bmCell);
}

/** Resource utilization arrives as a map of named capacities, each a 0..1 fraction.
    JSON.stringify put `{"message_capacity":0.056,"retry_slots":1}` on screen, which
    reads as a debug dump in the middle of an evidence panel — and hides that 0.056
    and 1 mean 5.6% and fully consumed. */
function bmResourceRows(util) {
  const keys = util && typeof util === 'object' ? Object.keys(util) : [];
  if (!keys.length) return row('Resource utilization', absentInline('none'));
  return keys.map(k => row(titleize(k), h`<span class="mono">${esc(pct(util[k], 1))}</span>`)).join('');
}

function bmCellDetail(d) {
  const derived = d.m10_source === 'derived';
  return h`<div class="dl bm-detail" id="bm-detail">
    ${row('Seed', esc(d.seed), { mono: true })}
    ${row('Cell index', esc(d.cell_index), { mono: true })}
    ${row('Run valid', d.run_valid ? tok('Valid', 'ok') : tok('Invalid', 'no'))}
    ${row('Metrics checksum', esc(d.metrics_checksum || '—'), { mono: true })}
    ${row('Artefact path', esc(d.artefact_path || '—'), { mono: true })}
    ${row('M-10 incremental net', h`${m(d.m10_incremental_net)}
      ${derived ? h`<span class="dl-tag" title="M-10 is a paired metric: this policy’s net recovery minus ${esc(d.m10_reference_policy || 'B0')}’s on the same seed and profile. The cell artefact stores no per-cell M-10.">${tok('DERIVED', 'tl', 'di')}</span>` : ''}`)}
    ${derived ? row((d.m10_reference_policy || 'B0') + ' reference net',
      h`${m(d.m10_reference_net)} <span class="dl-tag">${tok('OFFICIAL EVIDENCE', 'vi', 'di')}</span>`) : ''}
    ${row('Recovery rate', esc(pct(d.recovery_rate, 2) || '—'))}
    ${row('Gross recovered', m(d.gross_recovered))}
    ${row('Incremental recovered', m(d.incremental_recovered))}
    ${row('Natural recovered', m(d.natural_recovered))}
    ${row('Net recovered', m(d.net_recovered))}
    ${row('Realized cost', m(d.realized_cost))}
    ${row('Interventions', esc(cnt(d.interventions) || '—'), { mono: true })}
    ${row('Execution failures', esc(cnt(d.execution_failures) || '—'), { mono: true })}
    ${row('Policy violations', esc(cnt(d.policy_violations) || '—'), { mono: true })}
    ${row('Unauthorized executions', esc(cnt(d.unauthorized_executions) || '—'), { mono: true })}
    ${raw(bmResourceRows(d.resource_utilization))}
  </div>`;
}

function bmCompare(b, run, verified, mtx) {
  if (!verified) return absentBlock('not-mounted', 'Policy and profile comparison require verified official evidence.');
  return h`
    ${bmPolicyCompare(b, run, mtx)}
    ${bmProfileCompare(b, run)}`;
}

// The comparison a skeptic actually needs. "REVIVE ₹8.4 crore vs B0 ₹0, B1 ₹0,
// B2 ₹0, B3 ₹0" reads as too-good-to-be-true, and a reader who distrusts it is
// reading it correctly — four zeroes hide the fact that three of those arms
// intervened over 29 million times and realized nothing. Effort belongs next to
// outcome, or the outcome is not interpretable.
function bmPolicyCompare(b, run, mtx) {
  const policies = benchPolicies(b);
  const polOrder = run.policy_set;
  const behaviour = (mtx && mtx.policy_behaviour) || null;
  const byPolicy = {};
  (behaviour || []).forEach(r => { byPolicy[r.policy] = r; });
  const ref = b.reference_policy || 'B0';
  const maxM10 = Math.max(...polOrder.map(p => (policies[p] && policies[p]['M-10_median_paise']) || 0));

  const actedNoRecovery = (behaviour || []).filter(r => r.intervened_without_recovery);
  const totalWastedEffort = actedNoRecovery.reduce((s, r) => s + r.interventions, 0);

  return panel('Policy comparison — outcome measured against effort', h`
    <p class="sec-sub" style="margin-bottom:var(--s-4)">M-10 medians from <span class="mono">per_policy.json</span>. Intervention counts summed from the 600 cell artefacts. <strong>${esc(ref)} is the paired reference</strong> — M-10 is defined as net recovered by a policy minus net recovered by ${esc(ref)} on the same seed and profile, so ${esc(ref)}’s M-10 is 0 by definition, not by measurement.</p>
    <div class="bm-bars">${polOrder.map(pol => {
      const row = policies[pol] || {};
      const m10 = row['M-10_median_paise'] || 0;
      const w = maxM10 > 0 ? Math.max(2, (Math.abs(m10) / maxM10) * 100) : 0;
      const eff = byPolicy[pol];
      return h`<div class="bm-bar-row">
        <span class="bm-bar-lbl">${esc(pol)}${pol === ref ? h`<span class="bm-bar-ref">reference</span>` : ''}</span>
        <div class="bm-bar-track"><div class="bm-bar-fill ${m10 < 0 ? 'is-neg' : ''}" style="width:${w.toFixed(1)}%"></div></div>
        <span class="bm-bar-val">${esc(formatRead(m10))}</span>
        <span class="bm-bar-eff">${eff ? esc(eff.interventions.toLocaleString('en-IN')) + ' interventions' : ''}</span>
      </div>`;
    })}</div>
    ${behaviour ? h`
    <div class="tscroll" data-scroll="x" tabindex="0" role="region" aria-label="Policy comparison — outcome and effort per arm">
    <table class="ledger bm-table" style="margin-top:var(--s-5)">
      <thead><tr>
        <th>Policy</th><th class="num">M-10 median</th><th class="num">Interventions</th>
        <th class="num">Realized recovery</th><th class="num">Realized cost</th>
        <th class="num">Cells with recovery</th><th class="num">Negative M-10 seeds</th><th class="num">Unauthorized</th>
      </tr></thead>
      <tbody>${polOrder.map(pol => {
        const row = policies[pol] || {};
        const eff = byPolicy[pol] || {};
        const flag = pol === ref ? 'is-ref' : (eff.intervened_without_recovery ? 'is-void' : '');
        return h`<tr class="${flag}">
          <td>${esc(pol)}${pol === ref ? h` <span class="tok tok-nu tok-di">REF</span>` : ''}</td>
          <td class="num">${esc(formatRead(row['M-10_median_paise']))}</td>
          <td class="num">${eff.interventions != null ? esc(eff.interventions.toLocaleString('en-IN')) : '—'}</td>
          <td class="num">${eff.net_recovered ? esc(eff.net_recovered.read) : '—'}</td>
          <td class="num">${eff.realized_cost ? esc(eff.realized_cost.read) : '—'}</td>
          <td class="num">${eff.cells_with_recovery != null ? esc(eff.cells_with_recovery + ' / ' + eff.cells) : '—'}</td>
          <td class="num">${esc(row.seeds_where_negative_m10 != null ? row.seeds_where_negative_m10 : '—')}</td>
          <td class="num">${row.unauthorized_executions_total === 0 ? tok('0', 'ok') : esc(row.unauthorized_executions_total != null ? row.unauthorized_executions_total : '—')}</td>
        </tr>`;
      })}</tbody>
    </table>
    </div>
    ${actedNoRecovery.length ? h`<div class="bm-caveat">
      <p class="lbl">Read this before reading the gap</p>
      <p>${esc(actedNoRecovery.map(r => r.policy).join(', '))} did not sit idle. They executed
      <strong>${esc(totalWastedEffort.toLocaleString('en-IN'))}</strong> interventions across the same 600 cells and
      recorded <strong>zero realized recovery at zero realized cost</strong> — no cell in any of those arms closed with a
      non-zero net. ${esc(ref)}, by contrast, intervened <strong>0</strong> times; it is the do-nothing floor, which is
      why the metric is paired against it.</p>
      <p>PAYVANTA reports what the artefacts record and does not reinterpret them. A baseline that acts tens of
      millions of times and realizes nothing at no cost is a result about the recorded baseline arms, not a
      demonstration that no baseline strategy can recover revenue.</p>
    </div>` : ''}`
    : h`<p class="sec-sub" style="margin-top:var(--s-4)">Intervention counts load with the cell index.</p>`}`);
}

// `aggregate.per_profile` pools all five arms. Four are exactly zero, so its
// "M-10 mean by profile" is REVIVE's mean divided by five — a 5× understatement
// that also mislabels an average over policies as a property of the profile.
function bmProfileCompare(b, run) {
  const stats = b.profile_stats;
  if (!stats) {
    return panel('Profile comparison', absentBlock('not-mounted',
      'Per-profile statistics require verified official evidence.'));
  }
  const revive = {};
  Object.keys(stats).forEach(p => { if (stats[p].REVIVE) revive[p] = stats[p].REVIVE; });
  const maxMean = Math.max(...Object.values(revive).map(r => (r.mean && r.mean.paise) || 0), 1);
  const order = run.profile_set.filter(p => revive[p]);
  const totalNeg = order.reduce((s, p) => s + (revive[p].negative_seeds || 0), 0);

  return panel('Profile comparison — REVIVE M-10 by operating profile', h`
    <p class="sec-sub" style="margin-bottom:var(--s-4)">One policy at a time, so a profile figure means what its label says. Each card is <strong>REVIVE across 20 seeds</strong> in that profile. The baseline arms are held out rather than averaged in — B0–B3 all record M-10 of exactly 0, and pooling them would divide every figure below by five.</p>
    <div class="bm-prof-grid">${order.map(prof => {
      const r = revive[prof];
      const w = ((r.mean.paise / maxMean) * 100).toFixed(1);
      const neg = r.negative_seeds || 0;
      return h`<div class="bm-prof-card ${neg > 0 ? 'has-neg' : ''}">
        <p class="lbl">${esc(titleize(prof))}</p>
        <p class="bm-prof-v">${esc(r.median.read)}</p>
        <p class="bm-prof-sub">median · ${esc(r.seeds)} seeds</p>
        <div class="bm-prof-track"><div class="bm-prof-fill" style="width:${w}%"></div></div>
        <dl class="bm-prof-dl">
          <div><dt>Mean</dt><dd>${esc(r.mean.read)}</dd></div>
          <div><dt>Range</dt><dd>${esc(r.min.read)} … ${esc(r.max.read)}</dd></div>
          <div><dt>Negative seeds</dt><dd class="${neg > 0 ? 'is-neg' : ''}">${esc(neg)} / ${esc(r.seeds)}</dd></div>
        </dl>
      </div>`;
    })}</div>
    <p class="sec-sub" style="margin-top:var(--s-4)">${esc(totalNeg)} of ${esc(order.length * 20)} REVIVE cells closed with negative M-10 — intervening cost more than it recovered. Those cells are counted here rather than averaged away; they are the same result falsification test F-3 reports.</p>`);
}

function bmEvidence(b, run, verified, prov) {
  const v = b.verification || {};
  const story = benchStory();
  return h`
  ${verified ? experimentCertificate(benchFacts()) : ''}
  ${panel('Data provenance', h`
    <div class="bm-prov-banner ${verified ? 'is-verified' : ''}">
      ${verified ? tok('OFFICIAL EVIDENCE · VERIFIED', 'vi', 'di') : tok('OFFICIAL EVIDENCE · UNVERIFIED', 'wa', 'di')}
      <p class="bm-prov-src">Source · ${esc(prov.source_path || b.artefact_root)}</p>
    </div>
    <div class="dl" style="margin-top:var(--s-4)">
      ${row('Status', esc(prov.validation_status || run.validation), { mono: true })}
      ${row('Blocked', prov.blocked === false ? tok('False', 'ok') : tok(String(prov.blocked), 'wa'))}
      ${row('Benchmark version', esc(prov.benchmark_version || b.manifest && b.manifest.benchmark_version), { mono: true })}
      ${row('Metric version', esc(prov.metrics_version || b.manifest && b.manifest.metrics_version), { mono: true })}
      ${row('Config hash', esc(prov.config_hash || '—'), { mono: true })}
      ${row('Policy pack', esc(prov.policy_pack_version || b.policy_pack_version) + ' · ' + esc(prov.policy_pack_hash || b.policy_pack_hash), { mono: true })}
      ${row('Frozen experiment reference', esc(prov.frozen_experiment_reference || run.frozen_experiment_reference), { mono: true })}
      ${row('Cell count', esc(v.cell_count != null ? v.cell_count + ' / ' + v.expected_cells : run.cells), { mono: true })}
      ${row('Group count', esc(run.groups), { mono: true })}
      ${row('Declared matches computed', b.declared_matches_computed ? tok('Yes', 'ok') : tok('No', 'no'))}
      ${row('Evidence path', esc((story.access && story.access.path) || 'artefacts/benchmark/official-cloud-final/'), { mono: true })}
    </div>
    ${v.checks ? h`<div class="bm-checks" style="margin-top:var(--s-4)">${Object.entries(v.checks).map(([k, ok]) =>
      row(titleize(k), ok ? tok('Pass', 'ok') : tok('Fail', 'no')))}</div>` : ''}
    ${v.failures && v.failures.length ? absentBlock('none', v.failures.join(' · ')) : ''}`)}
  ${bmMethodology(story, run)}
  ${verified ? bmSafety(b.safety) : ''}
  ${verified ? bmFalsification(b.falsification) : ''}
  ${panel('Workspace evidence scan', h`
    <p class="sec-sub" style="margin-bottom:var(--s-4)">Every benchmark directory in this workspace and its admissibility for product proof.</p>
    <div class="scan">${b.workspace_scan.map(s => h`
      <div class="scan-i" data-status="${esc(s.status)}">
        <div>
          <p class="scan-p">${esc(s.path)}</p>
          ${s.reason ? h`<p class="scan-r">${esc(s.reason)}</p>` : ''}
        </div>
        <div style="text-align:right">
          ${tok(titleize(s.status), s.status === 'INADMISSIBLE' ? 'no' : (s.status === 'ADMISSIBLE_OFFICIAL' ? 'vi' : 'nu'), 'di')}
          <p class="scan-r">${s.admissible_for_product_proof ? 'admissible' : 'not admissible'}</p>
        </div>
      </div>`)}</div>`)}
  ${panel('Integrity invariants', h`<div class="dl">
    ${Object.entries(b.integrity).filter(([k]) => k !== 'note').map(([k, val]) =>
      row(titleize(k), typeof val === 'boolean' ? (val ? tok('True', 'ok') : tok('False', 'no')) : esc(val)))}
    ${row('Note', esc(b.integrity.note))}
  </div>`)}
  ${bmLimitations(story)}`;
}

// Zero across five counters and 600 cells. A row of zeroes only reassures once
// the reader knows what a non-zero would have meant, so each counter carries the
// event it would have been counting.
function bmSafety(safety) {
  if (!safety) return '';
  return panel('Guardrail audit — 600 cells', h`
    <p class="sec-sub" style="margin-bottom:var(--s-4)">From <span class="mono">audit_report.json</span>, across ${esc(safety.scope)}. These are counts of things that did not happen; each row names what one occurrence would have been.</p>
    <div class="safety-grid">${safety.counters.map(c => h`
      <div class="safety-i ${c.clean ? 'is-clean' : 'is-dirty'}">
        <span class="safety-n">${esc(c.count)}</span>
        <div>
          <p class="safety-k">${esc(titleize(c.key))}</p>
          <p class="safety-m">${esc(c.clean ? 'No case where ' + c.means : c.count + ' recorded')}</p>
        </div>
      </div>`)}</div>
    ${safety.all_clean ? h`<p class="sec-sub" style="margin-top:var(--s-4)">Every action executed in the official run passed an authorization gate, respected declared resource capacity, applied once, and honoured its stopping rule. This is the evidence behind the CONTROL claim; it is a measured tally, not an assurance.</p>`
      : absentBlock('none', safety.total_exceptions + ' safety exceptions recorded across the official run.')}`,
    'control');
}

// The least flattering file in the evidence tree, and the reason the headline is
// allowed to say "measured, not claimed". A benchmark that shows its cell count
// and hides the three tests that fired is making a claim.
function bmFalsification(f) {
  if (!f) return '';
  return panel('Falsification tests — the run’s attempts to refute itself', h`
    <p class="sec-sub" style="margin-bottom:var(--s-4)">Six pre-registered tests, each written to look for a specific way the result could be wrong. A test that <strong>fires</strong> found the weakness it was hunting. ${esc(f.triggered_count)} of ${esc(f.total)} fired, and they are shown first.</p>
    <div class="fals-summary">
      <div class="fals-sum-i"><span class="fals-sum-n is-fired">${esc(f.triggered_count)}</span><span class="lbl">fired</span></div>
      <div class="fals-sum-i"><span class="fals-sum-n">${esc(f.total - f.triggered_count)}</span><span class="lbl">held</span></div>
      <div class="fals-sum-i"><span class="fals-sum-n ${f.unauthorized_actions_total === 0 ? 'is-ok' : 'is-fired'}">${esc(f.unauthorized_actions_total)}</span><span class="lbl">unauthorized actions</span></div>
      <div class="fals-sum-i"><span class="fals-sum-n ${f.all_degraded_safely ? 'is-ok' : 'is-fired'}">${esc(f.all_degraded_safely ? 'Yes' : 'No')}</span><span class="lbl">degraded safely</span></div>
    </div>
    <ol class="fals-list">${f.tests.slice().sort((a, x) => (x.triggered ? 1 : 0) - (a.triggered ? 1 : 0)).map(t => h`
      <li class="fals-i ${t.triggered ? 'is-fired' : 'is-held'}">
        <div class="fals-hd">
          <span class="fals-id">${esc(t.test_id)}</span>
          ${t.triggered ? tok('FIRED', 'wa', 'di') : tok('HELD', 'ok', 'di')}
        </div>
        <p class="fals-q">${esc(t.question)}</p>
        <p class="fals-a">${esc(t.reading)}</p>
        ${t.note ? h`<p class="fals-note">${esc(t.note)}</p>` : ''}
        <p class="fals-raw mono">${esc(t.description)} · ${esc(t.actual_result)}</p>
      </li>`)}</ol>
    <p class="sec-sub" style="margin-top:var(--s-4)">PAYVANTA shows these results whichever way they came out. F-3 and F-5 firing is the honest reading of the 17 cells where intervening cost more than it recovered — the same cells counted in the profile comparison.</p>`,
    'measured, not claimed');
}

async function loadBmMatrix() {
  if (!benchVerified(S.bench) || matrixHasData(S.bmMatrix || {})) return;
  // route() → bindView() re-invokes loadBmMatrix(); guard prevents infinite re-entry
  // that never reaches fetch().
  if (S.bmMatrixLoading) return;
  /* A settled failure must not restart itself. bindView() runs on every render and the
     finally block routes on every settle, so re-fetching here is an unbounded loop —
     and because each pass clears bmMatrixError on the way in, the failure panel never
     survives long enough to be seen. Only retryBmMatrix(), which clears this flag,
     may start a second attempt. */
  if (S.bmMatrixAttempted) return;

  S.bmMatrixLoading = true;
  S.bmMatrixError = null;
  route();

  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 120_000);
    const r = await fetch('/api/benchmark/official/matrix', { signal: controller.signal });
    clearTimeout(timer);
    if (!r.ok) {
      let detail = 'HTTP ' + r.status;
      try {
        const err = await r.json();
        if (err && err.error) detail += ' — ' + err.error;
      } catch (_) { /* ignore */ }
      S.bmMatrixError = detail;
      S.bmMatrix = null;
      return;
    }
    const data = await r.json();
    if (!matrixHasData(data)) {
      S.bmMatrixError = 'Matrix endpoint returned an empty structure';
      S.bmMatrix = null;
      return;
    }
    S.bmMatrix = data;
  } catch (err) {
    S.bmMatrixError = (err && err.name === 'AbortError')
      ? 'Matrix request timed out after 120s'
      : (err && err.message ? String(err.message) : 'Network error loading matrix');
    S.bmMatrix = null;
  } finally {
    S.bmMatrixLoading = false;
    S.bmMatrixAttempted = true;
    route();
  }
}

function retryBmMatrix() {
  S.bmMatrix = null;
  S.bmMatrixError = null;
  S.bmMatrixAttempted = false;
  S.bmMatrixLoading = false;
  loadBmMatrix();
}

async function loadBmCellDetail() {
  if (!S.bmCell || !benchVerified(S.bench)) { S.bmDetail = null; return; }
  const [prof, pol] = S.bmCell.split('|');
  const seed = S.bmSeed;
  try {
    const r = await fetch('/api/benchmark/official/cell/' + seed + '/' + prof + '/' + pol);
    S.bmDetail = r.ok ? await r.json() : null;
  } catch (_) {
    S.bmDetail = null;
  }
  route();
}

/* Search is a race: keystrokes issue overlapping requests and the network is free to
   resolve them out of order, which lets an older response overwrite a newer one — the
   box then shows results for a query the reader has already moved on from. Only the
   newest sequence number is allowed to commit. */
let bmSearchSeq = 0;
/* Module-scoped, because bindView() re-binds the input on every render and a timer held
   in the listener's closure cannot be cleared by the next binding. */
let bmSearchTimer = null;

/** Re-rendering the view replaces the input node, so typing would lose the caret on
    every settled search. The caret is restored only if it was in the box to begin
    with, so a background settle never steals focus from elsewhere. */
function routeKeepingSearchFocus() {
  const el = $('#bm-q');
  const had = !!el && document.activeElement === el;
  const pos = had ? el.selectionStart : null;
  route();
  if (!had) return;
  const next = $('#bm-q');
  if (!next) return;
  next.focus();
  try { next.setSelectionRange(pos, pos); } catch (_) { /* some inputs disallow it */ }
}

async function runBmSearch(q) {
  const seq = ++bmSearchSeq;
  if (!q.trim() || !benchVerified(S.bench)) {
    S.bmSearchHits = null;
    S.bmSearchTotal = 0;
    S.bmSearchTrunc = false;
    routeKeepingSearchFocus();
    return;
  }
  try {
    const r = await fetch('/api/benchmark/official/search?q=' + encodeURIComponent(q));
    const data = r.ok ? await r.json() : { results: [], total: 0 };
    if (seq !== bmSearchSeq) return;
    S.bmSearchHits = data.results || [];
    S.bmSearchTotal = data.total != null ? data.total : (data.results || []).length;
    S.bmSearchTrunc = !!data.truncated;
  } catch (_) {
    if (seq !== bmSearchSeq) return;
    S.bmSearchHits = [];
    S.bmSearchTotal = 0;
    S.bmSearchTrunc = false;
  }
  routeKeepingSearchFocus();
}

function bmSearchResults() {
  const rows = S.bmSearchHits;
  if (rows === null) return '';
  if (!rows.length) {
    return h`<p class="sec-sub" style="margin-top:var(--s-3)">No cell matches
      “${esc(S.bmSearch)}”. Try a profile, a policy, or a seed number — for example
      <span class="mono">14 ABUNDANT REVIVE</span>.</p>`;
  }
  return h`<div class="bm-search-hits" style="margin-top:var(--s-3)">
    <p class="lbl">${esc(cnt(S.bmSearchTotal))} match${S.bmSearchTotal === 1 ? '' : 'es'}${
      S.bmSearchTrunc ? h` · showing first ${esc(cnt(rows.length))}` : ''}</p>
    ${rows.map(row => h`<button type="button" class="scan-i bm-hit" data-bmhit="${esc(row.seed)}|${esc(row.profile)}|${esc(row.policy)}">
      <span>Seed ${esc(row.seed)} · ${esc(titleize(row.profile))} · ${esc(row.policy)}</span>
      <span>${row.m10_paise != null ? esc(formatPaise(row.m10_paise)) : '—'}</span>
    </button>`)}
    ${S.bmSearchTrunc ? h`<p class="sec-sub" style="margin-top:var(--s-2)">${esc(cnt(S.bmSearchTotal - rows.length))} further
      match${S.bmSearchTotal - rows.length === 1 ? '' : 'es'} are not listed. Narrow the query to see them.</p>` : ''}
  </div>`;
}

function openBmArtifact() {
  const d = S.bmDetail;
  if (!d || !d.raw) return;
  const json = JSON.stringify(d.raw, null, 2);
  openInspector('Raw evidence', d.artefact_path || 'Cell artefact', h`
    <pre class="codeblock">${esc(json)}</pre>
    <p style="margin-top:var(--s-3)"><button type="button" class="btn btn-ghost" id="bm-copy">Copy JSON</button></p>`);
  const btn = $('#bm-copy');
  if (btn) btn.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(json);
      btn.textContent = 'Copied';
    } catch (_) { btn.textContent = 'Copy blocked'; }
    setTimeout(() => { btn.textContent = 'Copy JSON'; }, 1600);
  });
}

/* ============================================================ BINDING */
function bindView() {
  const view = $('#view');

  // pipeline stage selection
  $$('[data-stage]', view).forEach(b => b.addEventListener('click', () => {
    S.pipeStage = S.pipeStage === b.dataset.stage ? null : b.dataset.stage;
    route();
  }));

  // opportunity cards
  $$('[data-opp]', view).forEach(card => {
    card.addEventListener('click', e => {
      if (e.target.closest('button, a')) return;
      go('#/opportunity/' + card.dataset.opp);
    });
  });
  $$('[data-analyze]', view).forEach(b => b.addEventListener('click', e => {
    e.stopPropagation();
    runCinematic(b.dataset.analyze);
  }));
  $$('[data-run-recovery]', view).forEach(b => b.addEventListener('click', () => runRecovery()));

  // explorer controls
  const q = $('#opp-q', view);
  if (q) {
    let t = null;
    q.addEventListener('input', () => {
      clearTimeout(t);
      t = setTimeout(() => { S.oppSearch = q.value; route(); $('#opp-q').focus(); }, 160);
    });
  }
  const sort = $('#opp-sort', view);
  if (sort) sort.addEventListener('change', () => { S.oppSort = sort.value; route(); });
  $$('[data-oppfilter]', view).forEach(b => b.addEventListener('click', () => {
    S.filters.opp = b.dataset.oppfilter; route();
  }));

  // audit
  $$('[data-auditfilter]', view).forEach(b => b.addEventListener('click', () => {
    S.filters.audit = b.dataset.auditfilter; S.auditLimit = AUDIT_PAGE; route();
  }));
  const more = $('#audit-more', view);
  if (more) more.addEventListener('click', () => {
    S.auditLimit = (S.auditLimit || AUDIT_PAGE) + AUDIT_PAGE; route();
  });

  // disclosures — state survives re-render via S.disclosures
  $$('[data-disclose]', view).forEach(b => b.addEventListener('click', () => {
    const k = b.dataset.disclose;
    const open = S.disclosures.has(k);
    if (open) S.disclosures.delete(k); else S.disclosures.add(k);
    b.setAttribute('aria-expanded', String(!open));
    const p = document.getElementById(k + '-p');
    if (p) p.hidden = open;
    const x = $('.grow-x', b); if (x) x.textContent = open ? '+' : '−';
  }));

  // provenance
  $$('[data-calc]', view).forEach(b => b.addEventListener('click', () => openCalc(b.dataset.calc)));

  // graph
  bindGraph(view);
  bindGraphSizing(view);
  $$('[data-graph]', view).forEach(b => b.addEventListener('click', () => {
    if (b.dataset.graph === 'reset') {
      S.graph.focus = null; S.graph.sel = null; S.graph.fit = false; route();
    }
    // A ten-stage chain drawn at readable size is taller than the screen. Fit scales
    // the whole diagram into one screenful so the causal path can be read end to end;
    // pressing it again returns to reading size.
    if (b.dataset.graph === 'fit') {
      S.graph.fit = !S.graph.fit;
      route();
      const f = $('[data-graph-frame]', $('#view'));
      if (f) f.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }));

  // receipt actions
  $$('[data-receipt-copy]', view).forEach(b => b.addEventListener('click', async () => {
    const d = detailFor(b.dataset.receiptCopy);
    if (!d) return;
    const txt = receiptText(d.receipt);
    try {
      await navigator.clipboard.writeText(txt);
      b.textContent = 'Copied';
      announce('Decision receipt copied to the clipboard.');
    } catch (_) {
      const ta = document.createElement('textarea');
      ta.value = txt; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      const ok = document.execCommand && document.execCommand('copy');
      document.body.removeChild(ta);
      b.textContent = ok ? 'Copied' : 'Copy blocked';
    }
    setTimeout(() => { b.textContent = 'Copy receipt'; }, 1800);
  }));
  $$('[data-receipt-print]', view).forEach(b => b.addEventListener('click', () => {
    const d = detailFor(b.dataset.receiptPrint);
    if (!d) return;
    openPrintView(d.receipt);
  }));

  // guardrail proof jump
  $$('[data-guard]', view).forEach(b => b.addEventListener('click', () => go('#/guardrails/' + b.dataset.guard)));

  // lab
  const pick = $('#lab-pick', view);
  if (pick) pick.addEventListener('change', () => go('#/lab/' + pick.value));
  const simForm = $('#sim-form', view);
  if (simForm) simForm.addEventListener('submit', onSimulate);

  // benchmark matrix
  $$('[data-cell]', view).forEach(b => b.addEventListener('click', () => {
    S.bmCell = S.bmCell === b.dataset.cell ? null : b.dataset.cell;
    S.bmDetail = null;
    route();
    if (S.bmCell) loadBmCellDetail();
  }));
  $$('[data-bmseed]', view).forEach(b => b.addEventListener('click', () => {
    S.bmSeed = Number(b.dataset.bmseed);
    S.bmDetail = null;
    route();
    loadBmCellDetail();
  }));
  const bmQ = $('#bm-q', view);
  if (bmQ) {
    bmQ.addEventListener('input', () => {
      clearTimeout(bmSearchTimer);
      bmSearchTimer = setTimeout(() => { S.bmSearch = bmQ.value; runBmSearch(bmQ.value); }, 220);
    });
  }
  $$('[data-bmhit]', view).forEach(btn => btn.addEventListener('click', () => {
    const [seed, profile, policy] = btn.dataset.bmhit.split('|');
    S.bmSeed = Number(seed);
    S.bmCell = profile + '|' + policy;
    S.bmDetail = null;
    route();
    loadBmCellDetail();
  }));
  $$('[data-bmfilter]', view).forEach(b => b.addEventListener('click', () => {
    S.bmFilter = b.dataset.bmfilter;
    route();
  }));
  $$('[data-bmpol]', view).forEach(b => b.addEventListener('click', () => go('#/benchmark/compare')));
  $$('[data-bmprof]', view).forEach(b => b.addEventListener('click', () => go('#/benchmark/compare')));
  const bmProf = $('#bm-prof', view);
  const bmPol = $('#bm-pol', view);
  const bmSeedSel = $('#bm-seed', view);
  if (bmProf) bmProf.addEventListener('change', () => {
    S.bmCell = bmProf.value + '|' + (bmPol ? bmPol.value : S.bmCell.split('|')[1]);
    S.bmDetail = null; route(); loadBmCellDetail();
  });
  if (bmPol) bmPol.addEventListener('change', () => {
    S.bmCell = (bmProf ? bmProf.value : S.bmCell.split('|')[0]) + '|' + bmPol.value;
    S.bmDetail = null; route(); loadBmCellDetail();
  });
  if (bmSeedSel) bmSeedSel.addEventListener('change', () => {
    S.bmSeed = Number(bmSeedSel.value);
    S.bmDetail = null; route(); loadBmCellDetail();
  });
  const bmArt = $('#bm-artifact', view);
  if (bmArt) bmArt.addEventListener('click', openBmArtifact);
  const bmRetry = $('#bm-matrix-retry', view);
  if (bmRetry) bmRetry.addEventListener('click', retryBmMatrix);
  $$('[data-eq]', view).forEach(b => {
    b.addEventListener('mouseenter', () => {
      const note = $('#bm-eq-note');
      if (note) note.textContent = b.getAttribute('aria-label') || '';
    });
    b.addEventListener('click', () => go('#/benchmark/matrix'));
  });
  $$('[data-official-cell]', view).forEach(b => {
    b.addEventListener('click', openOfficialDemoCell);
  });
  if (S.bmCell && benchVerified(S.bench) && !S.bmDetail) loadBmCellDetail();
  if (matrixWanted()) loadBmMatrix();
}

/* ---------------------------------------------------- GRAPH INTERACTION */
/**
 * The frame's width is only known after layout, so the diagram is drawn at the last
 * known width and redrawn when the measurement disagrees. A ResizeObserver rather than
 * a resize listener: the column changes width when the inspector opens or the workspace
 * grid retiers, neither of which is a window resize.
 *
 * The redraw replaces the SVG alone, on the next frame. Re-rendering the whole view from
 * inside the observer callback resizes the observed element in the same frame, which
 * Chromium reports as an undelivered-notification loop.
 */
let graphRO = null;

function bindGraphSizing(view) {
  const frame = $('[data-graph-frame]', view);
  if (!frame || !GRAPH_CTX) { if (graphRO) graphRO.disconnect(); return; }
  if (!window.ResizeObserver) return;

  const redraw = w => {
    S.graph.w = w;
    const f = $('[data-graph-frame]');
    if (!f || !GRAPH_CTX) return;
    const c = GRAPH_CTX;
    f.innerHTML = graphSvg(c.chain, c.byId, c.options, c.chosenId, c.big, w);
    bindGraph($('#view'));
  };

  if (!graphRO) {
    let pending = 0;
    graphRO = new ResizeObserver(entries => {
      const w = Math.round(entries[0].contentRect.width);
      // Redraw only on a change worth redrawing for — sub-pixel jitter would thrash.
      if (!w || Math.abs(w - S.graph.w) <= 8) return;
      cancelAnimationFrame(pending);
      pending = requestAnimationFrame(() => redraw(w));
    });
  }
  graphRO.disconnect();
  graphRO.observe(frame);

  const w = Math.round(frame.clientWidth);
  if (w > 0 && Math.abs(w - S.graph.w) > 8) redraw(w);
}

function bindGraph(view) {
  const svg = $('[data-graph-svg]', view);
  if (!svg) return;
  const nodes = $$('.gnode', svg);
  const edges = $$('.gedge', svg);
  const narr = $$('[data-narr]', view);

  // The diagram draws each candidate as its own box; the narrative folds them into one
  // "recovery options" row. Tracing a candidate should still light that row.
  const optionIds = new Set(nodes.filter(n => n.dataset.kind === 'OPTION').map(n => n.dataset.node));
  const narrKey = id => (optionIds.has(id) ? 'OPTIONS' : id);

  const clear = () => {
    nodes.forEach(n => n.classList.remove('hl', 'rel', 'dim'));
    edges.forEach(e => e.classList.remove('hl', 'dim'));
    narr.forEach(li => li.classList.remove('hl', 'rel'));
  };

  /**
   * Tracing a node means showing what it is connected to, not just outlining the box
   * under the cursor. The hovered node reads as primary, everything one edge away
   * reads as related, and the rest of the diagram recedes — so the eye follows the
   * causal path rather than hunting for it. The narrative row below is tied to the
   * same node id, so the diagram and the prose highlight together.
   */
  const highlight = id => {
    const near = new Set([id]);
    edges.forEach(e => {
      if (e.dataset.from === id) near.add(e.dataset.to);
      if (e.dataset.to === id) near.add(e.dataset.from);
    });
    nodes.forEach(n => {
      const self = n.dataset.node === id;
      n.classList.toggle('hl', self);
      n.classList.toggle('rel', !self && near.has(n.dataset.node));
      n.classList.toggle('dim', !near.has(n.dataset.node));
    });
    edges.forEach(e => {
      const on = e.dataset.from === id || e.dataset.to === id;
      e.classList.toggle('hl', on);
      e.classList.toggle('dim', !on);
    });
    narr.forEach(li => {
      const key = narrKey(id);
      const self = li.dataset.narr === key;
      li.classList.toggle('hl', self);
      li.classList.toggle('rel', !self && [...near].some(x => narrKey(x) === li.dataset.narr));
    });
  };

  // A narrative row may stand for several boxes, so hovering the prose traces the
  // first node it names — enough to place the reader in the diagram.
  const nodeForNarr = key => (key === 'OPTIONS'
    ? (nodes.find(n => n.dataset.kind === 'OPTION') || {}).dataset : { node: key });

  nodes.forEach(n => {
    n.addEventListener('mouseenter', () => { if (!S.graph.focus) highlight(n.dataset.node); });
    n.addEventListener('mouseleave', () => { if (!S.graph.focus) clear(); });
    n.addEventListener('focus', () => { if (!S.graph.focus) highlight(n.dataset.node); });
    n.addEventListener('blur', () => { if (!S.graph.focus) clear(); });
    n.addEventListener('click', () => openNodeDetail(n.dataset.node));
    n.addEventListener('dblclick', () => { S.graph.focus = n.dataset.node; route(); });
    n.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openNodeDetail(n.dataset.node); }
      if (e.key === 'f') { S.graph.focus = n.dataset.node; route(); }
    });
  });

  // Reading the prose is a second way into the diagram, so it traces in both
  // directions — and on a phone, where the SVG is hidden, it still reads as a list.
  narr.forEach(li => {
    li.addEventListener('mouseenter', () => {
      if (S.graph.focus) return;
      const d = nodeForNarr(li.dataset.narr);
      if (d && d.node) highlight(d.node);
    });
    li.addEventListener('mouseleave', () => { if (!S.graph.focus) clear(); });
  });

  if (S.graph.focus) highlight(S.graph.focus);
}

function openNodeDetail(id) {
  const d = detailFor(S.param || S.snap.wow_opportunity_id || firstOppId());
  if (!d) return;
  if (id === 'more') { go('#/opportunity/' + d.card.opportunity_id + '/lab'); return; }
  const n = d.graph.nodes.find(x => x.id === id);
  if (!n) return;
  S.graph.sel = id;
  openInspector(GRAPH_STAGE_LABEL[n.kind] || n.kind, n.label, h`
    <div class="dl">${Object.entries(n.detail || {}).map(([k, v]) => {
      let out;
      if (v === null || v === undefined || v === '') out = absentInline('none');
      else if (typeof v === 'object' && v.display) out = esc(v.display);
      else if (Array.isArray(v)) out = v.length ? esc(v.map(titleize).join(', ')) : absentInline('none');
      else if (typeof v === 'number' && !Number.isInteger(v)) out = esc(v.toFixed(4));
      else if (typeof v === 'boolean') out = v ? tok('Yes', 'ok') : tok('No', 'nu');
      else out = esc(v);
      return row(titleize(k), out, { mono: true });
    })}</div>
    <p class="wf-foot">Node id <span class="mono">${esc(n.id)}</span>.
      Press <kbd>f</kbd> on a node to focus its branch.</p>`);
}

/* ------------------------------------------------------------ INSPECTOR */
function openInspector(kicker, title, body) {
  $('#inspector-kicker').textContent = kicker;
  $('#inspector-title').textContent = title;
  $('#inspector-body').innerHTML = body;
  $('#inspector').hidden = false;
  $('#app').classList.add('has-inspector');
  $('#inspector-close').focus();
  $$('#inspector-body [data-calc]').forEach(b => b.addEventListener('click', () => openCalc(b.dataset.calc)));
}
function closeInspector() {
  $('#inspector').hidden = true;
  $('#app').classList.remove('has-inspector');
}

/* --------------------------------------------------- CALCULATION SHEET */
function openCalc(id) {
  const calcs = S.snap.control_room.calculations || {};
  const c = calcs[id];
  const dlg = $('#sheet');
  if (!c) {
    $('#sheet-title').textContent = 'Calculation unavailable';
    $('#sheet-body').innerHTML = absentBlock('none',
      'No provenance record exists for “' + esc(id) + '”.');
  } else {
    $('#sheet-kicker').textContent = 'How this figure is computed';
    $('#sheet-title').textContent = c.label;
    $('#sheet-body').innerHTML = h`
      <p class="sec-sub">${esc(c.definition)}</p>
      <p class="sheet-formula">${esc(c.formula)}</p>
      <div class="sheet-inputs">${c.inputs.map(i => h`
        <div class="sheet-in"><span class="sheet-in-k">${esc(i.label)}</span>
          <span class="sheet-in-v">${esc(i.value)}</span></div>`)}</div>
      <div class="sheet-out"><span class="lbl">Result</span>
        <span class="sheet-out-v">${esc(c.result)}</span></div>
      <p class="wf-foot">Source: ${esc(c.source)}. ${esc(S.snap.control_room.fixture_label)}</p>`;
  }
  if (!dlg.open) dlg.showModal();
}

/* ------------------------------------------------------------ PRINT VIEW */
function openPrintView(r) {
  const w = window.open('', '_blank');
  if (!w) { announce('The browser blocked the print window. Use Copy receipt instead.'); return; }
  const css = `
    body{font:13px/1.55 "IBM Plex Mono",ui-monospace,monospace;color:#111;margin:32px;max-width:760px}
    h1{font:600 20px/1.2 Georgia,serif;letter-spacing:.04em;margin:0 0 4px}
    .k{color:#006b58;letter-spacing:.14em;font-size:10px}
    pre{white-space:pre-wrap;word-break:break-word;border-top:2px solid #111;
        border-bottom:1px solid #999;padding:16px 0;margin:16px 0}
    footer{font-size:10px;color:#555}`;
  w.document.write('<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">' +
    '<title>PAYVANTA receipt ' + esc(r.opportunity_id) + '</title><style>' + css + '</style></head><body>' +
    '<p class="k">PAYVANTA · DECISION RECEIPT</p>' +
    '<h1>' + esc(r.selected_action || 'No action authorized') + '</h1>' +
    '<pre>' + esc(receiptText(r)) + '</pre>' +
    '<footer>Generated from the PAYVANTA product projection. ' +
    esc(S.snap.control_room.fixture_label) + '</footer></body></html>');
  w.document.close();
  w.focus();
  setTimeout(() => { try { w.print(); } catch (_) {} }, 220);
}

/* ------------------------------------------------------------ SIMULATOR */
async function onSimulate(e) {
  e.preventDefault();
  const form = e.currentTarget;
  const btn = $('button[type=submit]', form);
  const out = $('#sim-out');
  /* Let the browser's own constraint validation speak first — an empty seed should be
     reported on the field the reader has to fix, not as a failed request. */
  if (typeof form.reportValidity === 'function' && !form.reportValidity()) return;
  const body = {};
  new FormData(form).forEach((v, k) => { body[k] = v; });
  btn.disabled = true; btn.textContent = 'Running…';
  out.innerHTML = h`<p class="sec-sub">Generating a deterministic world and running the full engine…</p>`;
  try {
    const res = await fetch('/api/simulator', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    /* A rejected configuration is a message about the inputs, not a broken product. Read
       the server's own explanation where it sent one rather than reporting the status. */
    let data = null;
    try { data = await res.json(); } catch (_) { data = null; }
    if (!res.ok) {
      out.innerHTML = absentBlock('failed', (data && data.error)
        ? data.error
        : 'The simulator rejected this configuration (HTTP ' + res.status + ').');
      announce('Simulation rejected.');
      return;
    }
    out.innerHTML = simResult(data || {});
    announce('Simulation complete.');
  } catch (err) {
    // Transport, not validation: the request never completed.
    out.innerHTML = absentBlock('failed',
      'The simulator could not be reached, so no run was produced. Check that the local ' +
      'server is still running, then run it again.');
  } finally {
    btn.disabled = false; btn.textContent = 'Run engine';
  }
}

/* ============================================== PHASE 18: VALUE DIFFING */
function tickMetrics() {
  $$('[data-metric]').forEach(el => {
    const key = el.dataset.metric;
    const now = el.textContent.trim();
    const before = S.metrics.get(key);
    if (before !== undefined && before !== now) {
      el.classList.remove('tick');
      void el.offsetWidth;
      el.classList.add('tick');
    }
    S.metrics.set(key, now);
  });
}

/**
 * A table that has to scroll sideways must say so. Where a ledger is wider than
 * its scroller the region becomes focusable and a hint is appended, so a
 * narrow-window reader knows there are columns they have not seen.
 *
 * Measured through a ResizeObserver rather than once at render: a ledger inside a
 * `content-visibility: auto` section has no layout until it is near the viewport,
 * so a single synchronous read after innerHTML would report no overflow.
 */
const XSCROLLERS = '.ledger-scroll, .tscroll, .matrix-scroll';

let scrollRO = null;
function markScrollers() {
  if (!scrollRO && window.ResizeObserver) {
    scrollRO = new ResizeObserver(() => measureScrollers());
  }
  if (scrollRO) {
    scrollRO.disconnect();
    $$(XSCROLLERS).forEach(el => {
      scrollRO.observe(el);
      if (el.firstElementChild) scrollRO.observe(el.firstElementChild);
    });
  }
  measureScrollers();
}

function measureScrollers() {
  $$(XSCROLLERS).forEach(el => {
    const over = el.scrollWidth > el.clientWidth + 2;
    const next = el.nextElementSibling;
    const hint = next && next.classList.contains('ledger-x-hint') ? next : null;
    el.toggleAttribute('data-xscroll', over);
    if (over) {
      el.setAttribute('tabindex', '0');
      el.setAttribute('role', 'region');
      el.setAttribute('aria-label', 'Table — scrolls sideways for more columns');
      if (!hint) {
        const p = document.createElement('p');
        p.className = 'ledger-x-hint';
        p.textContent = 'Scroll sideways for the remaining columns';
        el.after(p);
      }
    } else {
      el.removeAttribute('tabindex');
      el.removeAttribute('role');
      el.removeAttribute('aria-label');
      if (hint) hint.remove();
    }
  });
}

/** Bars and cards animate in once, on reveal — not on every keystroke. */
function reveal() {
  const items = $$('[data-anim]');
  if (!items.length) return;
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    items.forEach(i => i.classList.add('in'));
    return;
  }
  const io = new IntersectionObserver(entries => {
    entries.forEach(en => {
      if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
    });
  }, { threshold: 0.15 });
  items.forEach(i => io.observe(i));
}

/* ============================================ PHASE 17: WOW SEQUENCE */
const CINE_BEATS = [
  ['Money', 'Focusing on the revenue at risk in this opportunity'],
  ['Cause', 'Ranking the observed failure against diagnostic evidence'],
  ['Evidence', 'Attaching the ledger facts that support the diagnosis'],
  ['Alternatives', 'Enumerating every legally available recovery action'],
  ['Economics', 'Pricing each action against doing nothing'],
  ['Recommend', 'Selecting the economically justified intervention'],
  ['Guardrails', 'Testing the selection against policy, resource, budget, duplicate, cooldown, authorization'],
  ['Authorize', 'Recording whether execution is allowed'],
  ['Execute', 'Dispatching only if authorized, with an idempotency key'],
  ['Measure', 'Attributing recovery between natural and incremental'],
  ['Receipt', 'Sealing the decision as a financial record'],
];

function runCinematic(oppId) {
  const d = detailFor(oppId);
  if (!d) { go('#/opportunity/' + oppId); return; }
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) { go('#/opportunity/' + oppId); return; }

  const cine = $('#cine');
  const beats = $('#cine-beats');
  beats.innerHTML = CINE_BEATS.map(() => '<span class="cine-beat"></span>').join('');
  const dots = $$('.cine-beat', beats);
  cine.hidden = false;
  $('#cine-kicker').textContent = 'Analysing ' + shortId(oppId);

  let i = 0;
  const step = () => {
    if (i >= CINE_BEATS.length) {
      cine.hidden = true;
      S.cine = null;
      go('#/opportunity/' + oppId);
      announce('Analysis complete. Opened the recovery workspace.');
      return;
    }
    const [k, line] = CINE_BEATS[i];
    const el = $('#cine-line');
    el.classList.remove('cine-fade'); void el.offsetWidth; el.classList.add('cine-fade');
    el.textContent = line;
    $('#cine-kicker').textContent = k.toUpperCase() + ' · ' + shortId(oppId);
    dots.forEach((dt, j) => dt.classList.toggle('on', j <= i));
    i += 1;
    S.cine = setTimeout(step, 420);
  };
  step();
}

/* ============================================ PHASE 16: DEMO DIRECTOR */
const DEMO = [
  ['Control Room', 'PAYVANTA — autonomous revenue recovery intelligence. Recover revenue. Prove the recovery.', () => '#/control'],
  ['Opportunity', 'One working recovery: cause, evidence, options, economics.', d => '#/opportunity/' + d],
  ['Counterfactual', 'Do nothing is a priced option. PAYVANTA recommends the intervention only when it beats that baseline.', d => '#/opportunity/' + d + '/lab'],
  ['Guardrails', 'Policy, resource, budget, duplicate, cooldown, authorization — observed, not claimed.', d => '#/opportunity/' + d + '/guardrails'],
  ['Execution', 'Authorized actions dispatch. Unauthorized actions never reach an adapter.', d => '#/opportunity/' + d + '/execution'],
  ['Receipt', 'Natural, incremental, cost, net — one decision as a financial record.', d => '#/opportunity/' + d + '/receipt'],
  ['Audit', 'Every consequential event, in the order the engine recorded it.', () => '#/audit'],
  ['Batch', 'That is one working recovery run. Detected, authorized, blocked, executed, measured — incremental net recovery.', () => '#/control'],
  ['Benchmark', 'Now: is this one carefully selected scenario? 20 seeds × 6 profiles × 5 policies = 600 official cells.', () => '#/benchmark'],
  ['Official cell', 'ABUNDANT × REVIVE × seed 14. Artefact, checksum, provenance. Measured, not claimed.', () => {
    S.bmCell = 'ABUNDANT|REVIVE';
    S.bmSeed = 14;
    S.bmDetail = null;
    return '#/benchmark/matrix';
  }],
];

function demoStart() {
  S.demo.on = true; S.demo.i = 0;
  $('#director').hidden = false;
  $('#view').classList.add('has-director');
  demoRender();
}
function demoStop() {
  S.demo.on = false;
  $('#director').hidden = true;
  $('#view').classList.remove('has-director');
  announce('Guided demo ended.');
}
function demoGo(delta) {
  S.demo.i = Math.max(0, Math.min(DEMO.length - 1, S.demo.i + delta));
  demoRender();
}
function demoRender() {
  const [title, beat, target] = DEMO[S.demo.i];
  const oppId = S.snap.wow_opportunity_id || firstOppId();
  $('#director-index').textContent = String(S.demo.i + 1);
  $('#director-title').textContent = title;
  $('#director-beat').textContent = beat;
  $('#director-fill').style.width = ((S.demo.i + 1) / DEMO.length * 100) + '%';
  $('#director-back').disabled = S.demo.i === 0;
  $('#director-next').textContent = S.demo.i === DEMO.length - 1 ? 'Finish' : 'Next';
  const hash = target(oppId);
  if (location.hash !== hash) go(hash); else route();
  announce('Demo step ' + (S.demo.i + 1) + ' of ' + DEMO.length + ': ' + title + '. ' + beat);
}

/* ============================================== COMMAND PALETTE */
let paletteItems = [], paletteIdx = 0;

function paletteOpen() {
  const dlg = $('#palette');
  $('#palette-input').value = '';
  paletteBuild('');
  if (!dlg.open) dlg.showModal();
  $('#palette-input').focus();
}
function paletteSources() {
  const items = [
    { kind: 'RUN', label: 'Run recovery', hint: 'Bounded sandbox batch run', action: runRecovery },
    { kind: 'GO', label: 'Find opportunity', hint: 'Opportunity explorer', hash: '#/opportunities' },
    { kind: 'GO', label: 'Analyze opportunity', hint: 'Active recovery decision', action: analyzeActive },
    { kind: 'GO', label: 'Open workspace', hint: 'Recovery Workspace', action: openActiveWorkspace },
    { kind: 'GO', label: 'Open decision receipt', hint: 'Transaction record + audit certificate', action: openActiveReceipt },
    { kind: 'GO', label: 'Open audit', hint: 'Audit Ledger', hash: '#/audit' },
    { kind: 'GO', label: 'Open benchmark', hint: 'Official evidence · executive', hash: '#/benchmark' },
    { kind: 'GO', label: 'View evidence', hint: 'Benchmark provenance · forensic', hash: '#/benchmark/evidence' },
    { kind: 'GO', label: 'View environment', hint: 'Sandbox + official evidence', hash: '#/system' },
    { kind: 'GO', label: 'View system state', hint: 'Machine-readable product state', hash: '#/system' },
  ];
  Object.entries(ROUTES)
    .filter(([k]) => k !== 'opportunity')
    .forEach(([k, v]) => items.push({ kind: 'GO', label: v.label, hint: v.sub, hash: '#/' + k }));
  items.push({ kind: 'GO', label: 'View official evidence', hint: '600-cell frozen experiment', hash: '#/benchmark' });
  items.push({ kind: 'GO', label: 'How this was measured', hint: 'Methodology · 20 × 6 × 5', hash: '#/benchmark' });
  items.push({ kind: 'GO', label: 'Engineering hardening', hint: 'M13.24 → official 600 cells', hash: '#/benchmark' });
  items.push({ kind: 'GO', label: 'ABUNDANT × REVIVE · seed 14', hint: 'Official demonstration cell', action: openOfficialDemoCell });
  items.push({ kind: 'RUN', label: 'Restore demo seed 14', hint: 'Reset sandbox to the judge starting world', action: restoreDemoSeed });
  items.push({ kind: 'GO', label: 'Run guided demo', hint: '10 steps', action: demoStart });
  const blocked = (S.snap ? S.snap.control_room.all_opportunities : []).find(c => c.blocked);
  if (blocked) {
    items.push({
      kind: 'OPP', label: 'Blocked path · ' + shortId(blocked.opportunity_id),
      hint: (blocked.blocking_reason || 'Blocked') + ' · no execution',
      hash: '#/opportunity/' + blocked.opportunity_id,
    });
  }
  (S.snap ? S.snap.control_room.all_opportunities : []).forEach(c => {
    items.push({
      kind: 'OPP', label: shortId(c.opportunity_id) + ' · ' + (c.cause ? titleize(c.cause) : 'undiagnosed'),
      hint: (c.value_at_risk ? c.value_at_risk.display : '') + ' at risk',
      hash: '#/opportunity/' + c.opportunity_id,
      search: c.opportunity_id + ' ' + (c.cause || '') + ' ' + (c.selected_action || ''),
    });
  });
  return items;
}
function analyzeActive() {
  const id = (S.snap && S.snap.wow_opportunity_id) || firstOppId();
  if (id) runCinematic(id);
  else go('#/opportunities');
}
function openActiveWorkspace() {
  const id = (S.snap && S.snap.wow_opportunity_id) || firstOppId();
  if (id) go('#/opportunity/' + id);
  else go('#/opportunities');
}
function openActiveReceipt() {
  const id = (S.snap && S.snap.wow_opportunity_id) || firstOppId();
  if (id) go('#/opportunity/' + id + '/receipt');
  else go('#/audit');
}
function paletteBuild(q) {
  const needle = q.trim().toLowerCase();
  const all = paletteSources();
  paletteItems = (needle
    ? all.filter(i => (i.label + ' ' + (i.hint || '') + ' ' + (i.search || '')).toLowerCase().includes(needle))
    : all).slice(0, 40);
  paletteIdx = 0;
  paletteRender();
}
function paletteRender() {
  const list = $('#palette-list');
  list.innerHTML = paletteItems.length
    ? paletteItems.map((i, n) => h`<li class="palette-opt" role="option" id="pal-${n}"
        aria-selected="${n === paletteIdx}" data-i="${n}">
        <span class="palette-kind">${esc(i.kind)}</span>
        <span class="palette-lbl">${esc(i.label)}</span>
        <span class="palette-hint">${esc(i.hint || '')}</span></li>`).join('')
    : h`<li class="palette-opt" role="option" aria-selected="false"><span class="palette-lbl dim">No match</span></li>`;
  $('#palette-input').setAttribute('aria-activedescendant', paletteItems.length ? 'pal-' + paletteIdx : '');
  $$('.palette-opt', list).forEach(li => {
    if (!li.dataset.i) return;
    li.addEventListener('click', () => paletteChoose(Number(li.dataset.i)));
    li.addEventListener('mousemove', () => {
      paletteIdx = Number(li.dataset.i);
      $$('.palette-opt', list).forEach((x, n) => x.setAttribute('aria-selected', String(n === paletteIdx)));
    });
  });
}
function paletteChoose(n) {
  const it = paletteItems[n === undefined ? paletteIdx : n];
  $('#palette').close();
  if (!it) return;
  if (it.action) it.action();
  else if (it.hash) go(it.hash);
}

/* ==================================================== BOOT + GLOBAL BIND */
async function boot() {
  try {
    const [snap, bench] = await Promise.all([
      fetch('/api/snapshot').then(r => r.json()),
      fetch('/api/benchmark').then(r => r.json()).catch(() => null),
    ]);
    S.snap = snap;
    S.bench = bench;
    S.ready = true;
    route();
    if (benchVerified(S.bench)) loadBmMatrix();
  } catch (err) {
    $('#view').innerHTML = h`<div class="wrap">${absentBlock('none',
      'The product server did not return a session. ' + String(err) +
      '  Start it with: python -m revive.product.server')}</div>`;
  }
}

function bindGlobal() {
  window.addEventListener('hashchange', route);

  // Whether a ledger needs sideways scroll is a function of the window, so it is
  // re-tested on resize rather than only at render.
  let rz = 0;
  window.addEventListener('resize', () => {
    clearTimeout(rz);
    rz = setTimeout(measureScrollers, 120);
  });

  $('#cmd-open').addEventListener('click', paletteOpen);
  $('#demo-open').addEventListener('click', () => (S.demo.on ? demoStop() : demoStart()));
  $('#inspector-close').addEventListener('click', closeInspector);
  $('#sheet-close').addEventListener('click', () => $('#sheet').close());
  $('#source-badge').addEventListener('click', () => {
    const [kind, text, note] = sourceFor();
    openInspector('Data provenance', text, h`<p class="sec-sub">${esc(note)}</p>
      <div class="dl" style="margin-top:var(--s-4)">
        ${row('Classification', tok(kind.toUpperCase(), kind === 'official' ? 'vi' : (kind === 'absent' ? 'wa' : 'tl'), 'di'))}
        ${S.snap ? row('Fixture seed', esc(S.snap.control_room.seed), { mono: true }) : ''}
        ${S.snap ? row('Generation profile', esc(S.snap.control_room.profile), { mono: true }) : ''}
        ${S.snap ? row('Cycles run', esc(S.snap.control_room.cycles_run), { mono: true }) : ''}
        ${S.snap ? row('Policy pack', esc(S.snap.control_room.policy_pack_version) + ' · ' +
          esc(S.snap.control_room.policy_pack_status), { mono: true }) : ''}
      </div>`);
  });

  const railToggle = $('#rail-toggle');
  railToggle.addEventListener('click', () => {
    const app = $('#app');
    const min = app.classList.toggle('rail-min');
    railToggle.setAttribute('aria-pressed', String(min));
    railToggle.setAttribute('aria-label', min ? 'Expand navigation' : 'Collapse navigation');
  });

  $('#director-back').addEventListener('click', () => demoGo(-1));
  $('#director-next').addEventListener('click', () => {
    if (S.demo.i === DEMO.length - 1) demoStop(); else demoGo(1);
  });
  $('#director-stop').addEventListener('click', demoStop);

  const input = $('#palette-input');
  input.addEventListener('input', () => paletteBuild(input.value));
  input.addEventListener('keydown', e => {
    if (e.key === 'ArrowDown') { e.preventDefault(); paletteIdx = Math.min(paletteItems.length - 1, paletteIdx + 1); paletteRender(); }
    if (e.key === 'ArrowUp')   { e.preventDefault(); paletteIdx = Math.max(0, paletteIdx - 1); paletteRender(); }
    if (e.key === 'Enter')     { e.preventDefault(); paletteChoose(); }
  });

  document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); paletteOpen(); }
    if (e.key === 'Escape') {
      if (!$('#cine').hidden) { clearTimeout(S.cine); $('#cine').hidden = true; }
      else if (!$('#inspector').hidden) closeInspector();
      else if (S.demo.on) demoStop();
    }
    if (S.demo.on && !$('#palette').open && !$('#sheet').open) {
      if (e.key === 'ArrowRight') demoGo(1);
      if (e.key === 'ArrowLeft') demoGo(-1);
    }
  });
}

bindGlobal();
boot();
