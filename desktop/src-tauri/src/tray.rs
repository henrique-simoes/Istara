/// System tray — attaches menu to the config-created tray icon.
///
/// IMPORTANT: tauri.conf.json creates a tray icon with ID "main" automatically.
/// We must NOT create a new TrayIconBuilder — that creates an invisible second icon.
/// Instead, we get the existing icon via app.tray_by_id("main") and attach our menu.

use crate::commands::AppState;
use crate::config::AppConfig;
use crate::process::ProcessManager;
use std::sync::{Arc, Mutex};
use tauri::{
    menu::{Menu, MenuItem},
    AppHandle, Manager, Runtime,
};

pub fn setup_tray<R: Runtime>(
    app: &AppHandle<R>,
    cfg: &AppConfig,
) -> Result<(), Box<dyn std::error::Error>> {
    let menu = if cfg.mode == "server" {
        build_server_menu(app)?
    } else {
        build_client_menu(app, cfg)?
    };

    let pm: Arc<Mutex<ProcessManager>> = {
        let state = app.state::<AppState>();
        state.process_manager.clone()
    };

    // Get the EXISTING tray icon created by tauri.conf.json (ID = "main")
    // Do NOT use TrayIconBuilder::new() — that creates a second invisible icon
    let tray = app
        .tray_by_id("main")
        .expect("Tray icon 'main' should exist from tauri.conf.json");

    tray.set_menu(Some(menu))?;
    tray.set_show_menu_on_left_click(true)?;

    tray.on_menu_event(move |app, event| {
        let id = event.id().as_ref();
        match id {
            "open" => {
                let cfg = crate::config::load_config();
                let url = if cfg.mode == "server" {
                    "http://localhost:3000".to_string()
                } else {
                    cfg.server_url.clone()
                };
                let _ = open::that(&url);
            }
            "start_stop_server" => {
                let cfg = crate::config::load_config();
                let dir = if cfg.install_dir.is_empty() {
                    crate::commands::find_install_dir_public()
                } else {
                    cfg.install_dir.clone()
                };
                if let Ok(mut guard) = pm.lock() {
                    if guard.is_running() {
                        guard.stop_all();
                    } else {
                        let _ = guard.start_backend(&dir);
                        let _ = guard.start_frontend(&dir);
                    }
                }
            }
            "start_lm" => {
                #[cfg(target_os = "macos")]
                {
                    let _ = std::process::Command::new("open")
                        .arg("-a")
                        .arg("LM Studio")
                        .spawn();
                }
                #[cfg(target_os = "windows")]
                {
                    let _ = std::process::Command::new("cmd")
                        .args(["/c", "start", "", "lms"])
                        .spawn();
                }
            }
            "donate" => {
                let mut cfg = crate::config::load_config();
                cfg.donate_compute = !cfg.donate_compute;
                let _ = crate::config::save_config(&cfg);
                if let Ok(mut guard) = pm.lock() {
                    if cfg.donate_compute {
                        let dir = if cfg.install_dir.is_empty() {
                            crate::commands::find_install_dir_public()
                        } else {
                            cfg.install_dir.clone()
                        };
                        let _ = guard.start_relay(&dir, &cfg.connection_string);
                    } else {
                        guard.stop_relay();
                    }
                }
            }
            "stats" => {
                if let Some(window) = app.get_webview_window("stats") {
                    let _ = window.show();
                    let _ = window.set_focus();
                } else {
                    let _ = tauri::WebviewWindowBuilder::new(
                        app,
                        "stats",
                        tauri::WebviewUrl::App("index.html".into()),
                    )
                    .title("Istara — System Stats")
                    .inner_size(400.0, 300.0)
                    .build();
                }
            }
            "change_server" => {
                if let Some(window) = app.get_webview_window("setup") {
                    let _ = window.show();
                    let _ = window.set_focus();
                } else {
                    let _ = tauri::WebviewWindowBuilder::new(
                        app,
                        "setup",
                        tauri::WebviewUrl::App("index.html".into()),
                    )
                    .title("Istara — Change Server")
                    .inner_size(640.0, 520.0)
                    .center()
                    .build();
                }
            }
            "check_updates" => {
                let handle = app.clone();
                tauri::async_runtime::spawn(async move {
                    use tauri_plugin_updater::UpdaterExt;
                    use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};

                    match handle.updater() {
                        Ok(updater) => match updater.check().await {
                            Ok(Some(update)) => {
                                let version = update.version.clone();
                                let body = update.body.clone().unwrap_or_default();
                                let preview = if body.len() > 200 { &body[..200] } else { &body };
                                let yes = handle
                                    .dialog()
                                    .message(format!("Istara {} is available.\n\n{}\n\nUpdate now?", version, preview))
                                    .title("Update Available")
                                    .kind(MessageDialogKind::Info)
                                    .buttons(MessageDialogButtons::OkCancelCustom("Update Now".to_string(), "Later".to_string()))
                                    .blocking_show();
                                if yes {
                                    let _ = update.download_and_install(|_, _| {}, || {}).await;
                                    handle.restart();
                                }
                            }
                            Ok(None) => {
                                let _ = handle.dialog()
                                    .message("You're running the latest version of Istara.")
                                    .title("No Updates")
                                    .kind(MessageDialogKind::Info)
                                    .buttons(MessageDialogButtons::Ok)
                                    .blocking_show();
                            }
                            Err(e) => {
                                let _ = handle.dialog()
                                    .message(format!("Could not check for updates: {}", e))
                                    .title("Update Check Failed")
                                    .kind(MessageDialogKind::Error)
                                    .buttons(MessageDialogButtons::Ok)
                                    .blocking_show();
                            }
                        },
                        Err(e) => eprintln!("Updater error: {}", e),
                    }
                });
            }
            "quit" => {
                if let Ok(mut guard) = pm.lock() {
                    guard.stop_all();
                }
                app.exit(0);
            }
            _ => {}
        }
    });

    Ok(())
}

fn build_server_menu<R: Runtime>(
    app: &AppHandle<R>,
) -> Result<Menu<R>, Box<dyn std::error::Error>> {
    let server_running = check_port(8000);
    let lm_running = check_port(1234);
    let ollama_running = check_port(11434);
    let cfg = crate::config::load_config();

    let server_label = if server_running {
        "Stop Istara Server"
    } else {
        "Start Istara Server"
    };

    let lm_label = if lm_running {
        "LM Studio: Running ✓"
    } else if ollama_running {
        "Ollama: Running ✓"
    } else {
        "Start LM Studio"
    };

    let donate_label = if cfg.donate_compute {
        "Compute Donation: On"
    } else {
        "Compute Donation: Off"
    };

    let menu = Menu::with_items(
        app,
        &[
            &MenuItem::with_id(app, "open", "Open Istara", true, None::<&str>)?,
            &MenuItem::with_id(app, "start_stop_server", server_label, true, None::<&str>)?,
            &MenuItem::with_id(app, "start_lm", lm_label, true, None::<&str>)?,
            &MenuItem::with_id(app, "stats", "System Stats...", true, None::<&str>)?,
            &MenuItem::with_id(app, "donate", donate_label, true, None::<&str>)?,
            &MenuItem::with_id(app, "check_updates", "Check for Updates", true, None::<&str>)?,
            &MenuItem::with_id(app, "quit", "Quit Istara", true, None::<&str>)?,
        ],
    )?;
    Ok(menu)
}

fn build_client_menu<R: Runtime>(
    app: &AppHandle<R>,
    cfg: &AppConfig,
) -> Result<Menu<R>, Box<dyn std::error::Error>> {
    let status = if cfg.connection_string.is_empty() {
        "⚠ Not Connected"
    } else {
        "✓ Connected"
    };

    let donate_label = if cfg.donate_compute {
        "Compute Donation: On"
    } else {
        "Compute Donation: Off"
    };

    let menu = Menu::with_items(
        app,
        &[
            &MenuItem::with_id(app, "status", status, false, None::<&str>)?,
            &MenuItem::with_id(app, "open", "Open Istara", true, None::<&str>)?,
            &MenuItem::with_id(app, "stats", "System Stats...", true, None::<&str>)?,
            &MenuItem::with_id(app, "donate", donate_label, true, None::<&str>)?,
            &MenuItem::with_id(app, "change_server", "Change Server...", true, None::<&str>)?,
            &MenuItem::with_id(app, "check_updates", "Check for Updates", true, None::<&str>)?,
            &MenuItem::with_id(app, "quit", "Quit Istara", true, None::<&str>)?,
        ],
    )?;
    Ok(menu)
}

fn check_port(port: u16) -> bool {
    std::net::TcpStream::connect_timeout(
        &format!("127.0.0.1:{}", port).parse().unwrap(),
        std::time::Duration::from_secs(1),
    )
    .is_ok()
}
