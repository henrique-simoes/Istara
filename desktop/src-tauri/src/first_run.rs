/// First-run setup: copies bundled source from the read-only .app bundle
/// to a writable data directory where venv/node_modules/data can be created.
///
/// macOS: ~/Library/Application Support/com.istara.desktop/
/// Windows: %APPDATA%/com.istara.desktop/
/// Linux: ~/.local/share/com.istara.desktop/

use std::path::{Path, PathBuf};
use tauri::{AppHandle, Manager, Runtime};

/// Get the writable data directory for Istara.
pub fn get_data_dir<R: Runtime>(app: &AppHandle<R>) -> Result<PathBuf, String> {
    app.path().app_data_dir().map_err(|e| format!("Cannot determine data directory: {}", e))
}

/// Copy bundled source from app Resources to writable data dir.
/// Only runs if the data dir doesn't already have `backend/` (first run).
/// Returns the path to the writable data directory.
pub fn ensure_source_copied<R: Runtime>(app: &AppHandle<R>) -> Result<PathBuf, String> {
    let data_dir = get_data_dir(app)?;

    // Already set up? Return early.
    if data_dir.join("backend").join("app").exists() {
        return Ok(data_dir);
    }

    // Find the bundled source in the app's Resources
    let resource_dir = app
        .path()
        .resolve("istara", tauri::path::BaseDirectory::Resource)
        .map_err(|e| format!("Cannot find bundled source: {}", e))?;

    if !resource_dir.exists() {
        return Err(format!(
            "Bundled source not found at: {}. The app may not have been built with resources.",
            resource_dir.display()
        ));
    }

    println!("First run: copying source from {} to {}", resource_dir.display(), data_dir.display());

    // Copy everything from the bundle to the writable location
    copy_dir_recursive(&resource_dir, &data_dir)?;

    println!("Source copied to {}", data_dir.display());
    Ok(data_dir)
}

/// Recursively copy a directory.
fn copy_dir_recursive(src: &Path, dst: &Path) -> Result<(), String> {
    std::fs::create_dir_all(dst)
        .map_err(|e| format!("Failed to create dir {}: {}", dst.display(), e))?;

    let entries = std::fs::read_dir(src)
        .map_err(|e| format!("Failed to read dir {}: {}", src.display(), e))?;

    for entry in entries {
        let entry = entry.map_err(|e| format!("Failed to read entry: {}", e))?;
        let src_path = entry.path();
        let dst_path = dst.join(entry.file_name());

        if src_path.is_dir() {
            copy_dir_recursive(&src_path, &dst_path)?;
        } else {
            std::fs::copy(&src_path, &dst_path)
                .map_err(|e| format!("Failed to copy {} -> {}: {}", src_path.display(), dst_path.display(), e))?;
        }
    }

    Ok(())
}
