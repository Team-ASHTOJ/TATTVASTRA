JOCKY Windows endpoint bundle
============================

Contents
  jocky-bootstrap.exe           bounded lifecycle supervisor, installed as a service
  jocky-agent.exe               the native JOCKY endpoint agent
  install-jocky-bootstrap.ps1   one-time elevated installer
  Install-JOCKY.cmd             double-click entry point, elevates itself
  connect-jocky.ps1             manual onboarding path for a machine without the service
  README.txt                    this file

Before you install
  1. On the JOCKY machine, open the dashboard (http://localhost:13000 by default).
  2. Go to Endpoints -> Connect Endpoint -> Windows -> Advanced Setup.
  3. Choose Prepare. jocky-bootstrap.json downloads. It carries this host's
     one-time bootstrap credential, the control-plane CA, and the HTTPS
     addresses the supervisor dials. Treat it as a secret.
  4. Copy jocky-bootstrap.json into this folder, next to Install-JOCKY.cmd.

Install
  5. Right-click Install-JOCKY.cmd and choose Run as administrator, or run it
     normally and approve the UAC prompt it raises. It installs the supervisor
     into %ProgramFiles%\JOCKY, protects the state in %ProgramData%\JOCKY, and
     starts the JOCKY Endpoint Bootstrap service.
  6. Back in JOCKY, click Start Windows Endpoint.
     The endpoint moves READY -> STARTING -> ENROLLING -> WAITING FOR HEARTBEAT
     -> ONLINE. ONLINE means this machine's own jocky-agent sent an
     authenticated heartbeat; nothing else produces it.

Notes
  - Re-running Install-JOCKY.cmd is safe. It keeps the existing endpoint
    identity in %ProgramData%\JOCKY and never re-enrolls a bound host.
  - Compiled-job execution additionally needs jocky-worker.exe, an LLVM 18+
    build published separately as the jocky-worker-windows-x86_64 artifact when
    the build runner has that toolchain. Drop it in this folder before
    installing if you have one. A missing worker never blocks enrollment,
    heartbeat or collectors.
  - Without jocky-bootstrap.json, run connect-jocky.ps1 with the one-time
    enrollment token from Advanced Setup. That is onboarding, not the normal
    operator path.
  - The installer and the supervisor never disable certificate validation and
    never accept a plaintext address.
