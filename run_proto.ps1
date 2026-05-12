# Define paths relative to the script location
$PROTO_SRC = "proto"
$OUTPUT_DIR = "src/tak_simulator/proto"

# Create the output directory if it doesn't exist
if (!(Test-Path $OUTPUT_DIR)) {
    New-Item -ItemType Directory -Force -Path $OUTPUT_DIR
}

# Run the uv command
# Note: We use Get-Item to resolve the wildcard for the proto files
uv run python-grpc-tools-protoc `
    --proto_path=$PROTO_SRC `
    --python_out=$OUTPUT_DIR `
    --pyi_out=$OUTPUT_DIR `
    (Get-Item "$PROTO_SRC/*.proto")