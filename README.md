# PowerWorld Transmission Planning Tools

A Python package for automating transmission expansion planning (TEP) tasks in PowerWorld Simulator.

This package provides functions for:

- Adding transmission branches to PowerWorld cases
- Deleting transmission branches from PowerWorld cases
- Performing N-1 contingency analysis and calculating total contingency overload
- Estimating distances between two points given their longitudes and latitudes
- Generating candidate transmission lines
- Estimating candidate electrical parameters and costs from statistical transmission system data

The package is intended for use with PowerWorld Simulator and ESA's SimAuto interface.

---

# Installation

```bash
pip install powerworld-tplan-tools
```

---

# Dependencies

Typical usage requires:

- PowerWorld Simulator
- ESA (Easy SimAuto)
- Python 3.x

Example:

```python
from esa import SAW

saw = SAW(r"path_to_case.pwb")
```

---

# Package Overview

The package focuses on common transmission expansion planning tasks:

1. Create and remove branches to a PowerWorld case.
2. Run N-1 contingency analysis, and get overloads
3. Generate candidate transmission lines.
4. Estimate line distances and costs.
5. Build transmission expansion planning workflows.

---

# API Reference

## add_branch_to_case()

Add a branch to a PowerWorld case.

### Function Signature

```python
add_branch_to_case(
    saw,
    branch_value_list,
    branch_fields_list=BRANCH_KEY_AND_REQUIRED_FIELDS
)
```

### Description

Creates a new PowerWorld Branch object using PowerWorld's
`CreateData("Branch")` script command.

The function automatically converts Python field lists into the
PowerWorld format required by script commands.

### Inputs

#### saw

An ESA SimAuto wrapper object.

---

#### branch_value_list

List of branch values corresponding to the fields specified in
`branch_fields_list`.

When using the default field list, values must be supplied in the
following order:

```python
[
    BusNum,
    BusNum:1,
    LineCircuit,
    LineR,
    LineX,
    LineAMVA,
    LineAMVA:1,
    LineAMVA:2
]
```

Example:

```python
[
    1001,
    1002,
    "1",
    0.01,
    0.10,
    100,
    100,
    100
]
```

which corresponds to:

```text
BusNum      = 1001
BusNum:1    = 1002
LineCircuit = "1"
LineR       = 0.01
LineX       = 0.10
LineAMVA    = 100
LineAMVA:1  = 100
LineAMVA:2  = 100
```

---

#### branch_fields_list (optional)

List of PowerWorld Branch field names.

Defaults to:

```python
BRANCH_KEY_AND_REQUIRED_FIELDS
```

```python
[
    "BusNum",
    "BusNum:1",
    "LineCircuit",
    "LineR",
    "LineX",
    "LineAMVA",
    "LineAMVA:1",
    "LineAMVA:2"
]
```

These are the minimum key and required fields needed by
PowerWorld to create a Branch object.

Additional fields can be supplied:

```python
fields = (
    pwt.BRANCH_KEY_AND_REQUIRED_FIELDS
    + ["LineC", "LineG"]
)
```

Available PowerWorld Branch fields can be viewed by selecting:

```text
Window → Export Display Object Fields
```

and locating the Branch object definition.

### Output

```python
None
```

The branch is added to the PowerWorld case.

### Example

Create a branch using only required fields:

```python
pwt.add_branch_to_case(
    saw,
    [
        1001,
        1002,
        "1",
        0.01,
        0.10,
        100,
        100,
        100
    ]
)
```

Create a branch with additional charging susceptance and conductance:

```python
fields = (
    pwt.BRANCH_KEY_AND_REQUIRED_FIELDS
    + ["LineC", "LineG"]
)

values = [
    1001,
    1002,
    "1",
    0.01,
    0.10,
    100,
    100,
    100,
    0.02,
    0.00
]

pwt.add_branch_to_case(
    saw,
    values,
    fields
)
```

---

## delete_branch_from_case()

Delete a branch from a PowerWorld case.

### Function Signature

```python
delete_branch_from_case(
    saw,
    branch_key_field_values
)
```

### Description

Deletes an existing branch using PowerWorld's
`DeleteDevice()` script command.

### Inputs

#### saw

A ESA SimAuto wrapper object.

---

#### branch_key_field_values

Branch identifier:

```python
[
    from_bus_num,
    to_bus_num,
    circuit_id
]
```

Example:

```python
[
    1001,
    1002,
    "1"
]
```

### Output

```python
None
```

The branch is removed from a PowerWorld case.

### Example

```python
pwt.delete_branch_from_case(
    saw,
    [1001, 1002, "1"]
)
```

---

## get_total_ctg_overload()

Calculate total N-1 contingency overload for all branches in a PowerWorld case.

### Function Signature

```python
get_total_ctg_overload(
    saw,
    use_distributed="NO"
)
```

### Description

This function automatically:

1. Reads all branches in the case.
2. Deletes all existing contingency elements.
3. Creates an N-1 branch outage contingency element for every branch.
4. Clears all previous contingency results.
5. Solves contingencies using PowerWorld's `CTGSolveAll()` command.
6. Retrieves all overload violations.
7. Calculates total contingency overload.

The metric returned is:

```text
Σ(MVA Flow − MVA Limit)
```

for all contingency violations.

### Inputs

#### saw

Connected ESA SimAuto object.

---

#### use_distributed

String specifying whether to use PowerWorld distributed contingency analysis.

Accepted values:

```python
"YES"
"NO"
```

Default:

```python
"NO"
```

Note:

```text
use_distributed="YES"
```

does NOT automatically configure distributed computing.

Distributed computing must already be configured within PowerWorld.

### Output

```python
float
```

Total contingency overload in MVA.

Example:

```python
523.4
```

means that the sum of all contingency overload violations equals
523.4 MVA.

### Important Notes

This function deletes all existing contingency elements before
creating new ones.

If a study requires a custom contingency set rather than all branch
contingencies, modify the contingency-element creation section of
the source code.

The overload retrieval and overload summation logic can remain
unchanged.

### Examples

Solve all contingencies:

```python
total_overload = pwt.get_total_ctg_overload(
    saw
)
```

Use distributed contingency analysis:

```python
total_overload = pwt.get_total_ctg_overload(
    saw,
    use_distributed="YES"
)
```

---

## calc_haversine_distance()

Calculate geographic great-circle distance between two points.

### Function Signature

```python
calc_haversine_distance(
    long1,
    lat1,
    long2,
    lat2,
    earth_radius_km=6371
)
```

### Description

Calculates great-circle distance using the Haversine formula.

Unlike Euclidean distance, the Haversine formula accounts for the
Earth's curvature and produces more realistic distances when using
longitude and latitude coordinates.

This function is intended to estimate candidate transmission line
lengths between substations/buses.

### Inputs

#### long1

Longitude of first point (decimal degrees).

#### lat1

Latitude of first point (decimal degrees).

#### long2

Longitude of second point (decimal degrees).

#### lat2

Latitude of second point (decimal degrees).

#### earth_radius_km

Earth radius in kilometers.

Default:

```python
6371
```

### Output

```python
float
```

Great-circle distance in miles

### Example
Estimate length of candidate line between Houston and College Station
using Haversine equation.

```python
distance = pwt.calc_haversine_distance(
    -96.3344,
    30.6279,
    -95.3698,
    29.7604
)

print(distance)
```

Output:

```text
83.15
```

### Transmission Planning Note

The returned value is a straight-line distance estimate.

Actual transmission line lengths are often longer due to:

- Terrain
- Environmental restrictions
- Rights-of-way
- Property boundaries
- Existing infrastructure

Therefore, users may want to multiply the estimated length
by a certain factor to simulate real-life candidate line lengths.
---

## create_candidates()

Generate candidate transmission lines between bus pairs.

### Function Signature

```python
create_candidates(
    candidate_tuple_nums,
    bus_num_vals_dict,
    existing_branch_tuples,
    fixed_cost_multiplier=1.25
)
```

### Description

Creates Candidate objects for a collection of bus pairs.

For each candidate, the package:

1. Calculates geographic distance.
2. Estimates line routing distance.
3. Estimates electrical parameters.
4. Estimates thermal ratings.
5. Assigns a candidate circuit identifier.
6. Calculates estimated fixed cost.

### Inputs

#### candidate_tuple_nums

List of candidate bus pairs.

Example:

```python
[
    (1, 5),
    (1, 22),
    (35, 37)
]
```

Each tuple is:

```python
(
    from_bus_num,
    to_bus_num
)
```

---

#### bus_num_vals_dict

Dictionary containing information about each bus
in the case that is being studied.

**Example structure only** (actual values will vary by case):

```python
{
    1: {
        "nom_kv": 138.0,
        "sub_long": -157.85,
        "sub_lat": 21.31,
        "sub_num": 1
    },

    2: {
        "nom_kv": 230.0,
        "sub_long": -157.90,
        "sub_lat": 21.28,
        "sub_num": 2
    }
}
```

Each bus entry must contain:

```python
{
    "nom_kv": ...,
    "sub_long": ...,
    "sub_lat": ...,
    "sub_num": ...
}
```

where:

```text
nom_kv    = nominal bus voltage (kV)
sub_long  = substation longitude
sub_lat   = substation latitude
sub_num   = substation number
```

---

#### existing_branch_tuples

List of existing branches.

Example:

```python
[
    (1, 2, "1"),
    (1, 2, "2"),
    (5, 7, "C1")
]
```

Each tuple must contain:

```python
(
    from_bus_num,
    to_bus_num,
    circuit_id
)
```

This information is used to assign candidate circuit identifiers.

---

#### fixed_cost_multiplier

Used to estimate candidate fixed cost.

Default:

```python
1.25
```

Fixed cost calculation:

```python
fixed_cost =
distance * fixed_cost_multiplier
```

### Output

```python
list[Candidate]
```

A list of generated Candidate objects.
### Candidate Attributes

Each generated `Candidate` object contains the following attributes:

```text
candidate.fbus_num      -> From-bus number
candidate.tbus_num      -> To-bus number

candidate.fbus_nom_kv   -> From-bus nominal voltage (kV)
candidate.tbus_nom_kv   -> To-bus nominal voltage (kV)

candidate.id            -> Candidate circuit identifier (e.g., "1", "2", "C1")

candidate.r             -> Series resistance (per unit)
candidate.x             -> Series reactance (per unit)
candidate.b             -> Charging susceptance (per unit)

candidate.s1 		-> Lower-end MVA rating, statistically generated
               		 using the minimum, average, and maximum MVA values
               		 for the candidate voltage level.

candidate.s2 		-> Typical MVA rating, statistically generated
               		 using the minimum, average, and maximum MVA values
                		for the candidate voltage level.

candidate.s3 		-> Upper-end MVA rating, statistically generated
                	using the minimum, average, and maximum MVA values
               		 for the candidate voltage level.

candidate.row_dist      -> Estimated transmission line right-of-way distance (miles)

candidate.fixed_cost    -> Estimated candidate fixed cost
```

### Example

```python
candidates = pwt.create_candidates(
    candidate_tuple_nums,
    bus_num_vals_dict,
    existing_branch_tuples
)
```

Access candidate information:

```python
c = candidates[0]

print(c.fbus_num)
print(c.tbus_num)

print(c.id)

print(c.r)
print(c.x)
print(c.b)

print(c.fixed_cost)
```

---

# Candidate Generation Methodology

Candidate electrical parameters are generated using voltage-dependent
statistical distributions derived from real transmission system data.

The package automatically loads:

```text
branch_stats.csv
```

and uses those statistics to estimate:

- Resistance (R)
- Reactance (X)
- Charging susceptance (B)
- Thermal ratings

Separate models are used for:

- Transmission lines
- Transformers

This allows realistic candidate parameters to be estimated using only
endpoint bus information.

---

# Typical Transmission Planning Workflow

```text
Read PowerWorld case
        ↓
Extract bus information
        ↓
Generate candidate bus pairs
        ↓
Create candidate lines
        ↓
Add candidates to case
        ↓
Run contingency analysis
        ↓
Calculate total contingency overload
        ↓
Evaluate candidate plan
        ↓
Repeat
```

---

# Future Examples

Additional example scripts and full workflows will be added to the
GitHub repository.

Planned examples may include:

- Reading PowerWorld cases
- Building bus dictionaries
- Generating candidate lines
- Adding candidate lines to a case
- Deleting branches
- Running contingency analysis
- Transmission expansion planning studies
- Candidate screening workflows

Repository:

https://github.com/joshua-x-7/PowerWorld_Transmission_Planning_Tools

---