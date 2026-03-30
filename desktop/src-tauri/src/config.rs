/// Configuration for the Istara desktop app.
/// Stored at ~/.istara/config.json
/// Handles corrupt configs gracefully with backup + recovery.
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    /// "server" (full install) or "client" (relay only)
    pub mode: String,
    /// Server URL for client mode (from connection string)
    pub server_url: String,
    /// WebSocket URL for relay
    pub ws_url: String,
    /// Connection string (stored for reconnection)
    pub connection_string: String,
    /// Whether compute donation is enabled
    pub donate_compute: bool,
    /// Path to the Istara installation directory
    pub install_dir: String,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            mode: "server".to_string(),
            server_url: "http://localhost:3000".to_string(),
            ws_url: "ws://localhost:8000/ws/relay".to_string(),
            connection_string: String::new(),
            donate_compute: false,
            install_dir: String::new(),
        }
    }
}

fn config_path() -> PathBuf {
    let home = dirs::home_dir().unwrap_or_else(|| PathBuf::from("."));
    home.join(".istara").join("config.json")
}

pub fn load_config() -> AppConfig {
    let path = config_path();
    if !path.exists() {
        return AppConfig::default();
    }

    match std::fs::read_to_string(&path) {
        Ok(content) => {
            match serde_json::from_str::<AppConfig>(&content) {
                Ok(cfg) => cfg,
                Err(e) => {
                    // Config is corrupt — back it up and return defaults
                    eprintln!(
                        "[tray] WARNING: config.json is corrupt ({}). Backing up to config.json.bak",
                        e
                    );
                    let backup = path.with_extension("json.bak");
                    let _ = std::fs::copy(&path, &backup);
                    AppConfig::default()
                }
            }
        }
        Err(e) => {
            eprintln!("[tray] WARNING: Cannot read config.json: {}", e);
            AppConfig::default()
        }
    }
}

pub fn is_first_run() -> bool {
    !config_path().exists()
}

pub fn save_config(cfg: &AppConfig) -> Result<(), String> {
    let path = config_path();
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
    }
    let json = serde_json::to_string_pretty(cfg).map_err(|e| e.to_string())?;
    std::fs::write(path, json).map_err(|e| e.to_string())
}
