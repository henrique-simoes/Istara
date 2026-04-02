/// Rust-native process management — cross-platform (macOS, Windows, Linux).
///
/// Replaces the previous istara.sh shell delegation with direct Rust process
/// spawning. Each service (backend, frontend, relay) is a tracked Child process.
/// Platform-specific port cleanup via #[cfg] blocks.
///
/// Architecture: The tray app owns all child processes. On exit, all children
/// are killed. istara.sh remains as a CLI convenience but the tray app no
/// longer depends on it.

use crate::path_resolver;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::time::Duration;

pub struct ProcessManager {
    backend: Option<Child>,
    frontend: Option<Child>,
    relay: Option<Child>,
    log_dir: PathBuf,
}

pub fn check_port(port: u16) -> bool {
    std::net::TcpStream::connect_timeout(
        &format!("127.0.0.1:{}", port).parse().unwrap(),
        Duration::from_secs(1),
    )
    .is_ok()
}

/// Check if backend or frontend is running (port check).
pub fn is_server_running() -> bool {
    check_port(8000) || check_port(3000)
}

/// Check if LM Studio is running (port 1234).
pub fn is_lm_studio_running() -> bool {
    check_port(1234)
}

/// Check if Ollama is running (port 11434).
pub fn is_ollama_running() -> bool {
    check_port(11434)
}

impl ProcessManager {
    pub fn new() -> Self {
        let log_dir = dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".istara")
            .join("logs");
        let _ = fs::create_dir_all(&log_dir);
        Self {
            backend: None,
            frontend: None,
            relay: None,
            log_dir,
        }
    }

    /// Start backend + frontend as direct child processes.
    /// Non-blocking: spawns processes and returns immediately.
    /// Health loop will detect when ports come up.
    pub fn start_server(&mut self, install_dir: &str) -> Result<String, String> {
        if install_dir.is_empty() {
            return Err("No install directory configured.".to_string());
        }

        // Clean up any dead processes first
        self.cleanup_dead();

        // Kill orphan port holders before starting
        kill_port_holders(8000);
        kill_port_holders(3000);

        let backend_dir = PathBuf::from(install_dir).join("backend");
        if !backend_dir.exists() {
            return Err(format!("Backend not found at {}", backend_dir.display()));
        }

        // ── Start Backend (uvicorn) ──
        let python = path_resolver::find_python(install_dir);
        eprintln!("[tray] Starting backend with: {}", python);

        let backend_log = fs::File::create(self.log_dir.join("backend.log"))
            .map_err(|e| format!("Cannot create backend log: {}", e))?;
        let backend_err = backend_log.try_clone()
            .map_err(|e| format!("Cannot clone log: {}", e))?;

        let mut backend_cmd = Command::new(&python);
        backend_cmd
            .args(["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"])
            .current_dir(&backend_dir)
            .stdout(Stdio::from(backend_log))
            .stderr(Stdio::from(backend_err));

        // macOS Tahoe: fix Python's platform.mac_ver() returning wrong version
        backend_cmd.env("SYSTEM_VERSION_COMPAT", "0");

        // Ensure PATH includes common binary locations (GUI apps don't inherit shell PATH)
        let enriched_path = build_enriched_path();
        backend_cmd.env("PATH", &enriched_path);

        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            backend_cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }

        match backend_cmd.spawn() {
            Ok(child) => {
                eprintln!("[tray] Backend started (PID: {})", child.id());
                self.backend = Some(child);
            }
            Err(e) => {
                return Err(format!("Failed to start backend: {}. Python: {}", e, python));
            }
        }

        // ── Start Frontend (npm start or npm run dev) ──
        let frontend_dir = PathBuf::from(install_dir).join("frontend");
        if !frontend_dir.exists() {
            eprintln!("[tray] Frontend directory not found, skipping");
            return Ok("Backend started (no frontend directory)".to_string());
        }

        let npm = path_resolver::find_npm();
        eprintln!("[tray] Starting frontend with: {}", npm);

        let frontend_log = fs::File::create(self.log_dir.join("frontend.log"))
            .map_err(|e| format!("Cannot create frontend log: {}", e))?;
        let frontend_err = frontend_log.try_clone()
            .map_err(|e| format!("Cannot clone log: {}", e))?;

        let has_build = frontend_dir.join(".next").exists();
        let mut frontend_cmd = Command::new(&npm);
        if has_build {
            frontend_cmd.args(["start", "--", "--port", "3000"]);
        } else {
            frontend_cmd.args(["run", "dev", "--", "--port", "3000"]);
        }
        frontend_cmd
            .current_dir(&frontend_dir)
            .stdout(Stdio::from(frontend_log))
            .stderr(Stdio::from(frontend_err));

        // Ensure Node.js + Python are in PATH for npm (GUI apps don't inherit shell PATH)
        frontend_cmd.env("PATH", &enriched_path);

        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            frontend_cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }

        match frontend_cmd.spawn() {
            Ok(child) => {
                eprintln!("[tray] Frontend started (PID: {})", child.id());
                self.frontend = Some(child);
            }
            Err(e) => {
                eprintln!("[tray] Frontend start failed: {}", e);
            }
        }

        Ok("Server starting...".to_string())
    }

    /// Stop backend + frontend.
    pub fn stop_server(&mut self) -> Result<String, String> {
        // Kill managed children
        if let Some(ref mut child) = self.backend {
            eprintln!("[tray] Stopping backend (PID: {})", child.id());
            let _ = child.kill();
            let _ = child.wait();
        }
        self.backend = None;

        if let Some(ref mut child) = self.frontend {
            eprintln!("[tray] Stopping frontend (PID: {})", child.id());
            let _ = child.kill();
            let _ = child.wait();
        }
        self.frontend = None;

        // Also kill any orphans on the ports (catches processes started outside the tray)
        kill_port_holders(8000);
        kill_port_holders(3000);

        eprintln!("[tray] Server stopped");
        Ok("Server stopped".to_string())
    }

    /// Check if server is running (Child handles + port check).
    pub fn is_server_running(&mut self) -> bool {
        self.cleanup_dead();
        self.backend.is_some() || self.frontend.is_some() || check_port(8000) || check_port(3000)
    }

    /// Start the relay daemon.
    pub fn start_relay(&mut self, install_dir: &str, connection_string: &str) -> Result<(), String> {
        // Clean up dead relay first
        if let Some(ref mut c) = self.relay {
            match c.try_wait() {
                Ok(Some(_)) | Err(_) => { self.relay = None; }
                Ok(None) => return Ok(()), // Already running
            }
        }

        let relay_dir = format!("{}/relay", install_dir);
        if !Path::new(&relay_dir).exists() {
            return Err("Relay directory not found.".to_string());
        }

        let node = path_resolver::find_node();
        let mut cmd = Command::new(&node);
        cmd.arg("index.mjs");
        if !connection_string.is_empty() {
            cmd.args(["--connection-string", connection_string]);
        } else {
            cmd.args(["--server", "ws://localhost:8000/ws/relay"]);
        }

        let log_file = fs::File::create(self.log_dir.join("relay.log"))
            .map_err(|e| format!("Cannot create relay log: {}", e))?;
        let err_file = log_file.try_clone()
            .map_err(|e| format!("Cannot clone log: {}", e))?;

        let child = cmd
            .current_dir(&relay_dir)
            .stdout(Stdio::from(log_file))
            .stderr(Stdio::from(err_file))
            .spawn()
            .map_err(|e| format!("Failed to start relay: {}", e))?;

        eprintln!("[tray] Relay started (PID: {})", child.id());
        self.relay = Some(child);
        Ok(())
    }

    pub fn stop_relay(&mut self) {
        if let Some(ref mut child) = self.relay {
            let _ = child.kill();
            let _ = child.wait();
            eprintln!("[tray] Relay stopped");
        }
        self.relay = None;
    }

    pub fn stop_all(&mut self) {
        let _ = self.stop_server();
        self.stop_relay();
    }

    pub fn is_relay_running(&mut self) -> bool {
        if let Some(ref mut c) = self.relay {
            match c.try_wait() {
                Ok(Some(_)) | Err(_) => { self.relay = None; false }
                Ok(None) => true,
            }
        } else {
            false
        }
    }

    /// Clean up dead child processes (zombie detection via try_wait).
    fn cleanup_dead(&mut self) {
        for (name, child) in [
            ("backend", &mut self.backend),
            ("frontend", &mut self.frontend),
        ] {
            if let Some(ref mut c) = child {
                match c.try_wait() {
                    Ok(Some(status)) => {
                        eprintln!("[tray] {} exited with {}", name, status);
                        *child = None;
                    }
                    Err(_) => { *child = None; }
                    Ok(None) => {} // still running
                }
            }
        }
    }
}

impl Drop for ProcessManager {
    fn drop(&mut self) {
        self.stop_all();
    }
}

// ── PATH Resolution for GUI Apps ────────────────────────────────────

/// Build a comprehensive PATH for child processes.
/// GUI apps (Tauri, Finder-launched) don't inherit the user's shell PATH.
/// We construct a PATH that includes all common binary locations.
fn build_enriched_path() -> String {
    let mut paths: Vec<String> = Vec::new();

    // Homebrew (Apple Silicon + Intel)
    #[cfg(target_os = "macos")]
    {
        paths.push("/opt/homebrew/bin".to_string());
        paths.push("/opt/homebrew/opt/node/bin".to_string());
        paths.push("/opt/homebrew/opt/python@3.12/bin".to_string());
        paths.push("/opt/homebrew/opt/python@3.11/bin".to_string());
        paths.push("/usr/local/bin".to_string()); // Intel Homebrew
    }

    // System paths (all platforms)
    paths.push("/usr/bin".to_string());
    paths.push("/bin".to_string());
    paths.push("/usr/sbin".to_string());
    paths.push("/sbin".to_string());

    // User-specific paths
    if let Ok(home) = std::env::var("HOME") {
        // nvm
        let nvm_default = format!("{}/.nvm/versions/node", home);
        if Path::new(&nvm_default).exists() {
            if let Ok(entries) = std::fs::read_dir(&nvm_default) {
                let mut versions: Vec<_> = entries.flatten().collect();
                versions.sort_by(|a, b| b.file_name().cmp(&a.file_name()));
                if let Some(entry) = versions.first() {
                    paths.push(format!("{}/bin", entry.path().display()));
                }
            }
        }
        // pyenv
        paths.push(format!("{}/.pyenv/shims", home));
        // fnm
        let fnm_dir = format!("{}/.local/share/fnm/node-versions", home);
        if Path::new(&fnm_dir).exists() {
            if let Ok(entries) = std::fs::read_dir(&fnm_dir) {
                for entry in entries.flatten() {
                    let bin = entry.path().join("installation/bin");
                    if bin.exists() {
                        paths.push(bin.to_string_lossy().to_string());
                        break;
                    }
                }
            }
        }
    }

    // Inherit existing PATH as fallback
    if let Ok(existing) = std::env::var("PATH") {
        for p in existing.split(':') {
            if !paths.contains(&p.to_string()) {
                paths.push(p.to_string());
            }
        }
    }

    paths.join(":")
}

// ── Platform-Specific Port Cleanup ──────────────────────────────────

/// Kill any process holding a specific port (cleans up orphans).
#[cfg(unix)]
fn kill_port_holders(port: u16) {
    if let Ok(output) = Command::new("lsof")
        .args(["-ti", &format!(":{}", port)])
        .output()
    {
        let pids = String::from_utf8_lossy(&output.stdout);
        for pid in pids.trim().lines() {
            let pid = pid.trim();
            if !pid.is_empty() {
                let _ = Command::new("kill").arg(pid).output();
            }
        }
        // Force kill after brief wait
        std::thread::sleep(Duration::from_millis(300));
        if let Ok(output2) = Command::new("lsof")
            .args(["-ti", &format!(":{}", port)])
            .output()
        {
            let pids2 = String::from_utf8_lossy(&output2.stdout);
            for pid in pids2.trim().lines() {
                let pid = pid.trim();
                if !pid.is_empty() {
                    let _ = Command::new("kill").args(["-9", pid]).output();
                }
            }
        }
    }
}

#[cfg(target_os = "windows")]
fn kill_port_holders(port: u16) {
    // Use netstat to find PIDs holding the port, then taskkill
    if let Ok(output) = Command::new("netstat")
        .args(["-ano", "-p", "TCP"])
        .output()
    {
        let text = String::from_utf8_lossy(&output.stdout);
        let port_str = format!(":{}", port);
        for line in text.lines() {
            if line.contains(&port_str) && line.contains("LISTENING") {
                if let Some(pid) = line.split_whitespace().last() {
                    if pid != "0" {
                        let _ = Command::new("taskkill")
                            .args(["/PID", pid, "/F"])
                            .output();
                    }
                }
            }
        }
    }
}
