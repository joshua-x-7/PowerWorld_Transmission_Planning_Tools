from esa import SAW


# Function to add a branch to the case
def add_branch_to_case(saw, updated_branch_fields, branch_value_list):
    saw.RunScriptCommand("EnterMode(EDIT);")  # Set to edit mode
    updated_branch_value_list = "[" + ", ".join(f'"{item}"' if isinstance(item, str) else str(item) for item in branch_value_list) + "]"
    branch_command_string = f'CreateData("Branch", {updated_branch_fields}, {updated_branch_value_list});'
    saw.RunScriptCommand(branch_command_string)  # add line to case

