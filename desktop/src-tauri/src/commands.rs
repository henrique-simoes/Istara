/// Tauri IPC commands — process management only.
/// Reads install_dir from ~/.istara/config.json (set by the shell installer).
use crate::config;
use crate::path_resolver;
use crate::process::ProcessManager;
use crate::stats;
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
        return Err("Istara not installed. Run: curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash".to_string());
    }
    let dir = &cfg.install_dir;
    if !std::path::Path::new(dir).join("backend").exists() {
        return Err(format!("Backend not found at {}. Reinstall Istara.", dir));
    }

    let mut pm = state.process_manager.lock().map_err(|e| e.to_string())?;
    pm.start_backend(dir)?;
    pm.start_frontend(dir)?;
    if cfg.donate_compute {
        if let Err(e) = pm.start_relay(dir, &cfg.connection_string) {
            eprintln!("[tray] Relay start failed during server start: {}", e);
        }
    }
    Ok("Server started".to_string())
}

#[tauri::command]
pub fn stop_server(state: State<'_, AppState>) -> Result<String, String> {
    let mut pm = state.process_manager.lock().map_err(|e| e.to_string())?;
    pm.stop_all();
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
pub fn set_connection_string(state: State<'_, AppState>, conn_str: String) -> Result<String, String> {
    // Validate connection string format
    let trimmed = conn_str.trim();
    if !trimmed.is_empty() && !trimmed.starts_with("rcl_") && !trimmed.starts_with("ws://") && !trimmed.starts_with("wss://") {
        return Err("Invalid connection string. Expected rcl_... (from admin) or ws://... URL.".to_string());
    }

    let mut cfg = config::load_config();
    cfg.connection_string = trimmed.to_string();
    cfg.mode = "client".to_string();
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
    // Check if the server is actually running before opening
    let port_open = std::net::TcpStream::connect_timeout(
        &"127.0.0.1:3000".parse().unwrap(),
        std::time::Duration::from_secs(1),
    ).is_ok() || std::net::TcpStream::connect_timeout(
        &"127.0.0.1:8000".parse().unwrap(),
        std::time::Duration::from_secs(1),
    ).is_ok();

    if !port_open {
        return Err("Server is not running. Start it first.".to_string());
    }
    open::that(&cfg.server_url).map_err(|e| e.to_string())
}

#[tauri::command]
pub fn get_server_status() -> Result<serde_json::Value, String> {
    Ok(serde_json::json!({
        "backend_running": check_port(8000),
        "frontend_running": check_port(3000),
        "lm_studio_running": check_port(1234),
        "ollama_running": check_port(11434),
        "mode": config::load_config().mode,
        "install_dir": config::load_config().install_dir,
    }))
}

fn check_port(port: u16) -> bool {
    std::net::TcpStream::connect_timeout(
        &format!("127.0.0.1:{}", port).parse().unwrap(),
        std::time::Duration::from_secs(1),
    ).is_ok()
}
