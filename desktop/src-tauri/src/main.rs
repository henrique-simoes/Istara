// Istara Desktop — System tray manager for Istara server and relay.
//
// This app does NOT install anything. Installation is handled by:
//   curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash
//
// The tray app reads ~/.istara/config.json to find the install directory,
// then manages start/stop of the backend, frontend, and relay processes.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod config;
mod health;
mod path_resolver;
mod process;
mod stats;
mod tray;

use commands::AppState;
use process::ProcessManager;
use std::sync::{Arc, Mutex};
use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_process::init())
        .manage(AppState {
            process_manager: Arc::new(Mutex::new(ProcessManager::new())),
        })
        .setup(|app| {
            let cfg = config::load_config();

            // Set up system tray menu
            tray::setup_tray(app.handle(), &cfg)?;

            // Clone Arc once for process management
            let pm = {
                let state = app.state::<AppState>();
                state.process_manager.clone()
            };

            // Auto-start server if config says so and install dir exists
            if cfg.mode == "server" && !cfg.install_dir.is_empty() {
                if std::path::Path::new(&cfg.install_dir).join("backend").exists() {
                    if let Ok(mut guard) = pm.lock() {
                        if let Err(e) = guard.start_backend(&cfg.install_dir) {
                            eprintln!("[tray] Auto-start backend failed: {}", e);
                        }
                        if let Err(e) = guard.start_frontend(&cfg.install_dir) {
                            eprintln!("[tray] Auto-start frontend failed: {}", e);
                        }
                        if cfg.donate_compute {
                            if let Err(e) = guard.start_relay(&cfg.install_dir, &cfg.connection_string) {
                                eprintln!("[tray] Auto-start relay failed: {}", e);
                            }
                        }
                    }
                } else {
                    eprintln!("[tray] Backend dir not found at: {}/backend", cfg.install_dir);
                }
            }

            // Auto-start relay for client mode
            if cfg.mode == "client" && !cfg.connection_string.is_empty() && cfg.donate_compute {
                if let Ok(mut guard) = pm.lock() {
                    if let Err(e) = guard.start_relay(&cfg.install_dir, &cfg.connection_string) {
                        eprintln!("[tray] Auto-start relay (client) failed: {}", e);
                    }
                }
            }

            // Background health + update checker
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                health::health_loop(handle);
            });

            // Auto-check for updates on startup
            #[cfg(desktop)]
            {
                let update_handle = app.handle().clone();
                tauri::async_runtime::spawn(async move {
                    check_for_update(update_handle).await;
                });
            }

            // If no config exists, show a message
            if config::is_first_run() {
                eprintln!("No Istara installation found. Install with:");
                eprintln!("  curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash");
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_stats,
            commands::get_config,
            commands::start_server,
            commands::stop_server,
            commands::toggle_relay,
            commands::set_connection_string,
            commands::open_browser,
            commands::get_server_status,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Istara desktop app");
}

#[cfg(desktop)]
async fn check_for_update(app: tauri::AppHandle) {
    use tauri_plugin_updater::UpdaterExt;
    use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};

    tokio::time::sleep(std::time::Duration::from_secs(10)).await;

    let Ok(updater) = app.updater() else { return };
    let Ok(Some(update)) = updater.check().await else { return };

    let version = update.version.clone();
    let body = update.body.clone().unwrap_or_default();
    let preview = if body.len() > 200 { &body[..200] } else { &body };

    let yes = app.dialog()
        .message(format!("Istara {} is available.\n\n{}\n\nUpdate now?", version, preview))
        .title("Update Available")
        .kind(MessageDialogKind::Info)
        .buttons(MessageDialogButtons::OkCancelCustom("Update Now".to_string(), "Later".to_string()))
        .blocking_show();

    if yes {
        if update.download_and_install(|_, _| {}, || {}).await.is_ok() {
            app.restart();
        }
    }
}
