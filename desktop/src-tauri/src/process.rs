/// Child process management — start/stop backend, frontend, and relay.
/// Ports the logic from istara.sh to Rust for cross-platform subprocess control.

use std::process::{Child, Command, Stdio};

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

    /// Start the backend (FastAPI via uvicorn).
    /// Uses the Python venv if it exists, otherwise system Python.
    pub fn start_backend(&mut self, install_dir: &str) -> Result<(), String> {
        if self.backend.is_some() {
            return Ok(()); // Already running
        }

        let backend_dir = format!("{}/backend", install_dir);

        // Determine Python executable: prefer venv, fallback to system
        let python = find_python(install_dir);

        let child = Command::new(&python)
            .args(["-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])
            .current_dir(&backend_dir)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to start backend ({}): {}", python, e))?;

        println!("Backend started (PID: {})", child.id());
        self.backend = Some(child);
        Ok(())
    }

    /// Start the frontend (Next.js).
    pub fn start_frontend(&mut self, install_dir: &str) -> Result<(), String> {
        if self.frontend.is_some() {
            return Ok(());
        }

        let frontend_dir = format!("{}/frontend", install_dir);

        // Check if production build exists
        let has_build = std::path::Path::new(&format!("{}/.next", frontend_dir)).exists();

        let (cmd, args) = if has_build {
            ("npx", vec!["next", "start", "--port", "3000"])
        } else {
            ("npm", vec!["run", "dev", "--", "--port", "3000"])
        };

        let child = Command::new(cmd)
            .args(&args)
            .current_dir(&frontend_dir)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to start frontend: {}", e))?;

        println!("Frontend started (PID: {})", child.id());
        self.frontend = Some(child);
        Ok(())
    }

    /// Start the relay daemon for compute donation.
    pub fn start_relay(&mut self, install_dir: &str, connection_string: &str) -> Result<(), String> {
        if self.relay.is_some() {
            return Ok(());
        }

        let relay_dir = format!("{}/relay", install_dir);

        let mut cmd = Command::new("node");
        cmd.arg("index.mjs");

        if !connection_string.is_empty() {
            cmd.args(["--connection-string", connection_string]);
        } else {
            cmd.args(["--server", "ws://localhost:8000/ws/relay"]);
        }

        let child = cmd
            .current_dir(&relay_dir)
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| format!("Failed to start relay: {}", e))?;

        println!("Relay started (PID: {})", child.id());
        self.relay = Some(child);
        Ok(())
    }

    /// Stop only the relay process.
    pub fn stop_relay(&mut self) {
        if let Some(ref mut child) = self.relay {
            let _ = child.kill();
            println!("Relay stopped");
        }
        self.relay = None;
    }

    /// Stop all managed processes.
    pub fn stop_all(&mut self) {
        for (name, child) in [
            ("Backend", &mut self.backend),
            ("Frontend", &mut self.frontend),
            ("Relay", &mut self.relay),
        ] {
            if let Some(ref mut c) = child {
                let pid = c.id();
                let _ = c.kill();
                println!("{} stopped (PID: {})", name, pid);
            }
            *child = None;
        }
    }

    /// Check if any processes are running.
    pub fn is_running(&self) -> bool {
        self.backend.is_some() || self.frontend.is_some()
    }
}

impl Drop for ProcessManager {
    fn drop(&mut self) {
        self.stop_all();
    }
}

/// Find the best Python executable for the installation.
fn find_python(install_dir: &str) -> String {
    // 1. Check for venv in install_dir
    #[cfg(target_os = "windows")]
    {
        let venv_python = format!(r"{}\venv\Scripts\python.exe", install_dir);
        if std::path::Path::new(&venv_python).exists() {
            return venv_python;
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        let venv_python = format!("{}/venv/bin/python", install_dir);
        if std::path::Path::new(&venv_python).exists() {
            return venv_python;
        }
    }

    // 2. Check for venv in backend subdir
    #[cfg(target_os = "windows")]
    {
        let venv_python = format!(r"{}\backend\venv\Scripts\python.exe", install_dir);
        if std::path::Path::new(&venv_python).exists() {
            return venv_python;
        }
    }

    #[cfg(not(target_os = "windows"))]
    {
        let venv_python = format!("{}/backend/venv/bin/python", install_dir);
        if std::path::Path::new(&venv_python).exists() {
            return venv_python;
        }
    }

    // 3. Fall back to system Python
    #[cfg(target_os = "windows")]
    { "python".to_string() }

    #[cfg(not(target_os = "windows"))]
    { "python3".to_string() }
}
