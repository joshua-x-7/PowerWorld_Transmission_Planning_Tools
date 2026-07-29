
# VARIABLES
_ctg_element_branch_fields = ["BusNum", "BusNum:1", "LineCircuit", "BusName", "BusName:1", "LineXfmr"]
_ctg_element_field_list = ["CTGLabel", "Object", "Action", "FilterName", "TimeDelay"]
_updated_ctg_fields = "[" + ", ".join(f'"{item}"' for item in _ctg_element_field_list) + "]"
_overload_violation_fields = ["LimViolLimit", "LimViolValue"]
BRANCH_KEY_AND_REQUIRED_FIELDS = ["BusNum", "BusNum:1", "LineCircuit", "LineR", "LineX", "LineAMVA", "LineAMVA:1", "LineAMVA:2"]



# FUNCTIONS
# Function to add a branch to the case
def add_branch_to_case(saw, branch_fields_list, branch_value_list):
    """
    Add a branch to a PowerWorld case.

    This function creates a new Branch object using PowerWorld's
    ``CreateData("Branch", ...)`` script command. The provided
    branch field names are automatically converted into the format
    required by PowerWorld script commands.

    Parameters
    ----------
    saw : SAW
        SimAutoWrapper object connected to a PowerWorld case.

    branch_fields_list : list[str]
        List of branch field names corresponding to the values in
        ``branch_value_list``.

        At a minimum, this list must contain all PowerWorld key and
        required fields for a Branch object. These fields are provided
        by the package constant ``BRANCH_KEY_AND_REQUIRED_FIELDS``:

        - ``BusNum``: From-bus number.
        - ``BusNum:1``: To-bus number.
        - ``LineCircuit``: Circuit identifier.
        - ``LineR``: Series resistance (per unit).
        - ``LineX``: Series reactance (per unit).
        - ``LineAMVA``: Limit MVA A.
        - ``LineAMVA:1``: Limit MVA B.
        - ``LineAMVA:2``: Limit MVA C.

        Additional branch fields may also be included as needed.
        Available branch fields can be viewed in PowerWorld by using
        Window → Export Display Object Fields and locating the Branch
        object field definitions.

    branch_value_list : list
        Values corresponding to the fields in
        ``branch_fields_list``. The order of values must exactly
        match the order of the specified fields.

    Returns
    -------
    None

    Notes
    -----
    The function automatically places PowerWorld in EDIT mode before
    creating the branch.

    Examples
    --------
    Create a branch using only the required fields:

    >>> add_branch_to_case(
    ...     saw,
    ...     BRANCH_KEY_AND_REQUIRED_FIELDS,
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
    >>> add_branch_to_case(saw, fields, values)
    """
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

# Function to get total overload without pre-adding contingencies
def get_total_ctg_overload(saw, use_distributed):
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




