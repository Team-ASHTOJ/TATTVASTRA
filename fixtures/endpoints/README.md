# Endpoint fixture contract

Reserved for backend-seeded synthetic Windows/Ubuntu endpoint records after identity and fixture services exist. P0 contains no synthetic fleet or fake heartbeat status. Each future record must validate the Endpoint contract, use a fixture-prefixed identity, include simulation=true and a SIMULATED label, and be isolated from real enrollment.
