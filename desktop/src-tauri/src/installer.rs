/// Dependency detection and installation for Istara setup wizard.
/// Checks common installation paths on macOS and Windows since GUI apps
/// don't inherit the user's shell PATH.

use std::path::Path;
use std::process::Command;

#[derive(serde::Serialize, serde::Deserialize, Clone)]
pub struct DepStatus {
    pub id: String,
    pub name: String,
    pub detected: bool,
    pub version: String,
    pub required: bool,
}

/// Detect all dependencies and return their status.
#[tauri::command]
pub fn detect_dependencies() -> Vec<DepStatus> {
    vec![
        detect_python(),
        detect_node(),
        detect_lmstudio(),
        detect_ollama(),
        detect_docker(),
    ]
}

// ─── macOS common paths ──────────────────────────────────────────────
// GUI apps don't inherit shell PATH. We must check common locations.

#[cfg(target_os = "macos")]
const PYTHON_PATHS: &[&str] = &[
    "python3",                                    // system PATH (unlikely in GUI)
    "/opt/homebrew/bin/python3",                  // Homebrew Apple Silicon
    "/usr/local/bin/python3",                     // Homebrew Intel
    "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3",  // python.org installer
    "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3",
    "/Library/Frameworks/Python.framework/Versions/Current/bin/python3",
    "/usr/bin/python3",                           // macOS built-in (may be stub)
];

#[cfg(target_os = "macos")]
const NODE_PATHS: &[&str] = &[
    "node",
    "/opt/homebrew/bin/node",                     // Homebrew Apple Silicon
    "/usr/local/bin/node",                        // Homebrew Intel / nvm symlink
    "/usr/local/opt/node/bin/node",
    // nvm: check common nvm locations
    // fnm: check common fnm locations
];

#[cfg(target_os = "macos")]
const OLLAMA_PATHS: &[&str] = &[
    "ollama",
    "/opt/homebrew/bin/ollama",
    "/usr/local/bin/ollama",
];

#[cfg(target_os = "macos")]
const DOCKER_PATHS: &[&str] = &[
    "docker",
    "/usr/local/bin/docker",
    "/opt/homebrew/bin/docker",
    "/Applications/Docker.app/Contents/Resources/bin/docker",
];

// ─── Windows common paths ────────────────────────────────────────────

#[cfg(target_os = "windows")]
const PYTHON_PATHS: &[&str] = &[
    "python",
    "python3",
    r"C:\Python312\python.exe",
    r"C:\Python311\python.exe",
    r"C:\Users\Default\AppData\Local\Programs\Python\Python312\python.exe",
    r"C:\Users\Default\AppData\Local\Programs\Python\Python311\python.exe",
];

#[cfg(target_os = "windows")]
const NODE_PATHS: &[&str] = &[
    "node",
    r"C:\Program Files\nodejs\node.exe",
    r"C:\Program Files (x86)\nodejs\node.exe",
];

#[cfg(target_os = "windows")]
const OLLAMA_PATHS: &[&str] = &[
    "ollama",
    r"C:\Users\Default\AppData\Local\Programs\Ollama\ollama.exe",
];

#[cfg(target_os = "windows")]
const DOCKER_PATHS: &[&str] = &[
    "docker",
    r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
];

// ─── Linux fallback ──────────────────────────────────────────────────

#[cfg(not(any(target_os = "macos", target_os = "windows")))]
const PYTHON_PATHS: &[&str] = &["python3", "/usr/bin/python3"];
#[cfg(not(any(target_os = "macos", target_os = "windows")))]
const NODE_PATHS: &[&str] = &["node", "/usr/bin/node"];
#[cfg(not(any(target_os = "macos", target_os = "windows")))]
const OLLAMA_PATHS: &[&str] = &["ollama", "/usr/local/bin/ollama"];
#[cfg(not(any(target_os = "macos", target_os = "windows")))]
const DOCKER_PATHS: &[&str] = &["docker", "/usr/bin/docker"];

// ─── Detectors ───────────────────────────────────────────────────────

fn detect_python() -> DepStatus {
    let (detected, version) = try_paths(PYTHON_PATHS, &["--version"]);

    // Also check nvm/fnm managed versions on macOS
    #[cfg(target_os = "macos")]
    let (detected, version) = if detected {
        (detected, version)
    } else {
        // Check nvm
        let home = std::env::var("HOME").unwrap_or_default();
        let nvm_node = format!("{}/.nvm/versions/node", home);
        if Path::new(&nvm_node).exists() {
            // nvm exists but doesn't help with Python — skip
        }
        // Check pyenv
        let pyenv_root = format!("{}/.pyenv/shims/python3", home);
        if Path::new(&pyenv_root).exists() {
            run_version_check(&pyenv_root, &["--version"])
                .unwrap_or((false, String::new()))
        } else {
            (false, String::new())
        }
    };

    DepStatus {
        id: "python".to_string(),
        name: "Python 3.11+".to_string(),
        detected,
        version,
        required: true,
    }
}

fn detect_node() -> DepStatus {
    let (mut detected, mut version) = try_paths(NODE_PATHS, &["--version"]);

    // Check nvm-managed Node on macOS/Linux
    if !detected {
        let home = std::env::var("HOME").unwrap_or_default();

        // nvm: find the default version
        let nvm_default = format!("{}/.nvm/alias/default", home);
        if Path::new(&nvm_default).exists() {
            if let Ok(alias) = std::fs::read_to_string(&nvm_default) {
                let ver = alias.trim();
                let nvm_node = format!("{}/.nvm/versions/node/{}/bin/node", home, ver);
                if let Some((d, v)) = run_version_check(&nvm_node, &["--version"]) {
                    detected = d;
                    version = v;
                }
            }
        }

        // fnm
        let fnm_dir = format!("{}/.local/share/fnm/node-versions", home);
        if !detected && Path::new(&fnm_dir).exists() {
            if let Ok(entries) = std::fs::read_dir(&fnm_dir) {
                for entry in entries.flatten() {
                    let node = entry.path().join("installation/bin/node");
                    if node.exists() {
                        if let Some((d, v)) = run_version_check(
                            node.to_str().unwrap_or(""),
                            &["--version"],
                        ) {
                            detected = d;
                            version = v;
                            break;
                        }
                    }
                }
            }
        }
    }

    DepStatus {
        id: "node".to_string(),
        name: "Node.js 18+".to_string(),
        detected,
        version,
        required: true,
    }
}

fn detect_lmstudio() -> DepStatus {
    // Check if port 1234 is open (LM Studio server running)
    let port_open = std::net::TcpStream::connect_timeout(
        &"127.0.0.1:1234".parse().unwrap(),
        std::time::Duration::from_secs(2),
    )
    .is_ok();

    // Also check if the app is installed
    #[cfg(target_os = "macos")]
    let app_installed = Path::new("/Applications/LM Studio.app").exists()
        || Path::new(&format!(
            "{}/Applications/LM Studio.app",
            std::env::var("HOME").unwrap_or_default()
        ))
        .exists();

    #[cfg(target_os = "windows")]
    let app_installed = Path::new(r"C:\Users\Default\AppData\Local\Programs\LM Studio\LM Studio.exe").exists()
        || which_exists("lms");

    #[cfg(not(any(target_os = "macos", target_os = "windows")))]
    let app_installed = false;

    let detected = port_open || app_installed;

    DepStatus {
        id: "lmstudio".to_string(),
        name: "LM Studio".to_string(),
        detected,
        version: if port_open {
            "Running".to_string()
        } else if app_installed {
            "Installed (not running)".to_string()
        } else {
            String::new()
        },
        required: false,
    }
}

fn detect_ollama() -> DepStatus {
    let (cmd_found, version) = try_paths(OLLAMA_PATHS, &["--version"]);

    // Check if service is running
    let running = std::net::TcpStream::connect_timeout(
        &"127.0.0.1:11434".parse().unwrap(),
        std::time::Duration::from_secs(2),
    )
    .is_ok();

    // On macOS, also check if Ollama.app is installed
    #[cfg(target_os = "macos")]
    let app_installed = Path::new("/Applications/Ollama.app").exists();
    #[cfg(not(target_os = "macos"))]
    let app_installed = false;

    let detected = cmd_found || running || app_installed;

    DepStatus {
        id: "ollama".to_string(),
        name: "Ollama".to_string(),
        detected,
        version: if running {
            format!("{} (running)", version)
        } else if cmd_found || app_installed {
            if version.is_empty() {
                "Installed".to_string()
            } else {
                version
            }
        } else {
            String::new()
        },
        required: false,
    }
}

fn detect_docker() -> DepStatus {
    let (cmd_found, version) = try_paths(DOCKER_PATHS, &["--version"]);

    // On macOS, also check if Docker Desktop is installed
    #[cfg(target_os = "macos")]
    let app_installed = Path::new("/Applications/Docker.app").exists();
    #[cfg(not(target_os = "macos"))]
    let app_installed = false;

    DepStatus {
        id: "docker".to_string(),
        name: "Docker".to_string(),
        detected: cmd_found || app_installed,
        version: if cmd_found {
            version
        } else if app_installed {
            "Installed (not running)".to_string()
        } else {
            String::new()
        },
        required: false,
    }
}

// ─── Helpers ─────────────────────────────────────────────────────────

/// Try multiple paths for a command, return the first that succeeds.
fn try_paths(paths: &[&str], args: &[&str]) -> (bool, String) {
    for path in paths {
        if let Some((true, version)) = run_version_check(path, args) {
            return (true, version);
        }
    }
    (false, String::new())
}

fn run_version_check(cmd: &str, args: &[&str]) -> Option<(bool, String)> {
    if cmd.is_empty() {
        return None;
    }
    match Command::new(cmd).args(args).output() {
        Ok(output) if output.status.success() => {
            let stdout = String::from_utf8_lossy(&output.stdout).trim().to_string();
            let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
            // Some tools (like Python) output version to stderr
            let version = if stdout.is_empty() { stderr } else { stdout };
            Some((true, version))
        }
        _ => None,
    }
}

#[cfg(target_os = "windows")]
fn which_exists(cmd: &str) -> bool {
    Command::new("where").arg(cmd).output().map(|o| o.status.success()).unwrap_or(false)
}

// ─── Install functions ───────────────────────────────────────────────

/// Install a dependency. Returns Ok(message) on success.
#[tauri::command]
pub fn install_dependency(dep_id: String) -> Result<String, String> {
    match dep_id.as_str() {
        "python" => install_python(),
        "node" => install_node(),
        "ollama" => install_ollama(),
        "lmstudio" => {
            open::that("https://lmstudio.ai").map_err(|e| e.to_string())?;
            Ok("Opened LM Studio download page".to_string())
        }
        "docker" => {
            open::that("https://www.docker.com/products/docker-desktop/")
                .map_err(|e| e.to_string())?;
            Ok("Opened Docker download page".to_string())
        }
        _ => Err(format!("Unknown dependency: {}", dep_id)),
    }
}

#[cfg(target_os = "macos")]
fn install_python() -> Result<String, String> {
    let url = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-macos11.pkg";
    let dest = "/tmp/python-3.12.8-macos11.pkg";
    download_file(url, dest)?;
    Command::new("open").arg(dest).status().map_err(|e| e.to_string())?;
    Ok("Python installer opened — follow the prompts".to_string())
}

#[cfg(target_os = "windows")]
fn install_python() -> Result<String, String> {
    let url = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe";
    let dest = std::env::temp_dir().join("python-3.12.8-amd64.exe");
    download_file(url, dest.to_str().unwrap())?;
    Command::new(dest).args(["/quiet", "PrependPath=1", "Include_pip=1"])
        .status().map_err(|e| format!("Python install failed: {}", e))?;
    Ok("Python 3.12 installed".to_string())
}

#[cfg(target_os = "macos")]
fn install_node() -> Result<String, String> {
    let url = "https://nodejs.org/dist/v20.18.0/node-v20.18.0.pkg";
    let dest = "/tmp/node-v20.18.0.pkg";
    download_file(url, dest)?;
    Command::new("open").arg(dest).status().map_err(|e| e.to_string())?;
    Ok("Node.js installer opened — follow the prompts".to_string())
}

#[cfg(target_os = "windows")]
fn install_node() -> Result<String, String> {
    let url = "https://nodejs.org/dist/v20.18.0/node-v20.18.0-x64.msi";
    let dest = std::env::temp_dir().join("node-v20.18.0-x64.msi");
    download_file(url, dest.to_str().unwrap())?;
    Command::new("msiexec").args(["/i", dest.to_str().unwrap(), "/quiet", "/norestart"])
        .status().map_err(|e| format!("Node.js install failed: {}", e))?;
    Ok("Node.js 20 installed".to_string())
}

#[cfg(target_os = "macos")]
fn install_ollama() -> Result<String, String> {
    let status = Command::new("sh")
        .args(["-c", "curl -fsSL https://ollama.com/install.sh | sh"])
        .status()
        .map_err(|e| format!("Ollama install failed: {}", e))?;
    if status.success() {
        Ok("Ollama installed".to_string())
    } else {
        Err("Ollama install script failed".to_string())
    }
}

#[cfg(target_os = "windows")]
fn install_ollama() -> Result<String, String> {
    let url = "https://ollama.com/download/OllamaSetup.exe";
    let dest = std::env::temp_dir().join("OllamaSetup.exe");
    download_file(url, dest.to_str().unwrap())?;
    Command::new(dest).arg("/S").status()
        .map_err(|e| format!("Ollama install failed: {}", e))?;
    Ok("Ollama installed".to_string())
}

#[cfg(not(any(target_os = "macos", target_os = "windows")))]
fn install_python() -> Result<String, String> { Err("Use your package manager: apt install python3".to_string()) }
#[cfg(not(any(target_os = "macos", target_os = "windows")))]
fn install_node() -> Result<String, String> { Err("Use your package manager: apt install nodejs".to_string()) }
#[cfg(not(any(target_os = "macos", target_os = "windows")))]
fn install_ollama() -> Result<String, String> {
    Command::new("sh").args(["-c", "curl -fsSL https://ollama.com/install.sh | sh"])
        .status().map_err(|e| e.to_string())?;
    Ok("Ollama installed".to_string())
}

fn download_file(url: &str, dest: &str) -> Result<(), String> {
    Command::new("curl")
        .args(["-fsSL", "-o", dest, url])
        .status()
        .map_err(|e| format!("Download failed: {}", e))?;
    Ok(())
}
