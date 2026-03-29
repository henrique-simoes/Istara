/// System statistics — CPU, RAM, GPU via the sysinfo crate.
use sysinfo::System;

pub fn get_system_stats() -> Result<serde_json::Value, String> {
    let mut sys = System::new_all();
    sys.refresh_all();

    let total_ram_gb = sys.total_memory() as f64 / (1024.0 * 1024.0 * 1024.0);
    let available_ram_gb = sys.available_memory() as f64 / (1024.0 * 1024.0 * 1024.0);
    let cpu_usage = sys.global_cpu_usage();
    let cpu_cores = sys.cpus().len();

    Ok(serde_json::json!({
        "cpu_cores": cpu_cores,
        "cpu_usage_pct": cpu_usage,
        "total_ram_gb": format!("{:.1}", total_ram_gb),
        "available_ram_gb": format!("{:.1}", available_ram_gb),
        "os": System::long_os_version().unwrap_or_default(),
    }))
}
