// Istara Desktop — System tray app for server management and compute donation.
//
// Two modes:
// - Server+Client: manages backend, frontend, and relay subprocesses
// - Client-only: manages relay daemon only, connects to remote server
//
// On first launch (no config file), shows a setup wizard window.
// On subsequent launches, minimizes to system tray.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod backend_setup;
mod commands;
mod config;
mod health;
mod installer;
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
        .manage(AppState {
            process_manager: Arc::new(Mutex::new(ProcessManager::new())),
        })
        .setup(|app| {
            let cfg = config::load_config();

            // Set up system tray
            tray::setup_tray(app.handle(), &cfg)?;

            // If server mode, auto-start services
            if cfg.mode == "server" && !cfg.install_dir.is_empty() {
                let app_state = app.state::<AppState>();
                if let Ok(mut pm) = app_state.process_manager.lock() {
                    let _ = pm.start_backend(&cfg.install_dir);
                    let _ = pm.start_frontend(&cfg.install_dir);
                    if cfg.donate_compute {
                        let _ = pm.start_relay(&cfg.install_dir, &cfg.connection_string);
                    }
                }
            }

            // If client mode with connection string, start relay
            if cfg.mode == "client" && !cfg.connection_string.is_empty() && cfg.donate_compute {
                let app_state = app.state::<AppState>();
                if let Ok(mut pm) = app_state.process_manager.lock() {
                    let install_dir = if cfg.install_dir.is_empty() {
                        commands::find_install_dir_public()
                    } else {
                        cfg.install_dir.clone()
                    };
                    let _ = pm.start_relay(&install_dir, &cfg.connection_string);
                }
            }

            // Start background health checker
            let handle = app.handle().clone();
            std::thread::spawn(move || {
                health::health_loop(handle);
            });

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
        .on_window_event(|window, event| {
            // Graceful shutdown on window close
            if let tauri::WindowEvent::Destroyed = event {
                if window.label() == "main" || window.label() == "setup" {
                    let pm = window.state::<AppState>().process_manager.clone();
                    if let Ok(mut guard) = pm.lock() {
                        guard.stop_all();
                    }
                }
            }
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
