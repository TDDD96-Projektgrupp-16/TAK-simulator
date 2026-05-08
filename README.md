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

# Export scenario json schema
uv run scenario_schema > scenario.schema.json

# Run tests
uv run pytest tests/

# Run tests and report missing coverage
uv run pytest tests/ \
    --cov=src/tak_simulator \
    --cov-report=term-missing

# Install git hook
uv run pre-commit install

# Run formatter
./format.sh # Linux / Mac
./format.bat # Windows
```
