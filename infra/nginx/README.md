# Local legitimate relay template

The relay profile requires operator-provided `certs/localhost.crt` and `certs/localhost.key`, trusted for localhost. Keys and certificates are ignored by Git. Start with both `app` and `relay` profiles only after provisioning certificates. Use TLS verification; do not bypass certificate checks in acceptance tests.

This is local declared-origin TLS routing, not operational agent mTLS. The API refuses JOCKY_TRANSPORT_MODE=TRUSTED_RELAY until that authenticated mode is implemented. The current proxy forwards no asserted endpoint identity. P5 must implement mTLS passthrough or an authenticated identity-binding gateway, certificate expiry/rotation/revocation tests, and upstream protection before production use. No domain-fronting or covert proxy is supported.
