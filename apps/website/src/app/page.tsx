import { CodePanel, PageEnhancements, SiteHeader } from "./interactions";

const github = "https://github.com/Team-ASHTOJ/TATTVASTRA";

const compilerStages = [
  ["01", "SOURCE", ".jky forensic program"],
  ["02", "LEXER", "Native C++20 lexical analysis"],
  ["03", "PARSER / AST", "Structured investigation intent"],
  ["04", "TYPE CHECK", "Forensic types and capabilities"],
  ["05", "TYPED JIR", "Platform-independent effect ordering"],
  ["06", "LLVM IR", "Verified mandatory lowering"],
  ["07", "ORC / AOT", "Worker memory or native object"],
] as const;

const collectors = [
  "System",
  "Users & sessions",
  "Processes",
  "Interfaces",
  "Connections",
  "Routes",
  "Files / SHA-256",
  "Services",
  "Startup",
  "Scheduled tasks",
  "Logs",
  "Software",
  "Drivers",
  "Kernel modules",
];

const verified = [
  "Independent C++20 JOCKY frontend",
  "Typed, effect-aware JIR",
  "Mandatory LLVM lowering",
  "LLVM ORC memory execution",
  "Native AOT object generation",
  "Real Linux ELF output",
  "Real Windows COFF output",
  "Deterministic seeded variants",
  "Persistent Build Forge",
  "Signed build manifests",
  "Rust endpoint Agent",
  "One-time enrollment + mTLS",
  "Signed nonce-bound jobs",
  "Three independently enrolled Linux Agents",
  "Direct + trusted-relay transport",
  "Read-only collection",
  "Signed evidence manifests",
  "Artifacts + integrity verification",
  "Findings / graph / timeline",
  "Hunt-scoped reports",
  "Bounded Python interoperability",
  "AI-assisted report hypotheses",
];

function SectionHeading({
  eyebrow,
  title,
  intro,
}: {
  eyebrow: string;
  title: React.ReactNode;
  intro?: string;
}) {
  return (
    <header className="section-heading" data-reveal>
      <span className="eyebrow">{eyebrow}</span>
      <h2>{title}</h2>
      {intro ? <p>{intro}</p> : null}
    </header>
  );
}

function IdentityChain() {
  return (
    <div
      className="identity-chain"
      aria-label="Source to evidence identity chain"
    >
      {["SOURCE", "JIR", "LLVM", "VARIANT", "ENDPOINT", "EVIDENCE"].map(
        (item, index) => (
          <span key={item}>
            <b>{item}</b>
            {index < 5 ? <i aria-hidden="true">→</i> : null}
          </span>
        ),
      )}
    </div>
  );
}

function FabricDiagram() {
  return (
    <div className="fabric-card" aria-label="Forensic execution fabric">
      <div className="fabric-grid" />
      <div className="fabric-meta">
        <span>EXECUTION FABRIC</span>
        <span>TRACE // 7F.3A</span>
      </div>
      <svg
        className="fabric-lines"
        viewBox="0 0 620 570"
        role="img"
        aria-label="JOCKY source passes through typed JIR and LLVM to Linux and Windows target evidence"
      >
        <defs>
          <linearGradient id="line" x1="0" x2="1">
            <stop stopColor="#31586d" />
            <stop offset=".5" stopColor="#8bb6c9" />
            <stop offset="1" stopColor="#31586d" />
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <g className="links" fill="none" stroke="url(#line)" strokeWidth="1.4">
          <path d="M310 91V148" />
          <path d="M310 204V261" />
          <path d="M310 317L176 375" />
          <path d="M310 317L444 375" />
          <path d="M176 431L310 489" />
          <path d="M444 431L310 489" />
        </g>
        <g className="pulses" fill="#a8d7e9" filter="url(#glow)">
          <circle r="3">
            <animateMotion
              dur="4.8s"
              repeatCount="indefinite"
              path="M310 91V148"
            />
          </circle>
          <circle r="3">
            <animateMotion
              begin="1.1s"
              dur="4.8s"
              repeatCount="indefinite"
              path="M310 204V261"
            />
          </circle>
          <circle r="3">
            <animateMotion
              begin="2.1s"
              dur="5.2s"
              repeatCount="indefinite"
              path="M310 317L176 375"
            />
          </circle>
          <circle r="3">
            <animateMotion
              begin="2.1s"
              dur="5.2s"
              repeatCount="indefinite"
              path="M310 317L444 375"
            />
          </circle>
        </g>
      </svg>
      <div className="fabric-node n-source">
        <small>INPUT</small>
        <b>.JKY SOURCE</b>
        <em>typed intent</em>
      </div>
      <div className="fabric-node n-jir">
        <small>SEMANTIC CORE</small>
        <b>TYPED JIR</b>
        <em>canonical identity</em>
      </div>
      <div className="fabric-node n-llvm">
        <small>BACKEND</small>
        <b>LLVM</b>
        <em>mandatory lowering</em>
      </div>
      <div className="fabric-node n-linux">
        <small>VARIANT A</small>
        <b>LINUX ELF</b>
        <em>execution verified</em>
      </div>
      <div className="fabric-node n-windows">
        <small>VARIANT B</small>
        <b>WINDOWS COFF</b>
        <em>object verified</em>
      </div>
      <div className="fabric-node n-evidence">
        <small>OUTPUT</small>
        <b>SIGNED EVIDENCE</b>
        <em>provenance retained</em>
      </div>
      <div className="fabric-legend">
        <span>
          <i /> IDENTIFIED
        </span>
        <span>
          <i /> AUTHORIZED
        </span>
        <span>
          <i /> HASHED
        </span>
      </div>
    </div>
  );
}

function MiniFingerprint({ variant }: { variant: number }) {
  const patterns = [
    [30, 52, 38, 68, 46, 58, 32],
    [58, 36, 62, 42, 70, 32, 52],
    [42, 66, 34, 54, 40, 72, 48],
  ];
  const pattern = patterns[variant] ?? [];
  return (
    <div
      className="fingerprint"
      aria-label={`Variant ${variant + 1} structural fingerprint`}
    >
      {pattern.map((height, index) => (
        <i key={index} style={{ height }} />
      ))}
    </div>
  );
}

export default function Home() {
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <SiteHeader />
      <PageEnhancements />
      <main id="main">
        <section className="hero section" id="overview">
          <div className="hero-noise" />
          <div className="section-inner hero-grid">
            <div className="hero-copy" data-reveal>
              <span className="eyebrow">
                <i /> TATTVASTRA // FORENSIC OPERATIONS
              </span>
              <h1>
                ONE LANGUAGE.
                <br />
                <span>EVERY ENDPOINT.</span>
                <br />
                NO NOISE.
              </h1>
              <p className="hero-lead">
                A language-first forensic platform that turns typed
                investigation intent into LLVM-compiled execution and traceable
                evidence across endpoints.
              </p>
              <p className="hero-support">
                Write once in JOCKY. Compile through typed JIR and LLVM.
                Generate controlled variants. Execute through authorized agents.
                Preserve provenance from source to report.
              </p>
              <div className="hero-actions">
                <a className="button" href="#jocky">
                  Explore JOCKY <span>↓</span>
                </a>
                <a className="text-link" href="#architecture">
                  View architecture <span>↘</span>
                </a>
              </div>
              <div className="tech-chips" aria-label="Core technology">
                {[
                  "JOCKY DSL",
                  "TYPED JIR",
                  "LLVM ORC / AOT",
                  "BUILD DIVERSITY",
                  "SIGNED EVIDENCE",
                ].map((chip) => (
                  <span key={chip}>{chip}</span>
                ))}
              </div>
            </div>
            <div className="hero-visual" data-reveal>
              <FabricDiagram />
            </div>
          </div>
          <div className="proof-strip">
            <span>ENGINEERED WITH</span>
            {[
              "C++20 FRONTEND",
              "LLVM",
              "RUST AGENT",
              "FASTAPI CONTROL PLANE",
              "POSTGRESQL",
              "NEXT.JS",
            ].map((item) => (
              <b key={item}>{item}</b>
            ))}
          </div>
        </section>

        <section className="section problem-section">
          <div className="section-inner">
            <SectionHeading
              eyebrow="01 // THE PROBLEM"
              title={
                <>
                  FORENSICS SHOULD NOT BE REWRITTEN
                  <br />
                  FOR EVERY ENDPOINT.
                </>
              }
              intro="Different operating systems should not fracture investigation intent, result shape, or the chain between a question and its evidence."
            />
            <div className="before-after" data-reveal>
              <article className="comparison-side before">
                <span className="panel-label">BEFORE // FRAGMENTED</span>
                <div className="fragment-list">
                  {[
                    "Windows script",
                    "Linux script",
                    "Agent query",
                    "Manual export",
                    "Manual correlation",
                  ].map((x, i) => (
                    <div key={x}>
                      <i>{String(i + 1).padStart(2, "0")}</i>
                      <span>{x}</span>
                      <em>DISCONNECTED</em>
                    </div>
                  ))}
                </div>
                <strong>
                  FRAGMENTED EVIDENCE <b>×</b>
                </strong>
              </article>
              <div className="comparison-divider">
                <span>→</span>
              </div>
              <article className="comparison-side after">
                <span className="panel-label">AFTER // TRACEABLE</span>
                <div className="trace-stack">
                  <div className="primary-node">
                    ONE <code>.JKY</code> PROGRAM
                  </div>
                  {[
                    "TYPED JIR",
                    "LLVM",
                    "AUTHORIZED ENDPOINTS",
                    "NORMALIZED EVIDENCE",
                  ].map((x) => (
                    <div key={x}>
                      <i>↓</i>
                      <span>{x}</span>
                    </div>
                  ))}
                </div>
                <strong>
                  ONE IDENTITY CHAIN <b>✓</b>
                </strong>
              </article>
            </div>
          </div>
        </section>

        <section className="section language-section" id="jocky">
          <div className="section-inner">
            <SectionHeading
              eyebrow="02 // MEET JOCKY"
              title="FORENSIC INTENT, AS A LANGUAGE."
              intro="JOCKY is an independent typed forensic DSL — not a Python wrapper and not a collection of shell commands."
            />
            <div className="language-grid">
              <div data-reveal>
                <CodePanel />
              </div>
              <div className="language-features" data-reveal>
                {[
                  ["REAL LANGUAGE", "Handwritten C++20 lexer + parser"],
                  [
                    "FORENSIC TYPES",
                    "pid · path · ip · hash · time · duration · bytes",
                  ],
                  [
                    "CAPABILITY-BOUND",
                    "Collectors cannot silently exceed declared access",
                  ],
                  ["RESOURCE-AWARE", "CPU · memory · I/O · duration budgets"],
                  [
                    "TRUTH-PRESERVING",
                    "Option<T> + three-valued logic keep unknown data unknown",
                  ],
                  [
                    "NO SHELL",
                    "No dynamic evaluation or unrestricted native imports",
                  ],
                ].map(([title, text], i) => (
                  <article key={title}>
                    <span>{String(i + 1).padStart(2, "0")}</span>
                    <div>
                      <h3>{title}</h3>
                      <p>{text}</p>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="section compiler-section" id="compiler">
          <div className="section-inner wide">
            <SectionHeading
              eyebrow="03 // COMPILER PIPELINE"
              title={
                <>
                  NOT A SCRIPTING WRAPPER.
                  <br />A REAL COMPILER PIPELINE.
                </>
              }
            />
            <div className="compiler-flow" data-reveal>
              {compilerStages.map(([num, title, text], i) => (
                <article tabIndex={0} key={title}>
                  <small>{num}</small>
                  <div className="stage-icon">
                    <i />
                  </div>
                  <h3>{title}</h3>
                  <p>{text}</p>
                  {i < compilerStages.length - 1 ? (
                    <b aria-hidden="true">→</b>
                  ) : null}
                </article>
              ))}
            </div>
            <div className="compiler-lower">
              <div className="no-fallback" data-reveal>
                <span>DESIGN INVARIANT</span>
                <strong>
                  NO INTERPRETER
                  <br />
                  FALLBACK.
                </strong>
                <p>
                  LLVM is a required build dependency and the only execution
                  backend.
                </p>
              </div>
              <div className="inspection-card" data-reveal>
                <div className="inspection-head">
                  <span>COMPILER INSPECTION</span>
                  <b>IDENTITY FIELDS</b>
                </div>
                {[
                  ["SOURCE HASH", "COMPUTED AT BUILD"],
                  ["JIR HASH", "COMPUTED AT BUILD"],
                  ["LLVM IDENTITY", "RECORDED AT BUILD"],
                  ["TARGET TRIPLE", "x86_64-unknown-linux-gnu"],
                  ["ARTIFACT SHA-256", "RE-HASHED FROM BYTES"],
                ].map(([k, v]) => (
                  <div key={k}>
                    <span>{k}</span>
                    <code>{v}</code>
                  </div>
                ))}
                <div className="verified-line">
                  <i /> VALUES COME FROM THE BUILD
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="section jir-section">
          <div className="section-inner">
            <SectionHeading
              eyebrow="04 // TYPED JIR"
              title={
                <>
                  ONE SEMANTIC LAYER BETWEEN
                  <br />
                  INTENT AND MACHINE CODE.
                </>
              }
              intro="JIR is the stable, platform-independent boundary that makes forensic meaning inspectable before it becomes a machine artifact."
            />
            <div className="jir-grid">
              <div className="instruction-card" data-reveal>
                <div className="instruction-top">
                  <span>JIR.INSTRUCTION SCHEMA</span>
                  <code>REQUIRED FIELDS</code>
                </div>
                {[
                  ["OPCODE", "COLLECT_PROCESSES"],
                  ["RESULT TYPE", "dataset<process>"],
                  ["CAPABILITIES", "process.read"],
                  ["TARGET CONSTRAINT", "windows | linux"],
                  ["RESOURCE CLASS", "bounded_read"],
                  ["SOURCE SPAN", "retained"],
                  ["EFFECT PREDECESSOR", "ordered"],
                ].map(([a, b]) => (
                  <div key={a}>
                    <small>{a}</small>
                    <code>{b}</code>
                  </div>
                ))}
              </div>
              <div className="jir-copy" data-reveal>
                <div className="orbital-mark">
                  <span>JIR</span>
                  <i />
                  <i />
                  <i />
                </div>
                <ul>
                  {[
                    "Typed and platform-independent",
                    "Deterministic canonical identity",
                    "SSA-like dataset handles",
                    "Explicit effect ordering",
                    "Evidence semantics preserved through optimization and diversity",
                  ].map((x) => (
                    <li key={x}>
                      <span>+</span>
                      {x}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <IdentityChain />
          </div>
        </section>

        <section className="section forge-section" id="forge">
          <div className="section-inner wide">
            <SectionHeading
              eyebrow="05 // BUILD & ARTIFACT PROVENANCE LAYER"
              title={
                <>
                  ONE INTENT.
                  <br />
                  MULTIPLE VERIFIED BUILDS.
                </>
              }
              intro="Build Forge creates deterministic structural variation while preserving the program's declared operations, capabilities, budgets, and effect order."
            />
            <div className="forge-pipeline" data-reveal>
              {[
                "SOURCE",
                "VALIDATE",
                "JIR",
                "DIVERSIFY",
                "LLVM",
                "BUILD",
                "TEST",
                "EQUIVALENCE",
                "MANIFEST",
                "READY",
              ].map((x, i) => (
                <span key={x}>
                  <i>{String(i + 1).padStart(2, "0")}</i>
                  {x}
                  {i < 9 ? <b>›</b> : null}
                </span>
              ))}
            </div>
            <div className="variant-grid">
              {["A", "B", "C"].map((variant, i) => (
                <article className="variant-card" data-reveal key={variant}>
                  <header>
                    <span>VARIANT {variant}</span>
                    <em>BUILD SCHEMA</em>
                  </header>
                  <MiniFingerprint variant={i} />
                  <dl>
                    <div>
                      <dt>SEED</dt>
                      <dd>ASSIGNED</dd>
                    </div>
                    <div>
                      <dt>ARTIFACT</dt>
                      <dd>SHA-256</dd>
                    </div>
                    <div>
                      <dt>BLOCKS</dt>
                      <dd>MEASURED</dd>
                    </div>
                    <div>
                      <dt>FUNCTIONS</dt>
                      <dd>MEASURED</dd>
                    </div>
                    <div>
                      <dt>HELPERS</dt>
                      <dd>MEASURED</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
            <div className="forge-facts" data-reveal>
              <p>
                <strong>1–8</strong> deterministic seeded variants
              </p>
              <p>Structural fingerprints + real artifact SHA-256</p>
              <p>Ed25519 signed build manifests</p>
              <p>Protected literal pools</p>
            </div>
            <div className="precision-note">
              <span>PRECISE CLAIM</span>
              <p>
                <strong>
                  Bounded equivalence checks on immutable labeled fixtures.
                </strong>{" "}
                Controlled structural diversity reduces dependence on a single
                physical build identity while preserving forensic semantics.
              </p>
            </div>
          </div>
        </section>

        <section className="section target-section">
          <div className="section-inner">
            <SectionHeading
              eyebrow="06 // CROSS-TARGET COMPILATION"
              title={
                <>
                  SAME JIR.
                  <br />
                  DIFFERENT MACHINE TARGETS.
                </>
              }
            />
            <div className="target-diagram" data-reveal>
              <div className="target-jir">
                <small>CANONICAL SEMANTICS</small>
                <strong>TYPED JIR</strong>
                <code>jir_hash: computed at build</code>
              </div>
              <div className="target-branches">
                <i />
                <i />
              </div>
              <article>
                <span className="os-mark">LNX</span>
                <div>
                  <small>TARGET 01</small>
                  <h3>LINUX x86_64</h3>
                  <p>ELF object · ORC / AOT</p>
                  <b className="status verified">● EXECUTION VERIFIED</b>
                </div>
              </article>
              <article>
                <span className="os-mark">WIN</span>
                <div>
                  <small>TARGET 02</small>
                  <h3>WINDOWS x86_64</h3>
                  <p>COFF object · MSVC triple</p>
                  <b className="status verified">● OBJECT VERIFIED</b>
                </div>
              </article>
            </div>
            <div className="validation-boundary" data-reveal>
              <span>LIVE WINDOWS ENDPOINT EXECUTION</span>
              <strong>VALIDATION PENDING</strong>
              <p>
                Object generation is verified. Linking and runtime acceptance
                require the target environment.
              </p>
            </div>
          </div>
        </section>

        <section className="section execution-section" id="execution">
          <div className="section-inner wide">
            <SectionHeading
              eyebrow="07 // AUTHORIZED EXECUTION"
              title={
                <>
                  EXECUTION WITHOUT AN
                  <br />
                  UNRESTRICTED REMOTE SHELL.
                </>
              }
              intro="Compiler-generated programs move through authenticated, policy-bound infrastructure into a supervised worker owned by JOCKY."
            />
            <div className="execution-layout">
              <div className="execution-flow" data-reveal>
                {[
                  "CONTROL PLANE",
                  "SIGNED JOB + mTLS",
                  "RUST AGENT",
                  "ADMISSION",
                  "SUPERVISED WORKER",
                  "READ-ONLY RUNTIME ABI",
                  "COLLECTORS",
                ].map((x, i) => (
                  <div key={x} className={x === "ADMISSION" ? "admission" : ""}>
                    <span>{x}</span>
                    {x === "ADMISSION" ? (
                      <small>
                        signature · audience · expiry · nonce
                        <br />
                        capabilities · budgets · artifact hash
                      </small>
                    ) : null}
                    {i < 6 ? <i>↓</i> : null}
                  </div>
                ))}
              </div>
              <div className="execution-copy" data-reveal>
                <div className="mode-cards">
                  <article>
                    <span>MEMORY / JIT</span>
                    <h3>LLVM ORC</h3>
                    <p>Runs inside a JOCKY-owned worker process.</p>
                  </article>
                  <article>
                    <span>NATIVE / AOT</span>
                    <h3>LINKED WORKER</h3>
                    <p>Runs under Agent supervision.</p>
                  </article>
                </div>
                <ul>
                  {[
                    "One-time enrollment + endpoint identity",
                    "mTLS and signed expiring jobs",
                    "Nonce-bound replay protection",
                    "Artifact re-hashing before execution",
                    "Deadlines, cancellation, and concurrency supervision",
                    "Encrypted offline spool",
                    "Direct + trusted relay transport",
                  ].map((x) => (
                    <li key={x}>
                      <i>✓</i>
                      {x}
                    </li>
                  ))}
                </ul>
                <div className="never-strip">
                  <span>NEITHER MODE</span>
                  <p>
                    injects into foreign processes · hollows processes ·
                    disables AV/EDR · exposes arbitrary shell execution
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="section collectors-section">
          <div className="section-inner">
            <SectionHeading
              eyebrow="08 // READ-ONLY COLLECTION"
              title="A FIXED FORENSIC SURFACE."
              intro="Approved, typed, read-only collectors are admitted only when the program declares the capability and the endpoint policy allows it."
            />
            <div className="collector-grid" data-reveal>
              {collectors.map((x, i) => (
                <article key={x}>
                  <span>{String(i + 1).padStart(2, "0")}</span>
                  <b>{x}</b>
                  <i>READ</i>
                </article>
              ))}
            </div>
            <div className="failure-block">
              <div data-reveal>
                <span className="eyebrow">TRUTH PRESERVATION</span>
                <h3>FAILURE IS EVIDENCE.</h3>
                <p>
                  Missing access is never silently converted into an empty clean
                  result.
                </p>
              </div>
              <div className="state-cards" data-reveal>
                {[
                  ["SUCCESS", "Collection completed"],
                  ["PARTIAL", "Some scope unavailable"],
                  ["DENIED", "Policy or access refused"],
                  ["UNAVAILABLE", "Collector absent"],
                ].map(([a, b]) => (
                  <article key={a}>
                    <i />
                    <strong>{a}</strong>
                    <small>{b}</small>
                  </article>
                ))}
              </div>
            </div>
            <div className="provenance-badges">
              <span>REAL</span>
              <span>SIMULATED</span>
              <span>SANDBOX</span>
              <p>Simulation provenance travels with the evidence.</p>
            </div>
          </div>
        </section>

        <section className="section fleet-section">
          <div className="section-inner">
            <SectionHeading
              eyebrow="09 // MULTI-ENDPOINT INVESTIGATIONS"
              title={
                <>
                  ONE HUNT. MULTIPLE ENDPOINTS.
                  <br />
                  INDEPENDENT EVIDENCE.
                </>
              }
            />
            <div className="fleet-diagram" data-reveal>
              <div className="hunt-node">
                <small>INVESTIGATION</small>
                <b>HUNT</b>
              </div>
              <div className="fleet-lines top">
                <i />
                <i />
                <i />
              </div>
              <div className="endpoints">
                {["01", "02", "03"].map((n, i) => (
                  <article key={n}>
                    <span>ENDPOINT {n}</span>
                    <b>JOB / {String.fromCharCode(65 + i)}</b>
                    <small>{i === 1 ? "TRUSTED RELAY" : "DIRECT"}</small>
                    <i>↓</i>
                    <em>EVIDENCE {n}</em>
                  </article>
                ))}
              </div>
              <div className="fleet-lines bottom">
                <i />
                <i />
                <i />
              </div>
              <div className="correlation-node">CORRELATION</div>
            </div>
            <div className="fleet-copy" data-reveal>
              <ul>
                {[
                  "Independent job per endpoint",
                  "Per-endpoint variant and execution mode",
                  "Isolated retry, failure, and cancellation",
                  "Partial aggregate states",
                  "Sibling evidence survives endpoint failure",
                ].map((x) => (
                  <li key={x}>+ {x}</li>
                ))}
              </ul>
              <div>
                <span>VERIFIED PROTOTYPE</span>
                <strong>3 independently enrolled Linux Agents</strong>
                <p>2 direct · 1 trusted relay · shared Docker host</p>
                <small>Not three physical machines.</small>
              </div>
            </div>
          </div>
        </section>

        <section className="section evidence-section" id="evidence">
          <div className="section-inner wide">
            <SectionHeading
              eyebrow="10 // EVIDENCE & TRUST"
              title={
                <>
                  DO NOT SAY “VERIFIED.”
                  <br />
                  <span>SHOW WHAT WAS VERIFIED.</span>
                </>
              }
              intro="Trust is decomposed into exact mechanisms, each with a boundary an operator can inspect."
            />
            <div className="trust-grid">
              {[
                [
                  "01",
                  "INTEGRITY",
                  "RFC 8785 canonical JSON + SHA-256",
                  "Stored bytes are re-read and re-hashed.",
                ],
                [
                  "02",
                  "AUTHENTICITY",
                  "Ed25519 evidence manifests",
                  "Producer signatures are verified separately.",
                ],
                [
                  "03",
                  "PROVENANCE",
                  "Identity carried end to end",
                  "Source → JIR → LLVM → artifact → endpoint → evidence.",
                ],
                [
                  "04",
                  "AUDIT CONTINUITY",
                  "Previous-hash audit chain",
                  "Append-only entries expose modification or discontinuity.",
                ],
              ].map(([n, t, d, p]) => (
                <article data-reveal key={t}>
                  <span>{n}</span>
                  <div className="trust-glyph">
                    <i />
                    <i />
                  </div>
                  <h3>{t}</h3>
                  <strong>{d}</strong>
                  <p>{p}</p>
                </article>
              ))}
            </div>
            <div className="audit-precision" data-reveal>
              <div>
                <span>MECHANISM</span>
                <strong>LINEAR HASH CHAIN</strong>
              </div>
              <p>
                <b>NO CRYPTOGRAPHIC MERKLE TREE CLAIM.</b>
                <br />
                Precise trust claims replace one vague green badge.
              </p>
              <code>H(n) = SHA-256(event || H(n-1))</code>
            </div>
            <IdentityChain />
          </div>
        </section>

        <section className="section intelligence-section" id="intelligence">
          <div className="section-inner">
            <SectionHeading
              eyebrow="11 // INTELLIGENCE LAYER"
              title={
                <>
                  FROM COLLECTION TO
                  <br />
                  INVESTIGATION INTELLIGENCE.
                </>
              }
            />
            <div className="intelligence-grid" data-reveal>
              {[
                ["FINDINGS", "Evidence-linked persisted findings", "↗"],
                [
                  "FORENSIC GRAPH",
                  "Endpoint → User → Process → Connection → IP → Evidence",
                  "⌁",
                ],
                [
                  "SEMANTIC TIMELINE",
                  "Normalized investigation narrative",
                  "≋",
                ],
                [
                  "DRIVER INTELLIGENCE",
                  "Driver and module inventory with risk context",
                  "◇",
                ],
                ["HUNT REPORTS", "Deterministic investigation reports", "▤"],
                [
                  "ARTIFACT VERIFICATION",
                  "Content-addressed evidence verification",
                  "✓",
                ],
              ].map(([a, b, c], i) => (
                <article key={a}>
                  <span>{String(i + 1).padStart(2, "0")}</span>
                  <i>{c}</i>
                  <h3>{a}</h3>
                  <p>{b}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section reports-section">
          <div className="section-inner">
            <SectionHeading
              eyebrow="12 // FORENSIC REPORTS"
              title="AN INVESTIGATION SHOULD EXPLAIN ITSELF."
              intro="The canonical artifact is hunt-scoped, deterministic, content-addressed, and re-hashed on retrieval."
            />
            <div className="report-layout">
              <div className="report-mock" data-reveal>
                <header>
                  <div>
                    <span>TATTVASTRA</span>
                    <small>REPORT STRUCTURE PREVIEW · NO LIVE DATA</small>
                  </div>
                  <code>REPORT IDENTITY</code>
                </header>
                <div className="report-body">
                  <aside>
                    {[
                      "Executive Summary",
                      "Investigation Intent",
                      "Endpoint Results",
                      "Findings",
                      "What JOCKY Observed",
                      "Attack Reconstruction",
                      "Activity Timeline",
                      "Compiler Provenance",
                      "Evidence Integrity",
                      "Executed Source",
                      "Limitations",
                      "Report Identity",
                    ].map((x, i) => (
                      <span className={i === 0 ? "active" : ""} key={x}>
                        {String(i + 1).padStart(2, "0")} {x}
                      </span>
                    ))}
                  </aside>
                  <div className="report-page">
                    <span>EXECUTIVE SUMMARY</span>
                    <h3>
                      Investigation results remain scoped to the selected Hunt.
                    </h3>
                    <p>
                      Results, findings, provenance, source, and limitations are
                      assembled from persisted investigation data.
                    </p>
                    <div className="report-stats">
                      <b>
                        —<small>ENDPOINTS</small>
                      </b>
                      <b>
                        —<small>SUCCESS</small>
                      </b>
                      <b>
                        —<small>FINDINGS</small>
                      </b>
                    </div>
                    <div className="report-warning">
                      <i />
                      ZERO FINDINGS IS NOT PROOF OF SAFETY.
                    </div>
                    <div className="report-lines">
                      <i />
                      <i />
                      <i />
                      <i />
                    </div>
                  </div>
                </div>
              </div>
              <div className="report-points" data-reveal>
                {[
                  "Hunt-scoped data boundary",
                  "Deterministic canonical JSON",
                  "Content-addressed storage",
                  "Stored bytes re-hashed on retrieval",
                  "Human-readable browser / PDF output",
                  "Explicit limitations and missing values",
                ].map((x, i) => (
                  <div key={x}>
                    <span>0{i + 1}</span>
                    <p>{x}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="section ai-section">
          <div className="section-inner wide">
            <SectionHeading
              eyebrow="13 // AI-ASSISTED HYPOTHESES"
              title={
                <>
                  AI AFTER EVIDENCE.
                  <br />
                  NOT IN PLACE OF IT.
                </>
              }
              intro="The canonical report comes first. A bounded report-derived brief can then produce exactly three structured hypotheses tied to report-owned evidence."
            />
            <div className="ai-chain" data-reveal>
              <span>EVIDENCE</span>
              <i>→</i>
              <span>CANONICAL REPORT</span>
              <i>→</i>
              <span>3 HYPOTHESES</span>
            </div>
            <div className="simulation-label">
              STRUCTURE PREVIEW // SIMULATION=TRUE // NOT CANONICAL EVIDENCE
            </div>
            <div className="hypothesis-grid" data-reveal>
              {[
                [
                  "01",
                  "Unsigned process with external activity",
                  "MODERATE",
                  ["ev-proc-04", "ev-net-09"],
                ],
                [
                  "02",
                  "Administrative tool execution",
                  "LOW",
                  ["ev-proc-11", "ev-user-02"],
                ],
                [
                  "03",
                  "Persistence change requires review",
                  "MODERATE",
                  ["ev-start-03", "ev-file-08"],
                ],
              ].map(([n, title, support, ev]) => (
                <article key={String(n)}>
                  <header>
                    <span>SIMULATED HYPOTHESIS {n}</span>
                    <em>{support} SUPPORT</em>
                  </header>
                  <h3>{title}</h3>
                  {[
                    "WHAT IT MAY MEAN",
                    "LIKELY INTENT",
                    "SUCCESS ASSESSMENT",
                    "TATTVASTRA RESPONSE",
                    "RECOMMENDED ACTION",
                    "UNCERTAINTY",
                  ].map((x) => (
                    <div className="hypo-line" key={x}>
                      <small>{x}</small>
                      <i />
                    </div>
                  ))}
                  <footer>
                    {(ev as string[]).map((x) => (
                      <code key={x}>evidence_id</code>
                    ))}
                  </footer>
                </article>
              ))}
            </div>
            <div className="ai-boundary">
              <p>
                AI cannot modify Findings or the canonical report. It cannot
                select platform actions outside the report-derived allowed set.
              </p>
              <strong>NEVER: AI → EVIDENCE</strong>
            </div>
          </div>
        </section>

        <section className="section python-section">
          <div className="section-inner">
            <SectionHeading
              eyebrow="14 // PYTHON INTEROPERABILITY"
              title={
                <>
                  EXTEND JOCKY.
                  <br />
                  WITHOUT BYPASSING JOCKY.
                </>
              }
            />
            <div className="python-grid">
              <div className="terminal-stack" data-reveal>
                <div className="terminal">
                  <header>
                    <span>● ● ●</span>
                    <b>jocky — packages</b>
                  </header>
                  <pre>
                    <code>
                      <i>$</i> jocky install humanize{`\n`}
                      <i>$</i> jocky install numpy{`\n`}
                      <i>$</i> jocky packages
                    </code>
                  </pre>
                </div>
                <div className="python-code">
                  <pre>
                    <code>{`hunt "Python Package Interop" {
  capabilities { python.interop }
  python import "humanize" as humanize
  python call humanize.intcomma(1234567) as formatted
}`}</code>
                  </pre>
                </div>
              </div>
              <div className="python-arch" data-reveal>
                {[
                  ".JKY SOURCE",
                  "C++ FRONTEND",
                  "PYTHON_CALL JIR",
                  "LLVM",
                  "jocky_rt_analysis",
                  "EMBEDDED CPYTHON",
                  "SCALAR RESULT",
                ].map((x, i) => (
                  <span key={x}>
                    {x}
                    {i < 6 ? <i>↓</i> : null}
                  </span>
                ))}
              </div>
            </div>
            <div className="python-boundary" data-reveal>
              <strong>PYTHON DOES NOT BYPASS THE COMPILER.</strong>
              <p>
                Isolated packages · typed imports and calls · bounded literal
                arguments · scalar results · local ORC execution
              </p>
              <small>Not unrestricted FFI. Not remote collection.</small>
            </div>
          </div>
        </section>

        <section className="section cli-section" id="developers">
          <div className="section-inner">
            <SectionHeading
              eyebrow="15 // JOCKY CLI"
              title="THE LANGUAGE EXISTS OUTSIDE THE DASHBOARD."
            />
            <div className="cli-terminal" data-reveal>
              <header>
                <span>
                  <i />
                  <i />
                  <i />
                </span>
                <b>~/investigations</b>
                <em>JOCKY CLI</em>
              </header>
              <pre>
                <code>{`$ jocky --version
$ jocky doctor
$ jocky check investigation.jky
$ jocky tokens investigation.jky
$ jocky ast investigation.jky
$ jocky jir investigation.jky
$ jocky llvm investigation.jky
$ jocky compile investigation.jky
$ jocky pipeline investigation.jky --count 3`}</code>
              </pre>
            </div>
            <div className="command-groups" data-reveal>
              {[
                [
                  "BUILD / INSPECT",
                  "check · tokens · ast · jir · plan · llvm · compile · run",
                ],
                [
                  "VARIANTS",
                  "variants · variant-info · diverge · diff · equivalence · forge",
                ],
                ["EXPLAIN", "caps · budget · types · metrics · fingerprint"],
                [
                  "VALIDATE",
                  "verify · manifest · benchmark · pipeline · doctor",
                ],
                ["PYTHON", "install · packages"],
              ].map(([a, b]) => (
                <article key={a}>
                  <span>{a}</span>
                  <p>{b}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section why-section">
          <div className="section-inner wide">
            <SectionHeading
              eyebrow="16 // PRODUCT PRINCIPLES"
              title="WHY TATTVASTRA?"
            />
            <div className="why-grid" data-reveal>
              {[
                [
                  "01",
                  "LANGUAGE-FIRST FORENSICS",
                  "One typed forensic intent instead of separate per-OS scripts.",
                ],
                [
                  "02",
                  "REAL COMPILER PIPELINE",
                  "C++20 frontend → typed JIR → mandatory LLVM.",
                ],
                [
                  "03",
                  "VERIFIED BUILD DIVERSITY",
                  "Controlled seeded variants with bounded equivalence and signed build provenance.",
                ],
                [
                  "04",
                  "CONSTRAINED EXECUTION",
                  "Authorized compiler output reaches JOCKY-owned workers through a fixed read-only runtime ABI.",
                ],
                [
                  "05",
                  "TRUTH-PRESERVING EVIDENCE",
                  "PARTIAL, DENIED, UNAVAILABLE, and SIMULATED remain explicit.",
                ],
                [
                  "06",
                  "END-TO-END PROVENANCE",
                  "Source → JIR → LLVM → variant → endpoint → evidence → report.",
                ],
              ].map(([n, a, b]) => (
                <article key={n}>
                  <span>{n}</span>
                  <h3>{a}</h3>
                  <p>{b}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section comparison-section">
          <div className="section-inner">
            <SectionHeading
              eyebrow="17 // ARCHITECTURAL CONTEXT"
              title="A DIFFERENT LAYER OF THE FORENSIC STACK."
              intro="TATTVASTRA complements the DFIR ecosystem by placing a typed language, compiler, and identity chain ahead of endpoint execution."
            />
            <div className="stack-comparison" data-reveal>
              <article>
                <header>EXISTING DFIR / ENDPOINT QUERY</header>
                {[
                  "Query or agent centric",
                  "Execution tied to an existing runtime or query model",
                  "Collection-oriented workflows",
                  "Platform-specific implementation abstractions",
                ].map((x) => (
                  <p key={x}>
                    <i /> {x}
                  </p>
                ))}
                <footer>
                  Examples include Velociraptor, osquery, and GRR.
                </footer>
              </article>
              <div className="versus">
                LAYER
                <br />
                CONTEXT
              </div>
              <article className="tattvastra-side">
                <header>TATTVASTRA / JOCKY</header>
                {[
                  "Language-first investigation intent",
                  "Typed forensic intermediate representation",
                  "Mandatory native compiler path",
                  "Controlled build diversity",
                  "Explicit capabilities and budgets",
                  "Compiler-to-evidence provenance",
                ].map((x) => (
                  <p key={x}>
                    <i /> {x}
                  </p>
                ))}
                <footer>
                  No unsupported performance or security superiority claim.
                </footer>
              </article>
            </div>
          </div>
        </section>

        <section className="section architecture-section" id="architecture">
          <div className="section-inner wide">
            <SectionHeading
              eyebrow="18 // REFERENCE ARCHITECTURE"
              title="FROM SOURCE TO EVIDENCE."
              intro="Every layer has one job. Identity and provenance cross all of them."
            />
            <div className="architecture-map" data-reveal>
              {[
                ["01", "JOCKY SOURCE", ".jky typed intent"],
                ["02", "C++20 FRONTEND", "Lexer · Parser · AST · Types"],
                ["03", "TYPED JIR", "Effects · capabilities · budgets"],
                ["04", "LLVM BACKEND", "IR · ORC LLJIT · AOT"],
                ["05", "BUILD FORGE", "Variants · target objects"],
                ["06", "CONTROL PLANE", "Signed jobs · policy"],
                ["07", "mTLS / RELAY", "Authenticated transport"],
                ["08", "RUST AGENTS", "Admission · supervision"],
                ["09", "COLLECTORS", "Fixed read-only ABI"],
                ["10", "OBSERVATIONS", "Normalized evidence"],
                ["11", "INVESTIGATION", "Findings · graph · timeline"],
                ["12", "TRUST", "Artifacts · manifests"],
                ["13", "HUNT REPORT", "Canonical report"],
                ["14", "OPTIONAL AI", "Bounded hypotheses"],
              ].map(([n, a, b], i) => (
                <div
                  className={
                    i === 0 || i === 13 ? "arch-node emphasis" : "arch-node"
                  }
                  key={n}
                >
                  <span>{n}</span>
                  <strong>{a}</strong>
                  <small>{b}</small>
                  {i < 13 ? <i>↓</i> : null}
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="section technology-section">
          <div className="section-inner">
            <SectionHeading
              eyebrow="19 // TECHNOLOGY"
              title="ENGINEERED ACROSS THE STACK."
            />
            <div className="technology-grid" data-reveal>
              {[
                ["C++20", "JOCKY frontend / JIR / compiler"],
                ["LLVM", "IR · ORC LLJIT · AOT"],
                ["RUST", "Endpoint Agent"],
                ["PYTHON / FASTAPI", "Control plane"],
                ["POSTGRESQL", "Persistent forensic state"],
                ["gRPC / PROTOBUF", "Agent protocol"],
                ["mTLS / OPENSSL", "Authenticated transport"],
                ["Ed25519", "Signed jobs / manifests"],
                ["AES-256-GCM", "Encrypted spool / protected literals"],
                ["NEXT.JS / TYPESCRIPT", "Operator console"],
                ["DOCKER", "Prototype environment"],
              ].map(([a, b], i) => (
                <article key={a}>
                  <span>{String(i + 1).padStart(2, "0")}</span>
                  <strong>{a}</strong>
                  <p>{b}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="section verified-section">
          <div className="section-inner wide">
            <SectionHeading
              eyebrow="20 // VERIFIED TODAY"
              title="BUILT. TESTED. DEMONSTRATED."
              intro="Repository-backed capabilities, separated from environment-dependent and planned work."
            />
            <div className="verification-layout">
              <div className="verified-list" data-reveal>
                {verified.map((x, i) => (
                  <div key={x}>
                    <span>✓</span>
                    <p>{x}</p>
                    <small>{String(i + 1).padStart(2, "0")}</small>
                  </div>
                ))}
              </div>
              <aside className="boundaries" data-reveal>
                <span>CURRENT BOUNDARIES</span>
                <h3>
                  ENGINEERING STATUS,
                  <br />
                  WITHOUT THE ASTERISKS.
                </h3>
                {[
                  "Live Windows endpoint execution pending validation",
                  "Hard CPU / RAM / network governance incomplete",
                  "Certificate rotation and production secret storage pending",
                  "External audit anchoring planned",
                  "Optional YARA / Volatility / osquery adapters not operational",
                ].map((x) => (
                  <p key={x}>
                    <i /> {x}
                  </p>
                ))}
              </aside>
            </div>
          </div>
        </section>

        <section className="section developer-section">
          <div className="section-inner">
            <SectionHeading
              eyebrow="21 // DEVELOPER EXPERIENCE"
              title="WRITE. INSPECT. COMPILE. VERIFY."
            />
            <div className="developer-grid" data-reveal>
              {[
                ["WORKBENCH", "Write and inspect .jky", "01"],
                ["COMPILER EXPLORER", "Tokens → AST → JIR → LLVM", "02"],
                ["BUILD FORGE", "Variant / artifact lifecycle", "03"],
                ["CLI", "Local compiler inspection and verification", "04"],
              ].map(([a, b, n]) => (
                <article key={a}>
                  <span>{n}</span>
                  <div className="developer-screen">
                    <i />
                    <i />
                    <i />
                    <b />
                  </div>
                  <h3>{a}</h3>
                  <p>{b}</p>
                </article>
              ))}
            </div>
            <a
              className="button centered-button"
              href={github}
              target="_blank"
              rel="noreferrer"
            >
              Explore the repository <span>↗</span>
            </a>
          </div>
        </section>

        <section className="section final-cta">
          <div className="cta-grid" />
          <div className="section-inner" data-reveal>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/tattvastra-mark.png" alt="" />
            <span className="eyebrow">TATTVASTRA // JOCKY</span>
            <h2>
              FORENSIC INTENT
              <br />
              SHOULD SURVIVE
              <br />
              <span>ALL THE WAY TO EVIDENCE.</span>
            </h2>
            <p>
              TATTVASTRA combines a typed forensic language, native compilation,
              controlled endpoint execution, and verifiable evidence into one
              traceable workflow.
            </p>
            <div className="hero-actions">
              <a className="button" href="#jocky">
                Explore JOCKY <span>↑</span>
              </a>
              <a
                className="text-link"
                href={github}
                target="_blank"
                rel="noreferrer"
              >
                View on GitHub <span>↗</span>
              </a>
            </div>
            <strong className="tagline">
              ONE LANGUAGE. <i>EVERY ENDPOINT.</i> NO NOISE.
            </strong>
          </div>
        </section>
      </main>
      <footer className="site-footer">
        <div className="footer-brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/tattvastra-mark.png" alt="" />
          <div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/tattvastra-wordmark.png" alt="TATTVASTRA" />
            <p>JOCKY · Cross-Platform Forensic Scripting Language</p>
          </div>
        </div>
        <nav aria-label="Footer navigation">
          <a href="#overview">Overview</a>
          <a href="#architecture">Architecture</a>
          <a href="#jocky">JOCKY</a>
          <a href="#evidence">Evidence</a>
          <a href={github} target="_blank" rel="noreferrer">
            GitHub ↗
          </a>
        </nav>
        <div className="footer-meta">
          <strong>TEAM ASHTOJ</strong>
          <span>Built for Smart India Hackathon 2026.</span>
        </div>
      </footer>
    </>
  );
}
