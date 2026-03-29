// ReClaw Desktop — System tray app for server management and compute donation.
//
// Two modes:
// - Server+Client: manages backend, frontend, and relay subprocesses
// - Client-only: manages relay daemon only, connects to remote server
//
// The tray icon provides quick access to start/stop, stats, and settings.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;
mod config;
mod process;
mod stats;
mod tray;

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            // Load config to determine mode
            let cfg = config::load_config();

            // Build and set up system tray
            tray::setup_tray(app.handle(), &cfg)?;

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
        ])
        .run(tauri::generate_context!())
        .expect("error while running ReClaw desktop app");
}
