# TAK Simulator

```sh
# Update environment
uv sync

# Generate protobufs
uv run python-grpc-tools-protoc \
    --proto_path=proto \
    --python_out=src/tak_simulator/proto \
    --pyi_out=src/tak_simulator/proto \
    proto/*.proto

# Run simulator
uv run tak_simulator examples/scenario.json
```
