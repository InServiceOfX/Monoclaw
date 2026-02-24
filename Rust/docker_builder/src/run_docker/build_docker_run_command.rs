//! Build docker run argv from configuration.
//!
//! Supports two modes:
//! 1. YAML-driven: RunConfiguration fields (gpus, shm_size, env, ipc, command)
//!    from run_configuration.yml (richer docker_runner-style).
//! 2. CLI-driven: BuildDockerRunCommandConfiguration struct (legacy CLI flags).
//!
//! CLI flags override YAML where both exist.

use crate::configuration::run_docker_configuration::{
    expand_tilde, RunConfiguration, RunDockerConfigurationData,
};
use std::path::Path;

//------------------------------------------------------------------------------
/// Build docker run argv from a richer RunConfiguration (YAML-driven).
/// Produces: ["docker", "run", ...options..., image, ...command...].
//------------------------------------------------------------------------------
pub fn build_run_args_from_yaml(
    configuration: &RunConfiguration,
) -> Result<Vec<String>, String> {
    if configuration.docker_image_name.trim().is_empty() {
        return Err("Configuration 'docker_image_name' is empty".to_string());
    }

    let mut args = vec!["docker".to_string(), "run".to_string()];

    if let Some(ref g) = configuration.gpus {
        if !g.is_empty() {
            args.push("--gpus".to_string());
            args.push(g.clone());
        }
    }

    if let Some(ref s) = configuration.shm_size {
        if !s.is_empty() {
            args.push("--shm-size".to_string());
            args.push(s.clone());
        }
    }

    if let Some(ref port_list) = configuration.ports {
        for port_map in port_list {
            args.push("-p".to_string());
            args.push(
                format!(
                    "{}:{}", port_map.host_port, port_map.container_port));
        }
    }

    if let Some(ref vol_list) = configuration.volumes {
        for volume in vol_list {
            let host_exp = expand_tilde(volume.host_path.trim());
            args.push("-v".to_string());
            args.push(format!("{}:{}", host_exp, volume.container_path.trim()));
        }
    }

    if let Some(ref e) = configuration.env {
        for (k, v) in e.clone().into_env_pairs() {
            if !k.is_empty() {
                args.push("-e".to_string());
                args.push(format!("{}={}", k, v));
            }
        }
    }

    if let Some(ref i) = configuration.ipc {
        if !i.is_empty() {
            args.push("--ipc".to_string());
            args.push(i.clone());
        }
    }

    args.push(configuration.docker_image_name.trim().to_string());

    if let Some(ref cmd) = configuration.command {
        let parts = cmd.clone().into_vec();
        for p in parts {
            if !p.is_empty() {
                args.push(p);
            }
        }
    }

    Ok(args)
}

//------------------------------------------------------------------------------
/// Legacy CLI-driven run command configuration struct.
/// Used by build_docker_run_command and build_docker_run_command_with_no_gpu.
//------------------------------------------------------------------------------
#[derive(Debug, Clone)]
pub struct BuildDockerRunCommandConfiguration {
    /// Docker image name to run (required)
    pub docker_image_name: String,

    /// Volumes and ports loaded from run_configuration.yml (legacy fields)
    pub run_config: RunDockerConfigurationData,

    /// GPU device ID (for --gpus device=N)
    pub gpu_id: Option<u32>,

    /// Run in detached mode (-d)
    pub is_detached: bool,

    /// Run with interactive terminal (-it)
    pub is_interactive: bool,

    /// Custom entrypoint (--entrypoint)
    pub entrypoint: Option<String>,

    /// Use host network (--network host)
    pub use_host_network: bool,

    /// Additional networks to connect to
    pub networks: Vec<String>,

    /// Custom container name (--name)
    pub container_name: Option<String>,

    /// Enable GUI support (X11 forwarding)
    pub enable_gui: bool,

    /// Enable audio support (PulseAudio)
    pub enable_audio: bool,

    /// Additional environment variables
    pub env_vars: Vec<(String, String)>,

    /// Richer YAML run configuration (gpus, shm_size, env, ipc, command).
    /// When set, its fields are merged in; CLI args override where both exist.
    pub yaml_run_config: Option<RunConfiguration>,
}

impl Default for BuildDockerRunCommandConfiguration {
    fn default() -> Self {
        Self {
            docker_image_name: String::new(),
            run_config: RunDockerConfigurationData::default(),
            gpu_id: None,
            is_detached: false,
            // Default to interactive
            is_interactive: true,
            entrypoint: None,
            use_host_network: false,
            networks: vec![],
            container_name: None,
            enable_gui: false,
            enable_audio: false,
            env_vars: vec![],
            yaml_run_config: None,
        }
    }
}

//------------------------------------------------------------------------------
/// Add X11 GUI support to docker run command.
//------------------------------------------------------------------------------
fn add_gui_support(cmd: &mut Vec<String>) {
    let display = std::env::var("DISPLAY").unwrap_or_else(|_| ":0".to_string());
    cmd.push("-e".to_string());
    cmd.push(format!("DISPLAY={}", display));
    cmd.push("-v".to_string());
    cmd.push("/tmp/.X11-unix:/tmp/.X11-unix:rw".to_string());
}

//------------------------------------------------------------------------------
/// Add audio support (PulseAudio) to docker run command.
//------------------------------------------------------------------------------
fn add_audio_support(cmd: &mut Vec<String>) {
    #[cfg(unix)]
    let user_id = {
        use nix::unistd::getuid;
        getuid().as_raw()
    };

    #[cfg(not(unix))]
    let user_id = 1000;

    let pulse_socket = format!("/run/user/{}/pulse", user_id);
    let pulse_native = format!("/run/user/{}/pulse/native", user_id);

    // Check if PulseAudio socket exists
    if Path::new(&pulse_native).exists() {
        cmd.push("-v".to_string());
        cmd.push(format!("{}:/run/user/1000/pulse:ro", pulse_socket));

        cmd.push("-e".to_string());
        cmd.push("PULSE_SERVER=unix:/run/user/1000/pulse/native".to_string());

        cmd.push("-e".to_string());
        cmd.push("PULSE_RUNTIME_PATH=/run/user/1000/pulse".to_string());

        let cookie_paths = [
            format!(
                "{}/.config/pulse/cookie",
                std::env::var("HOME").unwrap_or_default()),
            format!("/run/user/{}/.config/pulse/cookie", user_id),
            format!("/run/user/{}/pulse-cookie", user_id),
        ];

        let mut cookie_mounted = false;
        for cookie_path in &cookie_paths {
            if std::path::Path::new(cookie_path).exists() {
                cmd.push("-v".to_string());
                cmd.push(format!(
                    "{}:/run/user/1000/pulse-cookie:ro",
                    cookie_path));
                cookie_mounted = true;
                break;
            }
        }

        if !cookie_mounted {
            let pulse_cookie_in_socket = format!("{}/cookie", pulse_socket);
            if std::path::Path::new(&pulse_cookie_in_socket).exists() {
                cmd.push("-v".to_string());
                cmd.push(format!(
                    "{}:/run/user/1000/pulse-cookie:ro",
                    pulse_cookie_in_socket));
            }
        }
    }

    // Always add ALSA device as fallback
    cmd.push("--device".to_string());
    cmd.push("/dev/snd".to_string());
}

pub fn build_docker_run_command(
    configuration: &BuildDockerRunCommandConfiguration,
) -> Result<Vec<String>, String> {
    if configuration.docker_image_name.is_empty() {
        return Err("Docker image name is empty".to_string());
    }

    let mut docker_run_cmd = vec!["docker".to_string(), "run".to_string()];

    // --- YAML-sourced fields (gpus, shm_size, ipc from yaml_run_config) ---
    // CLI gpu_id overrides YAML gpus when set.
    if let Some(ref yaml_cfg) = configuration.yaml_run_config {
        // gpus: CLI gpu_id takes precedence
        if configuration.gpu_id.is_none() {
            if let Some(ref g) = yaml_cfg.gpus {
                if !g.is_empty() {
                    docker_run_cmd.push("--gpus".to_string());
                    docker_run_cmd.push(g.clone());
                }
            }
        }

        if let Some(ref s) = yaml_cfg.shm_size {
            if !s.is_empty() {
                docker_run_cmd.push("--shm-size".to_string());
                docker_run_cmd.push(s.clone());
            }
        }
    }

    // CLI GPU support (overrides YAML)
    if let Some(gpu) = configuration.gpu_id {
        docker_run_cmd.push("--gpus".to_string());
        docker_run_cmd.push(format!("device={}", gpu));
    }

    if configuration.is_detached {
        docker_run_cmd.push("-d".to_string());
    } else {
        docker_run_cmd.push("--rm".to_string());
    }

    if configuration.is_interactive {
        docker_run_cmd.push("-it".to_string());
    }

    if configuration.use_host_network {
        docker_run_cmd.push("--network".to_string());
        docker_run_cmd.push("host".to_string());
    }

    for network in &configuration.networks {
        docker_run_cmd.push("--network".to_string());
        docker_run_cmd.push(network.clone());
    }

    // Ports: from legacy run_config
    for port_map in &configuration.run_config.ports {
        docker_run_cmd.push("-p".to_string());
        docker_run_cmd.push(
            format!("{}:{}",
            port_map.host_port,
            port_map.container_port));
    }
    // Ports: from YAML run config (if set and not already in legacy)
    if let Some(ref yaml_cfg) = configuration.yaml_run_config {
        if configuration.run_config.ports.is_empty() {
            if let Some(ref port_list) = yaml_cfg.ports {
                for port_map in port_list {
                    docker_run_cmd.push("-p".to_string());
                    docker_run_cmd.push(
                        format!("{}:{}", port_map.host_port, port_map.container_port));
                }
            }
        }
    }

    // Volumes: from legacy run_config
    for volume in &configuration.run_config.volumes {
        docker_run_cmd.push("-v".to_string());
        docker_run_cmd.push(
            format!("{}:{}",
            volume.host_path,
            volume.container_path));
    }
    // Volumes: from YAML run config (if set and not already in legacy)
    if let Some(ref yaml_cfg) = configuration.yaml_run_config {
        if configuration.run_config.volumes.is_empty() {
            if let Some(ref vol_list) = yaml_cfg.volumes {
                for volume in vol_list {
                    let host_exp = expand_tilde(volume.host_path.trim());
                    docker_run_cmd.push("-v".to_string());
                    docker_run_cmd.push(
                        format!("{}:{}", host_exp, volume.container_path.trim()));
                }
            }
        }
    }

    if configuration.enable_gui {
        add_gui_support(&mut docker_run_cmd);
    }
    if configuration.enable_audio {
        add_audio_support(&mut docker_run_cmd);
    }

    // Env vars from YAML
    if let Some(ref yaml_cfg) = configuration.yaml_run_config {
        if let Some(ref e) = yaml_cfg.env {
            for (k, v) in e.clone().into_env_pairs() {
                if !k.is_empty() {
                    docker_run_cmd.push("-e".to_string());
                    docker_run_cmd.push(format!("{}={}", k, v));
                }
            }
        }
    }

    // Env vars from CLI
    for (key, value) in &configuration.env_vars {
        docker_run_cmd.push("-e".to_string());
        docker_run_cmd.push(format!("{}={}", key, value));
    }

    // IPC: YAML value (CLI doesn't have a dedicated ipc flag in the old builder)
    if let Some(ref yaml_cfg) = configuration.yaml_run_config {
        if let Some(ref i) = yaml_cfg.ipc {
            if !i.is_empty() {
                docker_run_cmd.push("--ipc".to_string());
                docker_run_cmd.push(i.clone());
            }
        }
    }

    if let Some(name) = &configuration.container_name {
        docker_run_cmd.push("--name".to_string());
        docker_run_cmd.push(name.clone());
    }

    if let Some(entrypoint) = &configuration.entrypoint {
        docker_run_cmd.push("--entrypoint".to_string());
        docker_run_cmd.push(entrypoint.clone());
    }

    // Add image
    docker_run_cmd.push(configuration.docker_image_name.to_string());

    // Command from YAML (after image)
    if let Some(ref yaml_cfg) = configuration.yaml_run_config {
        if let Some(ref cmd) = yaml_cfg.command {
            let parts = cmd.clone().into_vec();
            for p in parts {
                if !p.is_empty() {
                    docker_run_cmd.push(p);
                }
            }
        }
    }

    Ok(docker_run_cmd)
}

pub fn build_docker_run_command_with_no_gpu(
    configuration: &BuildDockerRunCommandConfiguration,
) -> Result<Vec<String>, String> {
    if configuration.docker_image_name.is_empty() {
        return Err("Docker image name is empty".to_string());
    }

    let mut docker_run_cmd = vec!["docker".to_string(), "run".to_string()];

    // shm_size from YAML
    if let Some(ref yaml_cfg) = configuration.yaml_run_config {
        if let Some(ref s) = yaml_cfg.shm_size {
            if !s.is_empty() {
                docker_run_cmd.push("--shm-size".to_string());
                docker_run_cmd.push(s.clone());
            }
        }
    }

    if configuration.is_detached {
        docker_run_cmd.push("-d".to_string());
    } else {
        docker_run_cmd.push("--rm".to_string());
    }

    if configuration.is_interactive {
        docker_run_cmd.push("-it".to_string());
    }

    if configuration.use_host_network {
        docker_run_cmd.push("--network".to_string());
        docker_run_cmd.push("host".to_string());
    }

    for network in &configuration.networks {
        docker_run_cmd.push("--network".to_string());
        docker_run_cmd.push(network.clone());
    }

    for port_map in &configuration.run_config.ports {
        docker_run_cmd.push("-p".to_string());
        docker_run_cmd.push(
            format!("{}:{}",
            port_map.host_port,
            port_map.container_port));
    }

    for volume in &configuration.run_config.volumes {
        docker_run_cmd.push("-v".to_string());
        docker_run_cmd.push(
            format!("{}:{}",
            volume.host_path,
            volume.container_path));
    }

    if configuration.enable_gui {
        add_gui_support(&mut docker_run_cmd);
    }
    if configuration.enable_audio {
        add_audio_support(&mut docker_run_cmd);
    }

    for (key, value) in &configuration.env_vars {
        docker_run_cmd.push("-e".to_string());
        docker_run_cmd.push(format!("{}={}", key, value));
    }

    if let Some(name) = &configuration.container_name {
        docker_run_cmd.push("--name".to_string());
        docker_run_cmd.push(name.clone());
    }

    if let Some(entrypoint) = &configuration.entrypoint {
        docker_run_cmd.push("--entrypoint".to_string());
        docker_run_cmd.push(entrypoint.clone());
    }

    docker_run_cmd.push(configuration.docker_image_name.to_string());

    Ok(docker_run_cmd)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::configuration::run_docker_configuration::{
        PortMapping, VolumeMount};

    #[test]
    fn test_build_docker_run_command_with_gpu() {
        let run_config = RunDockerConfigurationData {
            volumes: vec![VolumeMount {
                host_path: "/host/data".to_string(),
                container_path: "/data".to_string(),
            }],
            ports: vec![PortMapping {
                host_port: 8080,
                container_port: 80,
            }],
        };

        let config = BuildDockerRunCommandConfiguration {
            docker_image_name: "test-image:latest".to_string(),
            run_config,
            gpu_id: Some(0),
            is_interactive: true,
            is_detached: false,
            use_host_network: true,
            container_name: Some("my-container".to_string()),
            ..Default::default()
        };

        let cmd = build_docker_run_command(&config).unwrap();

        assert_eq!(cmd[0], "docker");
        assert_eq!(cmd[1], "run");
        assert!(cmd.contains(&"--rm".to_string()));
        assert!(cmd.contains(&"-it".to_string()));
        assert!(cmd.contains(&"--gpus".to_string()));
        assert!(cmd.iter().any(|s| s.contains("device=0")));
        assert!(cmd.contains(&"--network".to_string()));
        assert!(cmd.contains(&"host".to_string()));
        assert!(cmd.contains(&"--name".to_string()));
        assert!(cmd.contains(&"my-container".to_string()));
        assert!(cmd.contains(&"-v".to_string()));
        assert!(cmd.iter().any(|s| s.contains("/host/data:/data")));
        assert!(cmd.contains(&"-p".to_string()));
        assert!(cmd.iter().any(|s| s.contains("8080:80")));
        assert_eq!(cmd.last().unwrap(), "test-image:latest");
    }

    #[test]
    fn test_build_docker_run_command_no_gpu() {
        let config = BuildDockerRunCommandConfiguration {
            docker_image_name: "test-no-gpu:latest".to_string(),
            run_config: RunDockerConfigurationData::default(),
            gpu_id: None,
            is_interactive: false,
            is_detached: true,
            ..Default::default()
        };

        let cmd = build_docker_run_command_with_no_gpu(&config).unwrap();

        assert!(!cmd.contains(&"--gpus".to_string()));
        assert!(!cmd.iter().any(|s| s.contains("device=")));
        assert!(!cmd.contains(&"--rm".to_string()));
        assert!(cmd.contains(&"-d".to_string()));
        assert!(!cmd.contains(&"-it".to_string()));
        assert_eq!(cmd.last().unwrap(), "test-no-gpu:latest");
    }

    #[test]
    fn test_build_run_args_from_yaml_full_config() {
        use crate::configuration::run_docker_configuration::{
            CommandOption, EnvOption, RunConfiguration};
        use std::collections::HashMap;

        let mut env_map = HashMap::new();
        env_map.insert("HF_TOKEN".to_string(), "secret".to_string());
        let config = RunConfiguration {
            docker_image_name: "lmsysorg/sglang:latest-cu130".to_string(),
            gpus: Some("device=1".to_string()),
            shm_size: Some("16g".to_string()),
            ports: Some(vec![PortMapping {
                host_port: 30000,
                container_port: 30000,
            }]),
            volumes: Some(vec![
                VolumeMount {
                    host_path: "/host/models".to_string(),
                    container_path: "/models".to_string(),
                },
            ]),
            env: Some(EnvOption::Map(env_map)),
            ipc: Some("host".to_string()),
            command: Some(CommandOption::List(vec![
                "python3".to_string(),
                "-m".to_string(),
                "sglang.launch_server".to_string(),
                "--model-path".to_string(),
                "/models".to_string(),
                "--port".to_string(),
                "30000".to_string(),
            ])),
        };

        let args = build_run_args_from_yaml(&config).expect(
            "build should succeed");
        assert!(args.len() >= 2);
        assert_eq!(args[0], "docker");
        assert_eq!(args[1], "run");
        assert!(args.contains(&"--gpus".to_string()));
        assert!(args.contains(&"device=1".to_string()));
        assert!(args.contains(&"--shm-size".to_string()));
        assert!(args.contains(&"16g".to_string()));
        assert!(args.contains(&"-p".to_string()));
        assert!(args.contains(&"30000:30000".to_string()));
        assert!(args.contains(&"-v".to_string()));
        assert!(args.iter().any(|a| a == "/host/models:/models"));
        assert!(args.contains(&"-e".to_string()));
        assert!(args.iter().any(|a| a.starts_with("HF_TOKEN=")));
        assert!(args.contains(&"--ipc".to_string()));
        assert!(args.contains(&"host".to_string()));
        assert!(args.contains(&"lmsysorg/sglang:latest-cu130".to_string()));
        assert!(args.contains(&"python3".to_string()));
        assert!(args.contains(&"sglang.launch_server".to_string()));
        assert!(args.contains(&"--model-path".to_string()));
        assert!(args.contains(&"/models".to_string()));
        assert!(args.contains(&"30000".to_string()));
    }
}
