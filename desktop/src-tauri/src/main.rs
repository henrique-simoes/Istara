// Istara Desktop — System tray app for server management and compute donation.
//
// Two modes:
// - Server+Client: manages backend, frontend, and relay subprocesses
// - Client-only: manages relay daemon only, connects to remote server
//
// On first launch (no config file), shows a setup wizard window.
// On subsequent launches, minimizes to system tray.
// Auto-checks for updates via tauri-plugin-updater.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend_setup;
mod commands;
mod config;
mod first_run;
mod health;
mod installer;
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

            // Set up system tray
            tray::setup_tray(app.handle(), &cfg)?;

            // Clone the Arc so we can use it without lifetime issues
            let pm = app.state::<AppState>().process_manager.clone();

            // If server mode, auto-start services
            if cfg.mode == "server" && !cfg.install_dir.is_empty() {
                if let Ok(mut guard) = pm.lock() {
                    let _ = guard.start_backend(&cfg.install_dir);
                    let _ = guard.start_frontend(&cfg.install_dir);
                    if cfg.donate_compute {
                        let _ = guard.start_relay(&cfg.install_dir, &cfg.connection_string);
                    }
                }
            }

            // If client mode with connection string, start relay
            if cfg.mode == "client" && !cfg.connection_string.is_empty() && cfg.donate_compute {
                if let Ok(mut guard) = pm.lock() {
                    let install_dir = if cfg.install_dir.is_empty() {
                        commands::find_install_dir_public()
                    } else {
                        cfg.install_dir.clone()
                    };
                    let _ = guard.start_relay(&install_dir, &cfg.connection_string);
                }
            }

            // Start background health checker
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                health::health_loop(handle);
            });

            // Check for updates on startup (non-blocking)
            #[cfg(desktop)]
            {
                let update_handle = app.handle().clone();
                tauri::async_runtime::spawn(async move {
                    check_for_update_on_startup(update_handle).await;
                });
            }

            // If first run (no config file exists), show the setup wizard window
            if config::is_first_run() {
                let window = tauri::WebviewWindowBuilder::new(
                    app,
                    "setup",
                    tauri::WebviewUrl::App("index.html".into()),
                )
                .title("Istara Setup")
                .inner_size(640.0, 520.0)
                .resizable(false)
                .center()
                .build()?;
                window.show()?;
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
            installer::detect_dependencies,
            installer::install_dependency,
            commands::run_backend_setup,
            commands::run_frontend_setup,
            commands::save_setup_config,
        ])
        .run(tauri::generate_context!())
        .expect("error while running Istara desktop app");
}

/// Check for updates on startup. Shows a dialog if an update is available.
#[cfg(desktop)]
async fn check_for_update_on_startup(app: tauri::AppHandle) {
    use tauri_plugin_updater::UpdaterExt;
    use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};

    // Wait a few seconds before checking (let the app finish loading)
    tokio::time::sleep(std::time::Duration::from_secs(5)).await;

    match app.updater() {
        Ok(updater) => {
            match updater.check().await {
                Ok(Some(update)) => {
                    let version = update.version.clone();
                    let body = update.body.clone().unwrap_or_default();
                    let preview = if body.len() > 200 { &body[..200] } else { &body };

                    let yes = app
                        .dialog()
                        .message(format!(
                            "Istara {} is available (you have {}).\n\n{}\n\nUpdate now?",
                            version, env!("CARGO_PKG_VERSION"), preview
                        ))
                        .title("Update Available")
                        .kind(MessageDialogKind::Info)
                        .buttons(MessageDialogButtons::OkCancelCustom("Update Now".to_string(), "Later".to_string()))
                        .blocking_show();

                    if yes {
                        println!("User accepted update to {}", version);
                        match update.download_and_install(
                            |chunk, total| {
                                let pct = total.map(|t| (chunk as u64) * 100 / t).unwrap_or(0);
                                println!("Downloading update: {}%", pct);
                            },
                            || println!("Download complete — installing..."),
                        ).await {
                            Ok(_) => {
                                println!("Update installed — restarting");
                                app.restart();
                            }
                            Err(e) => {
                                eprintln!("Update install failed: {}", e);
                                let _ = app.dialog()
                                    .message(format!("Update failed: {}", e))
                                    .title("Update Error")
                                    .kind(MessageDialogKind::Error)
                                    .buttons(MessageDialogButtons::Ok)
                                    .blocking_show();
                            }
                        }
                    }
                }
                Ok(None) => {
                    println!("Already on latest version");
                }
                Err(e) => {
                    eprintln!("Update check failed: {}", e);
                }
            }
        }
        Err(e) => {
            eprintln!("Updater init failed: {}", e);
        }
    }
}
