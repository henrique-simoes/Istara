/// Child process management — start/stop backend, frontend, and relay.
/// Ports the logic from reclaw.sh to Rust for cross-platform subprocess control.

use std::process::{Child, Command};

pub struct ProcessManager {
    backend: Option<Child>,
    frontend: Option<Child>,
    relay: Option<Child>,
}

impl ProcessManager {
    pub fn new() -> Self {
        Self {
            backend: None,
            frontend: None,
            relay: None,
        }
    }

    pub fn start_backend(&mut self, install_dir: &str) -> Result<(), String> {
        let child = Command::new("python")
            .args(["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])
            .current_dir(format!("{}/backend", install_dir))
            .spawn()
            .map_err(|e| format!("Failed to start backend: {}", e))?;
        self.backend = Some(child);
        Ok(())
    }

    pub fn start_frontend(&mut self, install_dir: &str) -> Result<(), String> {
        let child = Command::new("npm")
            .args(["run", "dev", "--", "--port", "3000"])
            .current_dir(format!("{}/frontend", install_dir))
            .spawn()
            .map_err(|e| format!("Failed to start frontend: {}", e))?;
        self.frontend = Some(child);
        Ok(())
    }

    pub fn start_relay(&mut self, install_dir: &str, connection_string: &str) -> Result<(), String> {
        let mut cmd = Command::new("node");
        cmd.arg("index.mjs");
        if !connection_string.is_empty() {
            cmd.args(["--connection-string", connection_string]);
        } else {
            cmd.args(["--server", "ws://localhost:8000/ws/relay"]);
        }
        let child = cmd
            .current_dir(format!("{}/relay", install_dir))
            .spawn()
            .map_err(|e| format!("Failed to start relay: {}", e))?;
        self.relay = Some(child);
        Ok(())
    }

    pub fn stop_all(&mut self) {
        for child in [&mut self.backend, &mut self.frontend, &mut self.relay] {
            if let Some(ref mut c) = child {
                let _ = c.kill();
            }
            *child = None;
        }
    }
}

impl Drop for ProcessManager {
    fn drop(&mut self) {
        self.stop_all();
    }
}
