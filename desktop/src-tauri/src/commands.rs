/// Tauri IPC commands — called from the webview frontend.
use crate::config;
use crate::stats;

#[tauri::command]
pub fn get_stats() -> Result<serde_json::Value, String> {
    stats::get_system_stats()
}

#[tauri::command]
pub fn get_config() -> Result<config::AppConfig, String> {
    Ok(config::load_config())
}

#[tauri::command]
pub fn start_server() -> Result<String, String> {
    // TODO: spawn backend + frontend subprocesses
    Ok("Server starting...".to_string())
}

#[tauri::command]
pub fn stop_server() -> Result<String, String> {
    // TODO: send SIGTERM to backend + frontend PIDs
    Ok("Server stopping...".to_string())
}

#[tauri::command]
pub fn toggle_relay(enabled: bool) -> Result<String, String> {
    let mut cfg = config::load_config();
    cfg.donate_compute = enabled;
    config::save_config(&cfg)?;
    // TODO: start/stop relay subprocess
    Ok(if enabled { "Relay started" } else { "Relay stopped" }.to_string())
}

#[tauri::command]
pub fn set_connection_string(conn_str: String) -> Result<String, String> {
    let mut cfg = config::load_config();
    cfg.connection_string = conn_str;
    cfg.mode = "client".to_string();
    config::save_config(&cfg)?;
    // TODO: restart relay with new connection string
    Ok("Connection string saved".to_string())
}

#[tauri::command]
pub fn open_browser() -> Result<(), String> {
    let cfg = config::load_config();
    let url = if cfg.mode == "server" {
        "http://localhost:3000".to_string()
    } else {
        cfg.server_url
    };
    open::that(&url).map_err(|e| e.to_string())
}
