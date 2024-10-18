from Synthesizer import Synthesizer
import os
from contextlib import redirect_stdout
import multiprocessing
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from z3 import ForAll, Implies, Not, And, Or
from wp import verify
from syntax.while_lang import parse, remove_assertions_program
from SynthGUI_CEGIS_tab import *
from SynthGUI_PBE_tab import *

# Initialize the main window
root = tk.Tk()
root.title("While Language Synthesis")
root.geometry("800x900")  # Increased height to accommodate both input and output areas

# Create a Notebook for tabs
notebook = ttk.Notebook(root)
notebook.pack(pady=10, expand=True, fill="both")

# Frame for Program by Example (PBE)
pbe_frame = ttk.Frame(notebook, width=800, height=600)
pbe_frame.pack(fill="both", expand=True)

# Frame for Assertion-based Synthesis
assertion_frame = ttk.Frame(notebook, width=800, height=600)
assertion_frame.pack(fill="both", expand=True)

# Add the frames as tabs in the notebook
notebook.add(pbe_frame, text="Synthesize with PBE")
notebook.add(assertion_frame, text="Synthesize with Assertion")

# Add a label for the loop unrolling limit
loop_unrolling_label = tk.Label(root, text="Loop Unrolling Limit (for synthesis only):", font=("Helvetica", 12))
loop_unrolling_label.pack(pady=5)

# Create an entry widget for the loop unrolling limit with a default value of 10
loop_unrolling_entry = tk.Entry(root, font=("Helvetica", 12))
loop_unrolling_entry.insert(0, "10")  # Set default value
loop_unrolling_entry.pack(pady=5)


# ------------------------------
# Scrollable Text Widget Function
# ------------------------------

def create_scrollable_text(parent, height, width):
    frame = tk.Frame(parent)
    frame.pack(pady=10, fill=tk.BOTH, expand=True)

    # Create a Text widget
    text_widget = tk.Text(frame, height=height, width=width, font=("Helvetica", 12))
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Create a scrollbar
    scrollbar = tk.Scrollbar(frame, command=text_widget.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Configure the Text widget to use the scrollbar
    text_widget.config(yscrollcommand=scrollbar.set)

    return text_widget

# Create scrollable input text widget with reduced width
program_input = create_scrollable_text(root, height=7, width=80)  # Reduced width from 90 to 80

# Label for the output section
output_label = tk.Label(root, text="Synthesis Output", font=("Helvetica", 14))
output_label.pack(pady=10)

# Create scrollable output text widget with reduced width
output_text = create_scrollable_text(root, height=7, width=80)  # Reduced width from 90 to 80

# Insert initial text
output_text.config(state='normal')  # Temporarily make the output editable
output_text.insert('1.0', "Output program")  # Add initial text
output_text.config(state='disabled')  # Make the output non-editable again

# Add a section for error messages below the output_text
message_label = tk.Label(root, text="Messages:", font=("Helvetica", 12, "bold"))
message_label.pack(pady=10)

# message_text = create_scrollable_text(root, height=7, width=80)  # Reduced width from 90 to 80
# message_text.config(wrap='word', bg='lightgray')  # Wrap text at word boundaries

message_text = tk.Text(root, height=7, width=80, wrap='word', bg='lightgray')
message_text.pack(padx=20, pady=(0, 10))
message_text.config(state='disabled')  # Make the output non-editable again

# ------------------------------
# PBE Tab Layout
# ------------------------------

# Function to create the PBE tab labels and buttons
def create_pbe_tab():
    # Label for PBE tab
    pbe_label = tk.Label(pbe_frame, text="Program by Example Mode", font=("Helvetica", 14))  # Larger font size
    pbe_label.pack(pady=10)

    pbe_info = tk.Label(pbe_frame, text="Enter input-output examples to synthesize the program", font=("Helvetica", 12))
    pbe_info.pack(pady=5)

    # Add a button to set conditions for PBE
    add_condition_button = tk.Button(pbe_frame, text="Set Conditions (P, Q, Linv)", command = lambda : open_conditions_window(pbe))
    add_condition_button.pack(pady=5)
    # Add a tooltip with a description for the button
    toolTip = (
        "Click to open a window where you can set P, Q, and Loop Invariant (Linv) conditions.\n"
        "Note: for PBE, P will be used only for verification of the output program."
    )
    CreateToolTip(add_condition_button, toolTip)

    # Add a Button to open the examples window
    open_window_button = tk.Button(pbe_frame, text="Set Examples", command=lambda: set_examples_routine(pbe))
    open_window_button.pack(pady=10)

    # Add a button to trigger synthesis in the PBE mode
    synthesize_button = tk.Button(pbe_frame, text="Synthesize with PBE", command=lambda : process_pbe_program_input())
    synthesize_button.pack(pady=10)

    verify_program_button = tk.Button(pbe_frame, text="Verify output Program", state='disabled', command = lambda : verify_output_program(pbe))
    verify_program_button.pack(pady=10)

    return add_condition_button, verify_program_button

# Create buttons below the output window
add_condition_button_pbe, verify_program_button_pbe = create_pbe_tab()

# Placeholder for future PBE specific functionalities

# ------------------------------
# Assertion-based Tab Layout
# ------------------------------

# Function to create the CEGIS tab labels and buttons
def create_cegis_tab():

    # Label for Assertion tab
    assertion_label = tk.Label(assertion_frame, text="CEGIS Synthesis Mode", font=("Helvetica", 14))  # Larger font size
    assertion_label.pack(pady=10)

    # Add information label for the assertion mode
    assertion_info = tk.Label(assertion_frame, text="Define assertions to synthesize the program", font=("Helvetica", 12))
    assertion_info.pack(pady=5)

    # Add a button to set conditions for CEGIS
    add_condition_button = tk.Button(assertion_frame, text="Set Conditions (P, Q, Linv)", command = lambda : open_conditions_window(cegis))
    add_condition_button.pack(pady=5)
    # Add a tooltip with a description for the button
    toolTip = (
        "Click to open a window where you can set P, Q, and Loop Invariant (Linv) conditions"
    )
    CreateToolTip(add_condition_button, toolTip)

    # Add a button to trigger synthesis in the assertion mode
    synthesize_button = tk.Button(assertion_frame, text="Synthesize with Assertion", command=process_assertion_program_input)
    synthesize_button.pack(pady=20)

    # Create an IntVar to store the checkbox state (1 for checked, 0 for unchecked)
    interactive_var = tk.IntVar()
    interactive_var.set(1)  # Set the initial value to unchecked
    # Create a Checkbox for interactive mode
    interactive_checkbox = tk.Checkbutton(assertion_frame, text="Interactive", variable=interactive_var, command=show_selection)
    interactive_checkbox.pack(pady=0)

    verify_program_button = tk.Button(assertion_frame, text="Verify output Program", state='disabled', command = lambda : verify_output_program(cegis))
    verify_program_button.pack(pady=5)

    return add_condition_button, verify_program_button, interactive_var

# Create buttons below the output window
add_condition_button_cegis, verify_program_button_cegis, interactive_var = create_cegis_tab()

# Start the main GUI loop
if __name__ == "__main__":
    
    cegis.root = root
    cegis.message_text = message_text
    cegis.verify_program_button = verify_program_button_cegis
    cegis.interactive_var = interactive_var
    cegis.output_text = output_text
    cegis.loop_unrolling_entry = loop_unrolling_entry
    cegis.program_input = program_input

    pbe.root = root
    pbe.message_text = message_text
    pbe.verify_program_button = verify_program_button_pbe
    pbe.output_text = output_text
    pbe.loop_unrolling_entry = loop_unrolling_entry
    pbe.program_input = program_input

    root.mainloop()

    
    # safe_env = {
    #     'And': And, 'Or': Or, 'Implies': Implies, 'Not': Not, 'ForAll': ForAll
    # }

    # linv_str = "And(d['a'] == d['b'], d['a'] > 0)"
    # print(linv_str)

    # try:
    #     linv = eval("lambda d:" + linv_str, safe_env)  # Evaluate in the context of Z3 functions
    #     env = {'a': 2, 'b': 1}
    #     print(linv(env))
    # except Exception as e:
    #     print(f"Error: Invalid loop invariant. {e}")
