/// Tauri IPC commands — real process management.
use crate::config;
use crate::first_run;
use crate::path_resolver;
use crate::process::ProcessManager;
use crate::stats;
use std::sync::{Arc, Mutex};
use tauri::State;

/// Shared process manager stored in Tauri managed state.
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
pub fn start_server(app: tauri::AppHandle, state: State<'_, AppState>) -> Result<String, String> {
    let cfg = config::load_config();
    let mut install_dir = get_install_dir(&cfg);

    // If no install dir found, try to copy source from bundle first
    if !std::path::Path::new(&install_dir).join("backend").exists() {
        match first_run::ensure_source_copied(&app) {
            Ok(data_dir) => {
                install_dir = data_dir.to_string_lossy().to_string();
                // Save for next time
                let mut cfg = config::load_config();
                cfg.install_dir = install_dir.clone();
                let _ = config::save_config(&cfg);
            }
            Err(e) => {
                return Err(format!("Cannot find Istara source code. Run the setup wizard first. ({})", e));
            }
        }
    }

    let mut pm = state.process_manager.lock().map_err(|e| e.to_string())?;
    pm.start_backend(&install_dir)?;
    pm.start_frontend(&install_dir)?;

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
        let dir = get_install_dir(&cfg);
        pm.start_relay(&dir, &cfg.connection_string)?;
        Ok("Relay started".to_string())
    } else {
        pm.stop_relay();
        Ok("Relay stopped".to_string())
    }
}

#[tauri::command]
pub fn set_connection_string(state: State<'_, AppState>, conn_str: String) -> Result<String, String> {
    let mut cfg = config::load_config();
    cfg.connection_string = conn_str;
    cfg.mode = "client".to_string();
    config::save_config(&cfg)?;

    let mut pm = state.process_manager.lock().map_err(|e| e.to_string())?;
    pm.stop_relay();
    if cfg.donate_compute {
        let dir = get_install_dir(&cfg);
        pm.start_relay(&dir, &cfg.connection_string)?;
    }

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

#[tauri::command]
pub fn get_server_status() -> Result<serde_json::Value, String> {
    let backend = check_port(8000);
    let frontend = check_port(3000);
    let lm_studio = check_port(1234);
    let ollama = check_port(11434);

    Ok(serde_json::json!({
        "backend_running": backend,
        "frontend_running": frontend,
        "lm_studio_running": lm_studio,
        "ollama_running": ollama,
        "mode": config::load_config().mode,
    }))
}

/// Run first-run copy + backend setup.
#[tauri::command]
pub fn run_backend_setup(app: tauri::AppHandle, llm_provider: String) -> Result<Vec<String>, String> {
    let mut log = Vec::new();

    // Step 1: Copy source from bundle to writable data dir
    log.push("Copying source files to data directory...".to_string());
    let data_dir = first_run::ensure_source_copied(&app)?;
    log.push(format!("  Source copied to {}", data_dir.display()));

    // Step 2: Run backend setup in the writable dir
    let setup_logs = crate::backend_setup::setup_backend(&data_dir, &llm_provider)?;
    log.extend(setup_logs);

    // Step 3: Save the install dir to config
    let mut cfg = config::load_config();
    cfg.install_dir = data_dir.to_string_lossy().to_string();
    config::save_config(&cfg)?;
    log.push(format!("  Configuration saved (install dir: {})", data_dir.display()));

    Ok(log)
}

/// Run frontend setup.
#[tauri::command]
pub fn run_frontend_setup() -> Result<Vec<String>, String> {
    let cfg = config::load_config();
    let install_dir = get_install_dir(&cfg);
    let path = std::path::Path::new(&install_dir);
    crate::backend_setup::setup_frontend(path)
}

/// Save setup config and mark first-run complete.
#[tauri::command]
pub fn save_setup_config(mode: String, _llm_provider: String, connection_string: String) -> Result<String, String> {
    let mut cfg = config::load_config();
    cfg.mode = mode;
    cfg.connection_string = connection_string;
    if cfg.install_dir.is_empty() {
        // Use default data dir
        if let Some(home) = dirs::home_dir() {
            let data_dir = home.join("Library/Application Support/com.istara.desktop");
            if data_dir.join("backend").exists() {
                cfg.install_dir = data_dir.to_string_lossy().to_string();
            }
        }
    }
    config::save_config(&cfg)?;
    Ok("Setup complete".to_string())
}

/// Public wrapper for finding install dir.
pub fn find_install_dir_public() -> String {
    get_install_dir(&config::load_config())
}

/// Determine the install directory.
/// Priority: config > app data dir > ~/.istara > CWD
/// NEVER returns the .app bundle path (read-only).
fn get_install_dir(cfg: &config::AppConfig) -> String {
    // 1. Config override
    if !cfg.install_dir.is_empty() && std::path::Path::new(&cfg.install_dir).join("backend").exists() {
        return cfg.install_dir.clone();
    }

    // 2. Standard app data dir (where first_run copies to)
    #[cfg(target_os = "macos")]
    {
        if let Some(home) = dirs::home_dir() {
            let data_dir = home.join("Library/Application Support/com.istara.desktop");
            if data_dir.join("backend").exists() {
                return data_dir.to_string_lossy().to_string();
            }
        }
    }

    #[cfg(target_os = "windows")]
    {
        if let Ok(appdata) = std::env::var("APPDATA") {
            let data_dir = std::path::Path::new(&appdata).join("com.istara.desktop");
            if data_dir.join("backend").exists() {
                return data_dir.to_string_lossy().to_string();
            }
        }
    }

    // 3. ~/.istara (manual setup)
    if let Some(home) = dirs::home_dir() {
        let istara_dir = home.join(".istara");
        if istara_dir.join("backend").exists() {
            return istara_dir.to_string_lossy().to_string();
        }
    }

    // 4. CWD (development)
    if std::path::Path::new("backend").exists() {
        return ".".to_string();
    }

    // 5. Windows Program Files
    #[cfg(target_os = "windows")]
    {
        let prog = std::path::Path::new(r"C:\Program Files\Istara");
        if prog.join("backend").exists() {
            return prog.to_string_lossy().to_string();
        }
    }

    // Fallback
    dirs::home_dir()
        .map(|h| h.join(".istara").to_string_lossy().to_string())
        .unwrap_or_else(|| ".".to_string())
}

fn check_port(port: u16) -> bool {
    std::net::TcpStream::connect_timeout(
        &format!("127.0.0.1:{}", port).parse().unwrap(),
        std::time::Duration::from_secs(1),
    ).is_ok()
}
