/// Path resolver: finds Python, Node, npm by checking common install locations.
/// GUI apps don't inherit shell PATH, so we check explicit paths.

use std::path::Path;
use std::process::Command;

/// Find Python 3 — checks venv first, then system locations.
pub fn find_python(install_dir: &str) -> String {
    // 1. Venv in install dir
    for venv_path in &[
        format!("{}/venv/bin/python", install_dir),
        format!("{}/venv/Scripts/python.exe", install_dir),
        format!("{}/backend/venv/bin/python", install_dir),
        format!("{}/backend/venv/Scripts/python.exe", install_dir),
    ] {
        if Path::new(venv_path).exists() {
            return venv_path.clone();
        }
    }

    // 2. System locations
    #[cfg(target_os = "macos")]
    let paths = &[
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
        "/Library/Frameworks/Python.framework/Versions/Current/bin/python3",
        "/usr/bin/python3",
    ];

    #[cfg(target_os = "windows")]
    let paths = &[
        r"C:\Python312\python.exe",
        r"C:\Python311\python.exe",
        r"C:\Program Files\Python312\python.exe",
        r"C:\Program Files\Python311\python.exe",
    ];

    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    let paths: &[&str] = &["/usr/bin/python3", "/usr/local/bin/python3"];

    for p in paths {
        if Path::new(p).exists() {
            return p.to_string();
        }
    }

    // 3. Pyenv
    if let Ok(home) = std::env::var("HOME") {
        let pyenv = format!("{}/.pyenv/shims/python3", home);
        if Path::new(&pyenv).exists() {
            return pyenv;
        }
    }

    // 4. Try bare command as last resort
    if command_exists("python3") { return "python3".to_string(); }
    if command_exists("python") { return "python".to_string(); }

    "python3".to_string()
}

/// Find Node.js binary.
pub fn find_node() -> String {
    #[cfg(target_os = "macos")]
    let paths = &[
        "/opt/homebrew/bin/node",
        "/usr/local/bin/node",
    ];

    #[cfg(target_os = "windows")]
    let paths = &[
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
    ];

    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    let paths: &[&str] = &["/usr/bin/node", "/usr/local/bin/node"];

    for p in paths {
        if Path::new(p).exists() {
            return p.to_string();
        }
    }

    // Check nvm
    if let Ok(home) = std::env::var("HOME") {
        let nvm_dir = format!("{}/.nvm/versions/node", home);
        if let Ok(entries) = std::fs::read_dir(&nvm_dir) {
            // Get the latest version
            let mut versions: Vec<_> = entries.flatten().collect();
            versions.sort_by(|a, b| b.file_name().cmp(&a.file_name()));
            if let Some(entry) = versions.first() {
                let node = entry.path().join("bin/node");
                if node.exists() {
                    return node.to_string_lossy().to_string();
                }
            }
        }

        // Check fnm
        let fnm_dir = format!("{}/.local/share/fnm/node-versions", home);
        if let Ok(entries) = std::fs::read_dir(&fnm_dir) {
            for entry in entries.flatten() {
                let node = entry.path().join("installation/bin/node");
                if node.exists() {
                    return node.to_string_lossy().to_string();
                }
            }
        }
    }

    if command_exists("node") { return "node".to_string(); }

    "node".to_string()
}

/// Find npm — derives from Node.js location.
pub fn find_npm() -> String {
    let node = find_node();
    if let Some(parent) = Path::new(&node).parent() {
        #[cfg(target_os = "windows")]
        {
            let npm = parent.join("npm.cmd");
            if npm.exists() { return npm.to_string_lossy().to_string(); }
        }
        #[cfg(not(target_os = "windows"))]
        {
            let npm = parent.join("npm");
            if npm.exists() { return npm.to_string_lossy().to_string(); }
        }
    }

    #[cfg(target_os = "windows")]
    { "npm.cmd".to_string() }
    #[cfg(not(target_os = "windows"))]
    { "npm".to_string() }
}

/// Find npx — derives from Node.js location.
pub fn find_npx() -> String {
    let node = find_node();
    if let Some(parent) = Path::new(&node).parent() {
        let npx = parent.join(if cfg!(target_os = "windows") { "npx.cmd" } else { "npx" });
        if npx.exists() { return npx.to_string_lossy().to_string(); }
    }

    if cfg!(target_os = "windows") { "npx.cmd".to_string() } else { "npx".to_string() }
}

/// Get the pip path for a venv.
pub fn find_pip(install_dir: &str) -> String {
    #[cfg(target_os = "windows")]
    let pip = format!(r"{}\venv\Scripts\pip.exe", install_dir);
    #[cfg(not(target_os = "windows"))]
    let pip = format!("{}/venv/bin/pip", install_dir);

    if Path::new(&pip).exists() { return pip; }

    // Fallback
    #[cfg(target_os = "windows")]
    { "pip".to_string() }
    #[cfg(not(target_os = "windows"))]
    { "pip3".to_string() }
}

fn command_exists(cmd: &str) -> bool {
    Command::new(cmd)
        .arg("--version")
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}
