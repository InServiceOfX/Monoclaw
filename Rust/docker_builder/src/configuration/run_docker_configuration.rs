//! Run configuration — merged from docker_runner's richer RunConfiguration.
//! Supports: gpus, shm_size, ports, volumes, env, ipc, command.
//! Only fields present in the file are used; nothing is assumed by default
//! beyond the required `docker_image_name`.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

//------------------------------------------------------------------------------
/// Path on the host machine / path inside the container (for -v).
//------------------------------------------------------------------------------
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq, Default)]
pub struct VolumeMount {
    /// Path on the host machine (supports ~)
    pub host_path: String,
    /// Path inside the container
    pub container_path: String,
}

impl VolumeMount {
    pub fn into_volume_mount(self) -> String {
        format!("{}:{}", self.host_path, self.container_path)
    }
}

//------------------------------------------------------------------------------
/// Host port to expose / container port to map to (for -p).
//------------------------------------------------------------------------------
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq, Default)]
pub struct PortMapping {
    /// Host port to expose
    pub host_port: u16,
    /// Container port to map to
    pub container_port: u16,
}

impl PortMapping {
    pub fn into_port_mapping(self) -> String {
        format!("{}:{}", self.host_port, self.container_port)
    }
}

//------------------------------------------------------------------------------
/// Command after the image: either a single string (split on whitespace)
/// or a list of strings. Omitted = use image CMD.
//------------------------------------------------------------------------------
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum CommandOption {
    Single(String),
    List(Vec<String>),
}

impl CommandOption {
    pub fn into_vec(self) -> Vec<String> {
        match self {
            CommandOption::Single(s) => {
                if s.trim().is_empty() {
                    vec![]
                } else {
                    s.split_whitespace().map(String::from).collect()
                }
            }
            CommandOption::List(v) => v,
        }
    }
}

/// Env: map (key: value) or list of "KEY=value" strings.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum EnvOption {
    Map(HashMap<String, String>),
    List(Vec<String>),
}

impl EnvOption {
    pub fn into_env_pairs(self) -> Vec<(String, String)> {
        match self {
            EnvOption::Map(m) => m.into_iter().collect(),
            EnvOption::List(l) => l
                .into_iter()
                .filter_map(|s| {
                    let s = s.trim();
                    if s.is_empty() {
                        return None;
                    }
                    let idx = s.find('=')?;
                    let (k, v) = s.split_at(idx);
                    let v = v.strip_prefix('=').unwrap_or(v);
                    Some((k.to_string(), v.to_string()))
                })
                .collect(),
        }
    }
}

//------------------------------------------------------------------------------
/// Richer run configuration (from docker_runner) used when loading from YAML.
/// Supports: gpus, shm_size, ports, volumes, env, ipc, command.
//------------------------------------------------------------------------------
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunConfiguration {
    /// Docker image name (required).
    pub docker_image_name: String,

    #[serde(default)]
    pub gpus: Option<String>,

    #[serde(default)]
    pub shm_size: Option<String>,

    /// Port mappings (docker run -p host:container).
    #[serde(default)]
    pub ports: Option<Vec<PortMapping>>,

    /// Volume mounts (docker run -v host:container). Host path supports ~.
    #[serde(default)]
    pub volumes: Option<Vec<VolumeMount>>,

    #[serde(default)]
    pub env: Option<EnvOption>,

    #[serde(default)]
    pub ipc: Option<String>,

    /// Optional command and args after the image.
    #[serde(default)]
    pub command: Option<CommandOption>,
}

impl RunConfiguration {
    pub const DEFAULT_FILENAME: &'static str = "run_configuration.yml";

    /// Load from a YAML file. `docker_image_name` must be present.
    pub fn load_from_path<P: AsRef<Path>>(path: P) -> Result<Self, String> {
        let content = fs::read_to_string(path.as_ref())
            .map_err(|e| format!("Failed to read config: {}", e))?;
        let configuration: RunConfiguration = serde_yaml::from_str(&content)
            .map_err(|e| format!("Failed to parse YAML: {}", e))?;
        if configuration.docker_image_name.trim().is_empty() {
            return Err(
                "Configuration must set 'docker_image_name' (non-empty)".to_string());
        }
        Ok(configuration)
    }

    /// Load from a directory (looks for run_configuration.yml there).
    pub fn load_from_directory<P: AsRef<Path>>(dir: P) -> Result<Self, String> {
        let path = dir.as_ref().join(Self::DEFAULT_FILENAME);
        Self::load_from_path(path)
    }
}

//------------------------------------------------------------------------------
/// Legacy minimal data struct used internally by build_docker_run_command.
/// Populated from either RunConfiguration (YAML) or CLI flags.
//------------------------------------------------------------------------------
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq, Default)]
pub struct RunDockerConfigurationData {
    #[serde(default)]
    pub volumes: Vec<VolumeMount>,
    #[serde(default)]
    pub ports: Vec<PortMapping>,
}

/// Builder for loading Docker run configuration from YAML files (legacy path)
pub struct RunDockerConfiguration;

impl RunDockerConfiguration {
    /// Default configuration file name
    pub const DEFAULT_FILE_NAME: &'static str = "run_configuration.yml";

    /// Load run configuration data from a YAML file.
    /// Returns empty config if file does not exist.
    pub fn load_data<P: AsRef<Path>>(
        file_path: Option<P>
    ) -> Result<RunDockerConfigurationData, String> {
        let path = match file_path {
            Some(p) => p.as_ref().to_path_buf(),
            None => {
                std::env::current_dir()
                    .map_err(|e| format!(
                        "Failed to get current directory: {}", e))?
                    .join(Self::DEFAULT_FILE_NAME)
            }
        };

        // Return default if file doesn't exist (optional config file)
        if !path.exists() {
            return Ok(RunDockerConfigurationData::default());
        }

        // Read file content
        let content = fs::read_to_string(&path)
            .map_err(|e| format!("Failed to read configuration file: {}", e))?;

        // Parse YAML
        let data: RunDockerConfigurationData = serde_yaml::from_str(&content)
            .map_err(|e| format!("Failed to parse YAML: {}", e))?;

        Ok(data)
    }

    /// Load from a specific directory (looks for run_configuration.yml there)
    pub fn load_from_directory<P: AsRef<Path>>(
        directory: P,
    ) -> Result<RunDockerConfigurationData, String> {
        let path = directory.as_ref().join(Self::DEFAULT_FILE_NAME);
        Self::load_data(Some(path))
    }
}

/// Expand leading ~ in path with home directory.
pub fn expand_tilde(path: &str) -> String {
    if path.starts_with("~/") {
        if let Some(home) = std::env::var_os("HOME") {
            return home.to_string_lossy().to_string() + &path[1..];
        }
    } else if path == "~" {
        if let Some(home) = std::env::var_os("HOME") {
            return home.to_string_lossy().to_string();
        }
    }
    path.to_string()
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn test_load_data_with_valid_yaml() {
        let temp_dir = TempDir::new().unwrap();
        let config_path = temp_dir.path().join("run_docker_configuration.yml");

        let yaml_content = r#"
volumes:
  - host_path: /host/data
    container_path: /container/data
ports:
  - host_port: 8080
    container_port: 80
"#;

        fs::write(&config_path, yaml_content).unwrap();

        let config = RunDockerConfiguration::load_data(
            Some(&config_path)).unwrap();

        assert_eq!(config.volumes.len(), 1);
        assert_eq!(config.volumes[0].host_path, "/host/data");
        assert_eq!(config.volumes[0].container_path, "/container/data");
        assert_eq!(config.ports.len(), 1);
        assert_eq!(config.ports[0].host_port, 8080);
        assert_eq!(config.ports[0].container_port, 80);
    }

    #[test]
    fn test_load_data_file_not_found() {
        let config = RunDockerConfiguration::load_data(
            Some("nonexistent.yml")).unwrap();
        assert!(config.volumes.is_empty());
        assert!(config.ports.is_empty());
    }

    #[test]
    fn test_default_config() {
        let config = RunDockerConfigurationData::default();
        assert!(config.volumes.is_empty());
        assert!(config.ports.is_empty());
    }

    /// Test parsing the richer RunConfiguration (from docker_runner).
    #[test]
    fn test_parse_run_configuration_yaml() {
        let yaml = r#"
docker_image_name: lmsysorg/sglang:latest-cu130
gpus: "device=1"
shm_size: "16g"
ipc: "host"
ports:
  - host_port: 30000
    container_port: 30000
volumes:
  - host_path: /media/data/models
    container_path: /models
  - host_path: ~/.cache/huggingface
    container_path: /root/.cache/huggingface
command:
  - python3
  - -m
  - sglang.launch_server
  - --model-path
  - /models
  - --host
  - "0.0.0.0"
  - --port
  - "30000"
"#;
        let config: RunConfiguration = serde_yaml::from_str(yaml).expect(
            "parse YAML");
        assert_eq!(config.docker_image_name, "lmsysorg/sglang:latest-cu130");
        assert_eq!(config.gpus.as_deref(), Some("device=1"));
        assert_eq!(config.shm_size.as_deref(), Some("16g"));
        assert_eq!(config.ipc.as_deref(), Some("host"));

        let ports = config.ports.as_ref().unwrap();
        assert_eq!(ports.len(), 1);
        assert_eq!(ports[0].host_port, 30000);
        assert_eq!(ports[0].container_port, 30000);

        let volumes = config.volumes.as_ref().unwrap();
        assert_eq!(volumes.len(), 2);
        assert_eq!(volumes[0].host_path, "/media/data/models");
        assert_eq!(volumes[0].container_path, "/models");
        assert_eq!(volumes[1].host_path, "~/.cache/huggingface");
        assert_eq!(volumes[1].container_path, "/root/.cache/huggingface");

        let cmd = config.command.as_ref().unwrap();
        let args = cmd.clone().into_vec();
        assert_eq!(args[0], "python3");
        assert_eq!(args[1], "-m");
        assert_eq!(args[2], "sglang.launch_server");
        assert_eq!(args[3], "--model-path");
        assert_eq!(args[4], "/models");
        assert!(args.contains(&"--host".to_string()));
        assert!(args.contains(&"0.0.0.0".to_string()));
        assert!(args.contains(&"--port".to_string()));
        assert!(args.contains(&"30000".to_string()));
    }
}
