# Labeled laboratory inputs

Fixtures are synthetic test inputs, not endpoint telemetry. Every synthetic record carries `simulation=true` and a SIMULATED/DEMO label. The evidence observation is generated with a real content hash so the stateless verifier can demonstrate recomputation and tamper detection. Its source/JIR hashes refer to explicit fixture-marker bytes, not compiler outputs; its variant ID is prefixed fixture and cannot authorize execution.

P0 does not seed endpoints into the API or dashboard. Future fixture services must enforce namespace/job-mode separation, propagate labels to derived artifacts, and never turn demo data into real inventory. Driver metadata here is fictional and does not assert a real CVE or Microsoft blocklist match. No executable driver or malware is included.
