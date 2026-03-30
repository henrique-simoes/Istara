/// Process management — delegates to istara.sh for backend + frontend.
/// Relay is managed directly since istara.sh doesn't handle it.
///
/// Architecture: The system tray is a thin GUI layer. istara.sh handles
/// PID files, process groups, port cleanup, and health waits. This ensures
/// the CLI and GUI use identical process management logic — one source of truth.

use crate::path_resolver;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::time::Duration;

pub struct ProcessManager {
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

/// Find istara.sh in the install directory or ~/.istara.
fn find_istara_script(install_dir: &str) -> Result<PathBuf, String> {
    // Check install_dir first
    if !install_dir.is_empty() {
        let script = PathBuf::from(install_dir).join("istara.sh");
        if script.exists() {
            return Ok(script);
        }
    }

    // Check ~/.istara/istara.sh
    if let Some(home) = dirs::home_dir() {
        let alt = home.join(".istara").join("istara.sh");
        if alt.exists() {
            return Ok(alt);
        }
    }

    Err(format!(
        "istara.sh not found. Install Istara first:\n  curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash"
    ))
}

impl ProcessManager {
    pub fn new() -> Self {
        let log_dir = dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".istara")
            .join("logs");
        let _ = fs::create_dir_all(&log_dir);
        Self {
            relay: None,
            log_dir,
        }
    }

    /// Start backend + frontend via istara.sh.
    /// BLOCKING: waits for health checks (up to ~35s). Run in a background thread.
    pub fn start_server(install_dir: &str) -> Result<String, String> {
        let script = find_istara_script(install_dir)?;

        eprintln!("[tray] Starting server via {}", script.display());
        let output = Command::new("bash")
            .arg(script.to_str().unwrap())
            .arg("start")
            .current_dir(if install_dir.is_empty() {
                dirs::home_dir()
                    .unwrap_or_else(|| PathBuf::from("."))
                    .join(".istara")
                    .to_str()
                    .unwrap_or(".")
                    .to_string()
            } else {
                install_dir.to_string()
            })
            .output()
            .map_err(|e| format!("istara.sh start failed: {}", e))?;

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        let stderr = String::from_utf8_lossy(&output.stderr).to_string();
        let combined = strip_ansi(&format!("{}{}", stdout, stderr));

        if check_port(8000) || check_port(3000) {
            eprintln!("[tray] Server started successfully");
            Ok(combined)
        } else if output.status.success() {
            eprintln!("[tray] istara.sh reported success but ports not yet bound");
            Ok(combined)
        } else {
            let msg = combined.trim().to_string();
            eprintln!("[tray] Server failed to start:\n{}", msg);
            Err(if msg.is_empty() {
                "Server failed to start. Check ~/.istara/logs/ for details.".to_string()
            } else {
                msg
            })
        }
    }

    /// Stop backend + frontend via istara.sh.
    /// BLOCKING: run in a background thread.
    pub fn stop_server(install_dir: &str) -> Result<String, String> {
        let script = find_istara_script(install_dir)?;

        eprintln!("[tray] Stopping server via {}", script.display());
        let output = Command::new("bash")
            .arg(script.to_str().unwrap())
            .arg("stop")
            .current_dir(if install_dir.is_empty() {
                dirs::home_dir()
                    .unwrap_or_else(|| PathBuf::from("."))
                    .join(".istara")
                    .to_str()
                    .unwrap_or(".")
                    .to_string()
            } else {
                install_dir.to_string()
            })
            .output()
            .map_err(|e| format!("istara.sh stop failed: {}", e))?;

        let stdout = String::from_utf8_lossy(&output.stdout).to_string();
        eprintln!("[tray] Server stopped");
        Ok(strip_ansi(&stdout))
    }

    /// Start the relay daemon. Managed directly (not part of istara.sh).
    pub fn start_relay(&mut self, install_dir: &str, connection_string: &str) -> Result<(), String> {
        // Clean up dead relay first
        if let Some(ref mut c) = self.relay {
            match c.try_wait() {
                Ok(Some(_)) | Err(_) => {
                    self.relay = None;
                }
                Ok(None) => return Ok(()), // Already running
            }
        }

        let relay_dir = format!("{}/relay", install_dir);
        if !Path::new(&relay_dir).exists() {
            return Err(
                "Relay directory not found. Compute donation requires the relay component."
                    .to_string(),
            );
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
        let err_file = log_file
            .try_clone()
            .map_err(|e| format!("Cannot clone log file: {}", e))?;

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

    /// Stop relay on drop. Backend/frontend are managed by istara.sh PID files.
    pub fn stop_all(&mut self) {
        self.stop_relay();
    }

    /// Check if relay is actually running.
    pub fn is_relay_running(&mut self) -> bool {
        if let Some(ref mut c) = self.relay {
            match c.try_wait() {
                Ok(Some(_)) | Err(_) => {
                    self.relay = None;
                    false
                }
                Ok(None) => true,
            }
        } else {
            false
        }
    }
}

impl Drop for ProcessManager {
    fn drop(&mut self) {
        self.stop_all();
    }
}

/// Strip ANSI escape codes from a string (istara.sh output has colors).
fn strip_ansi(s: &str) -> String {
    let mut result = String::with_capacity(s.len());
    let mut chars = s.chars().peekable();
    while let Some(c) = chars.next() {
        if c == '\x1b' {
            // Skip escape sequence: ESC [ ... final_byte
            if chars.peek() == Some(&'[') {
                chars.next();
                while let Some(&next) = chars.peek() {
                    chars.next();
                    if next.is_ascii_alphabetic() || next == 'm' {
                        break;
                    }
                }
            }
        } else {
            result.push(c);
        }
    }
    result
}
