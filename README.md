# TAK Simulator

```sh
# Update environment
uv sync --locked && uv build

# Run simulator
uv run tak_simulator

# Run simulator with file specified
uv run tak_simulator --filename  examples/scenario.json

# Run simulator headless
uv run tak_simulator --notui --filename  examples/scenario.json

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
