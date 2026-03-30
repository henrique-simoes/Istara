/// System tray setup and menu construction.
/// Two modes: Server+Client (full menu) and Client-only (relay menu).
/// Menu events are wired to actual process management commands.
use crate::commands::AppState;
use crate::config::AppConfig;
use tauri::{
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
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

    TrayIconBuilder::new()
        .menu(&menu)
        .tooltip("ReClaw")
        .show_menu_on_left_click(true)
        .on_menu_event(move |app, event| {
            let id = event.id().as_ref();
            match id {
                "open" => {
                    let _ = open::that(
                        if crate::config::load_config().mode == "server" {
                            "http://localhost:3000"
                        } else {
                            &crate::config::load_config().server_url
                        }
                    );
                }
                "start" => {
                    let state: tauri::State<'_, AppState> = app.state();
                    if let Ok(mut pm) = state.process_manager.lock() {
                        let cfg = crate::config::load_config();
                        let dir = if cfg.install_dir.is_empty() {
                            crate::commands::find_install_dir_public()
                        } else {
                            cfg.install_dir.clone()
                        };
                        let _ = pm.start_backend(&dir);
                        let _ = pm.start_frontend(&dir);
                    }
                }
                "stop" => {
                    let state: tauri::State<'_, AppState> = app.state();
                    if let Ok(mut pm) = state.process_manager.lock() {
                        pm.stop_all();
                    }
                }
                "donate" => {
                    let mut cfg = crate::config::load_config();
                    cfg.donate_compute = !cfg.donate_compute;
                    let _ = crate::config::save_config(&cfg);

                    let state: tauri::State<'_, AppState> = app.state();
                    if let Ok(mut pm) = state.process_manager.lock() {
                        if cfg.donate_compute {
                            let dir = if cfg.install_dir.is_empty() {
                                crate::commands::find_install_dir_public()
                            } else {
                                cfg.install_dir.clone()
                            };
                            let _ = pm.start_relay(&dir, &cfg.connection_string);
                        } else {
                            pm.stop_relay();
                        }
                    }
                }
                "quit" => {
                    let state: tauri::State<'_, AppState> = app.state();
                    if let Ok(mut pm) = state.process_manager.lock() {
                        pm.stop_all();
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
            &MenuItem::with_id(app, "open", "Open ReClaw in Browser", true, None::<&str>)?,
            &MenuItem::with_id(app, "start", "Start Server", true, None::<&str>)?,
            &MenuItem::with_id(app, "stop", "Stop Server", true, None::<&str>)?,
            &MenuItem::with_id(app, "donate", "Toggle Compute Donation", true, None::<&str>)?,
            &MenuItem::with_id(app, "quit", "Quit ReClaw", true, None::<&str>)?,
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
            &MenuItem::with_id(app, "open", "Open ReClaw in Browser", true, None::<&str>)?,
            &MenuItem::with_id(app, "donate", "Toggle Compute Donation", true, None::<&str>)?,
            &MenuItem::with_id(app, "quit", "Quit ReClaw", true, None::<&str>)?,
        ],
    )?;
    Ok(menu)
}
