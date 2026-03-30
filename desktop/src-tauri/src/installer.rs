/// Dependency detection and installation for ReClaw setup wizard.
/// Downloads and installs Python, Node.js, Ollama, LM Studio as needed.

use std::path::Path;
use std::process::Command;

#[derive(serde::Serialize, Clone)]
pub struct DepStatus {
    pub id: String,
    pub name: String,
    pub detected: bool,
    pub version: String,
    pub required: bool,
}

/// Detect all dependencies and return their status.
pub fn detect_dependencies() -> Vec<DepStatus> {
    vec![
        detect_python(),
        detect_node(),
        detect_lmstudio(),
        detect_ollama(),
        detect_docker(),
    ]
}

fn detect_python() -> DepStatus {
    let (detected, version) = run_version_check("python3", &["--version"])
        .or_else(|| run_version_check("python", &["--version"]))
        .unwrap_or((false, String::new()));

    DepStatus {
        id: "python".to_string(),
        name: "Python 3.12".to_string(),
        detected,
        version,
        required: true,
    }
}

fn detect_node() -> DepStatus {
    let (detected, version) = run_version_check("node", &["--version"])
        .unwrap_or((false, String::new()));

    DepStatus {
        id: "node".to_string(),
        name: "Node.js 20".to_string(),
        detected,
        version,
        required: true,
    }
}

fn detect_lmstudio() -> DepStatus {
    // LM Studio detection: check if port 1234 is open
    let detected = std::net::TcpStream::connect_timeout(
        &"127.0.0.1:1234".parse().unwrap(),
        std::time::Duration::from_secs(1),
    ).is_ok();

    DepStatus {
        id: "lmstudio".to_string(),
        name: "LM Studio".to_string(),
        detected,
        version: if detected { "Running".to_string() } else { String::new() },
        required: false,
    }
}

fn detect_ollama() -> DepStatus {
    let (detected, version) = run_version_check("ollama", &["--version"])
        .unwrap_or((false, String::new()));

    // Also check if service is running
    let running = std::net::TcpStream::connect_timeout(
        &"127.0.0.1:11434".parse().unwrap(),
        std::time::Duration::from_secs(1),
    ).is_ok();

    DepStatus {
        id: "ollama".to_string(),
        name: "Ollama".to_string(),
        detected: detected || running,
        version: if running { format!("{} (running)", version) } else { version },
        required: false,
    }
}

fn detect_docker() -> DepStatus {
    let (detected, version) = run_version_check("docker", &["--version"])
        .unwrap_or((false, String::new()));

    DepStatus {
        id: "docker".to_string(),
        name: "Docker".to_string(),
        detected,
        version,
        required: false,
    }
}

fn run_version_check(cmd: &str, args: &[&str]) -> Option<(bool, String)> {
    match Command::new(cmd).args(args).output() {
        Ok(output) if output.status.success() => {
            let version = String::from_utf8_lossy(&output.stdout).trim().to_string();
            Some((true, version))
        }
        _ => None,
    }
}

/// Install a dependency. Returns Ok(()) on success.
pub fn install_dependency(dep_id: &str) -> Result<String, String> {
    match dep_id {
        "python" => install_python(),
        "node" => install_node(),
        "ollama" => install_ollama(),
        "lmstudio" => install_lmstudio(),
        "docker" => install_docker(),
        _ => Err(format!("Unknown dependency: {}", dep_id)),
    }
}

#[cfg(target_os = "macos")]
fn install_python() -> Result<String, String> {
    // Download and run the official Python installer
    let url = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-macos11.pkg";
    download_and_run_pkg(url, "python-3.12.8-macos11.pkg")
}

#[cfg(target_os = "windows")]
fn install_python() -> Result<String, String> {
    let url = "https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe";
    let path = download_file(url, "python-3.12.8-amd64.exe")?;
    Command::new(&path)
        .args(["/quiet", "PrependPath=1", "Include_pip=1"])
        .status()
        .map_err(|e| format!("Python install failed: {}", e))?;
    Ok("Python 3.12 installed".to_string())
}

#[cfg(target_os = "macos")]
fn install_node() -> Result<String, String> {
    let url = "https://nodejs.org/dist/v20.18.0/node-v20.18.0.pkg";
    download_and_run_pkg(url, "node-v20.18.0.pkg")
}

#[cfg(target_os = "windows")]
fn install_node() -> Result<String, String> {
    let url = "https://nodejs.org/dist/v20.18.0/node-v20.18.0-x64.msi";
    let path = download_file(url, "node-v20.18.0-x64.msi")?;
    Command::new("msiexec")
        .args(["/i", &path, "/quiet", "/norestart"])
        .status()
        .map_err(|e| format!("Node.js install failed: {}", e))?;
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
    let path = download_file(url, "OllamaSetup.exe")?;
    Command::new(&path)
        .arg("/S") // Silent install
        .status()
        .map_err(|e| format!("Ollama install failed: {}", e))?;
    Ok("Ollama installed".to_string())
}

fn install_lmstudio() -> Result<String, String> {
    // LM Studio doesn't have a CLI installer — open the download page
    open::that("https://lmstudio.ai").map_err(|e| e.to_string())?;
    Ok("Opened LM Studio download page".to_string())
}

fn install_docker() -> Result<String, String> {
    #[cfg(target_os = "macos")]
    { open::that("https://www.docker.com/products/docker-desktop/").map_err(|e| e.to_string())?; }
    #[cfg(target_os = "windows")]
    { open::that("https://www.docker.com/products/docker-desktop/").map_err(|e| e.to_string())?; }
    Ok("Opened Docker download page".to_string())
}

/// Download a file to a temp directory and return the path.
fn download_file(url: &str, filename: &str) -> Result<String, String> {
    let tmp_dir = std::env::temp_dir();
    let dest = tmp_dir.join(filename);

    #[cfg(target_os = "macos")]
    {
        Command::new("curl")
            .args(["-fsSL", "-o", dest.to_str().unwrap(), url])
            .status()
            .map_err(|e| format!("Download failed: {}", e))?;
    }

    #[cfg(target_os = "windows")]
    {
        // Use PowerShell to download
        let ps_cmd = format!(
            "Invoke-WebRequest -Uri '{}' -OutFile '{}'",
            url,
            dest.to_string_lossy()
        );
        Command::new("powershell")
            .args(["-Command", &ps_cmd])
            .status()
            .map_err(|e| format!("Download failed: {}", e))?;
    }

    Ok(dest.to_string_lossy().to_string())
}

#[cfg(target_os = "macos")]
fn download_and_run_pkg(url: &str, filename: &str) -> Result<String, String> {
    let path = download_file(url, filename)?;
    Command::new("sudo")
        .args(["installer", "-pkg", &path, "-target", "/"])
        .status()
        .map_err(|e| format!("Package install failed: {}", e))?;
    Ok(format!("{} installed", filename))
}
