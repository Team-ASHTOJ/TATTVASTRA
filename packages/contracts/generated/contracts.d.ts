/* Generated from JOCKY Pydantic contracts. Do not edit. Runtime validation is required. */

export type ArtifactId = string;
export type CaseId = string;
export type CollectorId = string;
export type ContentHash = string;
export type EndpointId = string;
export type JobId = string;
export type MediaType = string;
export type SchemaVersion = "1.0.0";
export type Simulation = boolean;
export type SimulationLabel = string | null;
export type SizeBytes = number;
export type StorageKey = string;
export type Timestamp = string;
export type VariantId = string;
export type Action = string;
export type ActorId = string;
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "JsonValue".
 */
export type JsonValue = unknown;
export type IntegrityHash = string;
export type OrganizationId = string;
export type PreviousHash = string;
export type ResourceId = string;
export type SchemaVersion1 = "1.0.0";
export type Sequence = number;
export type Simulation1 = boolean;
export type SimulationLabel1 = string | null;
export type Timestamp1 = string;
export type CheckedEvents = number;
export type ExternallyAnchored = false;
export type FirstInvalidSequence = number | null;
export type IntegrityValid = boolean;
export type SchemaVersion2 = "1.0.0";
export type BenchmarkRunId = string;
export type AotCompileMs = number | null;
export type JirMs = number | null;
export type JitCompileMs = number | null;
export type LexMs = number | null;
export type LlvmGenerationMs = number | null;
export type OptimizeMs = number | null;
export type ParseMs = number | null;
export type PeakMemoryBytes = number | null;
export type SchemaVersion3 = "1.0.0";
export type SemanticMs = number | null;
export type Environment = string;
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "ExecutionMode".
 */
export type ExecutionMode = "native" | "memory" | "vm";
export type PeakMemoryBytes1 = number | null;
export type Repetitions = number;
export type RuntimeMs = number | null;
export type SchemaVersion4 = "1.0.0";
export type Simulation2 = boolean;
export type SimulationLabel2 = string | null;
export type VariantId1 = string;
export type CpuPercent = number;
export type DurationMs = number;
export type IoBytes = number;
export type MemoryBytes = number;
export type SchemaVersion5 = "1.0.0";
export type DemoEvidence = string;
export type Id = string;
export type Implementation = string;
export type Phase = string;
export type SafetyEnvironmentNote = string;
export type SchemaVersion6 = "1.0.0";
export type Simulation3 = boolean;
export type SimulationLabel3 = string | null;
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "ImplementationStatus".
 */
export type ImplementationStatus = "PLANNED" | "SCAFFOLDED" | "IMPLEMENTED" | "VERIFIED" | "BLOCKED_ENVIRONMENT";
export type Subsystem = string;
export type Title = string;
export type CaseId1 = string;
export type CreatedAt = string;
export type OrganizationId1 = string;
export type SchemaVersion7 = "1.0.0";
export type Simulation4 = boolean;
export type SimulationLabel4 = string | null;
export type State = "OPEN" | "CLOSED" | "ARCHIVED";
export type Title1 = string;
export type AlertObserved = "YES" | "NO" | "NOT_OBSERVED";
export type CompatibilityRunId = string;
export type Completed = boolean | null;
export type Correctness = "PASS" | "FAIL" | "NOT_MEASURED";
export type CpuPercent1 = number | null;
export type Environment1 = string;
export type Notes = string;
export type PeakMemoryBytes2 = number | null;
export type RuntimeMs1 = number | null;
export type SchemaVersion8 = "1.0.0";
export type SecurityProductLabel = string;
export type Simulation5 = boolean;
export type SimulationLabel5 = string | null;
export type VariantId2 = string;
export type CompilationId = string;
export type SchemaVersion9 = "1.0.0";
export type ScriptVersionId = string;
export type Simulation6 = boolean;
export type SimulationLabel6 = string | null;
export type SourceHash = string;
export type State1 = "REQUESTED" | "RUNNING" | "SUCCESS" | "FAILED" | "CANCELLED";
export type VariantIds = string[];
export type Profile = "minimal" | "balanced";
export type SchemaVersion10 = "1.0.0";
export type Simulation7 = boolean;
export type SimulationLabel7 = string | null;
export type Source = string;
export type Arch = "x86_64" | "aarch64";
export type Os = "windows" | "linux";
export type SchemaVersion11 = "1.0.0";
export type VariantSeed = string;
export type SchemaVersion12 = "1.0.0";
export type Code = string;
export type Column = number;
export type EndColumn = number;
export type EndLine = number;
export type Line = number;
export type Message = string;
export type SchemaVersion13 = "1.0.0";
export type Severity = "error" | "warning" | "info";
export type ActiveJobId = string | null;
export type AgentVersion = string;
export type Capabilities = string[];
export type CpuPercent2 = number | null;
export type EndpointId1 = string;
export type Hostname = string;
export type IdentityFingerprint = string;
export type LastSeen = string | null;
export type MemoryBytes1 = number | null;
export type OrganizationId2 = string;
export type SchemaVersion14 = "1.0.0";
export type Simulation8 = boolean;
export type SimulationLabel8 = string | null;
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "EndpointState".
 */
export type EndpointState =
  "ONLINE" | "IDLE" | "BUSY" | "OFFLINE" | "DEGRADED" | "QUARANTINED" | "UNTRUSTED" | "VERSION_MISMATCH";
export type Available = false;
/**
 * @maxItems 0
 */
export type Items = [];
export type Reason = string;
export type SchemaVersion15 = "1.0.0";
export type Simulation9 = boolean;
export type SimulationLabel9 = string | null;
export type AgentIdentity = string;
export type ArtifactHash = string;
export type CaseId2 = string;
export type CompletedAt = string;
export type EndpointId2 = string;
export type JirHash = string;
export type JobId1 = string;
export type LlvmIrHash = string;
export type ObservationHashes = string[];
export type SchemaVersion16 = "1.0.0";
export type Algorithm = "Ed25519" | null;
export type KeyId = string | null;
export type SchemaVersion17 = "1.0.0";
export type Status = "UNSIGNED" | "SIGNED" | "VERIFIED" | "INVALID" | "UNAVAILABLE";
export type ValueBase64 = string | null;
export type Simulation10 = boolean;
export type SimulationLabel10 = string | null;
export type SourceHash1 = string;
export type StartedAt = string;
export type VariantId3 = string;
export type VariantSeed1 = string;
export type CaseId3 = string;
/**
 * @minItems 1
 * @maxItems 1000
 */
export type EndpointIds = [string, ...string[]];
export type ExpiresAt = string;
export type JirHash1 = string;
export type PlanId = string;
export type PolicyVersion = string;
export type RequiredCapabilities = string[];
export type SchemaVersion18 = "1.0.0";
export type Simulation11 = boolean;
export type SimulationLabel11 = string | null;
export type SourceHash2 = string;
export type CaseId4 = string;
export type FindingId = string;
/**
 * @minItems 1
 */
export type ObservationIds = [string, ...string[]];
export type SchemaVersion19 = "1.0.0";
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Severity".
 */
export type Severity1 = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Simulation12 = boolean;
export type SimulationLabel12 = string | null;
export type Timestamp2 = string;
export type Title2 = string;
export type Reason1 = string | null;
export type SchemaVersion20 = "1.0.0";
export type Service = string;
export type Simulation13 = boolean;
export type SimulationLabel13 = string | null;
export type Status1 = "alive" | "not_ready";
export type Version = string;
export type ComputedHash = string;
export type ExpectedHash = string;
export type IntegrityValid1 = boolean;
export type ObservationId = string;
export type SchemaVersion21 = "1.0.0";
export type SignatureStatus = "NOT_CHECKED";
export type Simulation14 = boolean;
export type SimulationLabel14 = string | null;
export type VerificationScope = "SUBMITTED_OBSERVATION_ONLY";
export type Attempt = number;
export type CaseId5 = string;
export type EndpointId3 = string;
export type JobId2 = string;
export type PlanId1 = string;
export type RetryOf = string | null;
export type SchemaVersion22 = "1.0.0";
export type Simulation15 = boolean;
export type SimulationLabel15 = string | null;
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "JobState".
 */
export type JobState =
  | "CREATED"
  | "COMPILED"
  | "VALIDATED"
  | "QUEUED"
  | "DISPATCHED"
  | "RUNNING"
  | "SUCCESS"
  | "FAILED"
  | "CANCELLED"
  | "VERIFIED"
  | "ARCHIVED";
export type Algorithm1 = ("AES-256-GCM" | "ChaCha20-Poly1305") | null;
export type Enabled = boolean;
export type KeyId1 = string | null;
export type NoncePolicy = "unique-per-key-and-build" | null;
export type PoolHash = string | null;
export type SchemaVersion23 = "1.0.0";
export type CaseId6 = string;
export type CollectorId1 = string;
export type EndpointId4 = string;
export type IntegrityHash1 = string;
export type JirHash2 = string;
export type JobId3 = string;
export type ObservationId1 = string;
export type SchemaVersion24 = "1.0.0";
export type Simulation16 = boolean;
export type SimulationLabel16 = string | null;
export type SourceHash3 = string;
export type SourceTime = string | null;
export type Timestamp3 = string;
export type Type = string;
export type VariantId4 = string;
export type Name = string;
export type OrganizationId3 = string;
export type SchemaVersion25 = "1.0.0";
export type Simulation17 = boolean;
export type SimulationLabel17 = string | null;
export type Capabilities1 = CapabilityStatus[];
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Mode".
 */
export type Mode = "REAL" | "DEMO";
export type Name1 = "JOCKY";
export type ObservedAt = string;
export type Operational = boolean;
export type Phase1 = string;
export type SchemaVersion26 = "1.0.0";
export type Simulation18 = boolean;
export type SimulationLabel18 = string | null;
export type Tagline = "One Language. Every Endpoint. No Noise.";
export type Version1 = string;
export type Code1 = string;
export type Detail = string;
export type RequestId = string | null;
export type Retryable = boolean;
export type SchemaVersion27 = "1.0.0";
export type Simulation19 = boolean;
export type SimulationLabel19 = string | null;
export type Status2 = number;
export type SchemaVersion28 = "1.0.0";
export type Simulation20 = boolean;
export type SimulationLabel20 = string | null;
export type ArtifactId1 = string;
export type CaseId7 = string;
export type Format = "json" | "pdf";
export type GeneratedAt = string;
export type ReportId = string;
export type SchemaVersion29 = "1.0.0";
export type Simulation21 = boolean;
export type SimulationLabel21 = string | null;
export type Name2 = string;
export type OrganizationId4 = string;
export type SchemaVersion30 = "1.0.0";
export type ScriptId = string;
export type Simulation22 = boolean;
export type SimulationLabel22 = string | null;
export type CreatedAt1 = string;
export type SchemaVersion31 = "1.0.0";
export type ScriptId1 = string;
export type ScriptVersionId1 = string;
export type Simulation23 = boolean;
export type SimulationLabel23 = string | null;
export type Source1 = string;
export type SourceHash4 = string;
export type Version2 = number;
export type ArtifactHash1 = string;
export type CaseId8 = string;
export type EndpointId5 = string;
export type ExpiresAt1 = string;
export type IssuedAt = string;
export type JirHash3 = string;
export type JobId4 = string;
export type Nonce = string;
export type OrganizationId5 = string;
export type PlanId2 = string;
export type RequiredCapabilities1 = string[];
export type SchemaVersion32 = "1.0.0";
export type Simulation24 = boolean;
export type SimulationLabel24 = string | null;
export type SourceHash5 = string;
export type VariantId5 = string;
export type CaseId9 = string;
export type EndpointId6 = string;
export type EventId = string;
export type ObservationId2 = string;
export type SchemaVersion33 = "1.0.0";
export type Simulation25 = boolean;
export type SimulationLabel25 = string | null;
export type Summary = string;
export type TimeBasis = "source" | "collection";
export type Timestamp4 = string;
export type SchemaVersion34 = "1.0.0";
export type Simulation26 = boolean;
export type SimulationLabel26 = string | null;
export type Timestamp5 = string;
export type OrganizationId6 = string;
export type Role = "viewer" | "analyst" | "operator" | "administrator";
export type SchemaVersion35 = "1.0.0";
export type Simulation27 = boolean;
export type SimulationLabel27 = string | null;
export type Subject = string;
export type UserId = string;
export type ArtifactHash2 = string;
export type CompilerVersion = string;
export type CreatedAt2 = string;
export type JirHash4 = string;
export type LlvmIrHash1 = string;
export type LlvmVersion = string;
export type SchemaVersion36 = "1.0.0";
export type SemanticTestHash = string | null;
export type SemanticTestStatus = "NOT_RUN" | "PASS" | "FAIL";
export type Simulation28 = boolean;
export type SimulationLabel28 = string | null;
export type SourceHash6 = string;
export type TargetArch = "x86_64" | "aarch64";
export type TargetOs = "windows" | "linux";
export type VariantId6 = string;
export type VariantSeed2 = string;

/**
 * Generated from Pydantic; do not edit. Refinement rules also apply in Python.
 */
export interface JockyContracts {
  Artifact?: Artifact;
  AuditEvent?: AuditEvent;
  AuditVerification?: AuditVerification;
  BenchmarkRun?: BenchmarkRun;
  Budget?: Budget;
  CapabilityStatus?: CapabilityStatus;
  Case?: Case;
  CompatibilityRun?: CompatibilityRun;
  Compilation?: Compilation;
  CompileRequest?: CompileRequest;
  CompilerMetrics?: CompilerMetrics;
  Contract?: Contract;
  Diagnostic?: Diagnostic;
  Endpoint?: Endpoint;
  EndpointList?: EndpointList;
  EvidenceManifest?: EvidenceManifest;
  ExecutionPlan?: ExecutionPlan;
  Finding?: Finding;
  Health?: Health;
  IntegrityResult?: IntegrityResult;
  Job?: Job;
  LiteralEncryption?: LiteralEncryption;
  Observation?: Observation;
  Organization?: Organization;
  PlatformStatus?: PlatformStatus;
  Problem?: Problem;
  Provenance?: Provenance;
  Report?: Report;
  Script?: Script;
  ScriptVersion?: ScriptVersion;
  Signature?: Signature;
  SignedJob?: SignedJob;
  Target?: Target;
  TimelineEvent?: TimelineEvent;
  Timestamped?: Timestamped;
  User?: User;
  VariantManifest?: VariantManifest;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Artifact".
 */
export interface Artifact {
  artifact_id: ArtifactId;
  case_id: CaseId;
  collector_id: CollectorId;
  content_hash: ContentHash;
  endpoint_id: EndpointId;
  job_id: JobId;
  media_type: MediaType;
  schema_version?: SchemaVersion;
  simulation: Simulation;
  simulation_label?: SimulationLabel;
  size_bytes: SizeBytes;
  storage_key: StorageKey;
  timestamp: Timestamp;
  variant_id: VariantId;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "AuditEvent".
 */
export interface AuditEvent {
  action: Action;
  actor_id: ActorId;
  data: Data;
  integrity_hash: IntegrityHash;
  organization_id: OrganizationId;
  previous_hash: PreviousHash;
  resource_id: ResourceId;
  schema_version?: SchemaVersion1;
  sequence: Sequence;
  simulation: Simulation1;
  simulation_label?: SimulationLabel1;
  timestamp: Timestamp1;
}
export interface Data {
  [k: string]: JsonValue;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "AuditVerification".
 */
export interface AuditVerification {
  checked_events: CheckedEvents;
  externally_anchored?: ExternallyAnchored;
  first_invalid_sequence: FirstInvalidSequence;
  integrity_valid: IntegrityValid;
  schema_version?: SchemaVersion2;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "BenchmarkRun".
 */
export interface BenchmarkRun {
  benchmark_run_id: BenchmarkRunId;
  compiler_metrics: CompilerMetrics;
  environment: Environment;
  execution_mode: ExecutionMode;
  peak_memory_bytes?: PeakMemoryBytes1;
  repetitions: Repetitions;
  runtime_ms?: RuntimeMs;
  schema_version?: SchemaVersion4;
  simulation: Simulation2;
  simulation_label?: SimulationLabel2;
  variant_id: VariantId1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "CompilerMetrics".
 */
export interface CompilerMetrics {
  aot_compile_ms?: AotCompileMs;
  jir_ms?: JirMs;
  jit_compile_ms?: JitCompileMs;
  lex_ms?: LexMs;
  llvm_generation_ms?: LlvmGenerationMs;
  optimize_ms?: OptimizeMs;
  parse_ms?: ParseMs;
  peak_memory_bytes?: PeakMemoryBytes;
  schema_version?: SchemaVersion3;
  semantic_ms?: SemanticMs;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Budget".
 */
export interface Budget {
  cpu_percent: CpuPercent;
  duration_ms: DurationMs;
  io_bytes: IoBytes;
  memory_bytes: MemoryBytes;
  schema_version?: SchemaVersion5;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "CapabilityStatus".
 */
export interface CapabilityStatus {
  demo_evidence: DemoEvidence;
  id: Id;
  implementation: Implementation;
  phase: Phase;
  safety_environment_note: SafetyEnvironmentNote;
  schema_version?: SchemaVersion6;
  simulation: Simulation3;
  simulation_label?: SimulationLabel3;
  status: ImplementationStatus;
  subsystem: Subsystem;
  title: Title;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Case".
 */
export interface Case {
  case_id: CaseId1;
  created_at: CreatedAt;
  organization_id: OrganizationId1;
  schema_version?: SchemaVersion7;
  simulation: Simulation4;
  simulation_label?: SimulationLabel4;
  state: State;
  title: Title1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "CompatibilityRun".
 */
export interface CompatibilityRun {
  alert_observed: AlertObserved;
  compatibility_run_id: CompatibilityRunId;
  completed: Completed;
  correctness: Correctness;
  cpu_percent?: CpuPercent1;
  environment: Environment1;
  execution_mode: ExecutionMode;
  notes: Notes;
  peak_memory_bytes?: PeakMemoryBytes2;
  runtime_ms?: RuntimeMs1;
  schema_version?: SchemaVersion8;
  security_product_label: SecurityProductLabel;
  simulation: Simulation5;
  simulation_label?: SimulationLabel5;
  variant_id: VariantId2;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Compilation".
 */
export interface Compilation {
  compilation_id: CompilationId;
  metrics: CompilerMetrics;
  schema_version?: SchemaVersion9;
  script_version_id: ScriptVersionId;
  simulation: Simulation6;
  simulation_label?: SimulationLabel6;
  source_hash: SourceHash;
  state: State1;
  variant_ids: VariantIds;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "CompileRequest".
 */
export interface CompileRequest {
  execution_mode: ExecutionMode;
  profile?: Profile;
  schema_version?: SchemaVersion10;
  simulation: Simulation7;
  simulation_label?: SimulationLabel7;
  source: Source;
  target: Target;
  variant_seed?: VariantSeed;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Target".
 */
export interface Target {
  arch: Arch;
  os: Os;
  schema_version?: SchemaVersion11;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Contract".
 */
export interface Contract {
  schema_version?: SchemaVersion12;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Diagnostic".
 */
export interface Diagnostic {
  code: Code;
  column: Column;
  end_column: EndColumn;
  end_line: EndLine;
  line: Line;
  message: Message;
  schema_version?: SchemaVersion13;
  severity: Severity;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Endpoint".
 */
export interface Endpoint {
  active_job_id?: ActiveJobId;
  agent_version: AgentVersion;
  capabilities: Capabilities;
  cpu_percent?: CpuPercent2;
  endpoint_id: EndpointId1;
  hostname: Hostname;
  identity_fingerprint: IdentityFingerprint;
  last_seen: LastSeen;
  memory_bytes?: MemoryBytes1;
  organization_id: OrganizationId2;
  schema_version?: SchemaVersion14;
  simulation: Simulation8;
  simulation_label?: SimulationLabel8;
  state: EndpointState;
  target: Target;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "EndpointList".
 */
export interface EndpointList {
  available?: Available;
  items?: Items;
  reason: Reason;
  schema_version?: SchemaVersion15;
  simulation: Simulation9;
  simulation_label?: SimulationLabel9;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "EvidenceManifest".
 */
export interface EvidenceManifest {
  agent_identity: AgentIdentity;
  artifact_hash: ArtifactHash;
  case_id: CaseId2;
  completed_at: CompletedAt;
  endpoint_id: EndpointId2;
  execution_mode: ExecutionMode;
  jir_hash: JirHash;
  job_id: JobId1;
  llvm_ir_hash: LlvmIrHash;
  observation_hashes: ObservationHashes;
  schema_version?: SchemaVersion16;
  signature: Signature;
  simulation: Simulation10;
  simulation_label?: SimulationLabel10;
  source_hash: SourceHash1;
  started_at: StartedAt;
  variant_id: VariantId3;
  variant_seed: VariantSeed1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Signature".
 */
export interface Signature {
  algorithm?: Algorithm;
  key_id?: KeyId;
  schema_version?: SchemaVersion17;
  status: Status;
  value_base64?: ValueBase64;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "ExecutionPlan".
 */
export interface ExecutionPlan {
  budget: Budget;
  case_id: CaseId3;
  endpoint_ids: EndpointIds;
  execution_mode: ExecutionMode;
  expires_at: ExpiresAt;
  jir_hash: JirHash1;
  plan_id: PlanId;
  policy_version: PolicyVersion;
  required_capabilities: RequiredCapabilities;
  schema_version?: SchemaVersion18;
  simulation: Simulation11;
  simulation_label?: SimulationLabel11;
  source_hash: SourceHash2;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Finding".
 */
export interface Finding {
  case_id: CaseId4;
  finding_id: FindingId;
  observation_ids: ObservationIds;
  schema_version?: SchemaVersion19;
  severity: Severity1;
  simulation: Simulation12;
  simulation_label?: SimulationLabel12;
  timestamp: Timestamp2;
  title: Title2;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Health".
 */
export interface Health {
  reason?: Reason1;
  schema_version?: SchemaVersion20;
  service: Service;
  simulation: Simulation13;
  simulation_label?: SimulationLabel13;
  status: Status1;
  version: Version;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "IntegrityResult".
 */
export interface IntegrityResult {
  computed_hash: ComputedHash;
  expected_hash: ExpectedHash;
  integrity_valid: IntegrityValid1;
  observation_id: ObservationId;
  schema_version?: SchemaVersion21;
  signature_status?: SignatureStatus;
  simulation: Simulation14;
  simulation_label?: SimulationLabel14;
  verification_scope?: VerificationScope;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Job".
 */
export interface Job {
  attempt: Attempt;
  case_id: CaseId5;
  endpoint_id: EndpointId3;
  job_id: JobId2;
  plan_id: PlanId1;
  retry_of?: RetryOf;
  schema_version?: SchemaVersion22;
  simulation: Simulation15;
  simulation_label?: SimulationLabel15;
  state: JobState;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "LiteralEncryption".
 */
export interface LiteralEncryption {
  algorithm?: Algorithm1;
  enabled: Enabled;
  key_id?: KeyId1;
  nonce_policy?: NoncePolicy;
  pool_hash?: PoolHash;
  schema_version?: SchemaVersion23;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Observation".
 */
export interface Observation {
  case_id: CaseId6;
  collector_id: CollectorId1;
  data: Data1;
  endpoint_id: EndpointId4;
  integrity_hash: IntegrityHash1;
  jir_hash: JirHash2;
  job_id: JobId3;
  observation_id: ObservationId1;
  schema_version?: SchemaVersion24;
  simulation: Simulation16;
  simulation_label?: SimulationLabel16;
  source_hash: SourceHash3;
  source_time: SourceTime;
  timestamp: Timestamp3;
  type: Type;
  variant_id: VariantId4;
}
export interface Data1 {
  [k: string]: JsonValue;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Organization".
 */
export interface Organization {
  name: Name;
  organization_id: OrganizationId3;
  schema_version?: SchemaVersion25;
  simulation: Simulation17;
  simulation_label?: SimulationLabel17;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "PlatformStatus".
 */
export interface PlatformStatus {
  capabilities: Capabilities1;
  mode: Mode;
  name?: Name1;
  observed_at: ObservedAt;
  operational: Operational;
  phase: Phase1;
  schema_version?: SchemaVersion26;
  simulation: Simulation18;
  simulation_label?: SimulationLabel18;
  tagline: Tagline;
  version: Version1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Problem".
 */
export interface Problem {
  code: Code1;
  detail: Detail;
  request_id?: RequestId;
  retryable?: Retryable;
  schema_version?: SchemaVersion27;
  simulation: Simulation19;
  simulation_label?: SimulationLabel19;
  status: Status2;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Provenance".
 */
export interface Provenance {
  schema_version?: SchemaVersion28;
  simulation: Simulation20;
  simulation_label?: SimulationLabel20;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Report".
 */
export interface Report {
  artifact_id: ArtifactId1;
  case_id: CaseId7;
  format: Format;
  generated_at: GeneratedAt;
  report_id: ReportId;
  schema_version?: SchemaVersion29;
  simulation: Simulation21;
  simulation_label?: SimulationLabel21;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Script".
 */
export interface Script {
  name: Name2;
  organization_id: OrganizationId4;
  schema_version?: SchemaVersion30;
  script_id: ScriptId;
  simulation: Simulation22;
  simulation_label?: SimulationLabel22;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "ScriptVersion".
 */
export interface ScriptVersion {
  created_at: CreatedAt1;
  schema_version?: SchemaVersion31;
  script_id: ScriptId1;
  script_version_id: ScriptVersionId1;
  simulation: Simulation23;
  simulation_label?: SimulationLabel23;
  source: Source1;
  source_hash: SourceHash4;
  version: Version2;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "SignedJob".
 */
export interface SignedJob {
  artifact_hash: ArtifactHash1;
  budget: Budget;
  case_id: CaseId8;
  endpoint_id: EndpointId5;
  execution_mode: ExecutionMode;
  expires_at: ExpiresAt1;
  issued_at: IssuedAt;
  jir_hash: JirHash3;
  job_id: JobId4;
  nonce: Nonce;
  organization_id: OrganizationId5;
  plan_id: PlanId2;
  required_capabilities: RequiredCapabilities1;
  schema_version?: SchemaVersion32;
  signature: Signature;
  simulation: Simulation24;
  simulation_label?: SimulationLabel24;
  source_hash: SourceHash5;
  variant_id: VariantId5;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "TimelineEvent".
 */
export interface TimelineEvent {
  case_id: CaseId9;
  endpoint_id: EndpointId6;
  event_id: EventId;
  observation_id: ObservationId2;
  schema_version?: SchemaVersion33;
  severity: Severity1;
  simulation: Simulation25;
  simulation_label?: SimulationLabel25;
  summary: Summary;
  time_basis: TimeBasis;
  timestamp: Timestamp4;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Timestamped".
 */
export interface Timestamped {
  schema_version?: SchemaVersion34;
  simulation: Simulation26;
  simulation_label?: SimulationLabel26;
  timestamp: Timestamp5;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "User".
 */
export interface User {
  organization_id: OrganizationId6;
  role: Role;
  schema_version?: SchemaVersion35;
  simulation: Simulation27;
  simulation_label?: SimulationLabel27;
  subject: Subject;
  user_id: UserId;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "VariantManifest".
 */
export interface VariantManifest {
  artifact_hash: ArtifactHash2;
  compiler_version: CompilerVersion;
  created_at: CreatedAt2;
  execution_mode: ExecutionMode;
  jir_hash: JirHash4;
  literal_encryption: LiteralEncryption;
  llvm_ir_hash: LlvmIrHash1;
  llvm_version: LlvmVersion;
  schema_version?: SchemaVersion36;
  semantic_test_hash: SemanticTestHash;
  semantic_test_status: SemanticTestStatus;
  signature: Signature;
  simulation: Simulation28;
  simulation_label?: SimulationLabel28;
  source_hash: SourceHash6;
  target_arch: TargetArch;
  target_os: TargetOs;
  variant_id: VariantId6;
  variant_seed: VariantSeed2;
}
