/// System tray — mode-aware desktop companion for Istara.
/// Manages backend, frontend, and relay processes directly via ProcessManager.
/// Menu state is driven by config plus live health checks.
///
/// Fixed in v2026.03.30:
/// - Start/Stop runs in background thread, menu updates after delay
/// - Donate toggle always saves config, shows feedback on relay failure
/// - LM Studio click offers meaningful actions
/// - Check Updates shows clear result dialog
/// - Menu labels always reflect actual port state

use crate::commands::AppState;
use crate::config::AppConfig;
use crate::process::{self, ProcessManager};
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
            "open" => handle_open(app),
            "start_stop_server" => handle_start_stop(app, pm.clone()),
            "start_lm" => handle_lm_click(app, pm.clone()),
            "donate" => handle_donate(app, pm.clone()),
            "check_updates" => handle_check_updates(app),
            "change_server" => handle_change_server(app),
            "quit" => handle_quit(app, pm.clone()),
            _ => {}
        }
    });

    Ok(())
}

// ── Menu Event Handlers ──────────────────────────────────────────────

fn handle_open<R: Runtime>(app: &AppHandle<R>) {
    let cfg = crate::config::load_config();
    if cfg.mode == "client" {
        if cfg.server_url.is_empty() {
            show_dialog(
                app,
                "Connect to a Server",
                "This desktop app is in Client mode, but no server invite has been saved yet.\n\nChoose “Change Server...” and paste the rcl_ connection string from your admin.",
                DialogKind::Warning,
            );
        } else {
            let _ = open::that(&cfg.server_url);
        }
    } else if process::check_port(3000) || process::check_port(8000) {
        let _ = open::that(&cfg.server_url);
    } else {
        eprintln!("[tray] Server not running — cannot open browser");
        show_dialog(
            app,
            "Server Not Running",
            "Istara server is not running.\n\nStart it first using the tray menu.",
            DialogKind::Warning,
        );
    }
}

fn handle_start_stop<R: Runtime>(app: &AppHandle<R>, pm: Arc<Mutex<ProcessManager>>) {
    let cfg = crate::config::load_config();
    if cfg.install_dir.is_empty() {
        eprintln!("[tray] No install_dir configured");
        show_dialog(
            app,
            "Not Installed",
            "Istara is not installed yet.\n\nRun:\n  curl -fsSL https://raw.githubusercontent.com/henrique-simoes/Istara/main/scripts/install-istara.sh | bash",
            DialogKind::Warning,
        );
        return;
    }

    let running = process::is_server_running();
    let install_dir = cfg.install_dir.clone();
    let donate = cfg.donate_compute;
    let conn_str = cfg.connection_string.clone();
    let handle = app.clone();

    // Run start/stop in a background thread (istara.sh blocks for health checks)
    std::thread::spawn(move || {
        let result = if running {
            // Stop server + relay
            if let Ok(mut guard) = pm.lock() {
                guard.stop_server()
            } else {
                Err("Failed to acquire lock".to_string())
            }
        } else {
            // Start server
            let res = if let Ok(mut guard) = pm.lock() {
                guard.start_server(&install_dir)
            } else {
                Err("Failed to acquire lock".to_string())
            };
            // Start relay if donate_compute is enabled
            if res.is_ok() && donate {
                if let Ok(mut guard) = pm.lock() {
                    if let Err(e) = guard.start_relay(&install_dir, &conn_str) {
                        eprintln!("[tray] Relay start failed: {}", e);
                    }
                }
            }
            res
        };

        // Rebuild menu after operation completes
        rebuild_menu(&handle);

        // Show error dialog if operation failed
        if let Err(e) = result {
            let action = if running { "stop" } else { "start" };
            show_dialog(
                &handle,
                &format!("Failed to {} Server", action),
                &format!("Could not {} the server:\n\n{}", action, e),
                DialogKind::Error,
            );
        }
    });
}

fn handle_lm_click<R: Runtime>(app: &AppHandle<R>, pm: Arc<Mutex<ProcessManager>>) {
    let lm_running = process::is_lm_studio_running();
    let ollama_running = process::is_ollama_running();
    let cfg = crate::config::load_config();

    if lm_running || ollama_running {
        let provider = if lm_running { "LM Studio" } else { "Ollama" };
        let donate_status = if cfg.donate_compute { "ON" } else { "OFF" };

        let handle = app.clone();
        let pm_clone = pm.clone();
        tauri::async_runtime::spawn(async move {
            use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};
            let msg = format!(
                "{} is running and connected.\n\nCompute Donation is currently {}.\n\nWould you like to toggle compute donation?",
                provider, donate_status
            );
            let toggle = handle
                .dialog()
                .message(msg)
                .title(format!("{} Status", provider))
                .kind(MessageDialogKind::Info)
                .buttons(MessageDialogButtons::OkCancelCustom(
                    format!("Turn Donation {}", if cfg.donate_compute { "Off" } else { "On" }),
                    "Close".to_string(),
                ))
                .blocking_show();

            if toggle {
                // Toggle donation
                let mut new_cfg = crate::config::load_config();
                new_cfg.donate_compute = !new_cfg.donate_compute;
                let _ = crate::config::save_config(&new_cfg);

                if new_cfg.donate_compute {
                    if let Ok(mut guard) = pm_clone.lock() {
                        if let Err(e) = guard.start_relay(&new_cfg.install_dir, &new_cfg.connection_string) {
                            eprintln!("[tray] Relay start failed: {}", e);
                        }
                    }
                } else {
                    if let Ok(mut guard) = pm_clone.lock() {
                        guard.stop_relay();
                    }
                }
                rebuild_menu(&handle);
            }
        });
    } else {
        // LLM not running — offer to start it
        let handle = app.clone();
        tauri::async_runtime::spawn(async move {
            use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};
            let start = handle
                .dialog()
                .message(
                    "No LLM server detected.\n\nStart LM Studio to provide AI capabilities. \
                     If you use Ollama, start it from the terminal.\n\nOpen LM Studio?",
                )
                .title("LLM Not Running")
                .kind(MessageDialogKind::Info)
                .buttons(MessageDialogButtons::OkCancelCustom(
                    "Open LM Studio".to_string(),
                    "Cancel".to_string(),
                ))
                .blocking_show();

            if start {
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
        });
    }
}

fn handle_donate<R: Runtime>(app: &AppHandle<R>, pm: Arc<Mutex<ProcessManager>>) {
    let mut cfg = crate::config::load_config();
    let new_state = !cfg.donate_compute;

    if new_state && cfg.mode == "client" && cfg.connection_string.trim().is_empty() {
        show_dialog(
            app,
            "Connection Required",
            "Compute donation in Client mode needs a server invite first.\n\nChoose “Change Server...” and paste the rcl_ connection string from your admin.",
            DialogKind::Warning,
        );
        return;
    }

    cfg.donate_compute = new_state;

    // Always save the config toggle
    if let Err(e) = crate::config::save_config(&cfg) {
        eprintln!("[tray] Failed to save config: {}", e);
        show_dialog(
            app,
            "Config Error",
            &format!("Failed to save configuration: {}", e),
            DialogKind::Error,
        );
        return;
    }

    if new_state {
        // Try to start relay
        let relay_result = if let Ok(mut guard) = pm.lock() {
            guard.start_relay(&cfg.install_dir, &cfg.connection_string)
        } else {
            Err("Failed to acquire lock".to_string())
        };

        match relay_result {
            Ok(()) => {
                eprintln!("[tray] Compute donation enabled, relay started");
                show_dialog(
                    app,
                    "Compute Donation",
                    "Compute donation is now ON.\n\nYour idle compute will help other Istara users.",
                    DialogKind::Info,
                );
            }
            Err(e) => {
                eprintln!("[tray] Relay start failed: {}", e);
                show_dialog(
                    app,
                    "Compute Donation",
                    &format!(
                        "Compute donation enabled, but the relay could not start:\n\n{}\n\nDonation will activate once the relay component is installed.",
                        e
                    ),
                    DialogKind::Warning,
                );
            }
        }
    } else {
        if let Ok(mut guard) = pm.lock() {
            guard.stop_relay();
        }
        eprintln!("[tray] Compute donation disabled");
        show_dialog(
            app,
            "Compute Donation",
            "Compute donation is now OFF.",
            DialogKind::Info,
        );
    }

    // Rebuild menu to update label
    rebuild_menu(app);
}

fn handle_check_updates<R: Runtime>(app: &AppHandle<R>) {
    let handle = app.clone();
    tauri::async_runtime::spawn(async move {
        use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};
        use tauri_plugin_updater::UpdaterExt;

        // Try Tauri's built-in updater first (for .app/.dmg installs)
        if let Ok(updater) = handle.updater() {
            match updater.check().await {
                Ok(Some(update)) => {
                    let v = update.version.clone();
                    let body = update.body.clone().unwrap_or_default();
                    let preview = if body.len() > 200 { &body[..200] } else { &body };
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
                        if update.download_and_install(|_, _| {}, || {}).await.is_ok() {
                            handle.restart();
                        } else {
                            let _ = handle
                                .dialog()
                                .message("Update download failed. Try again later or run:\n  ./istara.sh update")
                                .title("Update Failed")
                                .kind(MessageDialogKind::Error)
                                .buttons(MessageDialogButtons::Ok)
                                .blocking_show();
                        }
                    }
                    return;
                }
                Ok(None) => {
                    let _ = handle
                        .dialog()
                        .message("You're running the latest version of Istara.")
                        .title("Up to Date")
                        .kind(MessageDialogKind::Info)
                        .buttons(MessageDialogButtons::Ok)
                        .blocking_show();
                    return;
                }
                Err(e) => {
                    eprintln!("[tray] Updater check error: {}", e);
                    // Fall through to git/manual check
                }
            }
        }

        // Fallback: for shell-installed Istara, offer git-based update
        let cfg = crate::config::load_config();
        let install_dir = cfg.install_dir.clone();

        // Try git-based version check
        let mut update_info = String::new();
        if !install_dir.is_empty() {
            let git_dir = std::path::PathBuf::from(&install_dir).join(".git");
            if git_dir.is_dir() {
                // Fetch latest tags
                if let Ok(output) = std::process::Command::new("git")
                    .args(["fetch", "--tags", "--quiet"])
                    .current_dir(&install_dir)
                    .output()
                {
                    if output.status.success() {
                        if let Ok(tag_output) = std::process::Command::new("git")
                            .args(["tag", "--sort=-v:refname"])
                            .current_dir(&install_dir)
                            .output()
                        {
                            if tag_output.status.success() {
                                let tags = String::from_utf8_lossy(&tag_output.stdout);
                                if let Some(latest) = tags.lines().next() {
                                    let latest_ver = latest.trim_start_matches('v');
                                    let current_ver_path =
                                        std::path::PathBuf::from(&install_dir).join("VERSION");
                                    let current = std::fs::read_to_string(&current_ver_path)
                                        .unwrap_or_else(|_| "unknown".to_string())
                                        .trim()
                                        .to_string();

                                    if current != "unknown" && crate::health::is_newer(latest_ver, &current) {
                                        update_info = format!(
                                            "Update available: {} \u{2192} {}\n\nRun in terminal:\n  cd {} && ./istara.sh update",
                                            current, latest_ver, install_dir
                                        );
                                    } else {
                                        update_info = format!(
                                            "You're running the latest version ({}).",
                                            current
                                        );
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }

        if !update_info.is_empty() {
            let open_releases = handle
                .dialog()
                .message(&update_info)
                .title(if update_info.contains("available") {
                    "Update Available"
                } else {
                    "Up to Date"
                })
                .kind(if update_info.contains("available") {
                    MessageDialogKind::Info
                } else {
                    MessageDialogKind::Info
                })
                .buttons(if update_info.contains("available") {
                    MessageDialogButtons::OkCancelCustom(
                        "Open Releases".to_string(),
                        "Close".to_string(),
                    )
                } else {
                    MessageDialogButtons::Ok
                })
                .blocking_show();
            // Note: for OkCancel, if the user clicks "Open Releases",
            // blocking_show returns true
            if update_info.contains("available") && open_releases {
                let _ = open::that("https://github.com/henrique-simoes/Istara/releases");
            }
        } else {
            // Last resort fallback
            let yes = handle
                .dialog()
                .message("Could not check for updates automatically.\n\nFor shell-installed Istara, run:\n  ./istara.sh update\n\nOr check GitHub releases?")
                .title("Check for Updates")
                .kind(MessageDialogKind::Info)
                .buttons(MessageDialogButtons::OkCancelCustom(
                    "Open GitHub".to_string(),
                    "Close".to_string(),
                ))
                .blocking_show();
            if yes {
                let _ = open::that("https://github.com/henrique-simoes/Istara/releases");
            }
        }
    });
}

fn handle_change_server<R: Runtime>(app: &AppHandle<R>) {
    if let Some(window) = app.get_webview_window("setup") {
        let _ = window.show();
        let _ = window.set_focus();
    } else {
        let _ = tauri::WebviewWindowBuilder::new(
            app,
            "setup",
            tauri::WebviewUrl::App("index.html".into()),
        )
        .title("Istara \u{2014} Change Server")
        .inner_size(640.0, 520.0)
        .center()
        .build();
    }
}

fn handle_quit<R: Runtime>(app: &AppHandle<R>, pm: Arc<Mutex<ProcessManager>>) {
    // Only stop relay (managed by us). Backend/frontend persist via PID files.
    if let Ok(mut guard) = pm.lock() {
        guard.stop_all();
    }
    app.exit(0);
}

// ── Menu Building ────────────────────────────────────────────────────

/// Rebuild the tray menu to reflect current state.
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
    let server_running = process::is_server_running();
    let lm_running = process::is_lm_studio_running();
    let ollama_running = process::is_ollama_running();
    let cfg = crate::config::load_config();

    // ── Start/Stop label reflects actual port state ──
    let server_label = if server_running {
        "\u{25CF} Stop Istara Server"
    } else {
        "\u{25CB} Start Istara Server"
    };

    // ── LLM status with green/yellow indicator ──
    let lm_label = if lm_running {
        "\u{2713} LM Studio: Running"
    } else if ollama_running {
        "\u{2713} Ollama: Running"
    } else {
        "\u{26A0} Start LM Studio"
    };

    // ── Donate with On/Off indicator ──
    let donate_label = if cfg.donate_compute {
        "\u{2713} Compute Donation: On"
    } else {
        "\u{25CB} Compute Donation: Off"
    };

    let menu = Menu::with_items(
        app,
        &[
            &MenuItem::with_id(app, "open", "Open Istara", true, None::<&str>)?,
            &MenuItem::with_id(app, "start_stop_server", server_label, true, None::<&str>)?,
            &MenuItem::with_id(app, "start_lm", lm_label, true, None::<&str>)?,
            &MenuItem::with_id(app, "donate", donate_label, true, None::<&str>)?,
            &MenuItem::with_id(
                app,
                "check_updates",
                "Check for Updates",
                true,
                None::<&str>,
            )?,
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
        "\u{26A0} Client Mode: Add Invite"
    } else {
        "\u{2713} Client Mode: Server Ready"
    };
    let donate_label = if cfg.donate_compute {
        "\u{2713} Compute Donation: On"
    } else {
        "\u{25CB} Compute Donation: Off"
    };

    let menu = Menu::with_items(
        app,
        &[
            &MenuItem::with_id(app, "status", status, false, None::<&str>)?,
            &MenuItem::with_id(app, "open", "Open Istara", true, None::<&str>)?,
            &MenuItem::with_id(app, "donate", donate_label, true, None::<&str>)?,
            &MenuItem::with_id(
                app,
                "change_server",
                "Change Server / Invite...",
                true,
                None::<&str>,
            )?,
            &MenuItem::with_id(
                app,
                "check_updates",
                "Check for Updates",
                true,
                None::<&str>,
            )?,
            &MenuItem::with_id(app, "quit", "Quit Istara", true, None::<&str>)?,
        ],
    )?;
    Ok(menu)
}

// ── Dialog Helpers ───────────────────────────────────────────────────

enum DialogKind {
    Info,
    Warning,
    Error,
}

fn show_dialog<R: Runtime>(app: &AppHandle<R>, title: &str, message: &str, kind: DialogKind) {
    let handle = app.clone();
    let title = title.to_string();
    let message = message.to_string();
    tauri::async_runtime::spawn(async move {
        use tauri_plugin_dialog::{DialogExt, MessageDialogButtons, MessageDialogKind};
        let dialog_kind = match kind {
            DialogKind::Info => MessageDialogKind::Info,
            DialogKind::Warning => MessageDialogKind::Warning,
            DialogKind::Error => MessageDialogKind::Error,
        };
        let _ = handle
            .dialog()
            .message(&message)
            .title(&title)
            .kind(dialog_kind)
            .buttons(MessageDialogButtons::Ok)
            .blocking_show();
    });
}
