use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Duration;
use tauri::{Manager, RunEvent, WindowEvent};

// Thread-safe handle to child backend process
#[allow(dead_code)]
type BackendChildHandle = Arc<Mutex<Option<Child>>>;

fn is_backend_healthy(addr: SocketAddr) -> bool {
    if let Ok(mut stream) = TcpStream::connect_timeout(&addr, Duration::from_millis(500)) {
        let request = "GET /api/v1/health HTTP/1.1\r\nHost: 127.0.0.1:8000\r\nConnection: close\r\n\r\n";
        let _ = stream.set_read_timeout(Some(Duration::from_millis(500)));
        let _ = stream.set_write_timeout(Some(Duration::from_millis(500)));
        let _ = stream.write_all(request.as_bytes());
        let mut buffer = [0u8; 512];
        if let Ok(n) = stream.read(&mut buffer) {
            let response = String::from_utf8_lossy(&buffer[..n]);
            return response.contains("200 OK") || response.contains("\"status\"");
        }
    }
    false
}

fn locate_backend_executable(resource_dir: Option<PathBuf>) -> (String, Vec<String>) {
    // 1. Check packaged binary in app bundle resources
    if let Some(ref res) = resource_dir {
        let candidates = [
            res.join("resources").join("engine").join("voicerep-engine").join("voicerep-engine"),
            res.join("engine").join("voicerep-engine").join("voicerep-engine"),
            res.join("resources").join("engine").join("voicerep-engine"),
            res.join("engine").join("voicerep-engine"),
            res.join("bin").join("voicerep-engine"),
        ];
        for candidate in candidates {
            if candidate.exists() {
                return (candidate.to_string_lossy().to_string(), vec![]);
            }
        }
    }

    // 2. Check current directory / app bundle MacOS dir
    if let Ok(current_exe) = std::env::current_exe() {
        if let Some(parent) = current_exe.parent() {
            let candidate_macos = parent.join("voicerep-engine");
            if candidate_macos.exists() {
                return (candidate_macos.to_string_lossy().to_string(), vec![]);
            }
        }
    }

    // 3. Check repo desktop/dist directory (local test/dev mode)
    let repo_dist_candidates = [
        PathBuf::from("../../desktop/dist/voicerep-engine/voicerep-engine"),
        PathBuf::from("desktop/dist/voicerep-engine/voicerep-engine"),
        PathBuf::from("../desktop/dist/voicerep-engine/voicerep-engine"),
    ];
    for dist in repo_dist_candidates {
        if dist.exists() {
            return (dist.to_string_lossy().to_string(), vec![]);
        }
    }

    // 3. Development / unpackaged fallback: Run Python entrypoint directly
    let python_candidates = [
        "/opt/homebrew/Caskroom/miniforge/base/envs/voicerep/bin/python",
        "/opt/homebrew/bin/python3",
        "python3",
        "python",
    ];

    let mut selected_python = "python3".to_string();
    for py in python_candidates {
        if Path::new(py).exists() {
            selected_python = py.to_string();
            break;
        }
    }

    // Locate desktop_entrypoint.py relative to project
    let entrypoint_candidates = [
        PathBuf::from("../../backend/desktop_entrypoint.py"),
        PathBuf::from("../backend/desktop_entrypoint.py"),
        PathBuf::from("backend/desktop_entrypoint.py"),
    ];

    for ep in entrypoint_candidates {
        if ep.exists() {
            return (
                selected_python,
                vec![ep.to_string_lossy().to_string()],
            );
        }
    }

    (selected_python, vec!["backend/desktop_entrypoint.py".to_string()])
}

fn spawn_backend(
    resource_dir: Option<PathBuf>,
    backend_state: Arc<Mutex<Option<Child>>>,
) {
    let addr: SocketAddr = "127.0.0.1:8000".parse().unwrap();

    // If backend is already running (e.g. dev server), skip spawning
    if is_backend_healthy(addr) {
        log::info!("VoiceRep backend already running on port 8000.");
        return;
    }

    let (exec_path, extra_args) = locate_backend_executable(resource_dir.clone());
    log::info!("Spawning VoiceRep backend: {} {:?}", exec_path, extra_args);

    let mut cmd = Command::new(&exec_path);
    for arg in extra_args {
        cmd.arg(arg);
    }
    cmd.arg("--port").arg("8000");
    cmd.arg("--host").arg("127.0.0.1");

    // In desktop mode, set environment variables
    cmd.env("VOICEREP_DESKTOP_MODE", "1");
    cmd.env("ENABLE_REDIS", "false");

    // Ensure working directory is within user Application Support and never root /
    if let Ok(home) = std::env::var("HOME") {
        let app_dir = PathBuf::from(home).join("Library/Application Support/VoiceRep");
        let _ = std::fs::create_dir_all(&app_dir);
        cmd.current_dir(&app_dir);
    }

    let mut extra_path_dirs: Vec<PathBuf> = Vec::new();
    let ffmpeg_candidates = [
        resource_dir.as_ref().map(|r| r.join("resources").join("bin").join("ffmpeg")),
        resource_dir.as_ref().map(|r| r.join("bin").join("ffmpeg")),
        Some(PathBuf::from("../../desktop/src-tauri/resources/bin/ffmpeg")),
        Some(PathBuf::from("desktop/src-tauri/resources/bin/ffmpeg")),
        Some(PathBuf::from("/opt/homebrew/Caskroom/miniforge/base/envs/voicerep/bin/ffmpeg")),
        Some(PathBuf::from("/opt/homebrew/bin/ffmpeg")),
    ];
    for fc in ffmpeg_candidates.into_iter().flatten() {
        if fc.exists() {
            cmd.env("VOICEREP_FFMPEG_PATH", &fc);
            if let Some(parent) = fc.parent() {
                extra_path_dirs.push(parent.to_path_buf());
            }
            break;
        }
    }

    // Ensure child backend process has comprehensive PATH (FFmpeg, Homebrew, Conda)
    let current_path = std::env::var("PATH").unwrap_or_else(|_| "/usr/bin:/bin:/usr/sbin:/sbin".to_string());
    let mut path_elements: Vec<String> = extra_path_dirs.iter().map(|p| p.to_string_lossy().to_string()).collect();
    path_elements.push("/opt/homebrew/bin".to_string());
    path_elements.push("/opt/homebrew/sbin".to_string());
    path_elements.push("/usr/local/bin".to_string());
    path_elements.push("/opt/homebrew/Caskroom/miniforge/base/envs/voicerep/bin".to_string());
    path_elements.push(current_path);
    cmd.env("PATH", path_elements.join(":"));

    match cmd.spawn() {
        Ok(child) => {
            log::info!("VoiceRep backend process spawned successfully (PID: {})", child.id());
            if let Ok(mut state) = backend_state.lock() {
                *state = Some(child);
            }

            // Wait for health endpoint in background
            thread::spawn(move || {
                for i in 1..=60 {
                    thread::sleep(Duration::from_millis(500));
                    if is_backend_healthy(addr) {
                        log::info!("VoiceRep backend health check passed at attempt {}.", i);
                        return;
                    }
                }
                log::warn!("VoiceRep backend did not respond to health checks within 30 seconds.");
            });
        }
        Err(e) => {
            log::error!("Failed to spawn VoiceRep backend process: {}", e);
        }
    }
}

fn kill_backend(backend_state: &Arc<Mutex<Option<Child>>>) {
    if let Ok(mut state) = backend_state.lock() {
        if let Some(mut child) = state.take() {
            log::info!("Terminating VoiceRep backend process (PID: {})...", child.id());
            let _ = child.kill();
            let _ = child.wait();
            log::info!("VoiceRep backend process terminated.");
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let backend_child = Arc::new(Mutex::new(None::<Child>));
    let backend_child_clone = Arc::clone(&backend_child);
    let backend_child_exit = Arc::clone(&backend_child);

    let app = tauri::Builder::default()
        .setup(move |app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            let resource_dir = app.path().resource_dir().ok();
            spawn_backend(resource_dir, backend_child_clone);
            Ok(())
        })
        .on_window_event(move |_window, event| {
            if let WindowEvent::CloseRequested { .. } = event {
                kill_backend(&backend_child);
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building VoiceRep tauri application");

    app.run(move |_app_handle, event| {
        if let RunEvent::Exit | RunEvent::ExitRequested { .. } = event {
            kill_backend(&backend_child_exit);
        }
    });
}
