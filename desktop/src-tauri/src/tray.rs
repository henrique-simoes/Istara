/// System tray setup and menu construction.
/// Menu events drive real process management.
use crate::commands::AppState;
use crate::config::AppConfig;
use crate::process::ProcessManager;
use std::sync::{Arc, Mutex};
use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
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

    // Clone the Arc<Mutex<ProcessManager>> so the closure owns it
    // (avoids all borrow-lifetime issues with tauri::State in closures)
    let pm: Arc<Mutex<ProcessManager>> = {
        let state = app.state::<AppState>();
        state.process_manager.clone()
    };

    TrayIconBuilder::new()
        .menu(&menu)
        .tooltip("Istara")
        .show_menu_on_left_click(true)
        .on_menu_event(move |app, event| {
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
                "start" => {
                    let cfg = crate::config::load_config();
                    let dir = if cfg.install_dir.is_empty() {
                        crate::commands::find_install_dir_public()
                    } else {
                        cfg.install_dir.clone()
                    };
                    if let Ok(mut guard) = pm.lock() {
                        let _ = guard.start_backend(&dir);
                        let _ = guard.start_frontend(&dir);
                    }
                }
                "stop" => {
                    if let Ok(mut guard) = pm.lock() {
                        guard.stop_all();
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
                "quit" => {
                    if let Ok(mut guard) = pm.lock() {
                        guard.stop_all();
                    }
                    app.exit(0);
                }
                _ => {}
            }
        })
        .build(app)?;

    Ok(())
}

fn build_server_menu<R: Runtime>(
    app: &AppHandle<R>,
) -> Result<Menu<R>, Box<dyn std::error::Error>> {
    let menu = Menu::with_items(
        app,
        &[
            &MenuItem::with_id(app, "open", "Open Istara in Browser", true, None::<&str>)?,
            &MenuItem::with_id(app, "start", "Start Server", true, None::<&str>)?,
            &MenuItem::with_id(app, "stop", "Stop Server", true, None::<&str>)?,
            &MenuItem::with_id(app, "donate", "Toggle Compute Donation", true, None::<&str>)?,
            &MenuItem::with_id(app, "quit", "Quit Istara", true, None::<&str>)?,
        ],
    )?;
    Ok(menu)
}

fn build_client_menu<R: Runtime>(
    app: &AppHandle<R>,
    cfg: &AppConfig,
) -> Result<Menu<R>, Box<dyn std::error::Error>> {
    let status_label = if cfg.connection_string.is_empty() {
        "Not Connected".to_string()
    } else {
        format!("Connected to {}", cfg.server_url)
    };

    let menu = Menu::with_items(
        app,
        &[
            &MenuItem::with_id(app, "status", &status_label, false, None::<&str>)?,
            &MenuItem::with_id(app, "open", "Open Istara in Browser", true, None::<&str>)?,
            &MenuItem::with_id(app, "donate", "Toggle Compute Donation", true, None::<&str>)?,
            &MenuItem::with_id(app, "quit", "Quit Istara", true, None::<&str>)?,
        ],
    )?;
    Ok(menu)
}
