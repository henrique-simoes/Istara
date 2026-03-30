/// Background health checker + update checker.
/// Polls backend health every 10s, rebuilds tray menu every 30s,
/// checks for updates every 6 hours.

use std::io::Read;
use std::time::Duration;
use tauri::{AppHandle, Emitter, Runtime};

const HEALTH_INTERVAL: Duration = Duration::from_secs(10);
const MENU_REBUILD_INTERVAL: Duration = Duration::from_secs(30);
const UPDATE_CHECK_INTERVAL: Duration = Duration::from_secs(6 * 3600); // 6 hours

#[derive(serde::Serialize, Clone)]
pub struct HealthStatus {
    pub backend: bool,
    pub frontend: bool,
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

    loop {
        std::thread::sleep(HEALTH_INTERVAL);

        // Health check
        let backend_healthy = check_port(8000);
        let frontend_healthy = check_port(3000);

        let status = HealthStatus {
            backend: backend_healthy,
            frontend: frontend_healthy,
            timestamp: now_secs(),
        };
        let _ = app.emit("health-status", &status);

        // Only rebuild tray menu when state changes OR every 30s (not every 10s)
        let state_changed = backend_healthy != prev_backend || frontend_healthy != prev_frontend;
        if state_changed || last_menu_rebuild.elapsed() >= MENU_REBUILD_INTERVAL {
            crate::tray::rebuild_menu_pub(&app);
            last_menu_rebuild = std::time::Instant::now();
            prev_backend = backend_healthy;
            prev_frontend = frontend_healthy;
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

/// Check GitHub Releases API for a newer version.
fn check_for_update() -> Option<UpdateAvailable> {
    let current = read_version_file().unwrap_or_else(|| "unknown".to_string());
    if current == "unknown" {
        return None;
    }

    let url = "https://api.github.com/repos/henrique-simoes/Istara/releases/latest";

    match std::process::Command::new("curl")
        .args([
            "-sS",
            "--max-time", "10",
            "-H", "Accept: application/vnd.github.v3+json",
            "-H", &format!("User-Agent: Istara/{}", current),
            url,
        ])
        .output()
    {
        Ok(output) if output.status.success() => {
            let body = String::from_utf8_lossy(&output.stdout);

            // Check for rate limit
            if body.contains("API rate limit") {
                eprintln!("[tray] GitHub API rate limited, skipping update check");
                return None;
            }

            let tag = extract_json_string(&body, "tag_name")
                .map(|t| t.trim_start_matches('v').to_string())
                .unwrap_or_default();
            let html_url = extract_json_string(&body, "html_url").unwrap_or_default();
            let changelog = extract_json_string(&body, "body").unwrap_or_default();

            // CalVer comparison: lexicographic works for YYYY.MM.DD.N format
            if !tag.is_empty() && tag > current {
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
        Ok(output) => {
            let stderr = String::from_utf8_lossy(&output.stderr);
            if !stderr.is_empty() {
                eprintln!("[tray] Update check failed: {}", stderr.trim());
            }
            None
        }
        Err(e) => {
            eprintln!("[tray] curl not available for update check: {}", e);
            None
        }
    }
}

fn read_version_file() -> Option<String> {
    // Try multiple locations for the VERSION file
    let mut candidates: Vec<std::path::PathBuf> = vec![
        "VERSION".into(),
        "../VERSION".into(),
        "../../VERSION".into(),
    ];

    // Also try from ~/.istara/VERSION (shell install location)
    if let Some(home) = dirs::home_dir() {
        candidates.push(home.join(".istara").join("VERSION"));
    }

    for path in &candidates {
        if let Ok(mut f) = std::fs::File::open(path) {
            let mut s = String::new();
            if f.read_to_string(&mut s).is_ok() {
                let v = s.trim().to_string();
                if !v.is_empty() {
                    return Some(v);
                }
            }
        }
    }

    // Try reading from app bundle (macOS)
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

/// Simple JSON string extraction (avoids serde_json dependency).
fn extract_json_string(json: &str, key: &str) -> Option<String> {
    let needle = format!("\"{}\"", key);
    let pos = json.find(&needle)?;
    let after_key = &json[pos + needle.len()..];
    let colon_pos = after_key.find(':')?;
    let after_colon = after_key[colon_pos + 1..].trim_start();

    if after_colon.starts_with('"') {
        let content = &after_colon[1..];
        let end_quote = content.find('"')?;
        Some(
            content[..end_quote]
                .replace("\\n", "\n")
                .replace("\\\"", "\""),
        )
    } else if after_colon.starts_with("null") {
        None
    } else {
        None
    }
}

fn check_port(port: u16) -> bool {
    std::net::TcpStream::connect_timeout(
        &format!("127.0.0.1:{}", port).parse().unwrap(),
        Duration::from_secs(1),
    )
    .is_ok()
}

fn now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}
