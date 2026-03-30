/// Child process management — start/stop backend, frontend, relay.
/// Uses path_resolver to find Python/Node/npm at their actual locations.

use crate::path_resolver;
use std::process::{Child, Command, Stdio};

pub struct ProcessManager {
    backend: Option<Child>,
    frontend: Option<Child>,
    relay: Option<Child>,
}

impl ProcessManager {
    pub fn new() -> Self {
        Self { backend: None, frontend: None, relay: None }
    }

    /// Start the backend (FastAPI via uvicorn).
    pub fn start_backend(&mut self, install_dir: &str) -> Result<(), String> {
        if self.backend.is_some() { return Ok(()); }

        let backend_dir = format!("{}/backend", install_dir);
        if !std::path::Path::new(&backend_dir).exists() {
            return Err(format!("Backend directory not found: {}", backend_dir));
        }

        let python = path_resolver::find_python(install_dir);
        println!("Starting backend with: {} -m uvicorn (cwd: {})", python, backend_dir);

        let child = Command::new(&python)
            .args(["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])
            .current_dir(&backend_dir)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("Failed to start backend ({}): {}", python, e))?;

        println!("Backend started (PID: {})", child.id());
        self.backend = Some(child);
        Ok(())
    }

    /// Start the frontend (Next.js).
    pub fn start_frontend(&mut self, install_dir: &str) -> Result<(), String> {
        if self.frontend.is_some() { return Ok(()); }

        let frontend_dir = format!("{}/frontend", install_dir);
        if !std::path::Path::new(&frontend_dir).exists() {
            return Err(format!("Frontend directory not found: {}", frontend_dir));
        }

        let has_build = std::path::Path::new(&format!("{}/.next", frontend_dir)).exists();

        let (cmd, args) = if has_build {
            let npx = path_resolver::find_npx();
            (npx, vec!["next".to_string(), "start".to_string(), "--port".to_string(), "3000".to_string()])
        } else {
            let npm = path_resolver::find_npm();
            (npm, vec!["run".to_string(), "dev".to_string(), "--".to_string(), "--port".to_string(), "3000".to_string()])
        };

        println!("Starting frontend with: {} {:?} (cwd: {})", cmd, args, frontend_dir);

        let child = Command::new(&cmd)
            .args(&args)
            .current_dir(&frontend_dir)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("Failed to start frontend ({}): {}", cmd, e))?;

        println!("Frontend started (PID: {})", child.id());
        self.frontend = Some(child);
        Ok(())
    }

    /// Start the relay daemon.
    pub fn start_relay(&mut self, install_dir: &str, connection_string: &str) -> Result<(), String> {
        if self.relay.is_some() { return Ok(()); }

        let relay_dir = format!("{}/relay", install_dir);
        let node = path_resolver::find_node();

        let mut cmd = Command::new(&node);
        cmd.arg("index.mjs");
        if !connection_string.is_empty() {
            cmd.args(["--connection-string", connection_string]);
        } else {
            cmd.args(["--server", "ws://localhost:8000/ws/relay"]);
        }

        let child = cmd
            .current_dir(&relay_dir)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()
            .map_err(|e| format!("Failed to start relay ({}): {}", node, e))?;

        println!("Relay started (PID: {})", child.id());
        self.relay = Some(child);
        Ok(())
    }

    pub fn stop_relay(&mut self) {
        if let Some(ref mut child) = self.relay {
            let _ = child.kill();
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
                println!("{} stopped", name);
            }
            *child = None;
        }
    }

    pub fn is_running(&self) -> bool {
        self.backend.is_some() || self.frontend.is_some()
    }
}

impl Drop for ProcessManager {
    fn drop(&mut self) {
        self.stop_all();
    }
}
