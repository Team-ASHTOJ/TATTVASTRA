/* Generated from JOCKY Pydantic contracts. Do not edit. Runtime validation is required. */

export type Collector = string;
export type Hash = boolean;
export type Limit = number;
export type Path = string | null;
export type Recursive = boolean;
export type SchemaVersion = "1.0.0";
export type Concurrency = "ENFORCED" | "OBSERVED_ONLY" | "UNSUPPORTED";
export type Cpu = "ENFORCED" | "OBSERVED_ONLY" | "UNSUPPORTED";
export type FileBytes = "ENFORCED" | "OBSERVED_ONLY" | "UNSUPPORTED";
export type FileCount = "ENFORCED" | "OBSERVED_ONLY" | "UNSUPPORTED";
export type Memory = "ENFORCED" | "OBSERVED_ONLY" | "UNSUPPORTED";
export type NetworkBytes = "ENFORCED" | "OBSERVED_ONLY" | "UNSUPPORTED";
export type ResultSize = "ENFORCED" | "OBSERVED_ONLY" | "UNSUPPORTED";
export type SchemaVersion1 = "1.0.0";
export type Timeout = "ENFORCED" | "OBSERVED_ONLY" | "UNSUPPORTED";
export type CaseId = string;
export type Collector1 = string;
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "JsonValue".
 */
export type JsonValue = unknown;
export type EndpointId = string;
export type IntegrityHash = string;
export type JobId = string;
export type ObservationId = string;
export type ObservedAt = string;
export type Arch = "x86_64" | "aarch64";
export type Os = "windows" | "linux";
export type SchemaVersion2 = "1.0.0";
export type SchemaVersion3 = "1.0.0";
export type Simulation = boolean;
export type SimulationLabel = string | null;
export type SourceTime = string | null;
export type CpuPercent = number;
export type DurationMs = number;
export type IoBytes = number;
export type MaxFileBytes = number;
export type MaxFileCount = number;
export type MaxResultBytes = number;
export type MemoryBytes = number;
export type SchemaVersion4 = "1.0.0";
export type CaseId1 = string;
/**
 * @minItems 1
 * @maxItems 1000
 */
export type Collectors = [AgentCollectorRequest, ...AgentCollectorRequest[]];
export type EndpointId1 = string;
export type EnforcementPolicy = "STRICT" | "MONITORED";
export type ExpiresAt = string;
export type IssuedAt = string;
export type JobId1 = string;
export type Nonce = string;
export type OrganizationId = string;
export type RequiredCapabilities = string[];
export type SchemaVersion5 = "1.0.0";
export type Algorithm = "Ed25519" | null;
export type KeyId = string | null;
export type SchemaVersion6 = "1.0.0";
export type Status = "UNSIGNED" | "SIGNED" | "VERIFIED" | "INVALID" | "UNAVAILABLE";
export type ValueBase64 = string | null;
export type Simulation1 = boolean;
export type SimulationLabel1 = string | null;
export type ArtifactId = string;
export type CaseId2 = string;
export type CollectorId = string;
export type ContentHash = string;
export type EndpointId2 = string;
export type JobId2 = string;
export type MediaType = string;
export type SchemaVersion7 = "1.0.0";
export type Simulation2 = boolean;
export type SimulationLabel2 = string | null;
export type SizeBytes = number;
export type StorageKey = string;
export type Timestamp = string;
export type VariantId = string;
export type ContentBase64 = string;
export type ContentHash1 = string;
export type JobId3 = string;
export type MediaType1 = string;
export type SchemaVersion8 = "1.0.0";
export type Simulation3 = boolean;
export type SimulationLabel3 = string | null;
export type Action = string;
export type ActorId = string;
export type IntegrityHash1 = string;
export type OrganizationId1 = string;
export type PreviousHash = string;
export type ResourceId = string;
export type SchemaVersion9 = "1.0.0";
export type Sequence = number;
export type Simulation4 = boolean;
export type SimulationLabel4 = string | null;
export type Timestamp1 = string;
export type CheckedEvents = number;
export type ExternallyAnchored = false;
export type FirstInvalidSequence = number | null;
export type IntegrityValid = boolean;
export type SchemaVersion10 = "1.0.0";
export type CompilationId = string;
export type Repetitions = number;
export type SchemaVersion11 = "1.0.0";
export type BenchmarkRunId = string;
export type AotCompileMs = number | null;
export type AotMs = number | null;
export type ExecutionMs = number | null;
export type JirMs = number | null;
export type JitCompileMs = number | null;
export type LexMs = number | null;
export type LlvmGenerationMs = number | null;
export type OptimizationMs = number | null;
export type OptimizeMs = number | null;
export type ParseMs = number | null;
export type PeakMemoryBytes = number | null;
export type SchemaVersion12 = "1.0.0";
export type SemanticMs = number | null;
export type VariantMs = number | null;
export type Environment = string;
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "ExecutionMode".
 */
export type ExecutionMode = "native" | "memory" | "vm";
export type PeakMemoryBytes1 = number | null;
export type Repetitions1 = number;
export type RuntimeMs = number | null;
export type SchemaVersion13 = "1.0.0";
export type Simulation5 = boolean;
export type SimulationLabel5 = string | null;
export type VariantId1 = string;
export type CpuPercent1 = number;
export type DurationMs1 = number;
export type IoBytes1 = number;
export type MemoryBytes1 = number;
export type SchemaVersion14 = "1.0.0";
export type DemoEvidence = string;
export type Id = string;
export type Implementation = string;
export type Phase = string;
export type SafetyEnvironmentNote = string;
export type SchemaVersion15 = "1.0.0";
export type Simulation6 = boolean;
export type SimulationLabel6 = string | null;
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "ImplementationStatus".
 */
export type ImplementationStatus = "PLANNED" | "SCAFFOLDED" | "IMPLEMENTED" | "VERIFIED" | "BLOCKED_ENVIRONMENT";
export type Subsystem = string;
export type Title = string;
export type CaseId3 = string;
export type CreatedAt = string;
export type OrganizationId2 = string;
export type SchemaVersion16 = "1.0.0";
export type Simulation7 = boolean;
export type SimulationLabel7 = string | null;
export type State = "OPEN" | "CLOSED" | "ARCHIVED";
export type Title1 = string;
export type Description = string;
export type SchemaVersion17 = "1.0.0";
export type Simulation8 = boolean;
export type SimulationLabel8 = string | null;
export type Title2 = string;
export type Description1 = string | null;
export type SchemaVersion18 = "1.0.0";
export type Status1 = ("OPEN" | "CLOSED") | null;
export type Title3 = string | null;
export type AlertObserved = "YES" | "NO" | "NOT_OBSERVED";
export type Correctness = "PASS" | "FAIL" | "NOT_MEASURED";
export type Environment1 = string;
export type Notes = string;
export type SchemaVersion19 = "1.0.0";
export type SecurityProductLabel = string;
export type VariantId2 = string;
export type AlertObserved1 = "YES" | "NO" | "NOT_OBSERVED";
export type CompatibilityRunId = string;
export type Completed = boolean | null;
export type Correctness1 = "PASS" | "FAIL" | "NOT_MEASURED";
export type CpuPercent2 = number | null;
export type Environment2 = string;
export type Notes1 = string;
export type PeakMemoryBytes2 = number | null;
export type RuntimeMs1 = number | null;
export type SchemaVersion20 = "1.0.0";
export type SecurityProductLabel1 = string;
export type Simulation9 = boolean;
export type SimulationLabel9 = string | null;
export type VariantId3 = string;
export type CompilationId1 = string;
export type SchemaVersion21 = "1.0.0";
export type ScriptVersionId = string;
export type Simulation10 = boolean;
export type SimulationLabel10 = string | null;
export type SourceHash = string;
export type State1 = "REQUESTED" | "RUNNING" | "SUCCESS" | "FAILED" | "CANCELLED";
export type VariantIds = string[];
export type Command = "check" | "tokens" | "ast" | "jir" | "plan" | "llvm" | "run";
export type Profile = "minimal" | "balanced";
export type SchemaVersion22 = "1.0.0";
export type Simulation11 = boolean;
export type SimulationLabel11 = string | null;
export type Source = string;
export type Arch1 = "x86_64" | "aarch64";
export type Os1 = "windows" | "linux";
export type SchemaVersion23 = "1.0.0";
export type VariantSeed = string;
export type SchemaVersion24 = "1.0.0";
export type Code = string;
export type Column = number;
export type EndColumn = number;
export type EndLine = number;
export type Line = number;
export type Message = string;
export type SchemaVersion25 = "1.0.0";
export type Severity = "error" | "warning" | "info";
export type ActiveJobId = string | null;
export type AgentVersion = string;
export type Capabilities = string[];
export type CpuPercent3 = number | null;
export type EndpointId3 = string;
export type Hostname = string;
export type IdentityFingerprint = string;
export type LastSeen = string | null;
export type MemoryBytes2 = number | null;
export type OrganizationId3 = string;
export type SchemaVersion26 = "1.0.0";
export type Simulation12 = boolean;
export type SimulationLabel12 = string | null;
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
export type SchemaVersion27 = "1.0.0";
export type Simulation13 = boolean;
export type SimulationLabel13 = string | null;
/**
 * @minItems 1
 * @maxItems 100
 */
export type Capabilities1 = [string, ...string[]];
export type SchemaVersion28 = "1.0.0";
export type Simulation14 = boolean;
export type SimulationLabel14 = string | null;
export type ValiditySeconds = number;
export type AgentIdentity = string;
export type ArtifactHash = string;
export type CaseId4 = string;
export type CompletedAt = string;
export type EndpointId4 = string;
export type JirHash = string;
export type JobId4 = string;
export type LlvmIrHash = string;
export type ObservationHashes = string[];
export type SchemaVersion29 = "1.0.0";
export type Simulation15 = boolean;
export type SimulationLabel15 = string | null;
export type SourceHash1 = string;
export type StartedAt = string;
export type VariantId4 = string;
export type VariantSeed1 = string;
export type CaseId5 = string;
/**
 * @minItems 1
 * @maxItems 1000
 */
export type EndpointIds = [string, ...string[]];
export type ExpiresAt1 = string;
export type JirHash1 = string;
export type PlanId = string;
export type PolicyVersion = string;
export type RequiredCapabilities1 = string[];
export type SchemaVersion30 = "1.0.0";
export type Simulation16 = boolean;
export type SimulationLabel16 = string | null;
export type SourceHash2 = string;
export type CaseId6 = string;
export type FindingId = string;
/**
 * @minItems 1
 */
export type ObservationIds = [string, ...string[]];
export type SchemaVersion31 = "1.0.0";
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Severity".
 */
export type Severity1 = "INFO" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Simulation17 = boolean;
export type SimulationLabel17 = string | null;
export type Timestamp2 = string;
export type Title4 = string;
export type Executable = false;
export type Hunt = string;
export type InstructionCount = number;
export type JirHash2 = string;
export type Kind = "FrontendCheck";
export type SchemaVersion32 = "1.0.0";
export type SourceHash3 = string;
export type Valid = true;
export type Code1 = string;
export type Help = string;
export type Message1 = string;
export type Severity2 = "error" | "warning";
export type SourceLine = string | null;
export type Column1 = number;
export type Line1 = number;
export type Offset = number;
export type Warnings = FrontendDiagnostic[];
export type AdmissionStatus = "REQUIRES_ENDPOINT_POLICY_AND_LLVM_LOWERING";
export type Dispatchable = false;
export type InstructionId = number;
export type Domain = string;
export type Name = string;
export type Nullable = boolean;
export type ExpectedResultSchemas = ResultSchema[];
export type JirHash3 = string;
export type Kind1 = "FrontendExecutionPlan";
export type Fields1 = string[];
export type InstructionId1 = number;
export type ProjectedFields = ProjectedFields1[];
export type Applied = false;
export type BranchInstructionId = number;
export type CollectorInstructionId = number;
export type Condition = "REQUIRES_ADAPTER_SUPPORT_AND_BRANCH_DEPENDENCY_PRESERVATION";
export type Kind2 = "filter" | "project";
export type Scope = "BRANCH_LOCAL";
export type Pushdown = PushdownCandidate[];
export type RequiredCapabilities2 = string[];
export type RequiredCollectors = string[];
export type Backend = "llvm";
export type Execution = "native" | "memory";
export type Enabled = boolean;
export type Profile1 = "minimal" | "balanced";
export type Seed = string;
export type SeedResolution = "EXPLICIT" | "DEFERRED_TO_BUILD_FORGE";
export type SchemaVersion33 = "1.0.0";
export type SourceHash4 = string;
/**
 * @minItems 1
 */
export type TargetOs = ["windows" | "linux", ...("windows" | "linux")[]];
export type Kind3 = "target" | "host" | "group";
export type Value = string;
export type Targets = FrontendTarget[];
export type Warnings1 = FrontendDiagnostic[];
/**
 * @minItems 1
 */
export type Diagnostics = [FrontendDiagnostic, ...FrontendDiagnostic[]];
export type Kind4 = "FrontendFailure";
export type SchemaVersion34 = "1.0.0";
export type Valid1 = false;
export type Reason1 = string | null;
export type SchemaVersion35 = "1.0.0";
export type Service = string;
export type Simulation18 = boolean;
export type SimulationLabel18 = string | null;
export type Status2 = "alive" | "ready" | "not_ready";
export type Version = string;
export type CaseId7 = string;
export type CompilationId2 = string;
export type Diverse = boolean;
/**
 * @minItems 1
 * @maxItems 1000
 */
export type EndpointIds1 = [string, ...string[]];
export type ExecutionMode1 = "memory" | "native";
export type RetryLimit = number;
export type SchemaVersion36 = "1.0.0";
export type ComputedHash = string;
export type ExpectedHash = string;
export type IntegrityValid1 = boolean;
export type ObservationId1 = string;
export type SchemaVersion37 = "1.0.0";
export type SignatureStatus = "NOT_CHECKED";
export type Simulation19 = boolean;
export type SimulationLabel19 = string | null;
export type VerificationScope = "SUBMITTED_OBSERVATION_ONLY";
export type Case1 = string;
export type CompilerVersion = "0.3.0";
export type Executable1 = false;
export type Hunt1 = string;
export type Effect = "pure" | "read" | "emit";
export type EffectPredecessor = number | null;
export type Family =
  "SYSTEM" | "PROCESS" | "NETWORK" | "FILESYSTEM" | "LOGS" | "PERSISTENCE" | "DRIVER" | "ANALYSIS" | "EVIDENCE";
export type Id1 = number;
export type Inputs = number[];
export type Opcode = string;
export type RequiredCapabilities3 = string[];
export type ResourceClass =
  "bounded_inventory" | "bounded_content_io" | "bounded_materialization" | "bounded_output" | "linear_transform";
export type TargetOs1 = ("windows" | "linux")[];
/**
 * @maxItems 65536
 */
export type Instructions = JirInstruction[];
export type Kind5 = "JIRModule";
export type RequiredCapabilities4 = string[];
export type SchemaVersion38 = "1.0.0";
export type SourceHash5 = string;
/**
 * @minItems 1
 */
export type TargetOs2 = ["windows" | "linux", ...("windows" | "linux")[]];
export type Targets1 = FrontendTarget[];
export type Attempt = number;
export type CaseId8 = string;
export type EndpointId5 = string;
export type JobId5 = string;
export type PlanId1 = string;
export type RetryOf = string | null;
export type SchemaVersion39 = "1.0.0";
export type Simulation20 = boolean;
export type SimulationLabel20 = string | null;
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
export type Detail = string;
export type JobId6 = string;
export type SchemaVersion40 = "1.0.0";
export type State2 = "RUNNING" | "SUCCESS" | "FAILED" | "CANCELLED";
export type Algorithm1 = ("AES-256-GCM" | "ChaCha20-Poly1305") | null;
export type Enabled1 = boolean;
export type KeyId1 = string | null;
export type NoncePolicy = "unique-per-key-and-build" | null;
export type PoolHash = string | null;
export type SchemaVersion41 = "1.0.0";
export type OrganizationId4 = string;
export type Password = string;
export type SchemaVersion42 = "1.0.0";
export type Username = string;
export type CaseId9 = string;
export type CollectorId1 = string;
export type EndpointId6 = string;
export type IntegrityHash2 = string;
export type JirHash4 = string;
export type JobId7 = string;
export type ObservationId2 = string;
export type SchemaVersion43 = "1.0.0";
export type Simulation21 = boolean;
export type SimulationLabel21 = string | null;
export type SourceHash6 = string;
export type SourceTime1 = string | null;
export type Timestamp3 = string;
export type Type = string;
export type VariantId5 = string;
export type Name1 = string;
export type OrganizationId5 = string;
export type SchemaVersion44 = "1.0.0";
export type Simulation22 = boolean;
export type SimulationLabel22 = string | null;
export type Capabilities2 = CapabilityStatus[];
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Mode".
 */
export type Mode = "REAL" | "DEMO";
export type Name2 = "JOCKY";
export type ObservedAt1 = string;
export type Operational = boolean;
export type Phase1 = string;
export type SchemaVersion45 = "1.0.0";
export type Simulation23 = boolean;
export type SimulationLabel23 = string | null;
export type Tagline = "One Language. Every Endpoint. No Noise.";
export type Version1 = string;
export type Code2 = string;
export type Detail1 = string;
export type RequestId = string | null;
export type Retryable = boolean;
export type SchemaVersion46 = "1.0.0";
export type Simulation24 = boolean;
export type SimulationLabel24 = string | null;
export type Status3 = number;
export type SchemaVersion47 = "1.0.0";
export type Simulation25 = boolean;
export type SimulationLabel25 = string | null;
export type ArtifactId1 = string;
export type CaseId10 = string;
export type Format = "json" | "pdf";
export type GeneratedAt = string;
export type ReportId = string;
export type SchemaVersion48 = "1.0.0";
export type Simulation26 = boolean;
export type SimulationLabel26 = string | null;
export type CaseId11 = string;
export type Format1 = "json";
export type SchemaVersion49 = "1.0.0";
export type Name3 = string;
export type OrganizationId6 = string;
export type SchemaVersion50 = "1.0.0";
export type ScriptId = string;
export type Simulation27 = boolean;
export type SimulationLabel27 = string | null;
export type CaseId12 = string;
export type Name4 = string;
export type SchemaVersion51 = "1.0.0";
export type Source1 = string;
export type CreatedAt1 = string;
export type SchemaVersion52 = "1.0.0";
export type ScriptId1 = string;
export type ScriptVersionId1 = string;
export type Simulation28 = boolean;
export type SimulationLabel28 = string | null;
export type Source2 = string;
export type SourceHash7 = string;
export type Version2 = number;
export type ArtifactHash1 = string;
export type CaseId13 = string;
export type EndpointId7 = string;
export type ExpiresAt2 = string;
export type IssuedAt1 = string;
export type JirHash5 = string;
export type JobId8 = string;
export type Nonce1 = string;
export type OrganizationId7 = string;
export type PlanId2 = string;
export type RequiredCapabilities5 = string[];
export type SchemaVersion53 = "1.0.0";
export type Simulation29 = boolean;
export type SimulationLabel29 = string | null;
export type SourceHash8 = string;
export type VariantId6 = string;
export type CaseId14 = string;
export type EndpointId8 = string;
export type EventId = string;
export type ObservationId3 = string;
export type SchemaVersion54 = "1.0.0";
export type Simulation30 = boolean;
export type SimulationLabel30 = string | null;
export type Summary = string;
export type TimeBasis = "source" | "collection";
export type Timestamp4 = string;
export type SchemaVersion55 = "1.0.0";
export type Simulation31 = boolean;
export type SimulationLabel31 = string | null;
export type Timestamp5 = string;
export type OrganizationId8 = string;
export type Role = "viewer" | "analyst" | "operator" | "administrator";
export type SchemaVersion56 = "1.0.0";
export type Simulation32 = boolean;
export type SimulationLabel32 = string | null;
export type Subject = string;
export type UserId = string;
export type Password1 = string;
export type Role1 = "ADMIN" | "ANALYST" | "VIEWER";
export type SchemaVersion57 = "1.0.0";
export type Username1 = string;
export type SchemaVersion58 = "1.0.0";
/**
 * @minItems 2
 * @maxItems 16
 */
export type VariantIds1 = [string, string, ...string[]];
export type Count = number;
export type SchemaVersion59 = "1.0.0";
export type ArtifactHash2 = string;
export type CompilerVersion1 = string;
export type CreatedAt2 = string;
export type JirHash6 = string;
export type LlvmIrHash1 = string;
export type LlvmVersion = string;
export type SchemaVersion60 = "1.0.0";
export type SemanticTestHash = string | null;
export type SemanticTestStatus = "NOT_RUN" | "PASS" | "FAIL";
export type Simulation33 = boolean;
export type SimulationLabel33 = string | null;
export type SourceHash9 = string;
export type TargetArch = "x86_64" | "aarch64";
export type TargetOs3 = "windows" | "linux";
export type VariantId7 = string;
export type VariantSeed2 = string;
export type SchemaVersion61 = "1.0.0";
export type Source3 = string;

/**
 * Generated from Pydantic; do not edit. Refinement rules also apply in Python.
 */
export interface JockyContracts {
  AgentCollectorRequest?: AgentCollectorRequest;
  AgentEnforcement?: AgentEnforcement;
  AgentObservation?: AgentObservation;
  AgentPlatform?: AgentPlatform;
  AgentResourceBudget?: AgentResourceBudget;
  AgentSignedJob?: AgentSignedJob;
  Artifact?: Artifact;
  ArtifactUpload?: ArtifactUpload;
  AuditEvent?: AuditEvent;
  AuditVerification?: AuditVerification;
  BenchmarkCreate?: BenchmarkCreate;
  BenchmarkRun?: BenchmarkRun;
  Budget?: Budget;
  CapabilityStatus?: CapabilityStatus;
  Case?: Case;
  CaseCreate?: CaseCreate;
  CasePatch?: CasePatch;
  CompatibilityCreate?: CompatibilityCreate;
  CompatibilityRun?: CompatibilityRun;
  Compilation?: Compilation;
  CompileRequest?: CompileRequest;
  CompilerMetrics?: CompilerMetrics;
  Contract?: Contract;
  Diagnostic?: Diagnostic;
  Endpoint?: Endpoint;
  EndpointList?: EndpointList;
  EnrollmentCreate?: EnrollmentCreate;
  EvidenceManifest?: EvidenceManifest;
  ExecutionPlan?: ExecutionPlan;
  Finding?: Finding;
  FrontendCheck?: FrontendCheck;
  FrontendExecutionPlan?: FrontendExecutionPlan;
  FrontendFailure?: FrontendFailure;
  Health?: Health;
  HuntCreate?: HuntCreate;
  IntegrityResult?: IntegrityResult;
  JirModule?: JirModule;
  Job?: Job;
  JobProgress?: JobProgress;
  LiteralEncryption?: LiteralEncryption;
  LoginRequest?: LoginRequest;
  Observation?: Observation;
  Organization?: Organization;
  PlatformStatus?: PlatformStatus;
  Problem?: Problem;
  Provenance?: Provenance;
  Report?: Report;
  ReportCreate?: ReportCreate;
  Script?: Script;
  ScriptCreate?: ScriptCreate;
  ScriptVersion?: ScriptVersion;
  Signature?: Signature;
  SignedJob?: SignedJob;
  Target?: Target;
  TimelineEvent?: TimelineEvent;
  Timestamped?: Timestamped;
  User?: User;
  UserCreate?: UserCreate;
  VariantCompare?: VariantCompare;
  VariantCreate?: VariantCreate;
  VariantManifest?: VariantManifest;
  VersionCreate?: VersionCreate;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "AgentCollectorRequest".
 */
export interface AgentCollectorRequest {
  collector: Collector;
  hash?: Hash;
  limit?: Limit;
  path?: Path;
  recursive?: Recursive;
  schema_version?: SchemaVersion;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "AgentEnforcement".
 */
export interface AgentEnforcement {
  concurrency: Concurrency;
  cpu: Cpu;
  file_bytes: FileBytes;
  file_count: FileCount;
  memory: Memory;
  network_bytes: NetworkBytes;
  result_size: ResultSize;
  schema_version?: SchemaVersion1;
  timeout: Timeout;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "AgentObservation".
 */
export interface AgentObservation {
  case_id: CaseId;
  collector: Collector1;
  data: Data;
  endpoint_id: EndpointId;
  integrity_hash: IntegrityHash;
  job_id: JobId;
  observation_id: ObservationId;
  observed_at: ObservedAt;
  platform: AgentPlatform;
  schema_version?: SchemaVersion3;
  simulation: Simulation;
  simulation_label?: SimulationLabel;
  source_time: SourceTime;
}
export interface Data {
  [k: string]: JsonValue;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "AgentPlatform".
 */
export interface AgentPlatform {
  arch: Arch;
  os: Os;
  schema_version?: SchemaVersion2;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "AgentResourceBudget".
 */
export interface AgentResourceBudget {
  cpu_percent: CpuPercent;
  duration_ms: DurationMs;
  io_bytes: IoBytes;
  max_file_bytes: MaxFileBytes;
  max_file_count: MaxFileCount;
  max_result_bytes: MaxResultBytes;
  memory_bytes: MemoryBytes;
  schema_version?: SchemaVersion4;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "AgentSignedJob".
 */
export interface AgentSignedJob {
  budget: AgentResourceBudget;
  case_id: CaseId1;
  collectors: Collectors;
  endpoint_id: EndpointId1;
  enforcement_policy: EnforcementPolicy;
  expires_at: ExpiresAt;
  issued_at: IssuedAt;
  job_id: JobId1;
  nonce: Nonce;
  organization_id: OrganizationId;
  required_capabilities: RequiredCapabilities;
  schema_version?: SchemaVersion5;
  signature: Signature;
  simulation: Simulation1;
  simulation_label?: SimulationLabel1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Signature".
 */
export interface Signature {
  algorithm?: Algorithm;
  key_id?: KeyId;
  schema_version?: SchemaVersion6;
  status: Status;
  value_base64?: ValueBase64;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Artifact".
 */
export interface Artifact {
  artifact_id: ArtifactId;
  case_id: CaseId2;
  collector_id: CollectorId;
  content_hash: ContentHash;
  endpoint_id: EndpointId2;
  job_id: JobId2;
  media_type: MediaType;
  schema_version?: SchemaVersion7;
  simulation: Simulation2;
  simulation_label?: SimulationLabel2;
  size_bytes: SizeBytes;
  storage_key: StorageKey;
  timestamp: Timestamp;
  variant_id: VariantId;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "ArtifactUpload".
 */
export interface ArtifactUpload {
  content_base64: ContentBase64;
  content_hash: ContentHash1;
  job_id: JobId3;
  media_type?: MediaType1;
  schema_version?: SchemaVersion8;
  simulation: Simulation3;
  simulation_label?: SimulationLabel3;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "AuditEvent".
 */
export interface AuditEvent {
  action: Action;
  actor_id: ActorId;
  data: Data1;
  integrity_hash: IntegrityHash1;
  organization_id: OrganizationId1;
  previous_hash: PreviousHash;
  resource_id: ResourceId;
  schema_version?: SchemaVersion9;
  sequence: Sequence;
  simulation: Simulation4;
  simulation_label?: SimulationLabel4;
  timestamp: Timestamp1;
}
export interface Data1 {
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
  schema_version?: SchemaVersion10;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "BenchmarkCreate".
 */
export interface BenchmarkCreate {
  compilation_id: CompilationId;
  repetitions?: Repetitions;
  schema_version?: SchemaVersion11;
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
  repetitions: Repetitions1;
  runtime_ms?: RuntimeMs;
  schema_version?: SchemaVersion13;
  simulation: Simulation5;
  simulation_label?: SimulationLabel5;
  variant_id: VariantId1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "CompilerMetrics".
 */
export interface CompilerMetrics {
  aot_compile_ms?: AotCompileMs;
  aot_ms?: AotMs;
  execution_ms?: ExecutionMs;
  jir_ms?: JirMs;
  jit_compile_ms?: JitCompileMs;
  lex_ms?: LexMs;
  llvm_generation_ms?: LlvmGenerationMs;
  optimization_ms?: OptimizationMs;
  optimize_ms?: OptimizeMs;
  parse_ms?: ParseMs;
  peak_memory_bytes?: PeakMemoryBytes;
  schema_version?: SchemaVersion12;
  semantic_ms?: SemanticMs;
  variant_ms?: VariantMs;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Budget".
 */
export interface Budget {
  cpu_percent: CpuPercent1;
  duration_ms: DurationMs1;
  io_bytes: IoBytes1;
  memory_bytes: MemoryBytes1;
  schema_version?: SchemaVersion14;
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
  schema_version?: SchemaVersion15;
  simulation: Simulation6;
  simulation_label?: SimulationLabel6;
  status: ImplementationStatus;
  subsystem: Subsystem;
  title: Title;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Case".
 */
export interface Case {
  case_id: CaseId3;
  created_at: CreatedAt;
  organization_id: OrganizationId2;
  schema_version?: SchemaVersion16;
  simulation: Simulation7;
  simulation_label?: SimulationLabel7;
  state: State;
  title: Title1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "CaseCreate".
 */
export interface CaseCreate {
  description?: Description;
  schema_version?: SchemaVersion17;
  simulation: Simulation8;
  simulation_label?: SimulationLabel8;
  title: Title2;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "CasePatch".
 */
export interface CasePatch {
  description?: Description1;
  schema_version?: SchemaVersion18;
  status?: Status1;
  title?: Title3;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "CompatibilityCreate".
 */
export interface CompatibilityCreate {
  alert_observed: AlertObserved;
  correctness: Correctness;
  environment: Environment1;
  notes: Notes;
  schema_version?: SchemaVersion19;
  security_product_label: SecurityProductLabel;
  variant_id: VariantId2;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "CompatibilityRun".
 */
export interface CompatibilityRun {
  alert_observed: AlertObserved1;
  compatibility_run_id: CompatibilityRunId;
  completed: Completed;
  correctness: Correctness1;
  cpu_percent?: CpuPercent2;
  environment: Environment2;
  execution_mode: ExecutionMode;
  notes: Notes1;
  peak_memory_bytes?: PeakMemoryBytes2;
  runtime_ms?: RuntimeMs1;
  schema_version?: SchemaVersion20;
  security_product_label: SecurityProductLabel1;
  simulation: Simulation9;
  simulation_label?: SimulationLabel9;
  variant_id: VariantId3;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Compilation".
 */
export interface Compilation {
  compilation_id: CompilationId1;
  metrics: CompilerMetrics;
  schema_version?: SchemaVersion21;
  script_version_id: ScriptVersionId;
  simulation: Simulation10;
  simulation_label?: SimulationLabel10;
  source_hash: SourceHash;
  state: State1;
  variant_ids: VariantIds;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "CompileRequest".
 */
export interface CompileRequest {
  command?: Command;
  execution_mode: ExecutionMode;
  profile?: Profile;
  schema_version?: SchemaVersion22;
  simulation: Simulation11;
  simulation_label?: SimulationLabel11;
  source: Source;
  target: Target;
  variant_seed?: VariantSeed;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Target".
 */
export interface Target {
  arch: Arch1;
  os: Os1;
  schema_version?: SchemaVersion23;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Contract".
 */
export interface Contract {
  schema_version?: SchemaVersion24;
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
  schema_version?: SchemaVersion25;
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
  cpu_percent?: CpuPercent3;
  endpoint_id: EndpointId3;
  hostname: Hostname;
  identity_fingerprint: IdentityFingerprint;
  last_seen: LastSeen;
  memory_bytes?: MemoryBytes2;
  organization_id: OrganizationId3;
  schema_version?: SchemaVersion26;
  simulation: Simulation12;
  simulation_label?: SimulationLabel12;
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
  schema_version?: SchemaVersion27;
  simulation: Simulation13;
  simulation_label?: SimulationLabel13;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "EnrollmentCreate".
 */
export interface EnrollmentCreate {
  capabilities: Capabilities1;
  schema_version?: SchemaVersion28;
  simulation: Simulation14;
  simulation_label?: SimulationLabel14;
  validity_seconds?: ValiditySeconds;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "EvidenceManifest".
 */
export interface EvidenceManifest {
  agent_identity: AgentIdentity;
  artifact_hash: ArtifactHash;
  case_id: CaseId4;
  completed_at: CompletedAt;
  endpoint_id: EndpointId4;
  execution_mode: ExecutionMode;
  jir_hash: JirHash;
  job_id: JobId4;
  llvm_ir_hash: LlvmIrHash;
  observation_hashes: ObservationHashes;
  schema_version?: SchemaVersion29;
  signature: Signature;
  simulation: Simulation15;
  simulation_label?: SimulationLabel15;
  source_hash: SourceHash1;
  started_at: StartedAt;
  variant_id: VariantId4;
  variant_seed: VariantSeed1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "ExecutionPlan".
 */
export interface ExecutionPlan {
  budget: Budget;
  case_id: CaseId5;
  endpoint_ids: EndpointIds;
  execution_mode: ExecutionMode;
  expires_at: ExpiresAt1;
  jir_hash: JirHash1;
  plan_id: PlanId;
  policy_version: PolicyVersion;
  required_capabilities: RequiredCapabilities1;
  schema_version?: SchemaVersion30;
  simulation: Simulation16;
  simulation_label?: SimulationLabel16;
  source_hash: SourceHash2;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Finding".
 */
export interface Finding {
  case_id: CaseId6;
  finding_id: FindingId;
  observation_ids: ObservationIds;
  schema_version?: SchemaVersion31;
  severity: Severity1;
  simulation: Simulation17;
  simulation_label?: SimulationLabel17;
  timestamp: Timestamp2;
  title: Title4;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "FrontendCheck".
 */
export interface FrontendCheck {
  executable: Executable;
  hunt: Hunt;
  instruction_count: InstructionCount;
  jir_hash: JirHash2;
  kind: Kind;
  schema_version?: SchemaVersion32;
  source_hash: SourceHash3;
  valid: Valid;
  warnings: Warnings;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "FrontendDiagnostic".
 */
export interface FrontendDiagnostic {
  code: Code1;
  help: Help;
  message: Message1;
  severity: Severity2;
  source_line?: SourceLine;
  span: SourceSpan;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "SourceSpan".
 */
export interface SourceSpan {
  end: SourcePosition;
  start: SourcePosition;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "SourcePosition".
 */
export interface SourcePosition {
  column: Column1;
  line: Line1;
  offset: Offset;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "FrontendExecutionPlan".
 */
export interface FrontendExecutionPlan {
  admission_status: AdmissionStatus;
  budget: Budget;
  dispatchable: Dispatchable;
  expected_result_schemas: ExpectedResultSchemas;
  jir_hash: JirHash3;
  kind: Kind1;
  projected_fields: ProjectedFields;
  pushdown: Pushdown;
  required_capabilities: RequiredCapabilities2;
  required_collectors: RequiredCollectors;
  runtime: FrontendRuntime;
  schema_version?: SchemaVersion33;
  source_hash: SourceHash4;
  target_os: TargetOs;
  targets: Targets;
  warnings: Warnings1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "ResultSchema".
 */
export interface ResultSchema {
  instruction_id: InstructionId;
  result_type: JirType;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "JirType".
 */
export interface JirType {
  domain: Domain;
  fields: Fields;
  name: Name;
  nullable: Nullable;
}
export interface Fields {
  [k: string]: JirType;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "ProjectedFields".
 */
export interface ProjectedFields1 {
  fields: Fields1;
  instruction_id: InstructionId1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "PushdownCandidate".
 */
export interface PushdownCandidate {
  applied: Applied;
  attributes: Attributes;
  branch_instruction_id: BranchInstructionId;
  collector_instruction_id: CollectorInstructionId;
  condition: Condition;
  kind: Kind2;
  scope: Scope;
}
export interface Attributes {
  [k: string]: JsonValue;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "FrontendRuntime".
 */
export interface FrontendRuntime {
  backend: Backend;
  execution: Execution;
  variant: FrontendVariant;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "FrontendVariant".
 */
export interface FrontendVariant {
  enabled: Enabled;
  profile: Profile1;
  seed: Seed;
  seed_resolution: SeedResolution;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "FrontendTarget".
 */
export interface FrontendTarget {
  kind: Kind3;
  value: Value;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "FrontendFailure".
 */
export interface FrontendFailure {
  diagnostics: Diagnostics;
  kind: Kind4;
  schema_version?: SchemaVersion34;
  valid: Valid1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Health".
 */
export interface Health {
  reason?: Reason1;
  schema_version?: SchemaVersion35;
  service: Service;
  simulation: Simulation18;
  simulation_label?: SimulationLabel18;
  status: Status2;
  version: Version;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "HuntCreate".
 */
export interface HuntCreate {
  case_id: CaseId7;
  compilation_id: CompilationId2;
  diverse?: Diverse;
  endpoint_ids: EndpointIds1;
  execution_mode?: ExecutionMode1;
  retry_limit?: RetryLimit;
  schema_version?: SchemaVersion36;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "IntegrityResult".
 */
export interface IntegrityResult {
  computed_hash: ComputedHash;
  expected_hash: ExpectedHash;
  integrity_valid: IntegrityValid1;
  observation_id: ObservationId1;
  schema_version?: SchemaVersion37;
  signature_status?: SignatureStatus;
  simulation: Simulation19;
  simulation_label?: SimulationLabel19;
  verification_scope?: VerificationScope;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "JirModule".
 */
export interface JirModule {
  budget: Budget;
  case: Case1;
  compiler_version: CompilerVersion;
  executable: Executable1;
  hunt: Hunt1;
  instructions: Instructions;
  kind: Kind5;
  required_capabilities: RequiredCapabilities4;
  runtime: FrontendRuntime;
  schema_version?: SchemaVersion38;
  source_hash: SourceHash5;
  target_os: TargetOs2;
  targets: Targets1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "JirInstruction".
 */
export interface JirInstruction {
  attributes: Attributes1;
  effect: Effect;
  effect_predecessor: EffectPredecessor;
  family: Family;
  id: Id1;
  inputs: Inputs;
  opcode: Opcode;
  required_capabilities: RequiredCapabilities3;
  resource_class: ResourceClass;
  result_type: JirType;
  span: SourceSpan;
  target_os: TargetOs1;
}
export interface Attributes1 {
  [k: string]: JsonValue;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Job".
 */
export interface Job {
  attempt: Attempt;
  case_id: CaseId8;
  endpoint_id: EndpointId5;
  job_id: JobId5;
  plan_id: PlanId1;
  retry_of?: RetryOf;
  schema_version?: SchemaVersion39;
  simulation: Simulation20;
  simulation_label?: SimulationLabel20;
  state: JobState;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "JobProgress".
 */
export interface JobProgress {
  detail?: Detail;
  job_id: JobId6;
  measurements?: Measurements;
  schema_version?: SchemaVersion40;
  state: State2;
}
export interface Measurements {
  [k: string]: JsonValue;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "LiteralEncryption".
 */
export interface LiteralEncryption {
  algorithm?: Algorithm1;
  enabled: Enabled1;
  key_id?: KeyId1;
  nonce_policy?: NoncePolicy;
  pool_hash?: PoolHash;
  schema_version?: SchemaVersion41;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "LoginRequest".
 */
export interface LoginRequest {
  organization_id: OrganizationId4;
  password: Password;
  schema_version?: SchemaVersion42;
  username: Username;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Observation".
 */
export interface Observation {
  case_id: CaseId9;
  collector_id: CollectorId1;
  data: Data2;
  endpoint_id: EndpointId6;
  integrity_hash: IntegrityHash2;
  jir_hash: JirHash4;
  job_id: JobId7;
  observation_id: ObservationId2;
  schema_version?: SchemaVersion43;
  simulation: Simulation21;
  simulation_label?: SimulationLabel21;
  source_hash: SourceHash6;
  source_time: SourceTime1;
  timestamp: Timestamp3;
  type: Type;
  variant_id: VariantId5;
}
export interface Data2 {
  [k: string]: JsonValue;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Organization".
 */
export interface Organization {
  name: Name1;
  organization_id: OrganizationId5;
  schema_version?: SchemaVersion44;
  simulation: Simulation22;
  simulation_label?: SimulationLabel22;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "PlatformStatus".
 */
export interface PlatformStatus {
  capabilities: Capabilities2;
  mode: Mode;
  name?: Name2;
  observed_at: ObservedAt1;
  operational: Operational;
  phase: Phase1;
  schema_version?: SchemaVersion45;
  simulation: Simulation23;
  simulation_label?: SimulationLabel23;
  tagline: Tagline;
  version: Version1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Problem".
 */
export interface Problem {
  code: Code2;
  detail: Detail1;
  request_id?: RequestId;
  retryable?: Retryable;
  schema_version?: SchemaVersion46;
  simulation: Simulation24;
  simulation_label?: SimulationLabel24;
  status: Status3;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Provenance".
 */
export interface Provenance {
  schema_version?: SchemaVersion47;
  simulation: Simulation25;
  simulation_label?: SimulationLabel25;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Report".
 */
export interface Report {
  artifact_id: ArtifactId1;
  case_id: CaseId10;
  format: Format;
  generated_at: GeneratedAt;
  report_id: ReportId;
  schema_version?: SchemaVersion48;
  simulation: Simulation26;
  simulation_label?: SimulationLabel26;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "ReportCreate".
 */
export interface ReportCreate {
  case_id: CaseId11;
  format?: Format1;
  schema_version?: SchemaVersion49;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Script".
 */
export interface Script {
  name: Name3;
  organization_id: OrganizationId6;
  schema_version?: SchemaVersion50;
  script_id: ScriptId;
  simulation: Simulation27;
  simulation_label?: SimulationLabel27;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "ScriptCreate".
 */
export interface ScriptCreate {
  case_id: CaseId12;
  name: Name4;
  schema_version?: SchemaVersion51;
  source: Source1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "ScriptVersion".
 */
export interface ScriptVersion {
  created_at: CreatedAt1;
  schema_version?: SchemaVersion52;
  script_id: ScriptId1;
  script_version_id: ScriptVersionId1;
  simulation: Simulation28;
  simulation_label?: SimulationLabel28;
  source: Source2;
  source_hash: SourceHash7;
  version: Version2;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "SignedJob".
 */
export interface SignedJob {
  artifact_hash: ArtifactHash1;
  budget: Budget;
  case_id: CaseId13;
  endpoint_id: EndpointId7;
  execution_mode: ExecutionMode;
  expires_at: ExpiresAt2;
  issued_at: IssuedAt1;
  jir_hash: JirHash5;
  job_id: JobId8;
  nonce: Nonce1;
  organization_id: OrganizationId7;
  plan_id: PlanId2;
  required_capabilities: RequiredCapabilities5;
  schema_version?: SchemaVersion53;
  signature: Signature;
  simulation: Simulation29;
  simulation_label?: SimulationLabel29;
  source_hash: SourceHash8;
  variant_id: VariantId6;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "TimelineEvent".
 */
export interface TimelineEvent {
  case_id: CaseId14;
  endpoint_id: EndpointId8;
  event_id: EventId;
  observation_id: ObservationId3;
  schema_version?: SchemaVersion54;
  severity: Severity1;
  simulation: Simulation30;
  simulation_label?: SimulationLabel30;
  summary: Summary;
  time_basis: TimeBasis;
  timestamp: Timestamp4;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "Timestamped".
 */
export interface Timestamped {
  schema_version?: SchemaVersion55;
  simulation: Simulation31;
  simulation_label?: SimulationLabel31;
  timestamp: Timestamp5;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "User".
 */
export interface User {
  organization_id: OrganizationId8;
  role: Role;
  schema_version?: SchemaVersion56;
  simulation: Simulation32;
  simulation_label?: SimulationLabel32;
  subject: Subject;
  user_id: UserId;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "UserCreate".
 */
export interface UserCreate {
  password: Password1;
  role: Role1;
  schema_version?: SchemaVersion57;
  username: Username1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "VariantCompare".
 */
export interface VariantCompare {
  schema_version?: SchemaVersion58;
  variant_ids: VariantIds1;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "VariantCreate".
 */
export interface VariantCreate {
  count?: Count;
  schema_version?: SchemaVersion59;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "VariantManifest".
 */
export interface VariantManifest {
  artifact_hash: ArtifactHash2;
  compiler_version: CompilerVersion1;
  created_at: CreatedAt2;
  execution_mode: ExecutionMode;
  jir_hash: JirHash6;
  literal_encryption: LiteralEncryption;
  llvm_ir_hash: LlvmIrHash1;
  llvm_version: LlvmVersion;
  schema_version?: SchemaVersion60;
  semantic_test_hash: SemanticTestHash;
  semantic_test_status: SemanticTestStatus;
  signature: Signature;
  simulation: Simulation33;
  simulation_label?: SimulationLabel33;
  source_hash: SourceHash9;
  target_arch: TargetArch;
  target_os: TargetOs3;
  variant_id: VariantId7;
  variant_seed: VariantSeed2;
}
/**
 * This interface was referenced by `JockyContracts`'s JSON-Schema
 * via the `definition` "VersionCreate".
 */
export interface VersionCreate {
  schema_version?: SchemaVersion61;
  source: Source3;
}
