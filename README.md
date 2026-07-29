# PowerWorld Transmission Planning Tools

PowerWorld Transmission Planning Tools is a Python package that simplifies automation of common transmission planning workflows in PowerWorld Simulator through SimAuto or the ESA (Easy Sim Auto) interface.

The package provides high-level functions for tasks frequently encountered in transmission planning studies, allowing users to focus on analysis rather than low-level SimAuto/ESA coding.

## Current Features

- Add new transmission branches to a PowerWorld case
- Delete existing transmission branches
- Run contingency analysis and get thermal overloads

## Installation

```bash
python -m pip install powerworld-tplan-tools
```

## Intended Use

This package is designed for transmission planners, power system engineers, researchers, and students who use PowerWorld Simulator for:

- Transmission expansion planning
- N-1 contingency analysis
- Planning study automation

## Example

```python
from powerworld_tplan_tools import branches

# Add a new transmission line
branches.add_branch(...)

# Remove an existing line
branches.delete_branch(...)

```

## Requirements

- PowerWorld Simulator
- ESA (Easy Sim Auto)
- Python 3.10+

## Project Status

This project is under active development. Additional transmission planning utilities and workflow automation tools will be added in future releases.