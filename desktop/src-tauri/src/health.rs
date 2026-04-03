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

        // Periodic update check (every 6 hours)
        if last_update_check.elapsed() >= UPDATE_CHECK_INTERVAL {
            last_update_check = std::time::Instant::now();

            if let Some(update) = check_for_update() {
                let _ = app.emit("update-available", &update);
            }
        }
    }
}

/// Check GitHub Releases for a newer version.
fn check_for_update() -> Option<UpdateAvailable> {
    let current = read_version_file().unwrap_or_else(|| "unknown".to_string());
    if current == "unknown" {
        return None;
    }
    let url = "https://api.github.com/repos/henrique-simoes/Istara/releases/latest";
    let output = std::process::Command::new("curl")
        .args(["-sS", "-H", "Accept: application/vnd.github.v3+json", url])
        .output()
        .ok()?;
    if !output.status.success() {
        return None;
    }

    let body = String::from_utf8_lossy(&output.stdout);
    let tag = extract_json_string(&body, "tag_name")
        .map(|t| t.trim_start_matches('v').to_string())
        .unwrap_or_default();
    let html_url = extract_json_string(&body, "html_url").unwrap_or_default();
    let changelog = extract_json_string(&body, "body").unwrap_or_default();

    if !tag.is_empty() && is_newer(&tag, &current) {
        Some(UpdateAvailable {
            current_version: current,
            latest_version: tag,
            release_url: html_url,
            changelog: changelog.chars().take(200).collect(),
        })
    } else {
        None
    }
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

fn extract_json_string(json: &str, key: &str) -> Option<String> {
    let needle = format!("\"{}\"", key);
    let pos = json.find(&needle)?;
    let after_key = &json[pos + needle.len()..];
    let colon_pos = after_key.find(':')?;
    let after_colon = after_key[colon_pos + 1..].trim_start();

    if after_colon.starts_with('"') {
        let content = &after_colon[1..];
        let end_quote = content.find('"')?;
        Some(content[..end_quote].replace("\\n", "\n").replace("\\\"", "\""))
    } else if after_colon.starts_with("null") {
        None
    } else {
        None
    }
}

fn now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

pub fn is_newer(latest: &str, current: &str) -> bool {
    use version_compare::{compare, Cmp};
    match compare(latest, current) {
        Ok(Cmp::Gt) => true,
        _ => false,
    }
}
