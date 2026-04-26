use std::path::PathBuf;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use clawdj::{
    JsonCommand, command::Deck, open_mixxx_database, open_output_port, port_presence_summary,
    queue_clear, queue_init, queue_set, send_message,
};
use tracing::info;
use tracing_subscriber::{EnvFilter, layer::SubscriberExt, util::SubscriberInitExt};

#[derive(Debug, Parser)]
#[command(name = "clawdj")]
#[command(about = "Drive Mixxx through the clawdj virtual MIDI bridge")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Debug, Subcommand)]
enum Commands {
    Setup,
    Load {
        deck: Deck,
        track_id: i64,
    },
    Cmd {
        json: String,
    },
    Queue {
        #[command(subcommand)]
        command: QueueCommands,
        #[arg(long)]
        db_path: Option<PathBuf>,
    },
}

#[derive(Debug, Subcommand)]
enum QueueCommands {
    Init,
    Set { deck: Deck, track_id: i64 },
    Clear,
}

fn main() -> Result<()> {
    init_tracing();
    let cli = Cli::parse();

    match cli.command {
        Commands::Setup => run_setup(),
        Commands::Load { deck, track_id } => {
            run_operation(clawdj::Operation::Load { deck, track_id })
        }
        Commands::Cmd { json } => {
            let command: JsonCommand =
                serde_json::from_str(&json).context("failed to parse command JSON")?;
            run_operation(command.into_operation()?)
        }
        Commands::Queue { command, db_path } => run_queue(command, db_path),
    }
}

fn run_setup() -> Result<()> {
    let summary = port_presence_summary()?;

    println!("Input ports:");
    for port in &summary.input_ports {
        println!("  - {port}");
    }

    println!("Output ports:");
    for port in &summary.output_ports {
        println!("  - {port}");
    }

    println!("clawdj present: {}", summary.clawdj_present);
    Ok(())
}

fn run_operation(operation: clawdj::Operation) -> Result<()> {
    let mut connection = open_output_port()?;
    if let clawdj::Operation::Load { deck, track_id } = operation {
        info!(deck = deck.as_u8(), track_id, "track id received for load");
        let message = operation.to_message();
        send_message(&mut connection, &message)?;
        return Ok(());
    }

    let message = operation.to_message();
    send_message(&mut connection, &message)
}

fn run_queue(command: QueueCommands, db_path: Option<PathBuf>) -> Result<()> {
    let path = db_path.unwrap_or_else(clawdj::default_mixxx_db_path);
    let connection = open_mixxx_database(&path)?;

    match command {
        QueueCommands::Init => {
            let playlist_id = queue_init(&connection)?;
            println!("initialized {playlist_id} at {}", path.display());
        }
        QueueCommands::Set { deck, track_id } => {
            queue_set(&connection, deck, track_id)?;
            println!(
                "set {} row 0 for deck {} to track_id {}",
                clawdj::QUEUE_NAME,
                deck.as_u8(),
                track_id
            );
        }
        QueueCommands::Clear => {
            queue_clear(&connection)?;
            println!("cleared {}", clawdj::QUEUE_NAME);
        }
    }

    Ok(())
}

fn init_tracing() {
    tracing_subscriber::registry()
        .with(EnvFilter::try_from_default_env().unwrap_or_else(|_| EnvFilter::new("info")))
        .with(tracing_subscriber::fmt::layer())
        .init();
}
