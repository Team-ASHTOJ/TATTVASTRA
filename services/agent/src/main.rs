use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(
    name = "jocky-agent",
    version,
    about = "JOCKY Agent foundation; no execution yet"
)]
struct Cli {
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Report actual host support and unavailable capabilities as JSON.
    Doctor,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .json()
        .with_writer(std::io::stderr)
        .init();
    match Cli::parse().command {
        Command::Doctor => println!("{}", serde_json::to_string_pretty(&jocky_agent::doctor())?),
    }
    Ok(())
}
