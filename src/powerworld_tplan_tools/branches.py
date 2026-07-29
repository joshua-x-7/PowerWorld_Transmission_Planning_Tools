
# VARIABLES
_ctg_element_branch_fields = ["BusNum", "BusNum:1", "LineCircuit", "BusName", "BusName:1", "LineXfmr"]
_ctg_element_field_list = ["CTGLabel", "Object", "Action", "FilterName", "TimeDelay"]
_updated_ctg_fields = "[" + ", ".join(f'"{item}"' for item in _ctg_element_field_list) + "]"
_overload_violation_fields = ["LimViolLimit", "LimViolValue"]



# FUNCTIONS
# Function to add a branch to the case
def add_branch_to_case(saw, updated_branch_fields, branch_value_list):
    saw.RunScriptCommand("EnterMode(EDIT);")  # Set to edit mode
    updated_branch_value_list = "[" + ", ".join(f'"{item}"' if isinstance(item, str) else str(item) for item in branch_value_list) + "]"
    branch_command_string = f'CreateData("Branch", {updated_branch_fields}, {updated_branch_value_list});'
    saw.RunScriptCommand(branch_command_string)  # add line to case

# Function to delete a line from the case
def delete_branch_from_case(saw, branch_key_field_values):
    saw.RunScriptCommand("EnterMode(EDIT);")  # Set to edit mode
    deletion_command = 'DeleteDevice([Branch {} {} "{}"]);'.format(branch_key_field_values[0], branch_key_field_values[1], branch_key_field_values[2])
    saw.RunScriptCommand(deletion_command)  # delete the line

# Function to get total overload without pre-adding contingencies
def get_total_ctg_overload(saw):
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
    saw.RunScriptCommand('CTGSolveAll(NO);')
    violation_value_list = saw.GetParametersMultipleElement("ViolationCTG", _overload_violation_fields)
    if violation_value_list is not None:
        violation_lims = violation_value_list["LimViolLimit"]
        violation_vals = violation_value_list["LimViolValue"]
        total_combined_overload = sum([violation_vals[ol] - violation_lims[ol] if violation_vals[ol] > violation_lims[ol] else 0 for ol in range(len(violation_lims))])
    else:
        total_combined_overload = 0

    return total_combined_overload
