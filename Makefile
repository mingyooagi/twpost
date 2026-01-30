.PHONY: install dev clean test help

# Default target
help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  install   Install dependencies via uv"
	@echo "  dev       Install with dev dependencies"
	@echo "  setup     Full setup (install + PATH hint)"
	@echo "  clean     Remove cache and build artifacts"
	@echo "  run       Run twpost (use: make run ARGS='your tweet')"

# Install dependencies
install:
	uv sync

# Install with dev dependencies
dev:
	uv sync --all-groups

# Full setup
setup: install
	@chmod +x twpost
	@echo ""
	@echo "Setup complete!"
	@echo "Add to PATH: export PATH=\"$(PWD):\$$PATH\""

# Run twpost
run:
	@./twpost $(ARGS)

# Clean build artifacts
clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
