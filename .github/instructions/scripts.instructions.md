---
applyTo: "scripts/**/*.sh"
---

# Shell Script Guidelines

## POSIX Compliance

All scripts must be POSIX-compliant for maximum portability:

```bash
#!/bin/bash

# Use POSIX-compatible syntax
# Avoid Bash-specific features unless absolutely necessary
```

**Guidelines**:
- Use `#!/bin/bash` shebang (not `#!/usr/bin/env bash`)
- Avoid Bash 4+ features (associative arrays, etc.)
- Test scripts with `shellcheck` if available
- Use standard POSIX utilities (avoid GNU-specific options)

## CRITICAL: Virtual Environment Handling

**CRITICAL RULE**: Scripts **MUST NOT** use `source .venv/bin/activate`. 

The virtual environment activation is lost between commands in stateless shells. All Python executables must be called with absolute paths.

### ❌ WRONG - Do Not Use

```bash
#!/bin/bash

# THIS WILL NOT WORK IN STATELESS ENVIRONMENTS
source .venv/bin/activate
python script.py  # Will use wrong Python!
pytest tests/     # Will use wrong pytest!
```

### ✅ CORRECT - Use Absolute Paths

```bash
#!/bin/bash

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Use absolute paths to virtual environment executables
PYTHON="$PROJECT_ROOT/.venv/bin/python"
PYTEST="$PROJECT_ROOT/.venv/bin/pytest"
PIP="$PROJECT_ROOT/.venv/bin/pip"

# Now run commands with correct executables
"$PYTHON" script.py
"$PYTEST" tests/ -v
"$PIP" install package
```

**Pattern**:
1. Calculate project root using `SCRIPT_DIR` and `PROJECT_ROOT`
2. Define variables for venv executables using absolute paths
3. Quote variables when using them (`"$PYTHON"` not `$PYTHON`)
4. Never assume venv is activated

## Script Structure

Follow consistent structure for all scripts:

```bash
#!/bin/bash

# Script: script_name.sh
# Purpose: Brief description of what this script does
# Usage: ./script_name.sh [arguments]

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'  # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to project root
cd "$PROJECT_ROOT"

# Define virtual environment executables
PYTHON="$PROJECT_ROOT/.venv/bin/python"
PYTEST="$PROJECT_ROOT/.venv/bin/pytest"

# Function definitions
function usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -h, --help     Show this help message"
    exit 1
}

function check_prerequisites() {
    if [ ! -f "$PYTHON" ]; then
        echo -e "${RED}Error: Virtual environment not found${NC}"
        echo "Run: python -m venv .venv"
        exit 1
    fi
}

# Main script logic
function main() {
    check_prerequisites
    
    # Script implementation
    "$PYTHON" script.py
    
    echo -e "${GREEN}✅ Operation complete${NC}"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
    shift
done

# Run main function
main "$@"
```

## Error Handling

Implement robust error handling:

```bash
set -e  # Exit immediately on error
set -u  # Treat unset variables as error
set -o pipefail  # Pipe failures cause script to fail

# Check for required files
if [ ! -f "$ENV_FILE" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    exit 1
fi

# Check command success
if ! "$PYTHON" script.py; then
    echo -e "${RED}Error: Script execution failed${NC}"
    exit 1
fi

# Cleanup on exit
trap cleanup EXIT
function cleanup() {
    # Clean up temporary files, connections, etc.
    rm -f /tmp/temp_file
}
```

## Output Formatting

Use consistent output formatting with colors:

```bash
# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# Usage
echo -e "${GREEN}✅ Success message${NC}"
echo -e "${RED}❌ Error message${NC}"
echo -e "${YELLOW}⚠️  Warning message${NC}"
echo -e "${BLUE}ℹ️  Info message${NC}"
```

## Command Execution

When executing commands, follow these patterns:

```bash
# Simple command execution
"$PYTHON" script.py

# Command with arguments
"$PYTEST" tests/ -v --cov=src

# Capture output
OUTPUT=$("$PYTHON" -c "import sys; print(sys.version)")

# Conditional execution
if "$PYTHON" script.py; then
    echo "Success"
else
    echo "Failed"
    exit 1
fi

# Silent execution
"$PYTHON" script.py > /dev/null 2>&1
```

## Testing Scripts

Scripts should be testable:

```bash
# Add dry-run mode
DRY_RUN=false

if [ "$DRY_RUN" = true ]; then
    echo "Would execute: $PYTHON script.py"
else
    "$PYTHON" script.py
fi

# Add verbose mode
VERBOSE=false

if [ "$VERBOSE" = true ]; then
    echo "Executing: $PYTHON script.py"
    "$PYTHON" script.py
else
    "$PYTHON" script.py > /dev/null
fi
```

## Terminal Resiliency

All scripts that produce output should follow the Terminal Resiliency Protocol:

```bash
# When calling from terminal, use redirect-and-cat pattern:
# ./script.sh > /tmp/copilot.out && cat /tmp/copilot.out

# Inside scripts, write to output directly
# The redirect pattern is applied when invoking the script
```

## Documentation

Document scripts with inline comments:

```bash
# Check if database is running before proceeding
if ! nc -z "$DB_HOST" "$DB_PORT"; then
    echo "Database not reachable"
    exit 1
fi

# Apply migrations in order
for migration in migrations/*.sql; do
    # Skip if already applied (check migrations table)
    "$PYTHON" check_migration.py "$migration" || continue
    
    # Apply migration
    psql -f "$migration"
done
```

## Common Patterns

### Path Calculation
```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
```

### Environment Variables
```bash
# Load from .env file
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi
```

### Argument Parsing
```bash
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done
```
