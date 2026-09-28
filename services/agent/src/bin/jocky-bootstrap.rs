#[cfg(not(windows))]
fn main() {
    eprintln!("jocky-bootstrap is available only for native Windows endpoints");
}

#[cfg(windows)]
mod windows_bootstrap {
    use std::error::Error;
    use std::ffi::OsString;
    use std::fs;
    use std::path::{Path, PathBuf};
    use std::process::{Child, Command, Stdio};
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::{Arc, OnceLock};
    use std::thread;
    use std::time::Duration;

    use reqwest::blocking::{Client, ClientBuilder};
    use reqwest::header::AUTHORIZATION;
    use serde::{Deserialize, Serialize};
    use serde_json::Value;
    use windows_service::define_windows_service;
    use windows_service::service::{
        ServiceControl, ServiceControlAccept, ServiceExitCode, ServiceState, ServiceStatus,
        ServiceType,
    };
    use windows_service::service_control_handler::{self, ServiceControlHandlerResult};
    use windows_service::service_dispatcher;

    const SERVICE_NAME: &str = "JockyBootstrap";
    static CONFIG_PATH: OnceLock<PathBuf> = OnceLock::new();

    #[derive(Deserialize)]
    #[serde(deny_unknown_fields)]
    struct Config {
        schema_version: String,
        api_url: String,
        control_server: String,
        enrollment_server: String,
        organization_id: String,
        bootstrap_id: String,
        bootstrap_secret: String,
        ca_pem: String,
    }

    #[derive(Serialize)]
    struct Report<'a> {
        state: &'a str,
        endpoint_id: Option<&'a str>,
        needs_enrollment: bool,
        error: Option<&'a str>,
    }

    #[derive(Deserialize)]
    struct Enrollment {
        one_time_token: String,
        ca_pem: String,
    }

    #[derive(Deserialize)]
    struct Instruction {
        action: String,
        authoritative_state: String,
        enrollment: Option<Enrollment>,
    }

    struct Runtime {
        config: Config,
        client: Client,
        install: PathBuf,
        state: PathBuf,
        child: Option<Child>,
        endpoint_id: Option<String>,
    }

    impl Runtime {
        fn load(path: &Path) -> Result<Self, Box<dyn Error>> {
            let config: Config = serde_json::from_slice(&fs::read(path)?)?;
            if config.schema_version != "1.0.0"
                || !config.api_url.starts_with("https://")
                || !config.control_server.starts_with("https://")
                || !config.enrollment_server.starts_with("https://")
            {
                return Err(
                    "bootstrap configuration requires schema 1.0.0 and HTTPS endpoints".into(),
                );
            }
            let certificate = reqwest::Certificate::from_pem(config.ca_pem.as_bytes())?;
            let client = ClientBuilder::new()
                .https_only(true)
                .add_root_certificate(certificate)
                .timeout(Duration::from_secs(15))
                .build()?;
            let install = std::env::current_exe()?
                .parent()
                .ok_or("bootstrap executable has no parent directory")?
                .to_path_buf();
            let state = PathBuf::from(
                std::env::var_os("ProgramData").ok_or("ProgramData is unavailable")?,
            )
            .join("JOCKY");
            let endpoint_id = read_endpoint_id(&state);
            Ok(Self { config, client, install, state, child: None, endpoint_id })
        }

        fn poll(&self, state: &str, error: Option<&str>) -> Result<Instruction, Box<dyn Error>> {
            let url = format!(
                "{}/api/windows-bootstrap/poll",
                self.config.api_url.trim_end_matches('/')
            );
            let credential = format!(
                "Bootstrap {}.{}",
                self.config.bootstrap_id, self.config.bootstrap_secret
            );
            Ok(self
                .client
                .post(url)
                .header(AUTHORIZATION, credential)
                .json(&Report {
                    state,
                    endpoint_id: self.endpoint_id.as_deref(),
                    needs_enrollment: !self.state.join("remote.json").is_file(),
                    error,
                })
                .send()?
                .error_for_status()?
                .json()?)
        }

        fn enroll(&mut self, enrollment: Enrollment) -> Result<(), Box<dyn Error>> {
            let staging = self.state.join("bootstrap");
            fs::create_dir_all(&staging)?;
            let token = staging.join("enrollment.token");
            let ca = staging.join("control-plane-ca.pem");
            fs::write(&token, enrollment.one_time_token)?;
            fs::write(&ca, enrollment.ca_pem)?;
            let status = Command::new("powershell.exe")
                .args(["-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File"])
                .arg(self.install.join("connect-jocky.ps1"))
                .args(["-Server", &self.config.control_server])
                .args(["-EnrollmentServer", &self.config.enrollment_server])
                .arg("-TokenFile")
                .arg(&token)
                .arg("-CaFile")
                .arg(&ca)
                .args(["-OrganizationId", &self.config.organization_id])
                .arg("-EnrollOnly")
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .status()?;
            if !status.success() {
                return Err(format!("fixed JOCKY enrollment exited with {status}").into());
            }
            self.endpoint_id = read_endpoint_id(&self.state);
            if self.endpoint_id.is_none() {
                return Err("enrollment completed without a remote endpoint binding".into());
            }
            Ok(())
        }

        fn start_agent(&mut self) -> Result<(), Box<dyn Error>> {
            if self.child.as_mut().is_some_and(|child| child.try_wait().ok().flatten().is_none()) {
                return Ok(());
            }
            let agent = self.install.join("jocky-agent.exe");
            if !agent.is_file() {
                return Err("jocky-agent.exe is missing from the bootstrap installation".into());
            }
            self.child = Some(
                Command::new(agent)
                    .arg("--state-dir")
                    .arg(&self.state)
                    .arg("connect")
                    .stdin(Stdio::null())
                    .stdout(Stdio::null())
                    .stderr(Stdio::null())
                    .spawn()?,
            );
            Ok(())
        }

        fn stop_agent(&mut self) {
            if let Some(mut child) = self.child.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }

    fn read_endpoint_id(state: &Path) -> Option<String> {
        let value: Value = serde_json::from_slice(&fs::read(state.join("remote.json")).ok()?).ok()?;
        value.get("endpoint_id")?.as_str().map(str::to_owned)
    }

    fn lifecycle(config: &Path, stopped: Arc<AtomicBool>) -> Result<(), Box<dyn Error>> {
        let mut runtime = Runtime::load(config)?;
        let mut state = if runtime.endpoint_id.is_some() { "STOPPED" } else { "READY" };
        let mut error: Option<String> = None;
        while !stopped.load(Ordering::Relaxed) {
            match runtime.poll(state, error.as_deref()) {
                Ok(instruction) if instruction.action == "STOP" => {
                    runtime.stop_agent();
                    state = "STOPPED";
                    error = None;
                }
                Ok(instruction) if instruction.action == "START" => {
                    let result = (|| -> Result<(), Box<dyn Error>> {
                        if runtime.endpoint_id.is_none() {
                            state = "ENROLLING";
                            let enrollment = instruction
                                .enrollment
                                .ok_or("control plane did not supply enrollment material")?;
                            runtime.enroll(enrollment)?;
                        }
                        runtime.start_agent()?;
                        state = if instruction.authoritative_state == "ONLINE" {
                            "ONLINE"
                        } else {
                            "WAITING_FOR_HEARTBEAT"
                        };
                        Ok(())
                    })();
                    match result {
                        Ok(()) => error = None,
                        Err(failure) => {
                            state = "FAILED";
                            error = Some(failure.to_string());
                            runtime.stop_agent();
                        }
                    }
                }
                Ok(_) => {
                    state = "FAILED";
                    error = Some("control plane returned an unknown lifecycle action".to_owned());
                }
                Err(failure) => {
                    error = Some(format!("control plane unavailable: {failure}"));
                }
            }
            thread::sleep(Duration::from_secs(2));
        }
        runtime.stop_agent();
        let _ = runtime.poll("STOPPED", None);
        Ok(())
    }

    define_windows_service!(service_entry, service_main);

    fn service_main(_arguments: Vec<OsString>) {
        let stopped = Arc::new(AtomicBool::new(false));
        let signal = Arc::clone(&stopped);
        let handler = move |control| match control {
            ServiceControl::Stop | ServiceControl::Shutdown => {
                signal.store(true, Ordering::Relaxed);
                ServiceControlHandlerResult::NoError
            }
            ServiceControl::Interrogate => ServiceControlHandlerResult::NoError,
            _ => ServiceControlHandlerResult::NotImplemented,
        };
        let Ok(status_handle) = service_control_handler::register(SERVICE_NAME, handler) else {
            return;
        };
        let _ = status_handle.set_service_status(ServiceStatus {
            service_type: ServiceType::OWN_PROCESS,
            current_state: ServiceState::Running,
            controls_accepted: ServiceControlAccept::STOP | ServiceControlAccept::SHUTDOWN,
            exit_code: ServiceExitCode::Win32(0),
            checkpoint: 0,
            wait_hint: Duration::default(),
            process_id: None,
        });
        if let Some(path) = CONFIG_PATH.get() {
            let _ = lifecycle(path, stopped);
        }
        let _ = status_handle.set_service_status(ServiceStatus {
            service_type: ServiceType::OWN_PROCESS,
            current_state: ServiceState::Stopped,
            controls_accepted: ServiceControlAccept::empty(),
            exit_code: ServiceExitCode::Win32(0),
            checkpoint: 0,
            wait_hint: Duration::default(),
            process_id: None,
        });
    }

    pub fn run() -> Result<(), Box<dyn Error>> {
        let arguments: Vec<OsString> = std::env::args_os().collect();
        let config_index = arguments.iter().position(|value| value == "--config");
        let path = config_index
            .and_then(|index| arguments.get(index + 1))
            .map(PathBuf::from)
            .ok_or("--config is required")?;
        CONFIG_PATH.set(path.clone()).map_err(|_| "configuration already initialized")?;
        if arguments.iter().any(|value| value == "--console") {
            return lifecycle(&path, Arc::new(AtomicBool::new(false)));
        }
        service_dispatcher::start(SERVICE_NAME, service_entry)?;
        Ok(())
    }
}

#[cfg(windows)]
fn main() {
    if let Err(error) = windows_bootstrap::run() {
        eprintln!("JOCKY bootstrap failed: {error}");
        std::process::exit(1);
    }
}
