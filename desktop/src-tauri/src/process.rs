/// Child process management — start/stop backend, frontend, relay.
/// Uses path_resolver to find Python/Node/npm at their actual locations.
/// Logs process output to ~/.istara/logs/ for debugging.

use crate::path_resolver;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};

pub struct ProcessManager {
    backend: Option<Child>,
    frontend: Option<Child>,
    relay: Option<Child>,
    log_dir: PathBuf,
}

fn check_port(port: u16) -> bool {
    std::net::TcpStream::connect_timeout(
        &format!("127.0.0.1:{}", port).parse().unwrap(),
        std::time::Duration::from_secs(1),
    )
    .is_ok()
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

    /// Check if a child process is actually alive (not just stored in the struct).
    fn is_child_alive(child: &mut Option<Child>) -> bool {
        if let Some(ref mut c) = child {
            // try_wait: Ok(Some(_)) = exited, Ok(None) = still running, Err = error
            match c.try_wait() {
                Ok(Some(_status)) => {
                    // Process exited — clean up the zombie
                    false
                }
                Ok(None) => true,  // Still running
                Err(_) => false,   // Error checking — assume dead
            }
        } else {
            false
        }
    }

    /// Clean up dead child processes (call before start to handle zombies).
    fn cleanup_dead(&mut self) {
        if !Self::is_child_alive(&mut self.backend) {
            self.backend = None;
        }
        if !Self::is_child_alive(&mut self.frontend) {
            self.frontend = None;
        }
        if !Self::is_child_alive(&mut self.relay) {
            self.relay = None;
        }
    }

    /// Start the backend (FastAPI via uvicorn). Logs to ~/.istara/logs/backend.log.
    pub fn start_backend(&mut self, install_dir: &str) -> Result<(), String> {
        self.cleanup_dead();
        if self.backend.is_some() {
            return Ok(()); // Actually running (verified by cleanup_dead)
        }

        let backend_dir = format!("{}/backend", install_dir);
        if !Path::new(&backend_dir).exists() {
            return Err(format!("Backend directory not found: {}", backend_dir));
        }

        let python = path_resolver::find_python(install_dir);
        if !Path::new(&python).exists() && !which_exists(&python) {
            return Err(format!(
                "Python not found at '{}'. Install Python 3.12+ or run the installer.",
                python
            ));
        }

        let log_file = fs::File::create(self.log_dir.join("backend.log"))
            .map_err(|e| format!("Cannot create backend log: {}", e))?;
        let err_file = log_file.try_clone()
            .map_err(|e| format!("Cannot clone log file: {}", e))?;

        eprintln!("[tray] Starting backend: {} -m uvicorn (cwd: {})", python, backend_dir);

        let child = Command::new(&python)
            .args(["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"])
            .current_dir(&backend_dir)
            .stdout(Stdio::from(log_file))
            .stderr(Stdio::from(err_file))
            .spawn()
            .map_err(|e| format!("Failed to start backend ({}): {}", python, e))?;

        eprintln!("[tray] Backend started (PID: {})", child.id());
        self.backend = Some(child);
        Ok(())
    }

    /// Start the frontend (Next.js). Logs to ~/.istara/logs/frontend.log.
    pub fn start_frontend(&mut self, install_dir: &str) -> Result<(), String> {
        self.cleanup_dead();
        if self.frontend.is_some() {
            return Ok(());
        }

        let frontend_dir = format!("{}/frontend", install_dir);
        if !Path::new(&frontend_dir).exists() {
            return Err(format!("Frontend directory not found: {}", frontend_dir));
        }

        // Check node_modules exist
        if !Path::new(&format!("{}/node_modules", frontend_dir)).exists() {
            return Err("Frontend dependencies not installed. Run: cd frontend && npm install".to_string());
        }

        let has_build = Path::new(&format!("{}/.next", frontend_dir)).exists();

        let (cmd, args) = if has_build {
            let npx = path_resolver::find_npx();
            (npx, vec!["next".to_string(), "start".to_string(), "--port".to_string(), "3000".to_string()])
        } else {
            let npm = path_resolver::find_npm();
            (npm, vec!["run".to_string(), "dev".to_string(), "--".to_string(), "--port".to_string(), "3000".to_string()])
        };

        let log_file = fs::File::create(self.log_dir.join("frontend.log"))
            .map_err(|e| format!("Cannot create frontend log: {}", e))?;
        let err_file = log_file.try_clone()
            .map_err(|e| format!("Cannot clone log file: {}", e))?;

        eprintln!("[tray] Starting frontend: {} {:?} (cwd: {})", cmd, args, frontend_dir);

        let child = Command::new(&cmd)
            .args(&args)
            .current_dir(&frontend_dir)
            .stdout(Stdio::from(log_file))
            .stderr(Stdio::from(err_file))
            .spawn()
            .map_err(|e| format!("Failed to start frontend ({}): {}", cmd, e))?;

        eprintln!("[tray] Frontend started (PID: {})", child.id());
        self.frontend = Some(child);
        Ok(())
    }

    /// Start the relay daemon. Logs to ~/.istara/logs/relay.log.
    pub fn start_relay(&mut self, install_dir: &str, connection_string: &str) -> Result<(), String> {
        self.cleanup_dead();
        if self.relay.is_some() {
            return Ok(());
        }

        let relay_dir = format!("{}/relay", install_dir);
        if !Path::new(&relay_dir).exists() {
            return Err(format!("Relay directory not found: {}", relay_dir));
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
            .map_err(|e| format!("Cannot clone log file: {}", e))?;

        let child = cmd
            .current_dir(&relay_dir)
            .stdout(Stdio::from(log_file))
            .stderr(Stdio::from(err_file))
            .spawn()
            .map_err(|e| format!("Failed to start relay ({}): {}", node, e))?;

        eprintln!("[tray] Relay started (PID: {})", child.id());
        self.relay = Some(child);
        Ok(())
    }

    pub fn stop_relay(&mut self) {
        if let Some(ref mut child) = self.relay {
            let _ = child.kill();
            let _ = child.wait(); // Reap the zombie
            eprintln!("[tray] Relay stopped");
        }
        self.relay = None;
    }

    pub fn stop_all(&mut self) {
        for (name, child) in [
            ("Backend", &mut self.backend),
            ("Frontend", &mut self.frontend),
            ("Relay", &mut self.relay),
        ] {
            if let Some(ref mut c) = child {
                let _ = c.kill();
                let _ = c.wait(); // Reap the zombie
                eprintln!("[tray] {} stopped", name);
            }
            *child = None;
        }
    }

    /// Check if backend or frontend is actually running (verifies process + port).
    pub fn is_running(&mut self) -> bool {
        self.cleanup_dead();
        // Check both: our managed process AND the actual port
        let has_managed = self.backend.is_some() || self.frontend.is_some();
        let has_ports = check_port(8000) || check_port(3000);
        has_managed || has_ports
    }
}

impl Drop for ProcessManager {
    fn drop(&mut self) {
        self.stop_all();
    }
}

/// Check if a command exists on PATH.
fn which_exists(cmd: &str) -> bool {
    Command::new("which")
        .arg(cmd)
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .status()
        .map(|s| s.success())
        .unwrap_or(false)
}
