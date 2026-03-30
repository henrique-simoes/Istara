/// Tauri IPC commands — real process management wired to ProcessManager.
use crate::config;
use crate::process::ProcessManager;
use crate::stats;
use std::sync::Mutex;
use tauri::State;

/// Shared process manager stored in Tauri managed state.
pub struct AppState {
    pub process_manager: Mutex<ProcessManager>,
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
    let install_dir = if cfg.install_dir.is_empty() {
        // Default: look for backend/frontend relative to app bundle or CWD
        find_install_dir()
    } else {
        cfg.install_dir.clone()
    };

    let mut pm = state.process_manager.lock().map_err(|e| e.to_string())?;
    pm.start_backend(&install_dir)?;
    pm.start_frontend(&install_dir)?;

    // If compute donation is enabled, also start relay
    if cfg.donate_compute {
        pm.start_relay(&install_dir, &cfg.connection_string)?;
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
        let install_dir = if cfg.install_dir.is_empty() {
            find_install_dir()
        } else {
            cfg.install_dir.clone()
        };
        pm.start_relay(&install_dir, &cfg.connection_string)?;
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
    let mut cfg = config::load_config();
    cfg.connection_string = conn_str;
    cfg.mode = "client".to_string();
    config::save_config(&cfg)?;

    // Restart relay with new connection string
    let mut pm = state.process_manager.lock().map_err(|e| e.to_string())?;
    pm.stop_relay();
    if cfg.donate_compute {
        let install_dir = if cfg.install_dir.is_empty() {
            find_install_dir()
        } else {
            cfg.install_dir.clone()
        };
        pm.start_relay(&install_dir, &cfg.connection_string)?;
    }

    Ok("Connection string saved and relay restarted".to_string())
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

#[tauri::command]
pub fn get_server_status() -> Result<serde_json::Value, String> {
    // Check if backend health endpoint responds
    let healthy = match std::net::TcpStream::connect_timeout(
        &"127.0.0.1:8000".parse().unwrap(),
        std::time::Duration::from_secs(2),
    ) {
        Ok(_) => true,
        Err(_) => false,
    };

    Ok(serde_json::json!({
        "backend_running": healthy,
        "mode": config::load_config().mode,
    }))
}

/// Public wrapper for find_install_dir (used from main.rs).
pub fn find_install_dir_public() -> String {
    find_install_dir()
}

/// Find the Istara installation directory.
/// Checks: config, app bundle Resources, CWD, ~/.istara
fn find_install_dir() -> String {
    // 1. Check app bundle (macOS)
    #[cfg(target_os = "macos")]
    {
        if let Ok(exe) = std::env::current_exe() {
            let resources = exe
                .parent() // MacOS/
                .and_then(|p| p.parent()) // Contents/
                .map(|p| p.join("Resources").join("istara"));
            if let Some(path) = resources {
                if path.join("backend").exists() {
                    return path.to_string_lossy().to_string();
                }
            }
        }
    }

    // 2. Check CWD
    if std::path::Path::new("backend").exists() {
        return ".".to_string();
    }

    // 3. Check ~/.istara
    if let Some(home) = dirs::home_dir() {
        let istara_dir = home.join(".istara");
        if istara_dir.join("backend").exists() {
            return istara_dir.to_string_lossy().to_string();
        }
    }

    // 4. Check standard install paths
    #[cfg(target_os = "windows")]
    {
        let prog = std::path::Path::new(r"C:\Program Files\Istara");
        if prog.join("backend").exists() {
            return prog.to_string_lossy().to_string();
        }
    }

    // Fallback: use home dir
    dirs::home_dir()
        .map(|h| h.join(".istara").to_string_lossy().to_string())
        .unwrap_or_else(|| ".".to_string())
}
