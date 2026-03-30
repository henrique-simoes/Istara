/// Background health checker + update checker.
/// Polls backend health endpoint every 10s.
/// Checks for updates every 6 hours.

use std::io::Read;
use std::time::Duration;
use tauri::{AppHandle, Emitter, Runtime};

const HEALTH_INTERVAL: Duration = Duration::from_secs(10);
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
    let mut last_update_check = std::time::Instant::now() - UPDATE_CHECK_INTERVAL; // Check immediately on first run

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

    // Use a simple HTTP GET to GitHub API
    let url = "https://api.github.com/repos/henrique-simoes/ReClaw/releases/latest";

    match std::process::Command::new("curl")
        .args(["-sS", "-H", "Accept: application/vnd.github.v3+json", url])
        .output()
    {
        Ok(output) if output.status.success() => {
            let body = String::from_utf8_lossy(&output.stdout);
            // Parse JSON manually (avoid serde_json dependency for this)
            let tag = extract_json_string(&body, "tag_name")
                .map(|t| t.trim_start_matches('v').to_string())
                .unwrap_or_default();
            let html_url = extract_json_string(&body, "html_url").unwrap_or_default();
            let changelog = extract_json_string(&body, "body").unwrap_or_default();

            if !tag.is_empty() && tag > current && current != "unknown" {
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
        _ => None,
    }
}

fn read_version_file() -> Option<String> {
    // Try multiple locations for the VERSION file
    for path in [
        "VERSION",
        "../VERSION",
        "../../VERSION",
    ] {
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
                .map(|p| p.join("Resources").join("reclaw").join("VERSION"));
            if let Some(path) = version_path {
                if let Ok(v) = std::fs::read_to_string(path) {
                    return Some(v.trim().to_string());
                }
            }
        }
    }

    None
}

/// Simple JSON string extraction (avoids external dependency).
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

fn check_port(port: u16) -> bool {
    std::net::TcpStream::connect_timeout(
        &format!("127.0.0.1:{}", port).parse().unwrap(),
        Duration::from_secs(2),
    )
    .is_ok()
}

fn now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}
