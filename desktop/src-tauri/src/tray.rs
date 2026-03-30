/// System tray — real process management with dynamic menu labels.
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

    let pm: Arc<Mutex<ProcessManager>> = {
        let state = app.state::<AppState>();
        state.process_manager.clone()
    };

    TrayIconBuilder::new()
        .menu(&menu)
        .tooltip("Istara — Local-first AI for UX Research")
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
                "start_server" | "stop_server" => {
                    let cfg = crate::config::load_config();
                    let dir = if cfg.install_dir.is_empty() {
                        crate::commands::find_install_dir_public()
                    } else {
                        cfg.install_dir.clone()
                    };
                    if let Ok(mut guard) = pm.lock() {
                        if guard.is_running() {
                            guard.stop_all();
                            println!("Server stopped");
                        } else {
                            let _ = guard.start_backend(&dir);
                            let _ = guard.start_frontend(&dir);
                            println!("Server started");
                        }
                    }
                }
                "start_lm" | "stop_lm" => {
                    // Check if LM Studio is running
                    let lm_running = std::net::TcpStream::connect_timeout(
                        &"127.0.0.1:1234".parse().unwrap(),
                        std::time::Duration::from_secs(1),
                    ).is_ok();

                    if lm_running {
                        // Can't really stop LM Studio from here — it's a separate app
                        // Show a notification or open LM Studio
                        println!("LM Studio is running on port 1234");
                    } else {
                        // Try to launch LM Studio
                        #[cfg(target_os = "macos")]
                        {
                            let _ = std::process::Command::new("open")
                                .arg("-a").arg("LM Studio")
                                .spawn();
                        }
                        #[cfg(target_os = "windows")]
                        {
                            let _ = std::process::Command::new("cmd")
                                .args(["/c", "start", "", "lms"])
                                .spawn();
                        }
                        println!("Launching LM Studio...");
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
                    // Show stats in a window
                    if let Some(window) = app.get_webview_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    } else {
                        let _ = tauri::WebviewWindowBuilder::new(
                            app,
                            "main",
                            tauri::WebviewUrl::App("index.html".into()),
                        )
                        .title("Istara Stats")
                        .inner_size(400.0, 300.0)
                        .build();
                    }
                }
                "change_server" => {
                    // Open a window for connection string input
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
        })
        .build(app)?;

    Ok(())
}

fn build_server_menu<R: Runtime>(
    app: &AppHandle<R>,
) -> Result<Menu<R>, Box<dyn std::error::Error>> {
    // Check current states for dynamic labels
    let server_running = std::net::TcpStream::connect_timeout(
        &"127.0.0.1:8000".parse().unwrap(),
        std::time::Duration::from_secs(1),
    ).is_ok();

    let lm_running = std::net::TcpStream::connect_timeout(
        &"127.0.0.1:1234".parse().unwrap(),
        std::time::Duration::from_secs(1),
    ).is_ok();

    let ollama_running = std::net::TcpStream::connect_timeout(
        &"127.0.0.1:11434".parse().unwrap(),
        std::time::Duration::from_secs(1),
    ).is_ok();

    let cfg = crate::config::load_config();
    let donate_label = if cfg.donate_compute {
        "Compute Donation: On"
    } else {
        "Compute Donation: Off"
    };

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

    let menu = Menu::with_items(
        app,
        &[
            &MenuItem::with_id(app, "open", "Open Istara", true, None::<&str>)?,
            &MenuItem::with_id(app, "start_server", server_label, true, None::<&str>)?,
            &MenuItem::with_id(app, "start_lm", lm_label, true, None::<&str>)?,
            &MenuItem::with_id(app, "stats", "System Stats...", true, None::<&str>)?,
            &MenuItem::with_id(app, "donate", donate_label, true, None::<&str>)?,
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
            &MenuItem::with_id(app, "quit", "Quit Istara", true, None::<&str>)?,
        ],
    )?;
    Ok(menu)
}
