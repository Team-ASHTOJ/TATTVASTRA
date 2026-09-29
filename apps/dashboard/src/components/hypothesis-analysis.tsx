"use client";

type StaticHypothesis = {
  rank: number;
  title: string;
  confidence: "HIGH" | "MODERATE";
  narrative: string;
  attackerObjective: string;
  analysis: string;
  indicators: string[];
  response: string[];
};

const hypotheses: StaticHypothesis[] = [
  {
    rank: 1,
    title: "Unauthorized Service Used as an Initial Foothold",
    confidence: "HIGH",
    narrative:
      "Our primary hypothesis is that an attacker launched or repurposed a network-facing service to establish an initial foothold inside the investigated environment.",
    attackerObjective:
      "Maintain remote access while blending into normal application or container traffic.",
    analysis:
      "A listening service associated with a scripting runtime can be legitimate, but in an intrusion it can also act as a lightweight command channel, staging server, or operator-controlled backdoor. The activity should be treated as suspicious until the service owner, deployment source, parent process, and expected port binding are verified.",
    indicators: [
      "Unexpected service or listener exposed from a scripting runtime",
      "Process ownership or launch context inconsistent with the approved baseline",
      "Network activity that cannot be tied to a documented workload",
    ],
    response: [
      "Identify the service owner, parent process, image, command line, and deployment source",
      "Restrict the listener while preserving process and network evidence",
      "Review adjacent authentication and connection activity for the same endpoint",
    ],
  },
  {
    rank: 2,
    title: "Container or Runtime Masquerading for Command Execution",
    confidence: "MODERATE",
    narrative:
      "A second hypothesis is that an attacker attempted to hide command execution inside a containerized or interpreter-based workload that would appear routine during a quick review.",
    attackerObjective:
      "Execute tools and stage follow-on activity under the identity of a trusted runtime.",
    analysis:
      "Attackers frequently abuse legitimate interpreters and container processes because their presence alone is not unusual. The meaningful distinction is whether the executable path, arguments, ancestry, user, image provenance, and outbound connections match the known deployment. A mismatch would increase the likelihood of living-off-the-land execution or a compromised workload.",
    indicators: [
      "Interpreter or container process with unusual ancestry or arguments",
      "Runtime-generated network connections outside the expected service path",
      "Executable, image, or package provenance that differs from the approved build",
    ],
    response: [
      "Compare process ancestry and command lines with the deployment manifest",
      "Verify image, executable, and package hashes against trusted build records",
      "Inspect sibling processes and outbound destinations for coordinated activity",
    ],
  },
  {
    rank: 3,
    title: "Reconnaissance Followed by Persistence Preparation",
    confidence: "MODERATE",
    narrative:
      "Our third hypothesis is that the observed activity represents early-stage reconnaissance intended to identify reachable services and prepare a durable return path.",
    attackerObjective:
      "Map the host and network, identify useful services, and prepare persistence without immediately triggering a destructive action.",
    analysis:
      "Process, connection, service, startup, and driver observations are most useful when interpreted as a sequence. A short-lived discovery process followed by a new listener, startup change, scheduled task, service modification, or unusual module would support this hypothesis. Absence of one element does not disprove it when collector visibility is partial.",
    indicators: [
      "Discovery-like process activity near the first unusual network event",
      "New or modified service, startup entry, or scheduled task",
      "Repeated access from the same process or endpoint after the initial event",
    ],
    response: [
      "Correlate process, connection, service, startup, task, and driver timelines",
      "Preserve relevant artifacts before containment changes the host state",
      "Hunt for the same process, destination, hash, or persistence pattern elsewhere",
    ],
  },
];

function CompactList({ values }: { values: string[] }) {
  return (
    <ul className="hypothesis-list">
      {values.map((value) => (
        <li key={value}>{value}</li>
      ))}
    </ul>
  );
}

export function HypothesisAnalysis() {
  return (
    <section className="panel hypothesis-section">
      <div className="hypothesis-heading">
        <div>
          <span className="badge hypothesis-badge">AI ANALYSIS</span>
          <h2>Investigation Hypothesis Analysis</h2>
        </div>
      </div>
      <p>
        Three deterministic analyst hypotheses for the current prototype. These
        are investigative theories to validate against evidence, not verified
        findings or claims of compromise.
      </p>
      <div className="hypothesis-assessment">
        <h3>Overall Assessment</h3>
        <p>
          The activity is consistent with a possible staged intrusion attempt:
          establish access through a service or trusted runtime, blend execution
          into normal workloads, then perform discovery and prepare a return
          path. The investigation should test each stage against process
          ancestry, network ownership, artifact provenance, persistence records,
          and the endpoint timeline.
        </p>
      </div>
      <div className="hypothesis-cards">
        {hypotheses.map((hypothesis) => (
          <article className="hypothesis-card" key={hypothesis.rank}>
            <div className="hypothesis-card-head">
              <span>HYPOTHESIS {String(hypothesis.rank).padStart(2, "0")}</span>
              <span className="badge">{hypothesis.confidence} PRIORITY</span>
            </div>
            <h3>{hypothesis.title}</h3>
            <div className="hypothesis-grid">
              <div>
                <h4>Hypothesis</h4>
                <p>{hypothesis.narrative}</p>
              </div>
              <div>
                <h4>Possible Attacker Objective</h4>
                <p>{hypothesis.attackerObjective}</p>
              </div>
              <div className="hypothesis-analysis-copy">
                <h4>Analyst Assessment</h4>
                <p>{hypothesis.analysis}</p>
              </div>
              <div>
                <h4>Indicators to Validate</h4>
                <CompactList values={hypothesis.indicators} />
              </div>
              <div>
                <h4>Recommended Investigation</h4>
                <CompactList values={hypothesis.response} />
              </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
