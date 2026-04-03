/// Tauri IPC commands for the Istara desktop companion.
/// Reads install_dir from ~/.istara/config.json (set by the shell installer).
use crate::config;
use crate::process::{self, ProcessManager};
use crate::stats;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use tauri::State;

pub struct AppState {
    pub process_manager: Arc<Mutex<ProcessManager>>,
}

#[tauri::command]
pub fn get_stats() -> Result<serde_json::Value, String> {
    stats::get_system_stats()
}

#[tauri::command]
pub fn get_config() -> Result<config::AppConfig, String> {
    Ok(config::load_config())
}

#[tauri::command]
pub fn start_server(state: State<'_, AppState>) -> Result<String, String> {
    let cfg = config::load_config();
    if cfg.install_dir.is_empty() {
        return Err(
            "Istara not installed. Run: curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash"
                .to_string(),
        );
    }

    // Start server via Rust-native process manager
    let mut pm = state.process_manager.lock().map_err(|e| e.to_string())?;
    pm.start_server(&cfg.install_dir)?;

    // Start relay if donation is enabled
    if cfg.donate_compute {
        if let Err(e) = pm.start_relay(&cfg.install_dir, &cfg.connection_string) {
            eprintln!("[tray] Relay start failed during server start: {}", e);
        }
    }
    Ok("Server starting...".to_string())
}

#[tauri::command]
pub fn stop_server(state: State<'_, AppState>) -> Result<String, String> {
    // Stop all processes (server + relay)
    let mut pm = state.process_manager.lock().map_err(|e| e.to_string())?;
    pm.stop_server()?;
    Ok("Server stopped".to_string())
}

#[tauri::command]
pub fn toggle_relay(state: State<'_, AppState>, enabled: bool) -> Result<String, String> {
    let mut cfg = config::load_config();
    cfg.donate_compute = enabled;
    config::save_config(&cfg)?;
    let mut pm = state.process_manager.lock().map_err(|e| e.to_string())?;
    if enabled {
        pm.start_relay(&cfg.install_dir, &cfg.connection_string)?;
        Ok("Relay started".to_string())
    } else {
        pm.stop_relay();
        Ok("Relay stopped".to_string())
    }
}

#[tauri::command]
pub fn set_connection_string(
    state: State<'_, AppState>,
    conn_str: String,
) -> Result<String, String> {
    // Validate connection string format
    let trimmed = conn_str.trim();
    if !trimmed.is_empty()
        && !trimmed.starts_with("rcl_")
        && !trimmed.starts_with("ws://")
        && !trimmed.starts_with("wss://")
    {
        return Err(
            "Invalid connection string. Expected rcl_... (from admin) or ws://... URL.".to_string(),
        );
    }

    let mut cfg = config::load_config();
    cfg.connection_string = trimmed.to_string();
    cfg.mode = "client".to_string();
    if let Some(hint) = config::decode_connection_string_hint(trimmed) {
        cfg.server_url = hint.server_url;
        cfg.ws_url = hint.ws_url;
    } else if trimmed.is_empty() {
        cfg.server_url.clear();
        cfg.ws_url.clear();
    }
    config::save_config(&cfg)?;
    let mut pm = state.process_manager.lock().map_err(|e| e.to_string())?;
    pm.stop_relay();
    if cfg.donate_compute && !trimmed.is_empty() {
        pm.start_relay(&cfg.install_dir, trimmed)?;
    }
    Ok("Connection string saved".to_string())
}

#[tauri::command]
pub fn open_browser() -> Result<(), String> {
    let cfg = config::load_config();
    let target = browser_target(&cfg, process::is_server_running())?;
    open::that(&target).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn save_setup_config(
    mode: String,
    _llm_provider: String,
    connection_string: String,
) -> Result<String, String> {
    let mut cfg = config::load_config();
    let home = dirs::home_dir().ok_or_else(|| "Could not resolve home directory".to_string())?;

    if cfg.install_dir.is_empty() {
        cfg.install_dir = home.join(".istara").to_string_lossy().to_string();
    }

    if mode == "client" {
        cfg.mode = "client".to_string();
        cfg.connection_string = connection_string.trim().to_string();
        cfg.donate_compute = !cfg.connection_string.is_empty();
        if let Some(hint) = config::decode_connection_string_hint(&cfg.connection_string) {
            cfg.server_url = hint.server_url;
            cfg.ws_url = hint.ws_url;
        } else {
            cfg.server_url.clear();
            cfg.ws_url.clear();
        }
    } else {
        cfg.mode = "server".to_string();
        if cfg.server_url.is_empty() {
            cfg.server_url = "http://localhost:3000".to_string();
        }
        if cfg.ws_url.is_empty() {
            cfg.ws_url = "ws://localhost:8000/ws/relay".to_string();
        }
    }

    config::save_config(&cfg)?;
    Ok("Configuration saved".to_string())
}

#[tauri::command]
pub fn run_backend_setup(llm_provider: String) -> Result<Vec<String>, String> {
    let install_dir = desktop_install_dir();
    let backend_dir = PathBuf::from(&install_dir).join("backend");
    if !backend_dir.exists() {
        return Err(
            "This desktop companion expects an existing Istara install at ~/.istara.\n\nFor a full Server install, run:\n  curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash"
                .to_string(),
        );
    }

    let mut logs = vec![format!("Using Istara install at {}", install_dir)];
    if PathBuf::from(&install_dir).join("venv").exists() {
        logs.push("Python environment already exists.".to_string());
    } else {
        logs.push("No Python virtual environment found yet. Run the shell installer to create it.".to_string());
    }
    if !llm_provider.trim().is_empty() {
        logs.push(format!("Selected provider: {}", llm_provider));
    }
    Ok(logs)
}

#[tauri::command]
pub fn run_frontend_setup() -> Result<Vec<String>, String> {
    let install_dir = desktop_install_dir();
    let frontend_dir = PathBuf::from(&install_dir).join("frontend");
    if !frontend_dir.exists() {
        return Err(
            "Frontend files were not found in ~/.istara.\n\nRun the shell installer first to prepare this machine for Server mode.".to_string(),
        );
    }

    let mut logs = vec![format!("Using frontend at {}", frontend_dir.display())];
    if frontend_dir.join(".next").exists() {
        logs.push("Existing production build detected.".to_string());
    } else {
        logs.push("No production build detected yet. Run the shell installer to build the frontend.".to_string());
    }
    Ok(logs)
}

#[tauri::command]
pub fn get_server_status() -> Result<serde_json::Value, String> {
    let cfg = config::load_config();
    Ok(serde_json::json!({
        "backend_running": process::check_port(8000),
        "frontend_running": process::check_port(3000),
        "lm_studio_running": process::is_lm_studio_running(),
        "ollama_running": process::is_ollama_running(),
        "mode": cfg.mode,
        "install_dir": cfg.install_dir,
        "donate_compute": cfg.donate_compute,
        "server_url": cfg.server_url,
        "connection_string_configured": !cfg.connection_string.is_empty(),
    }))
}

fn browser_target(cfg: &config::AppConfig, server_running: bool) -> Result<String, String> {
    if cfg.mode == "client" {
        if cfg.server_url.is_empty() {
            return Err(
                "This machine is in Client mode but no server is configured yet. Use Change Server and paste the rcl_ connection string from your admin.".to_string(),
            );
        }
        return Ok(cfg.server_url.clone());
    }

    if !server_running {
        return Err("Server is not running. Start it first.".to_string());
    }

    Ok(cfg.server_url.clone())
}

fn desktop_install_dir() -> String {
    let cfg = config::load_config();
    if !cfg.install_dir.is_empty() {
        return cfg.install_dir;
    }

    dirs::home_dir()
        .unwrap_or_else(|| PathBuf::from("."))
        .join(".istara")
        .to_string_lossy()
        .to_string()
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cfg(mode: &str, server_url: &str) -> config::AppConfig {
        config::AppConfig {
            mode: mode.to_string(),
            server_url: server_url.to_string(),
            ..Default::default()
        }
    }

    #[test]
    fn client_mode_uses_remote_server_url() {
        let open_target = browser_target(&cfg("client", "https://team.example.com"), false)
            .expect("client URL should open");
        assert_eq!(open_target, "https://team.example.com");
    }

    #[test]
    fn client_mode_requires_connection_details() {
        let err = browser_target(&cfg("client", ""), false).expect_err("should fail");
        assert!(err.contains("Client mode"));
    }

    #[test]
    fn server_mode_requires_local_server_to_be_running() {
        let err = browser_target(&cfg("server", "http://localhost:3000"), false)
            .expect_err("should fail");
        assert!(err.contains("Start it first"));
    }
}
