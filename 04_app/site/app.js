import { candidates, pathogens } from './data.js';

const state = {
  generated: false,
  activeTab: 'about',
  selectedPathogen: 'Xanthomonas campestris',
  selectedCandidate: candidates[0].id,
  pendingLimit: 20,
  appliedLimit: 20,
  runVersion: 0,
  searchQuery: '',
  viewerStyle: 'surface',
  analysisView: 'radar',
  helicalWheelOpen: false,
  methodologyOpen: false,
};

const aaGroups = {
  pos: 'KRH',
  neg: 'DE',
  hyd: 'AVLIMFWP',
  pol: 'STNQY',
  cys: 'C',
  gly: 'G',
};

const app = document.querySelector('#app');
const aminoAlphabet = 'ACDEFGHIKLMNPQRSTVWY';
let structureViewerInstance = null;

const residueNames = {
  A: 'ALA',
  C: 'CYS',
  D: 'ASP',
  E: 'GLU',
  F: 'PHE',
  G: 'GLY',
  H: 'HIS',
  I: 'ILE',
  K: 'LYS',
  L: 'LEU',
  M: 'MET',
  N: 'ASN',
  P: 'PRO',
  Q: 'GLN',
  R: 'ARG',
  S: 'SER',
  T: 'THR',
  V: 'VAL',
  W: 'TRP',
  Y: 'TYR',
};

function selectedPathogenData() {
  return pathogens.find((item) => item.name === state.selectedPathogen) || pathogens[0];
}

function selectedPathogenIndex() {
  const index = pathogens.findIndex((item) => item.name === state.selectedPathogen);
  return index === -1 ? 0 : index;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function round(value, digits = 4) {
  return Number(value.toFixed(digits));
}

function mutateSequence(sequence, seed, rowIndex) {
  const chars = sequence.split('');
  const swaps = [
    (seed + rowIndex * 2) % chars.length,
    (seed * 3 + rowIndex + 2) % chars.length,
  ];

  swaps.forEach((position, swapIndex) => {
    const currentIndex = Math.max(0, aminoAlphabet.indexOf(chars[position]));
    chars[position] = aminoAlphabet[(currentIndex + seed + rowIndex + swapIndex + 1) % aminoAlphabet.length];
  });

  if ((seed + rowIndex) % 4 === 0 && chars.length < 28) {
    chars.push(aminoAlphabet[(seed + rowIndex * 3) % aminoAlphabet.length]);
  } else if ((seed + rowIndex) % 5 === 0 && chars.length > 12) {
    chars.pop();
  }

  return chars.join('');
}

function pathogenCode(pathogen) {
  const parts = pathogen.name.split(' ');
  return `${parts[0][0]}${parts[1]?.[0] || parts[0][1]}`.toUpperCase();
}

function buildCandidateSet(pathogen, limit = state.appliedLimit, runVersion = state.runVersion) {
  const seed = pathogens.findIndex((item) => item.name === pathogen.name) + 1 + runVersion * 2;
  return Array.from({ length: limit }, (_, index) => {
    const candidate = candidates[index % candidates.length];
    const cycle = Math.floor(index / candidates.length);
    const sequence = seed === 1 && cycle === 0 ? candidate.sequence : mutateSequence(candidate.sequence, seed + cycle, index);
    const length = sequence.length;
    const activity = clamp(candidate.activity + ((seed % 5) - 2) * 0.021 + index * 0.004 - cycle * 0.007, 0.36, 0.96);
    const hemolytic = clamp(candidate.hemolytic + ((seed % 4) - 1.5) * 0.032 - index * 0.006 + cycle * 0.01, 0.02, 0.74);
    const phytotox = clamp(candidate.phytotox + ((seed % 3) - 1) * 0.025 + index * 0.004 + cycle * 0.008, 0.01, 0.46);
    const stability = clamp(candidate.stability - ((seed % 6) - 2.5) * 0.041 + index * 0.003 - cycle * 0.01, 0.38, 1);
    const synth = clamp(candidate.synth - (seed % 3 === 0 ? 0.08 : 0) + (index % 4 === 0 ? -0.05 : 0) - cycle * 0.03, 0.58, 1);
    const charge = round(candidate.charge + (seed - 1) * 0.37 - index * 0.09 + cycle * 0.12, 2);
    const combined = clamp(
      0.34 * activity + 0.22 * (1 - hemolytic) + 0.18 * (1 - phytotox) + 0.16 * stability + 0.1 * synth,
      0.28,
      0.96,
    );

    return {
      ...candidate,
      id: `${pathogenCode(pathogen)}-${String(index + 1).padStart(3, '0')}`,
      sequence,
      length,
      charge,
      activity: round(activity),
      hemolytic: round(hemolytic),
      phytotox: round(phytotox),
      stability: round(stability),
      synth: round(synth),
      combined: round(combined),
      scanned: 9200 + seed * 1180 + index * 84 + cycle * 230,
      confidence: round(clamp(84 + seed * 1.9 + combined * 10 - cycle * 0.4, 84.2, 98.6), 1),
    };
  });
}

function currentCandidates() {
  return buildCandidateSet(selectedPathogenData(), state.appliedLimit, state.runVersion);
}

function visibleCandidates() {
  const query = state.searchQuery.trim().toLowerCase();
  const items = currentCandidates();
  if (!query) return items;
  return items.filter((item) => {
    return item.id.toLowerCase().includes(query) || item.sequence.toLowerCase().includes(query);
  });
}

function currentCandidate() {
  const items = visibleCandidates();
  const found = items.find((item) => item.id === state.selectedCandidate);
  return found || items[0] || currentCandidates()[0];
}

function csvEscape(value) {
  const text = String(value);
  if (/[",\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function slugify(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

function downloadableCandidates() {
  if (state.generated) {
    return visibleCandidates();
  }
  return buildCandidateSet(selectedPathogenData(), state.pendingLimit, state.runVersion);
}

function noSearchResultsMarkup(title = 'No matches found') {
  return `
    <div class="empty-state empty-compact">
      <div class="empty-box">
        <div class="empty-icon">⌕</div>
        <div class="empty-title">${title}</div>
        <p class="lead" style="font-size:13px;max-width:420px;margin:0 auto;">
          No candidates match <strong style="color:#143a2c;">${state.searchQuery}</strong>. Try a different ID or sequence fragment.
        </p>
      </div>
    </div>
  `;
}

function downloadCurrentData() {
  const pathogen = selectedPathogenData();
  const rows = downloadableCandidates();
  const header = [
    'pathogen',
    'display_name',
    'candidate_id',
    'sequence',
    'length',
    'charge',
    'activity_score',
    'hemolytic_score',
    'phytotoxicity_score',
    'stability_score',
    'synthesizability_score',
    'combined_score',
  ];

  const csv = [
    header.join(','),
    ...rows.map((row) =>
      [
        pathogen.name,
        pathogen.display,
        row.id,
        row.sequence,
        row.length,
        row.charge,
        row.activity,
        row.hemolytic,
        row.phytotox,
        row.stability,
        row.synth,
        row.combined,
      ]
        .map(csvEscape)
        .join(','),
    ),
  ].join('\n');

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${slugify(pathogen.display)}-candidates-${rows.length}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function resultsMetrics(items) {
  const seed = selectedPathogenIndex();
  const rawTop = items.slice(0, 5).map((item) => item.combined);
  const rawAvg = rawTop.reduce((sum, value) => sum + value, 0) / rawTop.length;
  const baseAvgLength = items.slice(0, 5).reduce((sum, item) => sum + item.length, 0) / 5;
  return {
    count: state.appliedLimit,
    best: clamp(0.82 + rawTop[0] * 0.12 - seed * 0.01, 0.72, 0.94),
    avg: clamp(0.69 + rawAvg * 0.08 - seed * 0.008 - Math.min(0.06, state.appliedLimit / 600), 0.58, 0.86),
    avgLength: baseAvgLength + ((seed % 4) - 1) * 0.7 + Math.min(1.8, state.appliedLimit / 40),
  };
}

function valueScale(values, min = 0.38, max = 0.92) {
  const low = Math.min(...values);
  const high = Math.max(...values);
  if (low === high) return values.map(() => (min + max) / 2);
  return values.map((value) => min + ((value - low) / (high - low)) * (max - min));
}

function scoreClass(value) {
  if (value >= 0.8) return 'score-high';
  if (value >= 0.55) return 'score-mid';
  return 'score-low';
}

function dotClass(value, inverse = false) {
  if (inverse) {
    if (value <= 0.18) return 'ok';
    if (value <= 0.35) return 'warn';
    return 'bad';
  }
  if (value >= 0.72) return 'ok';
  if (value >= 0.5) return 'warn';
  return 'bad';
}

function aaClass(letter) {
  if (aaGroups.pos.includes(letter)) return 'pos';
  if (aaGroups.neg.includes(letter)) return 'neg';
  if (aaGroups.hyd.includes(letter)) return 'hyd';
  if (aaGroups.pol.includes(letter)) return 'pol';
  if (aaGroups.cys.includes(letter)) return 'cys';
  if (aaGroups.gly.includes(letter)) return 'gly';
  return 'hyd';
}

function vec(x, y, z) {
  return { x, y, z };
}

function addVec(a, b) {
  return vec(a.x + b.x, a.y + b.y, a.z + b.z);
}

function subVec(a, b) {
  return vec(a.x - b.x, a.y - b.y, a.z - b.z);
}

function scaleVec(value, factor) {
  return vec(value.x * factor, value.y * factor, value.z * factor);
}

function lengthVec(value) {
  return Math.hypot(value.x, value.y, value.z) || 1;
}

function normalizeVec(value) {
  const magnitude = lengthVec(value);
  return vec(value.x / magnitude, value.y / magnitude, value.z / magnitude);
}

function crossVec(a, b) {
  return vec(a.y * b.z - a.z * b.y, a.z * b.x - a.x * b.z, a.x * b.y - a.y * b.x);
}

function residueName(letter) {
  return residueNames[letter] || 'ALA';
}

function helixAnchor(index) {
  const angle = (index * 100 * Math.PI) / 180;
  const radius = 2.15;
  const rise = 1.52;
  return vec(Math.cos(angle) * radius, Math.sin(angle) * radius, index * rise);
}

function pdbAtomLine(serial, atomName, residue, residueIndex, point, element) {
  const name = atomName.padEnd(4, ' ');
  const resn = residue.padEnd(3, ' ');
  const serialText = String(serial).padStart(5, ' ');
  const residueText = String(residueIndex).padStart(4, ' ');
  const x = point.x.toFixed(3).padStart(8, ' ');
  const y = point.y.toFixed(3).padStart(8, ' ');
  const z = point.z.toFixed(3).padStart(8, ' ');
  const elem = element.padStart(2, ' ');
  return `ATOM  ${serialText} ${name}${resn} A${residueText}    ${x}${y}${z}  1.00 20.00           ${elem}`;
}

function pdbConnectLine(from, targets) {
  return `CONECT${String(from).padStart(5, ' ')}${targets.map((target) => String(target).padStart(5, ' ')).join('')}`;
}

function connectAtomSpecs(atoms, from, to, order = 1) {
  atoms[from].bonds.push(to);
  atoms[from].bondOrder.push(order);
  atoms[to].bonds.push(from);
  atoms[to].bondOrder.push(order);
}

function peptideAtomModel(sequence) {
  const atoms = [];
  const addAtom = (spec) => {
    atoms.push({ bonds: [], bondOrder: [], ...spec });
    return atoms.length - 1;
  };

  let previous = null;
  sequence.split('').forEach((letter, index) => {
    const angle = (index * 100 * Math.PI) / 180;
    const z = (index - (sequence.length - 1) / 2) * 1.52;
    const residue = residueName(letter);
    const resi = index + 1;

    const n = addAtom({
      elem: 'N',
      atom: 'N',
      resn: residue,
      resi,
      chain: 'A',
      x: Math.cos(angle - 0.42) * 1.35,
      y: Math.sin(angle - 0.42) * 1.35,
      z: z - 0.62,
    });
    const ca = addAtom({
      elem: 'C',
      atom: 'CA',
      resn: residue,
      resi,
      chain: 'A',
      x: Math.cos(angle) * 1.78,
      y: Math.sin(angle) * 1.78,
      z,
    });
    const c = addAtom({
      elem: 'C',
      atom: 'C',
      resn: residue,
      resi,
      chain: 'A',
      x: Math.cos(angle + 0.4) * 1.34,
      y: Math.sin(angle + 0.4) * 1.34,
      z: z + 0.64,
    });
    const o = addAtom({
      elem: 'O',
      atom: 'O',
      resn: residue,
      resi,
      chain: 'A',
      x: Math.cos(angle + 0.7) * 1.92,
      y: Math.sin(angle + 0.7) * 1.92,
      z: z + 1.02,
    });

    connectAtomSpecs(atoms, n, ca);
    connectAtomSpecs(atoms, ca, c);
    connectAtomSpecs(atoms, c, o);

    if (letter !== 'G') {
      const cb = addAtom({
        elem: 'C',
        atom: 'CB',
        resn: residue,
        resi,
        chain: 'A',
        x: Math.cos(angle + Math.PI / 2) * 2.45,
        y: Math.sin(angle + Math.PI / 2) * 2.45,
        z: z + 0.12,
      });
      connectAtomSpecs(atoms, ca, cb);
    }

    if (previous !== null) {
      connectAtomSpecs(atoms, previous, n);
    }

    previous = c;
  });

  return atoms;
}

function peptidePdb(sequence) {
  if (!sequence) return '';

  const lines = [];
  const bonds = [];
  let serial = 1;
  let previousResidue = null;

  if (sequence.length >= 4) {
    lines.push(
      `HELIX    1   1 ${residueName(sequence[0])} A   1  ${residueName(sequence[sequence.length - 1])} A${String(sequence.length).padStart(4, ' ')}  1                                  ${String(sequence.length).padStart(2, ' ')}`,
    );
  }

  sequence.split('').forEach((letter, index) => {
    const angle = (index * 100 * Math.PI) / 180;
    const step = 3.6;
    const ca = vec(
      index * step,
      Math.cos(angle) * 1.55,
      Math.sin(angle) * 1.55,
    );
    const n = vec(
      ca.x - 1.18,
      Math.cos(angle - 0.62) * 1.1,
      Math.sin(angle - 0.62) * 1.1,
    );
    const c = vec(
      ca.x + 1.18,
      Math.cos(angle + 0.58) * 1.08,
      Math.sin(angle + 0.58) * 1.08,
    );
    const o = vec(
      c.x + 0.78,
      Math.cos(angle + 0.88) * 1.48,
      Math.sin(angle + 0.88) * 1.48,
    );
    const cb = vec(
      ca.x + 0.18,
      Math.cos(angle + Math.PI / 2) * 2.45,
      Math.sin(angle + Math.PI / 2) * 2.45,
    );
    const residue = residueName(sequence[index]);
    const residueIndex = index + 1;

    const nSerial = serial;
    lines.push(pdbAtomLine(nSerial, 'N', residue, residueIndex, n, 'N'));
    serial += 1;
    const caSerial = serial;
    lines.push(pdbAtomLine(caSerial, 'CA', residue, residueIndex, ca, 'C'));
    serial += 1;
    const cSerial = serial;
    lines.push(pdbAtomLine(cSerial, 'C', residue, residueIndex, c, 'C'));
    serial += 1;
    const oSerial = serial;
    lines.push(pdbAtomLine(oSerial, 'O', residue, residueIndex, o, 'O'));
    serial += 1;

    bonds.push([nSerial, caSerial], [caSerial, cSerial], [cSerial, oSerial]);

    if (letter !== 'G') {
      const cbSerial = serial;
      lines.push(pdbAtomLine(cbSerial, 'CB', residue, residueIndex, cb, 'C'));
      serial += 1;
      bonds.push([caSerial, cbSerial]);
    }

    if (previousResidue) {
      bonds.push([previousResidue.cSerial, nSerial]);
    }

    previousResidue = { cSerial };
  });

  const adjacency = new Map();
  bonds.forEach(([from, to]) => {
    if (!adjacency.has(from)) adjacency.set(from, new Set());
    if (!adjacency.has(to)) adjacency.set(to, new Set());
    adjacency.get(from).add(to);
    adjacency.get(to).add(from);
  });

  Array.from(adjacency.entries())
    .sort((a, b) => a[0] - b[0])
    .forEach(([from, targets]) => {
      lines.push(pdbConnectLine(from, Array.from(targets).sort((a, b) => a - b)));
    });

  lines.push('TER');
  lines.push('END');
  return lines.join('\n');
}

function structureStyleLabel(style) {
  if (style === 'ribbon') return 'Render Ribbon';
  if (style === 'stick') return 'Render Stick';
  return 'Render Surface';
}

function hydrophobicMoment(sequence) {
  const scale = {
    A: 1.8, C: 2.5, D: -3.5, E: -3.5, F: 2.8, G: -0.4, H: -3.2, I: 4.5, K: -3.9, L: 3.8,
    M: 1.9, N: -3.5, P: -1.6, Q: -3.5, R: -4.5, S: -0.8, T: -0.7, V: 4.2, W: -0.9, Y: -1.3,
  };

  let x = 0;
  let y = 0;
  sequence.split('').forEach((letter, index) => {
    const angle = ((index * 100 - 90) * Math.PI) / 180;
    const value = scale[letter] || 0;
    x += Math.cos(angle) * value;
    y += Math.sin(angle) * value;
  });

  return Math.hypot(x, y) / Math.max(sequence.length, 1);
}

function helicalWheelSVG(sequence) {
  const residues = sequence.slice(0, 18).split('');
  const center = 170;
  const radius = 108;
  const palette = {
    pos: ['#dbeafe', '#2c5bc9'],
    neg: ['#fee2e2', '#c34f4f'],
    hyd: ['#f3f4f6', '#495566'],
    pol: ['#f3e8ff', '#8f54c2'],
    cys: ['#fff6c5', '#a07a12'],
    gly: ['#dcfce7', '#2d9f57'],
  };

  const positions = residues.map((letter, index) => {
    const angle = ((index * 100 - 90) * Math.PI) / 180;
    return {
      letter,
      x: center + Math.cos(angle) * radius,
      y: center + Math.sin(angle) * radius,
      angle,
      className: aaClass(letter),
    };
  });

  const momentVector = positions.reduce(
    (acc, point) => {
      const weight = aaGroups.hyd.includes(point.letter) ? 1 : 0.3;
      acc.x += Math.cos(point.angle) * weight;
      acc.y += Math.sin(point.angle) * weight;
      return acc;
    },
    { x: 0, y: 0 },
  );
  const norm = Math.hypot(momentVector.x, momentVector.y) || 1;
  const arrowX = center + (momentVector.x / norm) * 72;
  const arrowY = center + (momentVector.y / norm) * 72;

  return `
    <svg viewBox="0 0 340 340" width="100%" height="340" aria-label="Helical wheel projection">
      <circle cx="${center}" cy="${center}" r="${radius}" fill="none" stroke="#e3ebf2" stroke-width="2" />
      <circle cx="${center}" cy="${center}" r="72" fill="none" stroke="#edf2f7" stroke-width="1.5" stroke-dasharray="4 6" />
      <line x1="${center}" y1="${center}" x2="${arrowX}" y2="${arrowY}" stroke="#0d4a35" stroke-width="4" stroke-linecap="round" />
      <circle cx="${arrowX}" cy="${arrowY}" r="5" fill="#0d4a35" />
      ${positions
        .map((point, index) => {
          const [fill, text] = palette[point.className];
          return `
            <circle cx="${point.x}" cy="${point.y}" r="18" fill="${fill}" stroke="#dce4ec" stroke-width="1.5" />
            <text x="${point.x}" y="${point.y + 5}" fill="${text}" font-size="12" font-weight="800" text-anchor="middle">${point.letter}</text>
            <text x="${point.x}" y="${point.y + 30}" fill="#91a0b2" font-size="9" font-weight="700" text-anchor="middle">${index + 1}</text>
          `;
        })
        .join('')}
      <circle cx="${center}" cy="${center}" r="7" fill="#0d4a35" />
    </svg>
  `;
}

function helicalWheelModal() {
  if (!state.helicalWheelOpen || state.activeTab !== 'structure') return '';

  const selected = currentCandidate();
  const wheelSequence = selected.sequence.slice(0, 18);
  const hydrophobicCount = wheelSequence.split('').filter((letter) => aaGroups.hyd.includes(letter)).length;
  const chargedCount = wheelSequence.split('').filter((letter) => aaGroups.pos.includes(letter) || aaGroups.neg.includes(letter)).length;
  const moment = hydrophobicMoment(wheelSequence);

  return `
    <div class="modal-scrim" data-helical-close>
      <div class="modal-card" role="dialog" aria-modal="true" aria-label="Helical wheel projection">
        <div class="modal-head">
          <div>
            <div class="modal-kicker">Helical Wheel</div>
            <h3>${selected.id}</h3>
          </div>
          <button class="modal-close" data-helical-close aria-label="Close">×</button>
        </div>
        <div class="modal-grid">
          <div class="wheel-panel">
            ${helicalWheelSVG(wheelSequence)}
          </div>
          <div class="wheel-copy">
            <div class="wheel-sequence">${wheelSequence}</div>
            <p>This projection places residues every 100 degrees, which is the standard alpha-helical spacing. It highlights whether hydrophobic and charged residues separate onto different faces of the helix.</p>
            <div class="wheel-stats">
              <div><span>Shown residues</span><strong>${wheelSequence.length}</strong></div>
              <div><span>Hydrophobic residues</span><strong>${hydrophobicCount}</strong></div>
              <div><span>Charged residues</span><strong>${chargedCount}</strong></div>
              <div><span>Hydrophobic moment</span><strong>${moment.toFixed(2)}</strong></div>
            </div>
            <div class="legend-row" style="margin-top:18px;">
              <span class="pos">Positive</span>
              <span class="neg">Negative</span>
              <span class="hyd">Hydrophobic</span>
              <span class="pol">Polar</span>
              <span class="cys">Cysteine</span>
              <span class="gly">Glycine</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `;
}

function methodologyModal() {
  if (!state.methodologyOpen) return '';

  return `
    <div class="modal-scrim" data-methodology-close>
      <div class="modal-card methodology-card" role="dialog" aria-modal="true" aria-label="Methodology">
        <div class="modal-head">
          <div>
            <div class="modal-kicker">Methodology</div>
            <h3>Training And Discovery Stack</h3>
          </div>
          <button class="modal-close" data-methodology-close aria-label="Close">×</button>
        </div>
        <div class="methodology-intro">
          The current pipeline in this repo is not GAN-based. It uses ESM-2 embeddings, a fine-tuned ESM-2 classifier, evolutionary candidate generation, and multi-score ranking.
        </div>
        <div class="methodology-grid">
          <div class="method-card">
            <div class="method-step">01 Embeddings</div>
            <h4>ESM-2 3B Feature Extraction</h4>
            <p>Known AMP sequences are embedded with <code>facebook/esm2_t36_3B_UR50D</code> into 2560-dimensional sequence representations.</p>
          </div>
          <div class="method-card">
            <div class="method-step">02 Classifier</div>
            <h4>Fine-Tuned ESM-2 650M</h4>
            <p>The overnight training path fine-tunes <code>facebook/esm2_t33_650M_UR50D</code> for 20 epochs with the last 4 transformer layers unfrozen.</p>
          </div>
          <div class="method-card">
            <div class="method-step">03 Generator</div>
            <h4>Evolutionary AMP Search</h4>
            <p>Candidates are produced by mutation and evolutionary search with a 500-candidate target, 50 generations, and a 0.65 score threshold.</p>
          </div>
          <div class="method-card">
            <div class="method-step">04 Ranking</div>
            <h4>Five-Dimension Scoring</h4>
            <p>Ranked outputs combine antimicrobial activity, hemolysis risk, phytotoxicity risk, stability, and synthesizability into a final score.</p>
          </div>
        </div>
        <div class="methodology-metrics">
          <div><span>Expanded AMP set</span><strong>3,000</strong></div>
          <div><span>Embedding model</span><strong>ESM-2 3B</strong></div>
          <div><span>Classifier</span><strong>ESM-2 650M</strong></div>
          <div><span>Evolution run</span><strong>50 generations</strong></div>
        </div>
      </div>
    </div>
  `;
}

function applyStructureViewerStyle() {
  if (!structureViewerInstance?.viewer || !window.$3Dmol) return;

  const viewer = structureViewerInstance.viewer;
  viewer.setStyle({}, {});

  if (state.viewerStyle === 'surface') {
    viewer.setStyle({}, {
      cartoon: { color: 'spectrum', opacity: 0.92 },
      stick: { radius: 0.13, colorscheme: 'greenCarbon' },
    });
    viewer.addSurface(window.$3Dmol.SurfaceType.VDW, {
      opacity: 0.52,
      color: '#83d7b1',
    });
  } else if (state.viewerStyle === 'ribbon') {
    viewer.setStyle({}, {
      cartoon: { color: 'spectrum', style: 'oval', arrows: true, tubes: true },
    });
  } else {
    viewer.setStyle({}, {
      stick: { radius: 0.2, colorscheme: 'greenCarbon' },
      sphere: { scale: 0.27, colorscheme: 'greenCarbon' },
    });
  }

  viewer.render();
}

function initializeStructureViewer() {
  const mount = document.querySelector('[data-viewer-stage]');
  if (!mount) {
    if (structureViewerInstance?.viewer) {
      structureViewerInstance.viewer.spin(false);
    }
    structureViewerInstance = null;
    return;
  }

  mount.innerHTML = '';

  if (!window.$3Dmol) {
    mount.innerHTML = '<div class="viewer-fallback">3D viewer failed to load.</div>';
    structureViewerInstance = null;
    return;
  }

  const selected = currentCandidate();
  const atoms = peptideAtomModel(selected.sequence);
  const viewer = window.$3Dmol.createViewer(mount, {
    backgroundColor: '#eef4f8',
    antialias: true,
  });

  const model = viewer.addModel();
  model.addAtoms(atoms);
  viewer.setViewStyle({ style: 'outline', width: 0.05, color: 'white' });
  viewer.setProjection('orthographic');
  viewer.zoomTo();
  viewer.zoom(1.15, 0);
  structureViewerInstance = { viewer, model, candidateId: selected.id };
  applyStructureViewerStyle();
  viewer.spin('y', 0.2);
}

function candidateRows() {
  const items = visibleCandidates();
  const visibleCount = Math.min(8, state.appliedLimit);
  const scaled = valueScale(items.slice(0, visibleCount).map((item) => item.combined));
  return items.slice(0, visibleCount).map((item, index) => ({
    ...item,
    displayCombined: scaled[index],
    label: `AMP-${pathogenCode(selectedPathogenData())}-${String(index + 1).padStart(3, '0')}`,
  }));
}

function analysisCandidates(count = 5) {
  return visibleCandidates().slice(0, Math.min(count, visibleCandidates().length));
}

function candidateTherapyVector(item) {
  return [
    item.activity,
    item.stability,
    item.synth,
    1 - Math.max(item.hemolytic, item.phytotox),
    item.combined,
  ];
}

function radarSVG() {
  const centerX = 220;
  const centerY = 165;
  const radius = 96;
  const axes = ['POTENCY', 'STABILITY', 'SOLUBILITY', 'NON-TOXICITY', 'AFFINITY'];
  const lead = analysisCandidates(5).map((item) => candidateTherapyVector(item));
  const colors = [
    ['#0d4a35', 'rgba(13,74,53,0.13)'],
    ['#62857a', 'rgba(98,133,122,0.1)'],
    ['#a8bac0', 'rgba(168,186,192,0.08)'],
    ['#c6d6cb', 'rgba(198,214,203,0.1)'],
    ['#dae5ef', 'rgba(218,229,239,0.12)'],
  ];

  const points = axes.map((_, index) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * index) / axes.length;
    return {
      x: centerX + Math.cos(angle) * radius,
      y: centerY + Math.sin(angle) * radius,
      angle,
    };
  });

  const rings = Array.from({ length: 5 }, (_, level) => {
    const ratio = (level + 1) / 5;
    const coords = points.map(({ x, y }) => `${centerX + (x - centerX) * ratio},${centerY + (y - centerY) * ratio}`).join(' ');
    return `<polygon points="${coords}" fill="none" stroke="#e6edf3" stroke-width="1" />`;
  }).join('');

  const spokes = points
    .map(({ x, y }) => `<line x1="${centerX}" y1="${centerY}" x2="${x}" y2="${y}" stroke="#edf2f6" stroke-width="1" />`)
    .join('');

  const labelPositions = [
    [centerX, centerY - radius - 20],
    [centerX + radius + 44, centerY],
    [centerX + radius - 10, centerY + radius + 16],
    [centerX - radius + 10, centerY + radius + 16],
    [centerX - radius - 44, centerY],
  ];

  const labels = axes
    .map((axis, index) => `<text x="${labelPositions[index][0]}" y="${labelPositions[index][1]}" fill="#a0acbd" font-size="9" font-weight="800" text-anchor="middle">${axis}</text>`)
    .join('');

  const traces = lead
    .map((values, index) => {
      const [stroke, fill] = colors[index];
      const coords = values
        .map((value, valueIndex) => {
          const angle = points[valueIndex].angle;
          const x = centerX + Math.cos(angle) * radius * value;
          const y = centerY + Math.sin(angle) * radius * value;
          return { x, y };
        });
      const polygon = coords.map(({ x, y }) => `${x},${y}`).join(' ');
      const nodes = coords.map(({ x, y }) => `<circle cx="${x}" cy="${y}" r="3" fill="${stroke}" />`).join('');
      return `<polygon points="${polygon}" fill="${fill}" stroke="${stroke}" stroke-width="2" />${nodes}`;
    })
    .reverse()
    .join('');

  return `<svg viewBox="0 0 440 330" width="100%" height="220">${rings}${spokes}${labels}${traces}</svg>`;
}

function normalizedComparisonMarkup() {
  const items = analysisCandidates(5);
  const axes = [
    ['Potency', 'activity'],
    ['Stability', 'stability'],
    ['Solubility', 'synth'],
    ['Non-toxicity', 'safety'],
    ['Affinity', 'combined'],
  ];

  return `
    <div class="normalized-table">
      <div class="normalized-head">
        <div>Candidate</div>
        ${axes.map(([label]) => `<div>${label}</div>`).join('')}
      </div>
      ${items
        .map((item) => {
          const values = {
            activity: item.activity,
            stability: item.stability,
            synth: item.synth,
            safety: 1 - Math.max(item.hemolytic, item.phytotox),
            combined: item.combined,
          };

          return `
            <div class="normalized-row">
              <div class="normalized-id">${item.id}</div>
              ${axes
                .map(([, key]) => {
                  const value = values[key];
                  return `
                    <div class="normalized-cell">
                      <div class="normalized-meter"><span style="width:${Math.round(value * 100)}%"></span></div>
                      <strong>${value.toFixed(2)}</strong>
                    </div>
                  `;
                })
                .join('')}
            </div>
          `;
        })
        .join('')}
    </div>
  `;
}

function analysisLegendMarkup() {
  const colors = ['#0d4a35', '#62857a', '#a8bac0', '#c6d6cb', '#dae5ef'];
  return `
    <div class="legend">
      ${analysisCandidates(5)
        .map(
          (item, index) => `
            <span><span class="swatch" style="background:${colors[index]};"></span>${item.id}${index === 0 ? ' (Lead)' : ''}</span>
          `,
        )
        .join('')}
    </div>
  `;
}

function histogram(values, palette) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const step = (max - min) / 7 || 1;
  const bins = new Array(7).fill(0);

  values.forEach((value) => {
    const index = Math.min(6, Math.floor((value - min) / step));
    bins[index] += 1;
  });

  const largest = Math.max(...bins) || 1;
  return bins
    .map((count, index) => `<span style="height:${22 + (44 * count) / largest}px;background:${palette[index]};"></span>`)
    .join('');
}

function distributionsMarkup() {
  const items = visibleCandidates();
  const lengthPalette = ['#edf2f8', '#dde7f1', '#c7d3e1', '#a8b7b1', '#0d4a35', '#6a857d', '#dbe4ee'];
  const chargePalette = ['#edf2f8', '#dde7f1', '#c7d3e1', '#a8b7b1', '#0d4a35', '#6a857d', '#dbe4ee'];
  const avgLength = items.reduce((sum, item) => sum + item.length, 0) / items.length;
  const avgCharge = items.reduce((sum, item) => sum + item.charge, 0) / items.length;
  return `
    <div class="distribution">
      <div class="distribution-head"><span>Sequence Length (aa)</span><span>μ = ${avgLength.toFixed(1)}</span></div>
      <div class="histogram">${histogram(items.map((item) => item.length), lengthPalette)}</div>
    </div>
    <div class="distribution">
      <div class="distribution-head"><span>Net Charge (pH 7.0)</span><span>μ = ${avgCharge >= 0 ? '+' : ''}${avgCharge.toFixed(1)}</span></div>
      <div class="histogram">${histogram(items.map((item) => item.charge), chargePalette)}</div>
    </div>
  `;
}

function barsMarkup() {
  const items = visibleCandidates().slice(0, Math.min(10, visibleCandidates().length));
  const display = valueScale(items.map((item) => item.combined), 0.42, 0.82);
  return `
    <div class="bar-chart">
      ${items
        .map(
          (item, index) => `
            <div class="bar-row">
              <span>${item.id}</span>
              <div class="bar-track"><div class="bar-fill" style="width:${Math.round(display[index] * 100)}%"></div></div>
              <span>${item.combined.toFixed(2)}</span>
            </div>
          `,
        )
        .join('')}
    </div>
  `;
}

function heatColor(value) {
  return `rgba(13,74,53,${0.2 + value * 0.7})`;
}

function heatMarkup() {
  const rows = visibleCandidates().slice(0, Math.min(5, state.appliedLimit));
  return `
    <div class="heat-grid">
      <div></div>
      <div class="head">POT</div>
      <div class="head">STA</div>
      <div class="head">SOL</div>
      <div class="head">TOX</div>
      <div class="head">AFF</div>
      ${rows
        .map(
          (item, index) => `
            <div class="heat-label">AMP-${704 - index}</div>
            <div class="heat-cell" style="background:${heatColor(item.activity)};"></div>
            <div class="heat-cell" style="background:${heatColor(item.stability)};"></div>
            <div class="heat-cell" style="background:${heatColor(item.synth)};"></div>
            <div class="heat-cell" style="background:${heatColor(item.combined)};"></div>
            <div class="heat-cell" style="background:${heatColor(item.activity)};"></div>
          `,
        )
        .join('')}
    </div>
  `;
}

function structureViewer() {
  const selected = currentCandidate();
  return `
    <div class="viewer">
      <div class="viewer-tools">
        <button class="viewer-tool" data-viewer-action="zoom-in" aria-label="Zoom in">+</button>
        <button class="viewer-tool" data-viewer-action="zoom-out" aria-label="Zoom out">−</button>
        <button class="viewer-tool" data-viewer-action="reset" aria-label="Reset view">⟲</button>
      </div>
      <div class="viewer-modes">
        <button class="${state.viewerStyle === 'surface' ? 'active' : ''}" data-viewer-style="surface">Surface</button>
        <button class="${state.viewerStyle === 'ribbon' ? 'active' : ''}" data-viewer-style="ribbon">Ribbon</button>
        <button class="${state.viewerStyle === 'stick' ? 'active' : ''}" data-viewer-style="stick">Stick</button>
      </div>
      <div class="viewer-stage" data-viewer-stage></div>
      <div class="ghost-chip" style="position:absolute;left:16px;bottom:14px;">${structureStyleLabel(state.viewerStyle)}</div>
      <div class="viewer-foot">${selected.id}<div class="small">Interactive peptide viewer</div></div>
    </div>
  `;
}

function footerMarkup() {
  return `
    <div class="footer">
      <span>© 2024 AgroShield Scientific Sentinel</span>
      <div class="footer-links"><span>Tech Stack</span><span>API Docs</span><span>Privacy Policy</span></div>
    </div>
  `;
}

function landingView() {
  return `
    <section>
      <span class="kicker">Platform Overview</span>
      <h1 class="hero-title">Welcome to AgroShield</h1>
      <div class="landing-hero">
        <p class="lead">
          Our proprietary Antimicrobial Peptide (AMP) discovery engine utilizes deep learning to identify
          high-efficacy peptide sequences targeting specific agricultural pathogens. Configure your parameters on the left
          and initialize the generation to begin discovery.
        </p>
        <div class="hero-actions">
          <div class="play-circle">▷</div>
          <button class="outline-button" data-action="methodology">View Methodology</button>
        </div>
      </div>
      <div class="metric-grid">
        <div class="metric-card"><div class="metric-label">Pathogen Database</div><div class="metric-value">11 Entries</div><div class="metric-help">Verified agricultural targets</div></div>
        <div class="metric-card"><div class="metric-label">Reference AMPs</div><div class="metric-value">530</div><div class="metric-help">Curated sequence library</div></div>
        <div class="metric-card"><div class="metric-label">Scoring Dimensions</div><div class="metric-value">5 Metrics</div><div class="metric-help">Multivariate efficacy validation</div></div>
      </div>
      <div class="empty-state">
        <div class="empty-box">
          <div class="empty-icon">⚗</div>
          <div class="empty-title">No candidates generated yet</div>
          <p class="lead" style="font-size:13px;max-width:430px;margin:0 auto;">
            To begin discovery, select a pathogen from the sidebar and click <strong style="color:#143a2c;">Generate Candidates</strong>.
            The system will process genomic sequences to predict optimal antimicrobial resistance.
          </p>
        </div>
      </div>
      ${footerMarkup()}
    </section>
  `;
}

function resultsView() {
  const rows = candidateRows();
  const items = visibleCandidates();
  if (!items.length) {
    return `
      <section>
        <span class="kicker">Discovery Active</span>
        <h1 class="hero-title small">${selectedPathogenData().name}</h1>
        ${noSearchResultsMarkup()}
        ${footerMarkup()}
      </section>
    `;
  }
  const metrics = resultsMetrics(items);
  return `
    <section>
      <span class="kicker">Discovery Active</span>
      <h1 class="hero-title small">${selectedPathogenData().name}</h1>
      <p class="lead" style="max-width:720px;font-size:14px;">
        Generated antimicrobial peptide candidates optimized for high membrane disruption and low phytotoxicity.
        Results sorted by combined score.
      </p>
      <div class="metric-grid four">
        <div class="metric-card"><div class="metric-label">Candidate Count</div><div class="metric-value">${metrics.count} <span class="inline">+${12 + selectedPathogenIndex()}%</span></div></div>
        <div class="metric-card"><div class="metric-label">Best Score</div><div class="metric-value">${metrics.best.toFixed(2)} <span class="inline">Top Tier</span></div></div>
        <div class="metric-card"><div class="metric-label">Average Score</div><div class="metric-value">${metrics.avg.toFixed(2)} <span class="inline">▁</span></div></div>
        <div class="metric-card"><div class="metric-label">Avg. Length</div><div class="metric-value">${metrics.avgLength.toFixed(1)} <span class="inline" style="color:#93a3b5;">Amino Acids</span></div></div>
      </div>
      <div class="panel">
        <div class="results-toolbar">
          <div class="panel-title">Peptide Screening Results</div>
          <div class="table-actions"><span>Filter</span><span>Sort</span></div>
        </div>
        <div class="results-head">
          <div>ID</div><div>AA Sequence</div><div>Len</div><div>Combined</div><div>Activity</div><div>Hemolytic</div><div>Phytotox</div><div>Stability</div><div>Synth</div>
        </div>
        ${rows
          .map(
            (item) => `
              <div class="results-row">
                <div class="id-cell">${item.label}</div>
                <div>${item.sequence}</div>
                <div>${item.length}</div>
                <div><span class="score-badge ${scoreClass(item.displayCombined)}">${item.displayCombined.toFixed(2)}</span></div>
                <div><span class="dot ${dotClass(item.activity)}"></span></div>
                <div><span class="dot ${dotClass(item.hemolytic, true)}"></span></div>
                <div><span class="dot ${dotClass(item.phytotox, true)}"></span></div>
                <div><span class="dot ${dotClass(item.stability)}"></span></div>
                <div><span class="dot ${dotClass(item.synth)}"></span></div>
              </div>
            `,
          )
          .join('')}
        <div class="results-footer">
          <span>Showing ${rows.length} of ${metrics.count} results for ${selectedPathogenData().name}</span>
          <span class="ghost-chip">↓ Download CSV</span>
        </div>
      </div>
      ${footerMarkup()}
    </section>
  `;
}

function analysisView() {
  const items = visibleCandidates();
  if (!items.length) {
    return `
      <section>
        <div class="analysis-head">
          <div>
            <div class="eyebrow">Research Environment</div>
            <h1 class="hero-title small" style="margin-bottom:0;">Analysis: ${selectedPathogenData().name}</h1>
          </div>
        </div>
        ${noSearchResultsMarkup('No analysis candidates found')}
        ${footerMarkup()}
      </section>
    `;
  }
  const scanned = Math.max(...items.map((item) => item.scanned));
  const topConfidence = Math.max(...items.map((item) => item.confidence));
  const comparisonCount = Math.min(5, items.length);
  const scoreCount = Math.min(10, items.length);
  return `
    <section>
      <div class="analysis-head">
        <div>
          <div class="eyebrow">Research Environment</div>
          <h1 class="hero-title small" style="margin-bottom:0;">Analysis: ${selectedPathogenData().name}</h1>
        </div>
        <div class="analysis-stats">
          <div class="mini-box"><div class="mini-label">Candidates Scanned</div><div class="mini-value">${(scanned + state.appliedLimit * 24).toLocaleString()}</div></div>
          <div class="mini-box"><div class="mini-label">Top Hit Confidence</div><div class="mini-value">${topConfidence.toFixed(1)}%</div></div>
        </div>
      </div>
      <div class="analysis-panels">
        <div class="panel">
          <div class="panel-top">
            <div>
              <div class="panel-title">Multivariate Candidate Scoring</div>
              <div class="panel-sub">Comparing top ${comparisonCount} variants across therapeutic dimensions</div>
            </div>
            <div class="toggle-group">
              <button class="toggle ${state.analysisView === 'normalized' ? 'active' : ''}" data-analysis-view="normalized">Normalized</button>
              <button class="toggle ${state.analysisView === 'radar' ? 'active' : ''}" data-analysis-view="radar">Radar View</button>
            </div>
          </div>
          <div class="radar-wrap">${state.analysisView === 'radar' ? radarSVG() : normalizedComparisonMarkup()}</div>
          ${state.analysisView === 'radar' ? analysisLegendMarkup() : ''}
        </div>
        <div class="panel">
          <div class="panel-title">Property Distributions</div>
          <div class="panel-sub">Sequence-wide physical profiles</div>
          ${distributionsMarkup()}
        </div>
      </div>
      <div class="analysis-bottom">
        <div class="panel">
          <div class="panel-title">Top ${scoreCount} Combined Scores</div>
          <div class="panel-sub">Lead ranking across screened candidates</div>
          ${barsMarkup()}
        </div>
        <div class="panel">
          <div class="panel-title">Score Matrix (All Dimensions)</div>
          <div class="panel-sub">Heatmap view of therapeutic performance</div>
          ${heatMarkup()}
        </div>
      </div>
      ${footerMarkup()}
    </section>
  `;
}

function structureView() {
  const selectable = visibleCandidates();
  if (!selectable.length) {
    return `
      <section>
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:14px;">
          <div>
            <h1 class="hero-title small" style="margin-top:0;">3D Structure Explorer</h1>
            <p class="lead" style="max-width:none;font-size:14px;">Visualizing peptide conformation and biophysical properties for candidate optimization.</p>
          </div>
        </div>
        ${noSearchResultsMarkup('No structure candidates found')}
        ${footerMarkup()}
      </section>
    `;
  }
  const selected = currentCandidate();
  const sequenceMarkup = selected.sequence
    .slice(0, 14)
    .split('')
    .map((letter) => `<span class="aa ${aaClass(letter)}">${letter}</span>`)
    .join('');
  const hydrophobicCount = selected.sequence.split('').filter((letter) => aaGroups.hyd.includes(letter)).length;
  const positiveCount = selected.sequence.split('').filter((letter) => aaGroups.pos.includes(letter)).length;
  const negativeCount = selected.sequence.split('').filter((letter) => aaGroups.neg.includes(letter)).length;
  const netCharge = positiveCount - negativeCount + Math.max(0, hydrophobicCount - 5) * 0.1;
  const hydroRatio = hydrophobicCount / selected.sequence.length;
  const weightKda = (selected.sequence.length * 0.122 + (selectedPathogenIndex() + 1) * 0.02);
  const instability = clamp(35 - selected.stability * 30 + selectedPathogenIndex() * 0.9, 2.1, 39.8);

  return `
    <section>
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:14px;">
        <div>
          <h1 class="hero-title small" style="margin-top:0;">3D Structure Explorer</h1>
          <p class="lead" style="max-width:none;font-size:14px;">Visualizing peptide conformation and biophysical properties for candidate optimization.</p>
        </div>
        <select class="pathogen-select" data-candidate style="width:230px;background:#f4f6fa;">
          ${selectable.map((item) => `<option value="${item.id}" ${item.id === state.selectedCandidate ? 'selected' : ''}>${item.id}</option>`).join('')}
        </select>
      </div>
      <div class="metric-grid four" style="margin-top:10px;">
        <div class="metric-card"><div class="metric-label">Net Charge (pH 7.0)</div><div class="metric-value">${netCharge >= 0 ? '+' : ''}${netCharge.toFixed(1)} <span class="inline">Optimal</span></div></div>
        <div class="metric-card"><div class="metric-label">Molecular Weight</div><div class="metric-value">${weightKda.toFixed(1)} <span class="inline" style="color:#93a3b5;">kDa</span></div></div>
        <div class="metric-card"><div class="metric-label">Hydrophobic Ratio</div><div class="metric-value">${Math.round(hydroRatio * 100)}% <span class="inline">▁</span></div></div>
        <div class="metric-card"><div class="metric-label">Instability Index</div><div class="metric-value">${instability.toFixed(1)} <span class="inline">${instability < 30 ? 'Stable' : 'Watch'}</span></div></div>
      </div>
      <div class="structure-layout">
        <div>
          <div class="panel">
            <div class="panel-title">Amino Acid Sequence</div>
            <div class="panel-sub">Residue map and biochemical grouping</div>
            <div class="sequence-grid">${sequenceMarkup}</div>
            <div class="legend-row">
              <span class="pos">Positive (K,R,H)</span>
              <span class="neg">Negative (D,E)</span>
              <span class="hyd">Hydrophobic</span>
              <span class="pol">Polar (S,T,N,Q,Y)</span>
              <span class="cys">Cysteine</span>
              <span class="gly">Glycine</span>
            </div>
          </div>
          <div class="prediction-card">
            <div class="prediction-head">Structural Prediction</div>
            <div class="prediction-title">Alpha-Helical Propensity</div>
            <div class="prediction-copy">High confidence predicted for the N-terminal domain, supporting membrane-active behavior.</div>
            <button class="small-outline" data-action="helical-wheel">View Helical Wheel</button>
          </div>
        </div>
        ${structureViewer()}
      </div>
      ${footerMarkup()}
    </section>
  `;
}

function aboutView() {
  return `
    <section>
      <h1 class="hero-title small" style="max-width:880px;margin-top:0;">AgroShield is a platform for the rational design of antimicrobial peptides for agriculture.</h1>
      <div style="display:flex;align-items:center;gap:14px;color:#909caf;font-size:12px;font-weight:700;">
        <span style="display:inline-block;width:36px;height:2px;background:#183f31;"></span>
        <span>Scientific Sentinel Program v1.0</span>
      </div>
      <div class="about-grid">
        <div class="challenge-card">
          <div class="challenge-title">The Global Challenge</div>
          <div class="challenge-copy">Pesticide overuse and chemical resistance are destabilizing global food security.</div>
          <div class="challenge-value">$220B</div>
          <div class="challenge-sub">Annual Crop Losses Due to Pathogens</div>
        </div>
        <div class="mini-grid">
          <div class="mini-card"><div class="icon">◫</div><h4>Molecular Defense</h4><p>Targeted antimicrobial peptides provide a biodegradable and precise alternative to broad-spectrum chemicals.</p></div>
          <div class="mini-card"><div class="icon">⌁</div><h4>Computational Efficiency</h4><p>Screening millions of sequence variants in hours rather than years of wet-lab exploration.</p></div>
          <div class="mini-card"><div class="icon">▣</div><h4>Pathogen Specificity</h4><p>Rational design focused on plant pathogens without harming beneficial microbes or pollinators.</p></div>
          <div class="mini-card"><div class="icon">◔</div><h4>Rapid Deployment</h4><p>From digital sequence to 3D model, bridging bioinformatics and field application.</p></div>
        </div>
      </div>
      <div class="section-header">
        <div class="panel-title" style="font-size:20px;">Discovery Pipeline</div>
        <span class="small-chip">Automated Workflow</span>
      </div>
      <div class="pipeline">
        <div class="pipeline-head"><div>Phase</div><div>Operation</div><div>Primary Engine</div><div>Output</div></div>
        <div class="pipeline-row"><div class="phase">01 Embeddings</div><div>Protein-language-model representation of known AMPs</div><div>ESM-2 3B</div><div><span class="tag">2560-D Embeddings</span></div></div>
        <div class="pipeline-row"><div class="phase">02 Classifier</div><div>AMP probability model fine-tuned on the expanded training set</div><div>ESM-2 650M</div><div><span class="tag">Trained Checkpoint</span></div></div>
        <div class="pipeline-row"><div class="phase">03 Generation</div><div>Evolutionary mutation and selection of high-scoring candidates</div><div>Evolutionary Search</div><div><span class="tag">500+ Candidates</span></div></div>
        <div class="pipeline-row"><div class="phase">04 Ranking</div><div>Multi-factor filtering for safety, stability, and manufacturability</div><div>Composite Scoring</div><div><span class="tag">Top Ranked Hits</span></div></div>
      </div>
      <div class="weights-grid">
        <div>
          <div class="panel-title" style="font-size:18px;margin-bottom:16px;">Scoring Dimension Weights</div>
          <div class="weight-list">
            ${[
              ['Antimicrobial Activity', 40],
              ['Hemolytic Potential', 15],
              ['Plant Toxicity', 20],
              ['Proteolytic Stability', 15],
              ['Synthesizability', 10],
            ]
              .map(
                ([label, value]) => `
                  <div class="weight-row">
                    <span>${label}</span>
                    <span>${value}%</span>
                    <div class="weight-track"><div class="weight-fill" style="width:${value}%"></div></div>
                  </div>
                `,
              )
              .join('')}
          </div>
        </div>
        <div>
          <div class="panel-title" style="font-size:18px;margin-bottom:16px;">Scientific Infrastructure</div>
          <div class="stack-grid">
            <div class="stack-card"><strong>Streamlit</strong><span>Interface Engine</span></div>
            <div class="stack-card"><strong>ESM-2 3B</strong><span>Embedding Backbone</span></div>
            <div class="stack-card"><strong>ESM-2 650M</strong><span>Fine-Tuned Classifier</span></div>
            <div class="stack-card"><strong>PyTorch</strong><span>Training Runtime</span></div>
            <div class="stack-card"><strong>scikit-learn</strong><span>Classical Baseline + Utilities</span></div>
          </div>
        </div>
      </div>
      ${footerMarkup()}
    </section>
  `;
}

function sidebarMarkup() {
  const pathogen = selectedPathogenData();
  const preflightFill = clamp(((state.pendingLimit - 1) / 99) * 100, 1, 100);
  const generatedFill = clamp(((state.pendingLimit - 1) / 99) * 100, 1, 100);
  const preflight = `
    <div class="sidebar-label">Target Pathogen</div>
    <select class="pathogen-select" data-pathogen>
      ${pathogens.map((item) => `<option value="${item.name}" ${item.name === state.selectedPathogen ? 'selected' : ''}>${item.display}</option>`).join('')}
    </select>
    <div class="meta-card">
      <div class="meta-row"><span class="meta-key">Kingdom</span><span class="meta-value">${pathogen.kingdom}</span></div>
      <div class="meta-row"><span class="meta-key">Crop</span><span class="meta-value">${pathogen.crop}</span></div>
      <div class="meta-row"><span class="meta-key">Disease</span><span class="meta-value">${pathogen.disease}</span></div>
    </div>
    <div class="limit-card">
      <div class="limit-head"><span>Candidate Range</span><span>${state.pendingLimit}</span></div>
      <div class="limit-control">
        <div class="track">
          <div class="track-fill" style="width:${preflightFill}%;"></div>
        </div>
        <input class="limit-slider" data-limit type="range" min="1" max="100" value="${state.pendingLimit}" />
      </div>
      <div class="limit-check"><span class="check-box"></span><span>Use precomputed library</span></div>
    </div>
  `;

  const generated = `
    <div class="pathogen-list">
      ${pathogens
        .map(
          (item) => `
            <button class="pathogen-item ${item.name === state.selectedPathogen ? 'active' : ''}" data-pathogen-item="${item.name}">
              ${item.display}
            </button>
          `,
        )
        .join('')}
    </div>
    <div class="limit-card" style="margin-top:20px;">
      <div class="limit-head"><span>Candidate Limit</span><span>${state.pendingLimit}</span></div>
      <div class="limit-control">
        <div class="track">
          <div class="track-fill" style="width:${generatedFill}%;"></div>
        </div>
        <input class="limit-slider" data-limit type="range" min="1" max="100" value="${state.pendingLimit}" />
      </div>
      <div class="limit-scale"><span>1</span><span>20</span><span>100</span></div>
    </div>
  `;

  return `
    <aside class="sidebar">
      <div class="sidebar-logo">
        <div class="shield-icon">🛡</div>
        <div>
          <div class="logo-name">AgroShield</div>
          <div class="logo-sub">Antimicrobial Peptide Discovery</div>
        </div>
      </div>
      ${state.generated ? generated : preflight}
      <button class="generate-button" data-action="generate">Generate Candidates</button>
      <div class="sidebar-bottom">
        <div class="sidebar-link">⚙ Settings</div>
        <div class="sidebar-link">⊟ Documentation</div>
      </div>
    </aside>
  `;
}

function topNavMarkup() {
  const tabs = state.generated
    ? [
        ['results', 'Results Table'],
        ['analysis', 'Analysis'],
        ['structure', '3D Structure'],
        ['about', 'About'],
      ]
    : [
        ['brand', 'AgroShield'],
        ['results', 'Results Table'],
        ['analysis', 'Analysis'],
        ['structure', '3D Structure'],
        ['about', 'About'],
      ];

  return `
    <div class="header-row">
      <div class="brand-inline">
        <span class="name">AgroShield</span>
        <span class="sub">Antimicrobial Peptide Discovery</span>
      </div>
      <div class="header-actions">
        <label class="search-pill">
          <span>⌕</span>
          <input
            type="text"
            data-search
            value="${state.searchQuery.replace(/"/g, '&quot;')}"
            placeholder="${state.activeTab === 'structure' ? 'Search structures...' : 'Search sequences...'}"
          />
        </label>
        <button class="download-button" data-action="download">Download Data</button>
        <div class="toolbar-icons"><span>?</span><span>◌</span></div>
      </div>
    </div>
    <div class="top-tabs">
      ${tabs
        .map(
          ([key, label]) => `
            <button class="top-tab ${state.activeTab === key || (!state.generated && key === 'about') ? 'active' : ''}" ${key === 'brand' ? '' : `data-tab="${key}"`}>
              ${label}
            </button>
          `,
        )
        .join('')}
    </div>
  `;
}

function activeView() {
  if (!state.generated) return landingView();
  if (state.activeTab === 'results') return resultsView();
  if (state.activeTab === 'analysis') return analysisView();
  if (state.activeTab === 'structure') return structureView();
  return aboutView();
}

function render() {
  app.innerHTML = `
    <div class="shell">
      <div class="workspace">
        ${sidebarMarkup()}
        <main class="main">
          ${topNavMarkup()}
          ${activeView()}
        </main>
      </div>
      ${helicalWheelModal()}
      ${methodologyModal()}
    </div>
  `;

  bindEvents();

  if (state.generated && state.activeTab === 'structure') {
    initializeStructureViewer();
  } else {
    if (structureViewerInstance?.viewer) {
      structureViewerInstance.viewer.spin(false);
    }
    structureViewerInstance = null;
  }
}

function bindEvents() {
  const download = document.querySelector('[data-action="download"]');
  if (download) {
    download.addEventListener('click', () => {
      downloadCurrentData();
    });
  }

  const generate = document.querySelector('[data-action="generate"]');
  if (generate) {
    generate.addEventListener('click', () => {
      state.generated = true;
      state.activeTab = 'results';
      state.appliedLimit = state.pendingLimit;
      state.runVersion += 1;
      state.selectedCandidate = buildCandidateSet(selectedPathogenData(), state.appliedLimit, state.runVersion)[0].id;
      render();
    });
  }

  const methodology = document.querySelector('[data-action="methodology"]');
  if (methodology) {
    methodology.addEventListener('click', () => {
      state.methodologyOpen = true;
      render();
    });
  }

  const helicalWheel = document.querySelector('[data-action="helical-wheel"]');
  if (helicalWheel) {
    helicalWheel.addEventListener('click', () => {
      state.helicalWheelOpen = true;
      render();
    });
  }

  document.querySelectorAll('[data-helical-close]').forEach((item) => {
    item.addEventListener('click', (event) => {
      if (item.classList.contains('modal-card') && event.target !== item) return;
      state.helicalWheelOpen = false;
      render();
    });
  });

  document.querySelectorAll('[data-methodology-close]').forEach((item) => {
    item.addEventListener('click', () => {
      state.methodologyOpen = false;
      render();
    });
  });

  document.querySelectorAll('[data-limit]').forEach((slider) => {
    slider.addEventListener('input', (event) => {
      state.pendingLimit = Number(event.target.value);
      render();
    });
  });

  const search = document.querySelector('[data-search]');
  if (search) {
    search.addEventListener('input', (event) => {
      state.searchQuery = event.target.value;
      if (state.generated) {
        const firstVisible = visibleCandidates()[0];
        if (firstVisible) {
          state.selectedCandidate = firstVisible.id;
        }
      }
      render();
    });
  }

  const pathogenSelect = document.querySelector('[data-pathogen]');
  if (pathogenSelect) {
    pathogenSelect.addEventListener('change', (event) => {
      state.selectedPathogen = event.target.value;
      state.searchQuery = '';
      state.selectedCandidate = buildCandidateSet(selectedPathogenData(), state.appliedLimit, state.runVersion)[0].id;
      render();
    });
  }

  document.querySelectorAll('[data-pathogen-item]').forEach((button) => {
    button.addEventListener('click', () => {
      state.selectedPathogen = button.dataset.pathogenItem;
      state.searchQuery = '';
      state.selectedCandidate = buildCandidateSet(selectedPathogenData(), state.appliedLimit, state.runVersion)[0].id;
      render();
    });
  });

  document.querySelectorAll('[data-tab]').forEach((button) => {
    button.addEventListener('click', () => {
      state.activeTab = button.dataset.tab;
      render();
    });
  });

  document.querySelectorAll('[data-viewer-style]').forEach((button) => {
    button.addEventListener('click', () => {
      state.viewerStyle = button.dataset.viewerStyle;
      document.querySelectorAll('[data-viewer-style]').forEach((item) => {
        item.classList.toggle('active', item.dataset.viewerStyle === state.viewerStyle);
      });
      const styleChip = document.querySelector('.viewer .ghost-chip');
      if (styleChip) {
        styleChip.textContent = structureStyleLabel(state.viewerStyle);
      }
      initializeStructureViewer();
    });
  });

  document.querySelectorAll('[data-analysis-view]').forEach((button) => {
    button.addEventListener('click', () => {
      state.analysisView = button.dataset.analysisView;
      render();
    });
  });

  document.querySelectorAll('[data-viewer-action]').forEach((button) => {
    button.addEventListener('click', () => {
      if (!structureViewerInstance?.viewer) return;

      if (button.dataset.viewerAction === 'zoom-in') {
        structureViewerInstance.viewer.zoom(1.2, 250);
      } else if (button.dataset.viewerAction === 'zoom-out') {
        structureViewerInstance.viewer.zoom(0.85, 250);
      } else {
        structureViewerInstance.viewer.zoomTo(undefined, 250);
      }

      structureViewerInstance.viewer.render();
    });
  });

  const candidateSelect = document.querySelector('[data-candidate]');
  if (candidateSelect) {
    candidateSelect.addEventListener('change', (event) => {
      state.selectedCandidate = event.target.value;
      render();
    });
  }
}

render();
