/// Background health checker + update checker.
/// Polls backend health every 10s, rebuilds tray menu on state change or every 30s,
/// checks for updates every 6 hours.

use crate::process;
use std::time::Duration;
use tauri::{AppHandle, Emitter, Runtime};

const HEALTH_INTERVAL: Duration = Duration::from_secs(10);
const MENU_REBUILD_INTERVAL: Duration = Duration::from_secs(30);
const UPDATE_CHECK_INTERVAL: Duration = Duration::from_secs(6 * 3600); // 6 hours

#[derive(serde::Serialize, Clone)]
pub struct HealthStatus {
    pub backend: bool,
    pub frontend: bool,
    pub lm_studio: bool,
    pub ollama: bool,
    pub timestamp: u64,
}

#[derive(serde::Serialize, Clone)]
pub struct UpdateAvailable {
    pub current_version: String,
    pub latest_version: String,
    pub release_url: String,
    pub changelog: String,
}

/// Long-running health check + update check loop.
pub fn health_loop<R: Runtime>(app: AppHandle<R>) {
    let mut last_update_check = std::time::Instant::now() - UPDATE_CHECK_INTERVAL;
    let mut last_menu_rebuild = std::time::Instant::now() - MENU_REBUILD_INTERVAL;
    let mut prev_backend = false;
    let mut prev_frontend = false;
    let mut prev_lm = false;
    let mut prev_ollama = false;

    loop {
        std::thread::sleep(HEALTH_INTERVAL);

        // Health check — all ports
        let backend_healthy = process::check_port(8000);
        let frontend_healthy = process::check_port(3000);
        let lm_healthy = process::is_lm_studio_running();
        let ollama_healthy = process::is_ollama_running();

        let status = HealthStatus {
            backend: backend_healthy,
            frontend: frontend_healthy,
            lm_studio: lm_healthy,
            ollama: ollama_healthy,
            timestamp: now_secs(),
        };
        let _ = app.emit("health-status", &status);

        // Rebuild tray menu when ANY state changes or every 30s
        let state_changed = backend_healthy != prev_backend
            || frontend_healthy != prev_frontend
            || lm_healthy != prev_lm
            || ollama_healthy != prev_ollama;

        if state_changed || last_menu_rebuild.elapsed() >= MENU_REBUILD_INTERVAL {
            crate::tray::rebuild_menu_pub(&app);
            last_menu_rebuild = std::time::Instant::now();
            prev_backend = backend_healthy;
            prev_frontend = frontend_healthy;
            prev_lm = lm_healthy;
            prev_ollama = ollama_healthy;
        }

        // Periodic update check (every 6 hours) — git-based, no API rate limit
        if last_update_check.elapsed() >= UPDATE_CHECK_INTERVAL {
            last_update_check = std::time::Instant::now();

            if let Some(update) = check_for_update() {
                let _ = app.emit("update-available", &update);
            }
        }
    }
}

/// Check for a newer version using git tags (no GitHub API needed).
fn check_for_update() -> Option<UpdateAvailable> {
    let current = read_version_file().unwrap_or_else(|| "unknown".to_string());
    if current == "unknown" {
        return None;
    }

    // Try git-based check (no rate limit)
    let install_dir = find_install_dir()?;
    let git_dir = install_dir.join(".git");
    if !git_dir.is_dir() {
        return None;
    }

    // Fetch latest tags
    let fetch = std::process::Command::new("git")
        .args(["fetch", "--tags", "--quiet"])
        .current_dir(&install_dir)
        .output();

    if let Ok(output) = fetch {
        if output.status.success() {
            let tag_output = std::process::Command::new("git")
                .args(["tag", "--sort=-v:refname"])
                .current_dir(&install_dir)
                .output();

            if let Ok(tag_out) = tag_output {
                if tag_out.status.success() {
                    let tags = String::from_utf8_lossy(&tag_out.stdout);
                    if let Some(latest_line) = tags.lines().next() {
                        let tag = latest_line.trim_start_matches('v').to_string();
                        if !tag.is_empty() && tag > current {
                            return Some(UpdateAvailable {
                                current_version: current,
                                latest_version: tag.clone(),
                                release_url: format!(
                                    "https://github.com/henrique-simoes/Istara/releases/tag/v{}",
                                    tag
                                ),
                                changelog: String::new(),
                            });
                        }
                    }
                }
            }
        }
    }

    None
}

fn read_version_file() -> Option<String> {
    let mut candidates: Vec<std::path::PathBuf> = vec![
        "VERSION".into(),
        "../VERSION".into(),
        "../../VERSION".into(),
    ];

    if let Some(home) = dirs::home_dir() {
        candidates.push(home.join(".istara").join("VERSION"));
    }

    for path in &candidates {
        if let Ok(v) = std::fs::read_to_string(path) {
            let trimmed = v.trim().to_string();
            if !trimmed.is_empty() {
                return Some(trimmed);
            }
        }
    }

    // Try from app bundle (macOS)
    #[cfg(target_os = "macos")]
    {
        if let Ok(exe) = std::env::current_exe() {
            let version_path = exe
                .parent()
                .and_then(|p| p.parent())
                .map(|p| p.join("Resources").join("istara").join("VERSION"));
            if let Some(path) = version_path {
                if let Ok(v) = std::fs::read_to_string(path) {
                    let trimmed = v.trim().to_string();
                    if !trimmed.is_empty() {
                        return Some(trimmed);
                    }
                }
            }
        }
    }

    None
}

fn find_install_dir() -> Option<std::path::PathBuf> {
    // Check config first
    let cfg = crate::config::load_config();
    if !cfg.install_dir.is_empty() {
        let dir = std::path::PathBuf::from(&cfg.install_dir);
        if dir.exists() {
            return Some(dir);
        }
    }

    // Check ~/.istara
    if let Some(home) = dirs::home_dir() {
        let dir = home.join(".istara");
        if dir.exists() {
            return Some(dir);
        }
    }

    None
}

fn now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}
