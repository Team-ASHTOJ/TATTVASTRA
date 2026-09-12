fn main() -> Result<(), Box<dyn std::error::Error>> {
    println!("cargo:rerun-if-changed=../../proto/jocky/v1/agent.proto");
    tonic_prost_build::compile_protos("../../proto/jocky/v1/agent.proto")?;
    Ok(())
}
