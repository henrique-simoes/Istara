/// System tray — MANAGER only (not installer).
/// Finds the existing Istara installation and manages start/stop/status.
///
/// Key fixes:
/// - is_running() verifies actual process state + ports
/// - Menu rebuilds after every action to update labels
/// - Errors are logged, not silently discarded
/// - Donate compute verifies relay actually starts

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
                // Check if server is actually running before opening browser
                if check_port(3000) || check_port(8000) {
                    let _ = open::that(&cfg.server_url);
                } else {
                    eprintln!("[tray] Server not running — cannot open browser");
                    // Try to show a dialog
                    let handle = app.clone();
                    tauri::async_runtime::spawn(async move {
                        use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};
                        let _ = handle.dialog()
                            .message("Istara server is not running.\n\nStart it first using the tray menu.")
                            .title("Server Not Running")
                            .kind(MessageDialogKind::Warning)
                            .buttons(MessageDialogButtons::Ok)
                            .blocking_show();
                    });
                }
            }
            "start_stop_server" => {
                let cfg = crate::config::load_config();
                if cfg.install_dir.is_empty() {
                    eprintln!("[tray] No install_dir configured");
                    let handle = app.clone();
                    tauri::async_runtime::spawn(async move {
                        use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};
                        let _ = handle.dialog()
                            .message("Istara is not installed yet.\n\nRun: curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash")
                            .title("Not Installed")
                            .kind(MessageDialogKind::Warning)
                            .buttons(MessageDialogButtons::Ok)
                            .blocking_show();
                    });
                    return;
                }
                if let Ok(mut guard) = pm.lock() {
                    if guard.is_running() {
                        guard.stop_all();
                        eprintln!("[tray] Server stopped");
                    } else {
                        if let Err(e) = guard.start_backend(&cfg.install_dir) {
                            eprintln!("[tray] Backend start failed: {}", e);
                        }
                        if let Err(e) = guard.start_frontend(&cfg.install_dir) {
                            eprintln!("[tray] Frontend start failed: {}", e);
                        }
                        if cfg.donate_compute {
                            if let Err(e) = guard.start_relay(&cfg.install_dir, &cfg.connection_string) {
                                eprintln!("[tray] Relay start failed: {}", e);
                            }
                        }
                    }
                }
                // Rebuild menu to update Start/Stop label
                rebuild_menu(app);
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

                if cfg.donate_compute {
                    // Try to start relay BEFORE saving config
                    if let Ok(mut guard) = pm.lock() {
                        match guard.start_relay(&cfg.install_dir, &cfg.connection_string) {
                            Ok(()) => {
                                let _ = crate::config::save_config(&cfg);
                                eprintln!("[tray] Compute donation enabled, relay started");
                            }
                            Err(e) => {
                                eprintln!("[tray] Relay start failed: {}. Donation NOT enabled.", e);
                                cfg.donate_compute = false; // Revert
                            }
                        }
                    }
                } else {
                    let _ = crate::config::save_config(&cfg);
                    if let Ok(mut guard) = pm.lock() {
                        guard.stop_relay();
                    }
                    eprintln!("[tray] Compute donation disabled");
                }
                // Rebuild menu to update label
                rebuild_menu(app);
            }
            "check_updates" => {
                let handle = app.clone();
                tauri::async_runtime::spawn(async move {
                    use tauri_plugin_updater::UpdaterExt;
                    use tauri_plugin_dialog::{
                        DialogExt, MessageDialogButtons, MessageDialogKind,
                    };

                    let mut handled = false;
                    if let Ok(updater) = handle.updater() {
                        match updater.check().await {
                            Ok(Some(update)) => {
                                handled = true;
                                let v = update.version.clone();
                                let body = update.body.clone().unwrap_or_default();
                                let preview =
                                    if body.len() > 200 { &body[..200] } else { &body };
                                let yes = handle
                                    .dialog()
                                    .message(format!(
                                        "Istara {} is available.\n\n{}\n\nUpdate now?",
                                        v, preview
                                    ))
                                    .title("Update Available")
                                    .kind(MessageDialogKind::Info)
                                    .buttons(MessageDialogButtons::OkCancelCustom(
                                        "Update Now".to_string(),
                                        "Later".to_string(),
                                    ))
                                    .blocking_show();
                                if yes {
                                    let _ =
                                        update.download_and_install(|_, _| {}, || {}).await;
                                    handle.restart();
                                }
                            }
                            Ok(None) => {
                                handled = true;
                                let _ = handle
                                    .dialog()
                                    .message("You're running the latest version of Istara.")
                                    .title("No Updates")
                                    .kind(MessageDialogKind::Info)
                                    .buttons(MessageDialogButtons::Ok)
                                    .blocking_show();
                            }
                            Err(e) => {
                                eprintln!("[tray] Updater check error: {}", e);
                            }
                        }
                    }

                    if !handled {
                        // Fallback for shell-installed Istara
                        let yes = handle
                            .dialog()
                            .message(
                                "Check for updates on GitHub?\n\nFor shell-installed Istara, run:\nistara update",
                            )
                            .title("Check for Updates")
                            .kind(MessageDialogKind::Info)
                            .buttons(MessageDialogButtons::OkCancelCustom(
                                "Open GitHub".to_string(),
                                "Close".to_string(),
                            ))
                            .blocking_show();
                        if yes {
                            let _ = open::that(
                                "https://github.com/henrique-simoes/Istara/releases",
                            );
                        }
                    }
                });
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

/// Rebuild the tray menu to reflect current state (Start/Stop, Donate On/Off).
fn rebuild_menu<R: Runtime>(app: &AppHandle<R>) {
    let cfg = crate::config::load_config();
    let result = if cfg.mode == "server" {
        build_server_menu(app)
    } else {
        build_client_menu(app, &cfg)
    };
    match result {
        Ok(new_menu) => {
            if let Some(tray) = app.tray_by_id("main") {
                if let Err(e) = tray.set_menu(Some(new_menu)) {
                    eprintln!("[tray] Failed to update menu: {}", e);
                }
            }
        }
        Err(e) => eprintln!("[tray] Failed to build menu: {}", e),
    }
}

/// Public wrapper for health loop to rebuild menu periodically.
pub fn rebuild_menu_pub<R: Runtime>(app: &AppHandle<R>) {
    rebuild_menu(app);
}

fn build_server_menu<R: Runtime>(
    app: &AppHandle<R>,
) -> Result<Menu<R>, Box<dyn std::error::Error>> {
    let server_running = check_port(8000) || check_port(3000);
    let lm_running = check_port(1234);
    let ollama_running = check_port(11434);
    let cfg = crate::config::load_config();

    let server_label = if server_running {
        "Stop Istara Server"
    } else {
        "Start Istara Server"
    };
    let lm_label = if lm_running {
        "LM Studio: Running \u{2713}"
    } else if ollama_running {
        "Ollama: Running \u{2713}"
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
        "\u{26A0} Not Connected"
    } else {
        "\u{2713} Connected"
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
