from math import pi, sin, cos, atan2, sqrt
import pandas as pd
import numpy as np
from importlib.resources import files



# VARIABLES
_ctg_element_branch_fields = ["BusNum", "BusNum:1", "LineCircuit", "BusName", "BusName:1", "LineXfmr"]
_ctg_element_field_list = ["CTGLabel", "Object", "Action", "FilterName", "TimeDelay"]
_updated_ctg_fields = "[" + ", ".join(f'"{item}"' for item in _ctg_element_field_list) + "]"
_overload_violation_fields = ["LimViolLimit", "LimViolValue"]
BRANCH_KEY_AND_REQUIRED_FIELDS = ["BusNum", "BusNum:1", "LineCircuit", "LineR", "LineX", "LineAMVA", "LineAMVA:1", "LineAMVA:2"]

# Get branch stats
# Read in branch stats and create voltage branch stat dictionary
def load_branch_stats():
    branch_stats_file_path = files("powerworld_tplan_tools.data").joinpath("branch_stats.csv")
    df = pd.read_csv(branch_stats_file_path)
    column_names = df.columns.tolist()
    branch_stat_list_of_lists = [df[column_names[i]].tolist() for i in range(len(column_names))]
    # Iterate through each voltage level, create list of all stats for the voltage level
    branchstats = {}  # keys: voltage as a float, values are a list of  branch stats
    for i in range(len(branch_stat_list_of_lists[0])):
        voltage = float(branch_stat_list_of_lists[0][i])
        stat_list = [branch_stat_list_of_lists[stat_number][i] for stat_number in range(len(branch_stat_list_of_lists))]
        branchstats[voltage] = stat_list
    return branchstats
_branchstats = load_branch_stats()



# FUNCTIONS
# Function to add a branch to the case
def add_branch_to_case(saw, branch_value_list, branch_fields_list = BRANCH_KEY_AND_REQUIRED_FIELDS):
    """
    Add a branch to a PowerWorld case.

    This function creates a new Branch object using PowerWorld's
    ``CreateData("Branch", ...)`` script command. The provided
    branch field names are automatically converted into the format
    required by PowerWorld script commands.

    By default, the function assumes that the values in
    ``branch_value_list`` correspond to the PowerWorld key and
    required fields contained in ``BRANCH_KEY_AND_REQUIRED_FIELDS``.
    Users may provide a custom field list when additional branch
    attributes need to be specified.

    Parameters
    ----------
    saw : SAW
        SimAutoWrapper object connected to a PowerWorld case.

    branch_value_list : list
        Values corresponding to the fields specified in
        ``branch_fields_list``.

        When using the default field list
        ``BRANCH_KEY_AND_REQUIRED_FIELDS``, values must be provided
        in the following order:

        - ``BusNum``: From-bus number.
        - ``BusNum:1``: To-bus number.
        - ``LineCircuit``: Circuit identifier.
        - ``LineR``: Series resistance (per unit).
        - ``LineX``: Series reactance (per unit).
        - ``LineAMVA``: Limit MVA A.
        - ``LineAMVA:1``: Limit MVA B.
        - ``LineAMVA:2``: Limit MVA C.

    branch_fields_list : list[str], optional
        List of branch field names corresponding to the values in
        ``branch_value_list``.

        Defaults to ``BRANCH_KEY_AND_REQUIRED_FIELDS``, which
        contains the minimum PowerWorld key and required fields
        needed to create a Branch object. This argument may be supplied
        positionally or as a keyword argument.

        Additional branch fields may be included as needed. Available
        branch fields can be viewed in PowerWorld by selecting
        Window → Export Display Object Fields and locating the
        Branch object field definitions.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        If the number of fields does not match the number of values.

    Notes
    -----
    The function automatically places PowerWorld in EDIT mode before
    creating the branch.

    Examples
    --------
    Create a branch using only the required fields:

    >>> add_branch_to_case(
    ...     saw,
    ...     [1001, 1002, "1", 0.01, 0.10, 100, 100, 100]
    ... )

    Create a branch with additional susceptance and conductance
    fields:

    >>> fields = (
    ...     BRANCH_KEY_AND_REQUIRED_FIELDS
    ...     + ["LineC", "LineG"]
    ... )
    >>> values = [
    ...     1001, 1002, "1",
    ...     0.01, 0.10,
    ...     100, 100, 100,
    ...     0.02, 0.00
    ... ]
    >>> add_branch_to_case(
    ...     saw,
    ...     values,
    ...     fields
    ... )
    """
    if len(branch_fields_list) != len(branch_value_list):
        raise ValueError(f"Received {len(branch_fields_list)} fields but "f"{len(branch_value_list)} values.")
    # Convert branch fields list so they are acceptable for PowerWorld script commands
    updated_branch_fields = "[" + ", ".join(f'"{item}"' for item in branch_fields_list) + "]"
    saw.RunScriptCommand("EnterMode(EDIT);")  # Set to edit mode
    updated_branch_value_list = "[" + ", ".join(f'"{item}"' if isinstance(item, str) else str(item) for item in branch_value_list) + "]"
    branch_command_string = f'CreateData("Branch", {updated_branch_fields}, {updated_branch_value_list});'
    saw.RunScriptCommand(branch_command_string)  # add line to case

# Function to delete a line from the case
def delete_branch_from_case(saw, branch_key_field_values):
    """
    Delete a branch from a PowerWorld case.

    Parameters
    ----------
    saw : SAW
        SimAutoWrapper object connected to a PowerWorld case.
    branch_key_field_values : list
        Branch identifier in the format:
        [from bus number, to bus number, circuit id].

    Returns
    -------
    None

    Notes
    -----
    The function automatically places PowerWorld in EDIT mode deleting
    creating the branch.
    """
    saw.RunScriptCommand("EnterMode(EDIT);")  # Set to edit mode
    deletion_command = 'DeleteDevice([Branch {} {} "{}"]);'.format(branch_key_field_values[0], branch_key_field_values[1], branch_key_field_values[2])
    saw.RunScriptCommand(deletion_command)  # delete the line

# Function to get total overload for all branch contingencies
def get_total_ctg_overload(saw, use_distributed = "NO"):
    """
    Calculate the total contingency overload for all branches in
    a PowerWorld case.

    This function automatically performs the following steps:

    1. Reads all branches currently in the case.
    2. Deletes all existing contingency elements.
    3. Creates an N-1 branch-outage contingency element for every branch.
    4. Clears all existing contingency results.
    5. Solves all contingencies using PowerWorld's
       ``CTGSolveAll`` command.
    6. Retrieves all contingency overload violations.
    7. Computes the total contingency overload by summing:

       ``MVA Flow - MVA Limit``

       for every violation where the monitored flow exceeds its
       corresponding limit.

    Parameters
    ----------
    saw : SAW
        SimAutoWrapper object connected to a PowerWorld case.

    use_distributed : str, default="NO"
        Specifies whether PowerWorld should use distributed
        contingency analysis when solving contingencies.

        Accepted values are:

        - ``"NO"``: Use standard contingency analysis.
        - ``"YES"``: Use distributed contingency analysis.

        Note that setting ``use_distributed="YES"`` does not
        automatically configure distributed computing. Distributed
        computing must already be properly configured within
        PowerWorld before this option can be used successfully.

    Returns
    -------
    float
        Total contingency overload in MVA, calculated as the sum of
        ``Flow - Limit`` across all contingency violations.

        A value of ``0`` indicates that no contingency overload
        violations were found.

    Raises
    ------
    ValueError
        If ``use_distributed`` is not equal to ``"YES"`` or ``"NO"``.

    Notes
    -----
    - All existing contingency elements in the case are deleted
      before new contingencies elements are created.
    - The contingencies generated by this function correspond to
      branch outage contingencies for every branch currently in the
      case.
    - Existing contingency results are cleared before solving.
    - Transformer contingencies and transmission line contingencies
      can both be included.

    Custom Contingency Sets
    -----------------------
    This function is designed to evaluate contingencies for all
    branches in the case. Users who wish to evaluate only a specific
    subset of contingencies should modify the contingency element creation
    section of the source code.

    The overload retrieval and overload summation logic can remain
    unchanged. Only the section responsible for creating contingency
    elements needs to be modified.

    Refer to the project's GitHub repository for implementation
    details and examples.

    Examples
    --------
    Solve all branch contingencies without distributed computing:

    >>> total_overload = get_total_ctg_overload(saw)

    Solve all branch contingencies using distributed computing:

    >>> total_overload = get_total_ctg_overload(
    ...     saw,
    ...     use_distributed="YES"
    ... )
    """
    if use_distributed not in {"YES", "NO"}:
        raise ValueError( f'use_distributed must be "YES" or "NO", not "{use_distributed}"')
    df_branch = saw.GetParametersMultipleElement("branch", _ctg_element_branch_fields)  # read in branch field values
    from_bus_nums = df_branch["BusNum"]
    to_bus_nums = df_branch["BusNum:1"]
    circuit_ids = df_branch["LineCircuit"]
    from_bus_names = [x.replace(" ", "") for x in df_branch["BusName"]]
    to_bus_names = [x.replace(" ", "") for x in df_branch["BusName:1"]]
    is_xf_list = df_branch["LineXfmr"]
    # Delete existing contingencies
    saw.RunScriptCommand("EnterMode(EDIT);")  # Set to edit mode
    saw.RunScriptCommand("Delete(Contingency);")  # delete base case and previously added contingencies
    # Create contingency elements
    for bn in range(len(from_bus_nums)):
        from_bus_num_leading_zeros = "{:06d}".format(from_bus_nums[bn])
        from_bus_name = from_bus_names[bn]
        to_bus_num_leading_zeros = "{:06d}".format(to_bus_nums[bn])
        to_bus_name = to_bus_names[bn]
        starting_letter = "T" if is_xf_list[bn] == "YES" else "L"
        ckt_id = circuit_ids[bn]

        ctg_label = f"{starting_letter}_{from_bus_num_leading_zeros}{from_bus_name}-{to_bus_num_leading_zeros}{to_bus_name}C{ckt_id}"
        ctg_object = f"BRANCH {from_bus_nums[bn]} {to_bus_nums[bn]} {ckt_id}"
        ctg_value_list = [ctg_label, ctg_object, "OPEN", "", 0]
        updated_value_list = "[" + ", ".join(f'"{item}"' if isinstance(item, str) else str(item) for item in ctg_value_list) + "]"
        command_string = f'CreateData("ContingencyElement", {_updated_ctg_fields}, {updated_value_list});'
        saw.RunScriptCommand(command_string)  # create contingency
    # Solve contingencies all at once
    saw.RunScriptCommand("CTGClearAllResults;")
    saw.RunScriptCommand(f'CTGSolveAll({use_distributed});')
    violation_value_list = saw.GetParametersMultipleElement("ViolationCTG", _overload_violation_fields)
    if violation_value_list is not None:
        violation_lims = violation_value_list["LimViolLimit"]
        violation_vals = violation_value_list["LimViolValue"]
        total_combined_overload = sum([violation_vals[ol] - violation_lims[ol] if violation_vals[ol] > violation_lims[ol] else 0 for ol in range(len(violation_lims))])
    else:
        total_combined_overload = 0

    return total_combined_overload

# Function to calculate straight-line geographic distance given two longitudes and latitudes in miles
def calc_haversine_distance(long1, lat1, long2, lat2, earth_radius_km = 6371):
    """
    Calculate the great-circle geographic distance between two
    locations using the Haversine formula.

    This function computes the great-circle distance between two points
    specified by longitude and latitude coordinates. The result is
    returned in miles.

    The Haversine formula accounts for the Earth's curvature and is
    therefore more accurate than applying Euclidean distance directly
    to longitude and latitude coordinates. Longitude and latitude are
    angular coordinates on the surface of a sphere, not Cartesian
    coordinates in a flat plane. As a result, the physical distance
    represented by one degree of longitude varies with latitude, and
    straight-line Euclidean calculations on geographic coordinates can
    produce significant errors, especially over longer distances.

    This function is intended to help estimate the length of candidate
    transmission lines between two buses. In PowerWorld, bus and substation coordaintes are the same.
    Users can provide the longitude and latitude coordinates of
    two substations to estimate the straight-line length of a candidate transmission line between them.
    Real transmission lines typically do not follow a perfectly straight path due to terrain,
    right-of-way constraints, environmental considerations, and other
    engineering requirements, so actual line lengths may be longer than
    the calculated distance.

    Parameters
    ----------
    long1 : float
        Longitude of the first location in decimal degrees.

    lat1 : float
        Latitude of the first location in decimal degrees.

    long2 : float
        Longitude of the second location in decimal degrees.

    lat2 : float
        Latitude of the second location in decimal degrees.

    earth_radius_km : float, default=6371
        Radius of the Earth in kilometers. The default value of 6371 km
        corresponds to the Earth's mean radius.

    Returns
    -------
    float
        Great-circle distance between the two locations in miles.

    Notes
    -----
    - Input coordinates must be provided in decimal degrees.
    - Internally, coordinates are converted from degrees to radians.
    - The returned distance represents the shortest path along the
      Earth's surface between the two locations.
    - Actual transmission line lengths are often greater than the
      calculated distance due to routing constraints.

    Examples
    --------
    Calculate the approximate straight-line distance between two
    substations:

    >>> distance = calc_haversine_distance(
    ...     -96.3344, 30.6279,
    ...     -95.3698, 29.7604
    ... )
    >>> print(distance)
    83.15

    Estimate the length of a candidate transmission line:

    >>> candidate_length = calc_haversine_distance(
    ...     bus_substation_1_longitude,
    ...     bus_substation_1_latitude,
    ...     bus_substation_2_longitude,
    ...     bus_substation_2_latitude
    ... )
    """
    long1_rad, lat1_rad = (long1 * pi) / 180, (lat1 * pi) / 180
    long2_rad, lat2_rad = (long2 * pi) / 180, (lat2 * pi) / 180
    dLong = long2_rad - long1_rad
    dLat = lat2_rad - lat1_rad
    a = pow(sin(.5 * dLat), 2) + cos(lat1_rad) * cos(lat2_rad) * pow(sin(.5 * dLong), 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance_km = earth_radius_km * c
    return distance_km / 1.609

# Candidate branch class
class Candidate:
    def __init__(self, fbus_list, tbus_list, circuit_id, fixed_cost_multiplier, kv=None):
        self.fbus_num = fbus_list[0]
        self.fbus_nom_kv = fbus_list[1]
        self.fbus_sub_num = fbus_list[2]

        self.tbus_num = tbus_list[0]
        self.tbus_nom_kv = tbus_list[1]
        self.tbus_sub_num = tbus_list[2]

        self.branches = None
        if kv is None:
            self.kv = self.fbus_num
            self.category = f"{int(self.kv)}_line" if self.kv == self.tbus_nom_kv  else "transformer"
        else:
            self.kv = kv
            self.category = "Line"
        self.su1 = self.fbus_sub_num
        self.su2 = self.tbus_sub_num

        self.id = circuit_id
        self.fixed_cost_multiplier = fixed_cost_multiplier

    def set_selection(self):
        if self.s2 > 80 and self.row_dist < 10:
            # self.select = True
            self.select = 1
        else:
            # self.select = False
            self.select = 0
        # self.sensitivities = [0,0]

    def branch_parameters(self, dist, kv=None):
        c = self
        c.row_dist = float(dist)
        is_xf = c.fbus_nom_kv != c.tbus_nom_kv
        if kv is None:
            kv = max(c.fbus_nom_kv, c.tbus_nom_kv)
        else:
            is_xf = False
        stats = _branchstats[kv]

        if is_xf:
            xmean, xmin, xmax, xrmean, xrmin, xrmax, smean, smin, smax = \
                stats[14], stats[13], stats[15], \
                    stats[17], stats[16], stats[18], \
                    stats[11], stats[10], stats[12]
            xsd = min(xmax - xmean, xmean - xmin) / 3.0
            x = max(xmin, min(xmax, np.random.normal(xmean, xsd)))
            xrsd = min(xrmax - xrmean, xrmean - xrmin) / 3.0
            r = x / max(xrmin, min(xrmax, np.random.normal(xrmean, xrsd)))
            s1 = np.random.triangular(smin, (smean + smin) / 2, smean)
            sleft, sright = max(smin, 2 * smean - smax), min(smax, 2 * smean - smin)
            s2 = np.random.triangular(sleft, smean, sright)
            s3 = np.random.triangular(smean, (smean + smax) / 2, smax)
            s1, s2, s3 = sorted([s1, s2, s3])
            c.x, c.r, c.b, c.s1, c.s2, c.s3 = round(x, 6), round(r, 5), 0, round(s1, 1), round(s2, 1), round(s3, 1)
        else:
            xmean, xmin, xmax, xrmean, xrmin, xrmax, smean, smin, smax = stats[5], stats[4], stats[6], stats[8], stats[7], stats[9], stats[2], stats[1], stats[3]
            xsd = min(xmax - xmean, xmean - xmin) / 3.0
            xdist = max(xmin, min(xmax, np.random.normal(xmean, xsd)))
            if dist < 10:  # Note: Distances are in MILES
                c.row_dist = 0.2 + dist * max(1.02, np.random.normal(1.3, 0.1))
            else:
                c.row_dist = dist * max(1.02, np.random.normal(1.12, 0.03))
            c.row_dist = round(c.row_dist, 2)
            x = xdist * c.row_dist
            vprop = np.random.triangular(0.95, 0.97, 0.98) * 299792.458  # Km/sec
            b = np.power(dist * 1.609334 * 2 * np.pi * 60 / vprop, 2) / x
            xrsd = min(xrmax - xrmean, xrmean - xrmin) / 3.0
            r = x / max(xrmin, min(xrmax, np.random.normal(xrmean, xrsd)))
            s1 = np.random.triangular(smin, (smean + smin) / 2, smean)
            sleft, sright = max(smin, 2 * smean - smax), min(smax, 2 * smean - smin)
            s2 = np.random.triangular(sleft, smean, sright)
            s3 = np.random.triangular(smean, (smean + smax) / 2, smax)
            s1, s2, s3 = sorted([s1, s2, s3])
            c.x, c.r, c.b, c.s1, c.s2, c.s3 = round(x, 6), round(r, 5), round(b, 5), round(s1, 1), round(s2,1), round(s3, 1)

        c.set_selection()

        # Calculate fixed cost
        c.fixed_cost = float(dist) * self.fixed_cost_multiplier

# Function to generate new candidate lines
def create_candidates(candidate_tuple_nums, bus_num_vals_dict, existing_branch_tuples, fixed_cost_multiplier = 1.25):
    """
    Generate candidate transmission lines between bus pairs.

    This function creates Candidate objects for a collection of
    candidate bus pairs. For each candidate pair, geographic distance
    is calculated using the Haversine formula and branch electrical
    parameters are estimated using voltage-dependent statistical
    distributions contained in the package's branch statistics data.

    Candidate circuit identifiers are assigned automatically using the
    format ``C1``, ``C2``, ``C3``, and so on. If candidate circuit
    identifiers already exist between a given bus pair, the next
    available candidate identifier is assigned.

    Parameters
    ----------
    candidate_tuple_nums : list[tuple[int, int]]
        List of candidate bus pairs.

        Each tuple contains:

        - From-bus number.
        - To-bus number.

        Example::

            [
                (1, 5),
                (1, 22),
                (35, 37)
            ]

    bus_num_vals_dict : dict
        Dictionary containing bus information keyed by bus number.

        Each bus entry must contain the following keys:

        - ``"nom_kv"``: Nominal bus voltage in kV.
        - ``"sub_long"``: Substation longitude in decimal degrees.
        - ``"sub_lat"``: Substation latitude in decimal degrees.
        - ``"sub_num"``: PowerWorld substation number.

        Example::

            {
                1: {
                    "nom_kv": 138.0,
                    "sub_long": -157.85,
                    "sub_lat": 21.31,
                    "sub_num": 1
                },
                2: {
                    "nom_kv": 138.0,
                    "sub_long": -157.90,
                    "sub_lat": 21.28,
                    "sub_num": 2
                }
            }

    existing_branch_tuples : list[tuple[int, int, str]]
        List of existing branches in the case.

        Each tuple must be in the format::

            (
                from_bus_num,
                to_bus_num,
                circuit_id
            )

        This information is used to determine the proper candidate
        circuit identifier for each generated candidate.

        Example::

            [
                (1, 2, "1"),
                (1, 2, "2"),
                (5, 7, "C1")
            ]

    fixed_cost_multiplier : float, default=1.25
        Multiplier used when estimating candidate fixed costs.

        Fixed cost is calculated as::

            fixed_cost = distance * fixed_cost_multiplier

        where distance is the great-circle geographic distance
        between the endpoint substations in miles.

    Returns
    -------
    list[Candidate]
        List of generated Candidate objects.

        Each Candidate object contains:

        - From-bus information.
        - To-bus information.
        - Circuit identifier.
        - Series resistance.
        - Series reactance.
        - Charging susceptance.
        - Thermal ratings.
        - Estimated fixed cost.
        - Geographic distance information.

    Notes
    -----
    - Geographic distances are calculated using
      ``calc_haversine_distance()``.
    - Electrical parameters are randomly sampled from statistical
      distributions derived from existing transmission and transformer
      data for the corresponding voltage level.
    - Candidate circuit identifiers are automatically assigned using
      the format ``C1``, ``C2``, ``C3``, etc.
    - Candidates whose calculated resistance or susceptance are
      effectively zero are excluded from the returned list.
    - Branch statistics are loaded automatically from the package's
      bundled ``branch_stats.csv`` file.

    Examples
    --------
    Generate candidate lines for all bus pairs in a PowerWorld case:

    >>> from esa import SAW
    >>> from itertools import combinations
    >>> import powerworld_tplan_tools as pwt
    >>>
    >>> case_path = r"C:\\Cases\\case.pwb"
    >>> saw = SAW(case_path)
    >>>
    >>> branch_fields = saw.get_key_field_list("Branch")
    >>> df_branch = saw.GetParametersMultipleElement(
    ...     "Branch",
    ...     branch_fields
    ... )
    >>>
    >>> existing_branch_tuples = [
    ...     (
    ...         df_branch["BusNum"][i],
    ...         df_branch["BusNum:1"][i],
    ...         df_branch["LineCircuit"][i].replace(" ", "")
    ...     )
    ...     for i in range(len(df_branch))
    ... ]
    >>>
    >>> bus_fields = (
    ...     saw.get_key_field_list("Bus")
    ...     + [
    ...         "BusNomVolt",
    ...         "Latitude:1",
    ...         "Longitude:1",
    ...         "SubNum"
    ...     ]
    ... )
    >>>
    >>> df_bus = saw.GetParametersMultipleElement(
    ...     "Bus",
    ...     bus_fields
    ... )
    >>>
    >>> bus_nums = df_bus["BusNum"].tolist()
    >>>
    >>> candidate_tuple_nums = list(
    ...     combinations(bus_nums, 2)
    ... )
    >>>
    >>> bus_num_vals_dict = {
    ...     bus_nums{
    ...         "nom_kv": df_bus["BusNomVolt"][i],
    ...         "sub_long": df_bus["Longitude:1"][i],
    ...         "sub_lat": df_bus["Latitude:1"][i],
    ...         "sub_num": df_bus["SubNum"][i]
    ...     }
    ...     for i in range(len(bus_nums))
    ... }
    >>>
    >>> candidates = pwt.create_candidates(
    ...     candidate_tuple_nums,
    ...     bus_num_vals_dict,
    ...     existing_branch_tuples
    ... )

    Example of accessing candidate information:

    >>> c = candidates[0]
    >>> c.fbus_num
    1
    >>> c.tbus_num
    5
    >>> c.id
    'C1'
    >>> c.fixed_cost
    12.7
    """
    # Create candidate pair circuit ID dict
    bus_pair_cand_circuit_id_list_dict = {}
    for from_bus_num, to_bus_num, circuit_id in existing_branch_tuples:
        bus_num_pair = (from_bus_num, to_bus_num)
        if circuit_id.startswith("C"):
            if bus_num_pair not in bus_pair_cand_circuit_id_list_dict.keys():
                bus_pair_cand_circuit_id_list_dict[bus_num_pair] = [int(circuit_id[1:])]
            else:
                bus_pair_cand_circuit_id_list_dict[bus_num_pair].append(int(circuit_id[1:]))

    # Create "empty" candidate lines. Then, calculate their parameters
    candidates_list = []
    for fbus_num, tbus_num in candidate_tuple_nums:
        fbus_val_dict = bus_num_vals_dict[fbus_num]
        tbus_val_dict = bus_num_vals_dict[tbus_num]

        # From bus values
        fbus_nom_kv = fbus_val_dict["nom_kv"]
        fbus_long = fbus_val_dict["sub_long"]
        fbus_lat = fbus_val_dict["sub_lat"]
        fbus_sub_num = fbus_val_dict["sub_num"]

        # To bus values
        tbus_nom_kv = tbus_val_dict["nom_kv"]
        tbus_long = tbus_val_dict["sub_long"]
        tbus_lat = tbus_val_dict["sub_lat"]
        tbus_sub_num = tbus_val_dict["sub_num"]

        # Create lists
        fbus_list = [fbus_num, fbus_nom_kv, fbus_sub_num]
        tbus_list = [tbus_num, tbus_nom_kv, tbus_sub_num]

        # Get circuit ID
        if (fbus_num, tbus_num) in bus_pair_cand_circuit_id_list_dict:
            max_ckt_num = max(bus_pair_cand_circuit_id_list_dict[(fbus_num, tbus_num)])
            circuit_id = f"C{max_ckt_num + 1}"
        else:
            circuit_id = "C1"

        # Create candidate
        c = Candidate(fbus_list, tbus_list, circuit_id, fixed_cost_multiplier)
        c.branch_parameters(calc_haversine_distance(fbus_long, fbus_lat, tbus_long, tbus_lat))

        if c.b > 1e-6 and c.r > 1e-8:  # make sure b isn't zero
            candidates_list.append(c)

    return candidates_list




