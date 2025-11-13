# Python Environment Setup

## System Prerequisites

Before setting up the Python environment, ensure you have the required system dependencies installed:

### PostgreSQL Client Tools

**Required for database setup, migrations, and management.**

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install -y postgresql-client

# Verify installation
psql --version  # Should show: psql (PostgreSQL) 16.x
```

**macOS:**
```bash
brew install postgresql

# Verify installation
psql --version
```

**Windows:**
- Install WSL2 and follow Ubuntu instructions, OR
- Download PostgreSQL from https://www.postgresql.org/download/windows/

---

## Recommended: venv (Python Virtual Environment)

This project uses Python's built-in `venv` module for virtual environment management.

### Why venv?
- ✓ Built into Python (no extra installation)
- ✓ Lightweight and fast
- ✓ Standard for production deployments
- ✓ Works seamlessly with pip and requirements.txt
- ✓ CI/CD friendly

---

## Quick Start

### 1. Create Virtual Environment

```bash
# Navigate to project root
cd ~/code/mas-memory-layer

# Create venv
python3 -m venv .venv

# Alternative: specify Python version explicitly
python3.11 -m venv .venv
```

### 2. Activate Virtual Environment

```bash
# On Linux/macOS
source .venv/bin/activate

# On Windows
.venv\Scripts\activate

# Verify activation (should show project path)
which python
```

### 3. Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install test dependencies (optional, for running tests)
pip install -r requirements-test.txt

# If you encounter build errors on Python 3.13:
# See docs/python-3.13-compatibility.md
```

### 4. Verify Installation

```bash
# Check installed packages
pip list

# Run smoke tests to verify infrastructure connectivity
./scripts/run_smoke_tests.sh --summary
```

---

## Daily Workflow

### Starting Work

```bash
# Activate environment
cd ~/code/mas-memory-layer
source .venv/bin/activate

# Verify you're in the right environment
which python  # Should show .venv/bin/python
```

### Ending Work

```bash
# Deactivate when done
deactivate
```

---

## Dependency Management

### Adding New Dependencies

```bash
# Install new package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt

# Better: manually add to requirements.txt with version pinning
echo "package-name==1.2.3  # Description of why needed" >> requirements.txt
```

### Updating Dependencies

```bash
# Update specific package
pip install --upgrade package-name

# Update all packages (use cautiously)
pip install --upgrade -r requirements.txt

# Update requirements.txt
pip freeze > requirements.txt
```

### Checking Outdated Packages

```bash
# List outdated packages
pip list --outdated

# Show dependency tree
pip install pipdeptree
pipdeptree
```

---

## Environment Reproducibility

### Exporting Environment

```bash
# Exact versions (for reproducibility)
pip freeze > requirements-frozen.txt

# Development environment
pip freeze > requirements-dev.txt
```

### Clean Installation

```bash
# Remove old environment
rm -rf .venv

# Create fresh environment
python3 -m venv .venv
source .venv/bin/activate

# Install from requirements
pip install -r requirements.txt
```

---

## Multiple Python Versions

If you need to test with different Python versions:

```bash
# Create environment with specific Python version
python3.11 -m venv .venv-py311
python3.12 -m venv .venv-py312

# Activate specific version
source .venv-py311/bin/activate
```

---

## VS Code Integration

VS Code should automatically detect the virtual environment.

### Manual Selection

1. Open Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P`)
2. Type "Python: Select Interpreter"
3. Choose `.venv/bin/python`

### Settings

Add to `.vscode/settings.json`:

```json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": [
        "tests",
        "-v"
    ]
}
```

---

## Troubleshooting

### Virtual Environment Not Activating

```bash
# Ensure venv module is available
python3 -m venv --help

# If missing on Ubuntu/Debian
sudo apt-get install python3-venv
```

### Wrong Python Version

```bash
# Check available Python versions
ls /usr/bin/python*

# Use specific version
/usr/bin/python3.11 -m venv .venv
```

### pip Not Found After Activation

```bash
# Recreate environment with --upgrade-deps
python3 -m venv .venv --upgrade-deps
source .venv/bin/activate
```

### Permission Errors

```bash
# Don't use sudo with pip in venv
# If you get permission errors, ensure venv is activated first
source .venv/bin/activate
pip install package-name  # No sudo needed
```

---

## Alternative: uv (Faster Package Manager)

For faster dependency installation, consider using `uv`:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv with uv
uv venv

# Install dependencies (much faster than pip)
uv pip install -r requirements.txt

# Sync dependencies
uv pip sync requirements.txt
```

---

## .gitignore Configuration

Ensure `.venv/` is in `.gitignore`:

```gitignore
# Virtual environments
.venv/
venv/
env/
ENV/

# Python cache
__pycache__/
*.py[cod]
*$py.class
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
        cache: 'pip'
    
    - name: Create virtual environment
      run: python -m venv .venv
    
    - name: Install dependencies
      run: |
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements-test.txt
    
    - name: Run tests
      run: |
        source .venv/bin/activate
        pytest tests/ -v
```

---

## When to Consider Conda

Consider switching to conda if you need:
- Complex scientific computing stack (numpy, scipy optimized builds)
- Non-Python system dependencies
- CUDA/GPU libraries
- Cross-platform binary reproducibility
- Environment management across multiple languages

---

## References

- [Python venv documentation](https://docs.python.org/3/library/venv.html)
- [pip documentation](https://pip.pypa.io/)
- [uv - Fast Python package installer](https://github.com/astral-sh/uv)
