const app = document.querySelector('#app');
const { gsap, ScrollTrigger, ScrollToPlugin, Observer } = window;

const engineCards = [
  {
    eyebrow: 'Curated AMP Datasets',
    title: 'Foundation Model Tuning',
    copy:
      'Protein-language modeling is anchored on curated antimicrobial peptide references so sequence intelligence starts from biologically relevant agricultural signal.',
    stat: '530 curated AMP references',
    visual: 'tuning',
  },
  {
    eyebrow: 'Embedding Analysis',
    title: 'Diversity-Preserving Search',
    copy:
      'Candidates are compared and clustered in embedding space to preserve novelty, suppress redundancy, and keep the shortlist biologically diverse.',
    stat: '841,132 generated variants',
    visual: 'embedding',
  },
  {
    eyebrow: 'Multi-Objective Filtering',
    title: 'Activity, Toxicity, Synthesis',
    copy:
      'The ranking layer prioritizes candidates across antimicrobial activity, hemolysis risk, phytotoxicity, stability, and synthesis feasibility.',
    stat: '5 ranking criteria',
    visual: 'ranking',
  },
];

function engineVisualMarkup(type) {
  if (type === 'tuning') {
    return `
      <div class="engine-visual engine-visual-tuning" aria-hidden="true">
        <div class="visual-stage">
          <span class="visual-label">Raw protein corpus</span>
          <span class="visual-bar visual-bar-wide"></span>
        </div>
        <div class="visual-stage">
          <span class="visual-label">Curated AMP set</span>
          <span class="visual-bar visual-bar-mid"></span>
        </div>
        <div class="visual-stage">
          <span class="visual-label">AgroShield-tuned model</span>
          <span class="visual-bar visual-bar-core"></span>
        </div>
      </div>
    `;
  }

  if (type === 'embedding') {
    return `
      <div class="engine-visual engine-visual-embedding" aria-hidden="true">
        <span class="cluster-node cluster-a"></span>
        <span class="cluster-node cluster-b"></span>
        <span class="cluster-node cluster-c"></span>
        <span class="cluster-node cluster-d"></span>
        <span class="cluster-node cluster-e is-selected"></span>
        <span class="cluster-node cluster-f"></span>
        <span class="cluster-node cluster-g"></span>
        <span class="cluster-node cluster-h"></span>
        <span class="cluster-node cluster-i"></span>
        <span class="cluster-node cluster-j is-selected"></span>
      </div>
    `;
  }

  return `
    <div class="engine-visual engine-visual-ranking" aria-hidden="true">
      <div class="criteria-row"><span>Activity</span><i style="--fill:0.92"></i></div>
      <div class="criteria-row"><span>Hemolysis</span><i style="--fill:0.24"></i></div>
      <div class="criteria-row"><span>Phyto</span><i style="--fill:0.31"></i></div>
      <div class="criteria-row"><span>Stability</span><i style="--fill:0.78"></i></div>
      <div class="criteria-row"><span>Synthesis</span><i style="--fill:0.69"></i></div>
    </div>
  `;
}

const metrics = [
  {
    value: '841,132',
    label: 'Generated sequence variants',
    copy: 'Candidate peptides produced by the generation pipeline before final prioritization and experimental triage.',
  },
  {
    value: '13',
    label: 'Shortlisted peptides',
    copy: 'Final candidates advanced into the current validation set after multi-objective scoring.',
  },
  {
    value: '530',
    label: 'Curated AMP references',
    copy: 'Reference antimicrobial peptides used to anchor the biological search space and model tuning.',
  },
];

const domains = [
  {
    name: 'Xanthomonas',
    type: 'Bacterial pressure',
    copy: 'High-value citrus and horticultural disease programs where sequence selectivity matters.',
  },
  {
    name: 'Pseudomonas',
    type: 'Bacterial pressure',
    copy: 'Programs targeting hard-to-manage foliar and systemic infection pathways in productive crops.',
  },
  {
    name: 'Fusarium',
    type: 'Fungal pressure',
    copy: 'A strategic domain for broad agricultural loss mitigation and resistant outbreak management.',
  },
  {
    name: 'Ralstonia',
    type: 'Bacterial pressure',
    copy: 'A vascular wilt target where prioritization quality and deployment precision are critical.',
  },
  {
    name: 'Botrytis',
    type: 'Fungal pressure',
    copy: 'Gray mold programs focused on precision bioactives instead of broad collateral chemistry.',
  },
  {
    name: 'Phytophthora',
    type: 'Oomycete pressure',
    copy: 'A domain that benefits from candidate diversity, scale-up planning, and manufacturing foresight.',
  },
];

const roadmap = [
  {
    phase: 'Phase 01',
    title: 'Computational Design',
    copy: 'Curate references, learn sequence-space structure, and define high-conviction candidate zones.',
  },
  {
    phase: 'Phase 02',
    title: 'Experimental Validation',
    copy: 'Move shortlisted peptides into expression, secretion, purification, cleavage, and activity testing workflows.',
  },
  {
    phase: 'Phase 03',
    title: 'Scaled Bioproduction',
    copy: 'Optimize secretion-forward expression systems designed for downstream processing and bioreactor readiness.',
  },
  {
    phase: 'Phase 04',
    title: 'Commercial Translation',
    copy: 'Advance pathogen-specific programs toward crop protection partnerships, pilot studies, and field-driven product development.',
  },
];

const marketSegments = [
  {
    eyebrow: 'Customer',
    title: 'Crop Protection Companies',
    copy: 'Pipeline expansion for bacterial, fungal, and oomycete programs that need novel bioactive starting points beyond conventional chemistry.',
  },
  {
    eyebrow: 'Customer',
    title: 'Agri-Biotech Labs',
    copy: 'A faster way to move from broad sequence-space exploration to a small set of candidates worth synthesis and assay budget.',
  },
  {
    eyebrow: 'Deployment',
    title: 'Scale-Up Partners',
    copy: 'Candidates are prioritized with secretion, purification, stability, and synthesis constraints in mind before wet-lab handoff.',
  },
];

function particleMarkup() {
  const points = [
    [86, 22, 34], [79, 28, 18], [90, 35, 22], [74, 38, 14], [84, 43, 30], [68, 47, 16],
    [76, 54, 18], [89, 52, 14], [70, 58, 12], [81, 61, 20], [64, 66, 12], [74, 69, 14],
    [87, 68, 10], [59, 52, 10], [61, 36, 12], [72, 18, 10], [95, 44, 10], [92, 60, 12],
  ];
  return points
    .map(
      ([x, y, size], index) => `
        <span class="hero-particle p-${index}" style="left:${x}%;top:${y}%;width:${size}px;height:${size}px;"></span>
      `,
    )
    .join('');
}

function navMarkup() {
  const items = [
    ['Platform', '#platform'],
    ['Results', '#results'],
    ['Validation', '#scale-up'],
    ['Pathogens', '#domains'],
    ['About', '#roadmap'],
  ];

  return `
    <header class="site-header">
      <a class="brand-mark" href="#top">AgroShield</a>
      <nav class="site-nav">
        ${items.map(([label, href]) => `<a href="${href}">${label}</a>`).join('')}
      </nav>
      <a class="nav-cta" href="#contact">Request Partnership</a>
    </header>
  `;
}

function heroMarkup() {
  return `
    <section class="hero-section snap-section" id="top">
      <div class="hero-backdrop" aria-hidden="true">
        <img class="hero-backdrop-image" src="./assets/hero-first-section.jpeg" alt="" />
        <img class="hero-backdrop-image hero-backdrop-image-blur" src="./assets/hero-first-section.jpeg" alt="" />
        <div class="hero-backdrop-shade"></div>
      </div>
      <div class="section-shell">
        <div class="hero-grid">
          <div class="hero-copy">
            <div class="eyebrow">Next-Generation Bioactive Discovery</div>
            <h1>The Future of Agricultural <span>Bioactives</span> is Decoded, Not Discovered.</h1>
            <p class="hero-lead">
              AgroShield combines AI-guided peptide discovery, multi-dimensional prioritization, and scalable
              experimental validation to protect crops from evolving pathogen pressure. Built for crop protection
              companies and agri-biotech labs.
            </p>
            <div class="hero-actions">
              <a class="button button-primary" href="#contact">Request Partnership</a>
              <a class="button button-secondary" href="#platform">Explore Methodology</a>
            </div>
          </div>
          <div class="hero-visual" aria-hidden="true">
            <div class="hero-glow"></div>
            <div class="hero-network">
              ${particleMarkup()}
            </div>
          </div>
        </div>
      </div>
    </section>
  `;
}

function problemMarkup() {
  return `
    <section class="content-band band-problem snap-section" id="problem">
      <div class="section-shell split-panel">
        <div class="problem-copy" data-reveal>
          <div class="eyebrow">Challenge</div>
          <h2>Pathogen Pressure & Chemical Resistance.</h2>
          <p>
            Agricultural systems need more precise molecular defenses. Resistance pressure, regulatory complexity,
            and the limits of broad chemistry create an opening for bioactive programs that are both targeted and scalable.
          </p>
          <ul class="signal-list">
            <li>Precision is becoming more valuable than blanket chemistry.</li>
            <li>Sequence-guided bioactives create a path toward specificity and faster iteration.</li>
            <li>Discovery must be linked to manufacturability from the beginning.</li>
          </ul>
        </div>
        <div class="leaf-panel" data-reveal>
          <div class="leaf-frame">
            <img class="leaf-image" src="./assets/pathogen-leaf.png" alt="Leaf with visible pathogen damage" />
          </div>
        </div>
      </div>
    </section>
  `;
}

function engineMarkup() {
  return `
    <section class="content-band snap-section" id="platform">
      <div class="section-shell">
        <div class="section-intro centered" data-reveal>
          <div class="eyebrow">Platform Architecture</div>
          <h2>The AgroShield Discovery Engine</h2>
          <p>
            Trained on curated AMP datasets and built for multi-objective filtering across activity, toxicity,
            stability, and synthesis feasibility.
          </p>
        </div>
        <div class="engine-grid">
          ${engineCards
            .map(
              (card) => `
                <article class="engine-card" data-reveal>
                  <div class="engine-icon"></div>
                  <div class="mini-eyebrow">${card.eyebrow}</div>
                  <h3>${card.title}</h3>
                  <p>${card.copy}</p>
                  <div class="engine-stat">${card.stat}</div>
                  ${engineVisualMarkup(card.visual)}
                </article>
              `,
            )
            .join('')}
        </div>
      </div>
    </section>
  `;
}

function metricsMarkup() {
  return `
    <section class="content-band band-metrics snap-section" id="results">
      <div class="section-shell">
        <div class="section-intro split-heading" data-reveal>
          <div>
            <div class="eyebrow">Discovery Metrics</div>
            <h2>Pipeline Outputs With Clear Meaning.</h2>
          </div>
          <p>
            Each number maps to a concrete stage of the discovery funnel, from biological priors to generated sequence space to the validation shortlist.
          </p>
        </div>
        <div class="metric-grid">
          ${metrics
            .map(
              (metric) => `
                <article class="metric-card" data-reveal>
                  <div class="metric-value">${metric.value}</div>
                  <div class="metric-label">${metric.label}</div>
                  <p>${metric.copy}</p>
                </article>
              `,
            )
            .join('')}
        </div>
        <div class="feature-strip" data-reveal>
          <div class="feature-key">
            <div class="mini-eyebrow">Shortlisting Logic</div>
            <strong>Activity, safety, manufacturability</strong>
          </div>
          <p>
            Every candidate is filtered across antimicrobial activity, hemolysis risk, phytotoxicity, stability, and synthesizability before entering the final shortlist.
          </p>
          <div class="feature-node">
            <span></span><span></span><span></span><span></span><span></span>
          </div>
        </div>
      </div>
    </section>
  `;
}

function scaleMarkup() {
  return `
    <section class="content-band snap-section" id="scale-up">
      <div class="section-shell split-panel scale-panel">
        <div class="reactor-panel" data-reveal>
          <div class="reactor-frame">
            <img class="reactor-image" src="./assets/reactor-chatgpt.png" alt="Bioreactor-inspired concept render" />
          </div>
        </div>
        <div class="scale-copy" data-reveal>
          <div class="eyebrow">Experimental Scale-Up Strategy</div>
          <h2>From Sequence Design to Bioreactor Readiness.</h2>
          <ol class="process-list">
            <li>
              <strong>Cloning & Fusion Expression</strong>
              <span>Candidate peptides are placed into inducible fusion-expression systems with MBP-style solubility support and a TEV cleavage site.</span>
            </li>
            <li>
              <strong>Induced Production</strong>
              <span>Expression begins only after high cell density is reached, reducing toxicity and improving upstream control.</span>
            </li>
            <li>
              <strong>Secretion-First Recovery</strong>
              <span>Bacillus subtilis is prioritized where possible because extracellular secretion is more favorable than in Escherichia coli.</span>
            </li>
            <li>
              <strong>Recovery, Cleavage & Final Purification</strong>
              <span>Supernatant recovery, fusion-protein purification, enzymatic release, and final cleanup define a scalable downstream workflow.</span>
            </li>
          </ol>
        </div>
      </div>
    </section>
  `;
}

function domainsMarkup() {
  return `
    <section class="content-band snap-section" id="domains">
      <div class="section-shell">
        <div class="section-intro" data-reveal>
          <div class="eyebrow">Strategic Target Domains</div>
          <h2>Commercially Relevant Pathogen Classes.</h2>
          <p>
            AgroShield organizes discovery around pathogen programs tied to real agricultural pressure and partner demand, not around a public-facing peptide browser.
          </p>
        </div>
        <div class="domain-grid">
          ${domains
            .map(
              (domain) => `
                <article class="domain-card" data-reveal>
                  <div class="mini-eyebrow">${domain.type}</div>
                  <h3>${domain.name}</h3>
                  <p>${domain.copy}</p>
                </article>
              `,
            )
            .join('')}
        </div>
      </div>
    </section>
  `;
}

function roadmapMarkup() {
  return `
    <section class="content-band band-roadmap snap-section" id="roadmap">
      <div class="section-shell">
        <div class="section-intro centered" data-reveal>
          <div class="eyebrow">Growth Path</div>
          <h2>The Path to Market</h2>
          <p>
            Discovery is only one layer. AgroShield is designed to progress from computational advantage to validation, scale-up, and deployment.
          </p>
        </div>
        <div class="roadmap">
          <div class="roadmap-line"></div>
          ${roadmap
            .map(
              (step, index) => `
                <article class="roadmap-step ${index % 2 ? 'right' : 'left'}" data-reveal>
                  <div class="roadmap-marker"></div>
                  <div class="roadmap-card">
                    <div class="mini-eyebrow">${step.phase}</div>
                    <h3>${step.title}</h3>
                    <p>${step.copy}</p>
                  </div>
                </article>
              `,
            )
            .join('')}
        </div>
      </div>
    </section>
  `;
}

function marketMarkup() {
  return `
    <section class="content-band band-manifesto snap-section">
      <div class="section-shell">
        <div class="section-intro centered" data-reveal>
          <div class="eyebrow">Go-To-Market</div>
          <h2>Built for Teams That Need Better Crop Protection Leads.</h2>
          <p>
            AgroShield helps R&amp;D teams move from large sequence-space exploration to a small, testable peptide shortlist that can enter validation and partnership workflows.
          </p>
        </div>
        <div class="market-grid">
          ${marketSegments
            .map(
              (segment) => `
                <article class="market-card" data-reveal>
                  <div class="mini-eyebrow">${segment.eyebrow}</div>
                  <h3>${segment.title}</h3>
                  <p>${segment.copy}</p>
                </article>
              `,
            )
            .join('')}
        </div>
      </div>
    </section>
  `;
}

function ctaMarkup() {
  return `
    <section class="cta-band snap-section" id="contact">
      <div class="section-shell cta-shell" data-reveal>
          <div class="eyebrow">Contact</div>
        <h2>Secure the Future of Crop Health.</h2>
        <p>
          AgroShield is built for crop protection companies, agri-biotech labs, and strategic partners spanning discovery,
          experimental validation, and production-scale deployment.
        </p>
        <div class="hero-actions cta-actions">
          <a class="button button-dark" href="mailto:partners@agroshield.bio">Contact AgroShield</a>
        </div>
      </div>
    </section>
  `;
}

function footerMarkup() {
  return `
    <footer class="site-footer">
      <div>
        <div class="footer-brand">AgroShield</div>
        <p>AI-guided antimicrobial peptide design for next-generation agriculture.</p>
      </div>
      <div class="footer-links">
        <a href="#platform">Platform</a>
        <a href="#results">Results</a>
        <a href="#scale-up">Scale-Up</a>
        <a href="#contact">Contact</a>
      </div>
      <div class="footer-word">BIO</div>
    </footer>
  `;
}

function render() {
  app.innerHTML = `
    <div class="site-shell">
      <div class="site-noise"></div>
      ${navMarkup()}
      ${heroMarkup()}
      ${problemMarkup()}
      ${engineMarkup()}
      ${metricsMarkup()}
      ${scaleMarkup()}
      ${domainsMarkup()}
      ${roadmapMarkup()}
      ${marketMarkup()}
      ${ctaMarkup()}
      ${footerMarkup()}
    </div>
  `;
}

function bindMotion() {
  gsap.registerPlugin(ScrollTrigger, ScrollToPlugin, Observer);

  const root = document.documentElement;
  const header = document.querySelector('.site-header');
  const heroCopy = document.querySelector('.hero-copy');
  const heroVisual = document.querySelector('.hero-visual');
  const heroNetwork = document.querySelector('.hero-network');
  const noise = document.querySelector('.site-noise');
  const sections = gsap.utils.toArray('.snap-section');
  const navLinks = [...document.querySelectorAll('.site-nav a')];
  const sectionTargets = navLinks
    .map((link) => {
      const href = link.getAttribute('href');
      const target = href === '#top' ? document.querySelector('#top') : document.querySelector(href);
      return [link, target];
    })
    .filter(([, section]) => section);

  document.body.classList.add('motion-ready');

  const updateActiveNav = (activeId) => {
    navLinks.forEach((link) => {
      link.classList.toggle('is-active', link.getAttribute('href') === activeId);
    });
  };

  sectionTargets.forEach(([link, section]) => {
    ScrollTrigger.create({
      trigger: section,
      start: 'top center',
      end: 'bottom center',
      onToggle: (self) => {
        if (self.isActive) {
          updateActiveNav(link.getAttribute('href'));
        }
      },
    });
  });

  ScrollTrigger.create({
    start: 28,
    end: 'max',
    onUpdate: (self) => {
      header?.classList.toggle('is-condensed', self.scroll() > 28);
      root.style.setProperty('--scroll-y', self.scroll().toFixed(2));
      root.style.setProperty('--scroll-progress', Math.min(self.scroll() / 600, 1).toFixed(3));
      noise?.style.setProperty('transform', `translate3d(0, ${self.scroll() * 0.015}px, 0)`);
    },
  });

  if (heroCopy && heroVisual && heroNetwork) {
    gsap.timeline({
      scrollTrigger: {
        trigger: '.hero-section',
        start: 'top top',
        end: 'bottom top',
        scrub: 0.8,
      },
    })
      .to(heroCopy, { y: -46, ease: 'none' }, 0)
      .to(heroVisual, { y: 26, ease: 'none' }, 0)
      .to(heroNetwork, { y: 38, scale: 1.025, ease: 'none' }, 0);
  }

  const intro = gsap.timeline({ defaults: { ease: 'power3.out' } });
  intro
    .from('.site-header', { y: -20, autoAlpha: 0, duration: 0.8 })
    .from('.hero-copy .eyebrow', { y: 20, autoAlpha: 0, duration: 0.45 }, '-=0.4')
    .from('.hero-copy h1', { y: 38, autoAlpha: 0, duration: 0.9 }, '-=0.18')
    .from('.hero-copy .hero-lead', { y: 24, autoAlpha: 0, duration: 0.6 }, '-=0.45')
    .from('.hero-copy .hero-actions', { y: 20, autoAlpha: 0, duration: 0.55 }, '-=0.32')
    .from('.hero-visual', { autoAlpha: 0, scale: 0.96, duration: 1.1 }, '-=1.0');

  gsap.utils.toArray('[data-reveal]').forEach((node, index) => {
    if (node.closest('.hero-section')) return;
    gsap.fromTo(
      node,
      { y: 40, autoAlpha: 0, filter: 'blur(10px)' },
      {
        y: 0,
        autoAlpha: 1,
        filter: 'blur(0px)',
        duration: 0.95,
        delay: Math.min(index * 0.02, 0.12),
        ease: 'power3.out',
        scrollTrigger: {
          trigger: node,
          start: 'top 84%',
          once: true,
        },
      },
    );
  });

  if (window.matchMedia('(min-width: 960px) and (prefers-reduced-motion: no-preference)').matches) {
    let currentSection = 0;
    let isAnimating = false;
    const headerOffset = 82;
    const boundarySlack = 18;

    const syncSectionIndex = () => {
      const scrollY = window.scrollY + headerOffset + window.innerHeight * 0.2;
      sections.forEach((section, index) => {
        const top = section.offsetTop;
        const bottom = top + section.offsetHeight;
        if (scrollY >= top && scrollY < bottom) {
          currentSection = index;
        }
      });
    };

    const getSectionWindow = (section) => {
      const usableHeight = window.innerHeight - headerOffset;
      const minY = Math.max(section.offsetTop - headerOffset, 0);
      const maxY = Math.max(minY, section.offsetTop + section.offsetHeight - window.innerHeight);
      const isTall = section.offsetHeight > usableHeight + boundarySlack;
      return { minY, maxY, usableHeight, isTall };
    };

    const scrollWithinSection = (direction) => {
      const section = sections[currentSection];
      if (!section) return false;

      const { minY, maxY, usableHeight, isTall } = getSectionWindow(section);
      if (!isTall) return false;

      const currentY = window.scrollY;

      if (direction > 0 && currentY < maxY - boundarySlack) {
        gsap.to(window, {
          duration: 0.72,
          ease: 'power2.out',
          scrollTo: { y: Math.min(currentY + usableHeight * 0.88, maxY), autoKill: false },
        });
        return true;
      }

      if (direction < 0 && currentY > minY + boundarySlack) {
        gsap.to(window, {
          duration: 0.72,
          ease: 'power2.out',
          scrollTo: { y: Math.max(currentY - usableHeight * 0.88, minY), autoKill: false },
        });
        return true;
      }

      return false;
    };

    const goToSection = (index) => {
      const nextIndex = gsap.utils.clamp(0, sections.length - 1, index);
      if (isAnimating || nextIndex === currentSection) return;
      isAnimating = true;
      currentSection = nextIndex;

      gsap.to(window, {
        duration: 1.05,
        ease: 'expo.inOut',
        scrollTo: { y: sections[nextIndex], offsetY: 82, autoKill: false },
        onComplete: () => {
          isAnimating = false;
        },
      });
    };

    Observer.create({
      target: window,
      type: 'wheel,touch,pointer',
      preventDefault: true,
      wheelSpeed: 1,
      tolerance: 14,
      onDown: () => {
        syncSectionIndex();
        if (scrollWithinSection(1)) return;
        goToSection(currentSection + 1);
      },
      onUp: () => {
        syncSectionIndex();
        if (scrollWithinSection(-1)) return;
        goToSection(currentSection - 1);
      },
    });

    window.addEventListener(
      'keydown',
      (event) => {
        if (event.key === 'ArrowDown' || event.key === 'PageDown' || event.key === ' ') {
          event.preventDefault();
          syncSectionIndex();
          goToSection(currentSection + 1);
        }

        if (event.key === 'ArrowUp' || event.key === 'PageUp') {
          event.preventDefault();
          syncSectionIndex();
          goToSection(currentSection - 1);
        }
      },
      { passive: false },
    );
  }
}

function bindEvents() {
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener('click', (event) => {
      const href = link.getAttribute('href');
      const target = href === '#top' ? document.querySelector('#top') : document.querySelector(href);
      if (!target) return;
      event.preventDefault();
      gsap.to(window, {
        duration: 1,
        ease: 'expo.inOut',
        scrollTo: { y: target, offsetY: 82, autoKill: false },
      });
    });
  });
}

render();
bindMotion();
bindEvents();
