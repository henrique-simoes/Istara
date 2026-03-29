/// System tray setup and menu construction.
/// Two modes: Server+Client (full menu) and Client-only (relay menu).
use crate::config::AppConfig;
use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    AppHandle, Runtime,
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
        .on_menu_event(move |_app, event| {
            println!("Tray menu event: {:?}", event.id());
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
            &MenuItem::with_id(app, "open", "Open ReClaw", true, None::<&str>)?,
            &MenuItem::with_id(app, "separator1", "---", false, None::<&str>)?,
            &MenuItem::with_id(app, "start", "Start Server", true, None::<&str>)?,
            &MenuItem::with_id(app, "stop", "Stop Server", true, None::<&str>)?,
            &MenuItem::with_id(app, "separator2", "---", false, None::<&str>)?,
            &MenuItem::with_id(app, "stats", "System Stats...", true, None::<&str>)?,
            &MenuItem::with_id(app, "donate", "Compute Donation: Off", true, None::<&str>)?,
            &MenuItem::with_id(app, "separator3", "---", false, None::<&str>)?,
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
            &MenuItem::with_id(app, "open", "Open ReClaw", true, None::<&str>)?,
            &MenuItem::with_id(app, "separator1", "---", false, None::<&str>)?,
            &MenuItem::with_id(app, "stats", "System Stats...", true, None::<&str>)?,
            &MenuItem::with_id(
                app,
                "donate",
                if cfg.donate_compute { "Donating Compute" } else { "Compute Donation: Off" },
                true,
                None::<&str>,
            )?,
            &MenuItem::with_id(app, "change_server", "Change Server...", true, None::<&str>)?,
            &MenuItem::with_id(app, "separator2", "---", false, None::<&str>)?,
            &MenuItem::with_id(app, "quit", "Quit ReClaw", true, None::<&str>)?,
        ],
    )?;
    Ok(menu)
}
