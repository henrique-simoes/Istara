/// Background health checker — polls backend health endpoint.
/// Updates tray tooltip and emits events to any open webview windows.

use tauri::{AppHandle, Emitter, Runtime};
use std::time::Duration;

const POLL_INTERVAL: Duration = Duration::from_secs(10);
const HEALTH_URL: &str = "http://127.0.0.1:8000/api/health";
const FRONTEND_URL: &str = "http://127.0.0.1:3000";

#[derive(serde::Serialize, Clone)]
struct HealthStatus {
    backend: bool,
    frontend: bool,
    timestamp: u64,
}

/// Long-running health check loop. Call from a spawned thread.
pub fn health_loop<R: Runtime>(app: AppHandle<R>) {
    loop {
        std::thread::sleep(POLL_INTERVAL);

        let backend_healthy = check_port(8000);
        let frontend_healthy = check_port(3000);

        let status = HealthStatus {
            backend: backend_healthy,
            frontend: frontend_healthy,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
        };

        // Emit to any listening webview windows
        let _ = app.emit("health-status", &status);
    }
}

/// Quick TCP port check — doesn't do HTTP, just verifies something is listening.
fn check_port(port: u16) -> bool {
    std::net::TcpStream::connect_timeout(
        &format!("127.0.0.1:{}", port).parse().unwrap(),
        Duration::from_secs(2),
    )
    .is_ok()
}
