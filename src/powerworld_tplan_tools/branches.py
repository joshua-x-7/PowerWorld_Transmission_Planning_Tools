
# VARIABLES
_ctg_element_branch_fields = ["BusNum", "BusNum:1", "LineCircuit", "BusName", "BusName:1", "LineXfmr"]
_ctg_element_field_list = ["CTGLabel", "Object", "Action", "FilterName", "TimeDelay"]
_updated_ctg_fields = "[" + ", ".join(f'"{item}"' for item in _ctg_element_field_list) + "]"
_overload_violation_fields = ["LimViolLimit", "LimViolValue"]
BRANCH_KEY_AND_REQUIRED_FIELDS = ["BusNum", "BusNum:1", "LineCircuit", "LineR", "LineX", "LineAMVA", "LineAMVA:1", "LineAMVA:2"]



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




