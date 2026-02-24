//! Run Docker container - main logic for loading configs and building command

use std::path::{Path, PathBuf};
use std::process::Command;

use crate::configuration::build_docker_configuration::BuildDockerConfiguration;
use crate::configuration::run_docker_configuration::{
    RunConfiguration, RunDockerConfiguration};
use super::build_docker_run_command::{
    BuildDockerRunCommandConfiguration,
    build_docker_run_command,
    build_docker_run_command_with_no_gpu,
};

//------------------------------------------------------------------------------
/// Arguments from CLI
//------------------------------------------------------------------------------
#[derive(Debug, Clone)]
pub struct RunDockerArgs {
    pub build_dir: PathBuf,
    pub gpu_id: Option<u32>,
    pub interactive: bool,
    pub detached: bool,
    pub entrypoint: Option<String>,
    pub network_host: bool,
    pub no_gpu: bool,
    pub gui: bool,
    pub audio: bool,
}

//------------------------------------------------------------------------------
/// Load configs and build docker run command.
///
/// # Steps:
/// 1. Load build_configuration.yml from build_dir (for docker_image_name)
/// 2. Load run_configuration.yml from build_dir.
///    Tries RunConfiguration (richer YAML format) first; falls back to legacy
///    RunDockerConfiguration (volumes/ports only).
/// 3. Populate BuildDockerRunCommandConfiguration from args + configs
/// 4. Build docker run command (Vec<String>)
///
/// CLI flags (gpu_id, interactive, etc.) override corresponding YAML fields.
///
/// # Returns
/// * `Ok((Vec<String>, String))` - Command args and image name
/// * `Err(String)` - Error loading configs or building command
//------------------------------------------------------------------------------
pub fn build_run_command_from_args(
    args: &RunDockerArgs,
) -> Result<(Vec<String>, String), String> {
    // Resolve build directory
    let build_dir = args.build_dir
        .canonicalize()
        .map_err(|e| format!(
            "Invalid build directory '{}': {}",
            args.build_dir.display(), e))?;

    println!("==> Loading configurations from: {}", build_dir.display());

    // 1. Load build_configuration.yml (for docker_image_name)
    let config_file = build_dir.join("build_configuration.yml");
    if !config_file.exists() {
        return Err(format!(
            "Build configuration file not found: {}",
            config_file.display()
        ));
    }

    let build_config = BuildDockerConfiguration::load_data(Some(&config_file))?;
    let docker_image_name = build_config.docker_image_name.clone();

    println!("    Docker image: {}", docker_image_name);

    // Check if image exists
    if !check_image_exists(&docker_image_name) {
        eprintln!(
            "\n⚠ Warning: Docker image '{}' not found locally.",
            docker_image_name);
        eprintln!("  You may need to build it first:");
        eprintln!("  docker_builder build {}\n", build_dir.display());
    }

    // 2. Load run_configuration.yml
    //    Try richer RunConfiguration first (has gpus, shm_size, env, ipc, command).
    //    If the file has `docker_image_name`, it parses as RunConfiguration.
    //    Otherwise fall back to legacy (volumes/ports only).
    let run_config_file = build_dir.join("run_configuration.yml");

    let (yaml_run_config, legacy_run_config) = if run_config_file.exists() {
        println!(
            "    Loading run configuration from: {}",
            run_config_file.display());

        // Try richer format first
        match RunConfiguration::load_from_path(&run_config_file) {
            Ok(rc) => {
                println!("    Run config: richer YAML format (docker_runner style)");
                (Some(rc), Default::default())
            }
            Err(_) => {
                // Fall back to legacy (volumes/ports only, no docker_image_name required)
                let legacy = RunDockerConfiguration::load_data(
                    Some(&run_config_file))?;
                println!("    Run config: legacy format (volumes/ports only)");
                println!("    Volumes: {}", legacy.volumes.len());
                println!("    Ports: {}", legacy.ports.len());
                (None, legacy)
            }
        }
    } else {
        println!(
            "    Warning: Run configuration file not found (using defaults)");
        (None, Default::default())
    };

    // 3. Populate BuildDockerRunCommandConfiguration
    let mut docker_run_config = BuildDockerRunCommandConfiguration::default();
    docker_run_config.docker_image_name = docker_image_name.clone();
    docker_run_config.run_config = legacy_run_config;
    docker_run_config.yaml_run_config = yaml_run_config;

    // Set fields from CLI args
    docker_run_config.is_interactive = args.interactive;
    docker_run_config.is_detached = args.detached;
    docker_run_config.use_host_network = args.network_host;
    docker_run_config.enable_gui = args.gui;
    docker_run_config.enable_audio = args.audio;

    if let Some(entrypoint) = &args.entrypoint {
        docker_run_config.entrypoint = Some(entrypoint.clone());
    }

    // Handle GPU: --no-gpu takes precedence, then --gpu N
    if args.no_gpu {
        docker_run_config.gpu_id = None;
    } else if let Some(gpu_id) = args.gpu_id {
        docker_run_config.gpu_id = Some(gpu_id);
    }

    // 4. Build docker run command
    println!("\n==> Building docker run command...");
    let docker_cmd = if args.no_gpu {
        build_docker_run_command_with_no_gpu(&docker_run_config)?
    } else {
        build_docker_run_command(&docker_run_config)?
    };

    println!("    Command ready ({} args)", docker_cmd.len());

    Ok((docker_cmd, docker_image_name))
}

//------------------------------------------------------------------------------
/// Execute a docker run command.
//------------------------------------------------------------------------------
pub fn execute_docker_run_command(
    cmd: &[String],
    working_dir: &Path,
) -> Result<(), String> {
    println!("\n{}", "=".repeat(80));
    println!("Starting container...");
    println!("{}", "=".repeat(80));
    println!();

    let status = Command::new(&cmd[0])
        .args(&cmd[1..])
        .current_dir(working_dir)
        .status()
        .map_err(|e| format!("Failed to execute docker command: {}", e))?;

    if !status.success() && status.code() != Some(127) {
        return Err(format!(
            "Docker run failed with exit code: {}",
            status.code().unwrap_or(-1)
        ));
    } else if status.code() == Some(127) {
        println!(
            "Note: Container exited with code 127 (may be normal for shell exit in some setups)");
    }

    println!("\n✓ Container finished successfully!");
    Ok(())
}

/// Check if a Docker image exists locally.
pub fn check_image_exists(image_name: &str) -> bool {
    let output = Command::new("docker")
        .args(&["images", "-q", image_name])
        .output();

    match output {
        Ok(out) => !String::from_utf8_lossy(&out.stdout).trim().is_empty(),
        Err(_) => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn test_build_run_command_with_all_configs() {
        let temp = TempDir::new().unwrap();

        let build_config_yaml = r#"
docker_image_name: test-image:latest
base_image: ubuntu:22.04
dockerfile_components: []
"#;
        fs::write(temp.path().join("build_configuration.yml"), build_config_yaml).unwrap();

        let run_config_yaml = r#"
ports:
  - host_port: 8080
    container_port: 80
volumes:
  - host_path: /host/data
    container_path: /data
"#;
        fs::write(temp.path().join("run_configuration.yml"), run_config_yaml).unwrap();

        let args = RunDockerArgs {
            build_dir: temp.path().to_path_buf(),
            gpu_id: Some(0),
            interactive: true,
            detached: false,
            entrypoint: Some("/bin/bash".to_string()),
            network_host: true,
            no_gpu: false,
            gui: true,
            audio: false,
        };

        let result = build_run_command_from_args(&args);
        assert!(result.is_ok(), "Should succeed with valid configs");

        let (cmd, image_name) = result.unwrap();

        assert_eq!(image_name, "test-image:latest");
        assert_eq!(cmd[0], "docker");
        assert_eq!(cmd[1], "run");
        assert!(cmd.contains(&"--gpus".to_string()));
        assert!(cmd.iter().any(|s| s.contains("device=0")));
        assert!(cmd.contains(&"-it".to_string()));
        assert!(cmd.contains(&"--network".to_string()));
        assert!(cmd.contains(&"host".to_string()));
        assert!(cmd.contains(&"--entrypoint".to_string()));
        assert!(cmd.contains(&"/bin/bash".to_string()));
        assert!(cmd.contains(&"-v".to_string()));
        assert!(cmd.iter().any(|s| s.contains("/host/data:/data")));
        assert!(cmd.contains(&"-p".to_string()));
        assert!(cmd.iter().any(|s| s.contains("8080:80")));
        assert!(cmd.iter().any(|s| s.contains("DISPLAY")));
        assert_eq!(cmd.last().unwrap(), "test-image:latest");
    }

    #[test]
    fn test_build_run_command_with_no_gpu_and_missing_run_config() {
        let temp = TempDir::new().unwrap();

        let build_config_yaml = r#"
docker_image_name: no-gpu-image:v1.0
base_image: ubuntu:20.04
dockerfile_components: []
"#;
        fs::write(
            temp.path().join("build_configuration.yml"),
            build_config_yaml).unwrap();

        let args = RunDockerArgs {
            build_dir: temp.path().to_path_buf(),
            gpu_id: None,
            interactive: false,
            detached: true,
            entrypoint: None,
            network_host: false,
            no_gpu: true,
            gui: false,
            audio: false,
        };

        let result = build_run_command_from_args(&args);
        assert!(
            result.is_ok(),
            "Should succeed even without run_configuration.yml");

        let (cmd, image_name) = result.unwrap();

        assert_eq!(image_name, "no-gpu-image:v1.0");
        assert!(!cmd.contains(&"--gpus".to_string()));
        assert!(!cmd.iter().any(|s| s.contains("device=")));
        assert!(!cmd.contains(&"--rm".to_string()));
        assert!(cmd.contains(&"-d".to_string()));
        assert!(!cmd.contains(&"-it".to_string()));

        let volume_count = cmd.iter().filter(|s| *s == "-v").count();
        let port_count = cmd.iter().filter(|s| *s == "-p").count();
        assert_eq!(volume_count, 0);
        assert_eq!(port_count, 0);

        assert!(!cmd.iter().any(|s| s.contains("DISPLAY")));
        assert!(!cmd.iter().any(|s| s.contains("pulse")));
        assert_eq!(cmd.last().unwrap(), "no-gpu-image:v1.0");
    }

    #[test]
    fn test_build_run_command_with_richer_yaml_run_config() {
        let temp = TempDir::new().unwrap();

        let build_config_yaml = r#"
docker_image_name: my-ml-image:latest
base_image: ubuntu:24.04
dockerfile_components: []
"#;
        fs::write(temp.path().join("build_configuration.yml"), build_config_yaml).unwrap();

        // Richer run_configuration.yml with docker_image_name (docker_runner style)
        let run_config_yaml = r#"
docker_image_name: my-ml-image:latest
gpus: "all"
shm_size: "32g"
ipc: "host"
ports:
  - host_port: 8888
    container_port: 8888
volumes:
  - host_path: /data
    container_path: /data
env:
  MY_TOKEN: "abc123"
command:
  - python3
  - train.py
"#;
        fs::write(temp.path().join("run_configuration.yml"), run_config_yaml).unwrap();

        let args = RunDockerArgs {
            build_dir: temp.path().to_path_buf(),
            gpu_id: None,
            interactive: false,
            detached: false,
            entrypoint: None,
            network_host: false,
            no_gpu: false,
            gui: false,
            audio: false,
        };

        let result = build_run_command_from_args(&args);
        assert!(result.is_ok(), "Should succeed: {:?}", result.err());

        let (cmd, image_name) = result.unwrap();
        assert_eq!(image_name, "my-ml-image:latest");
        assert_eq!(cmd[0], "docker");
        assert_eq!(cmd[1], "run");
        assert!(cmd.contains(&"--gpus".to_string()));
        assert!(cmd.contains(&"all".to_string()));
        assert!(cmd.contains(&"--shm-size".to_string()));
        assert!(cmd.contains(&"32g".to_string()));
        assert!(cmd.contains(&"--ipc".to_string()));
        assert!(cmd.contains(&"host".to_string()));
        assert!(cmd.contains(&"-p".to_string()));
        assert!(cmd.iter().any(|s| s.contains("8888:8888")));
        assert!(cmd.contains(&"-v".to_string()));
        assert!(cmd.iter().any(|s| s.contains("/data:/data")));
        assert!(cmd.iter().any(|s| s.contains("MY_TOKEN=abc123")));
        assert!(cmd.contains(&"my-ml-image:latest".to_string()));
        assert!(cmd.contains(&"python3".to_string()));
        assert!(cmd.contains(&"train.py".to_string()));
    }
}
