/// Configuration for the Istara desktop app.
/// Stored at ~/.istara/config.json
/// Handles corrupt configs gracefully with backup + recovery.
use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine as _};
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

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ConnectionStringHint {
    pub server_url: String,
    pub ws_url: String,
    pub label: String,
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

pub fn decode_connection_string_hint(conn_str: &str) -> Option<ConnectionStringHint> {
    let trimmed = conn_str.trim();
    if !trimmed.starts_with("rcl_") {
        return None;
    }

    let body = &trimmed["rcl_".len()..];
    let (payload_b64, _) = body.split_once('.')?;
    let payload = URL_SAFE_NO_PAD.decode(payload_b64).ok()?;
    let value: serde_json::Value = serde_json::from_slice(&payload).ok()?;

    Some(ConnectionStringHint {
        server_url: value
            .get("server_url")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .trim_end_matches('/')
            .to_string(),
        ws_url: value
            .get("ws_url")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .to_string(),
        label: value
            .get("label")
            .and_then(|v| v.as_str())
            .unwrap_or_default()
            .to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn decodes_connection_string_hint_without_signature_verification() {
        let payload = serde_json::json!({
            "v": 1,
            "server_url": "https://team.example.com",
            "ws_url": "wss://team.example.com/ws/relay",
            "label": "Design Team"
        });
        let payload_b64 = URL_SAFE_NO_PAD.encode(payload.to_string().as_bytes());
        let conn = format!("rcl_{}.signature", payload_b64);

        let hint = decode_connection_string_hint(&conn).expect("hint should decode");
        assert_eq!(hint.server_url, "https://team.example.com");
        assert_eq!(hint.ws_url, "wss://team.example.com/ws/relay");
        assert_eq!(hint.label, "Design Team");
    }

    #[test]
    fn ignores_non_connection_strings() {
        assert!(decode_connection_string_hint("https://example.com").is_none());
        assert!(decode_connection_string_hint("rcl_invalid").is_none());
    }
}
