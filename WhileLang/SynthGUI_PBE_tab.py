from Synthesizer import Synthesizer
import os
from contextlib import redirect_stdout
import multiprocessing
import tkinter as tk
from wp import getPvars
from syntax.while_lang import parse, remove_assertions_program
from SynthGUI_common import *

class PBE_Tab:
    def __init__(self):
        self.P = lambda d: True
        self.Q = lambda d: True
        self.linv = lambda d: True

        self.P_str = "True"
        self.Q_str = "True"
        self.linv_str = "True"

        self.loop_unrolling_entry = None
        self.examples = []
        self.parameters = []
        self.inputs_examples_synth_format = []
        self.outputs_examples_synth_format = []

        self.name = "PBE"
        self.root = None
        self.message_text : tk.Text = None
        self.output_text : tk.Text = None
        self.program_input : tk.Text = None

    # Global variable to keep track of the conditions window
    conditions_window = None

    # Global variable to keep track of the conditions window
    examples_window = None

pbe = PBE_Tab()

# ------------------------------
# Common Functions
# ------------------------------

def convert_examples_to_synthersizer_format(examples):
    synth_inputs = []
    synth_outputs = []
    for example in examples:
        synth_input = [(param, example[param][0]) for param in example]
        synth_output = [(param, example[param][1]) for param in example]
        synth_inputs.append(synth_input)
        synth_outputs.append(synth_output)

    return synth_inputs, synth_outputs


def is_int(value):
    try:
        value = int(value)  # Try to convert to integer
        return True
    except Exception:
        return False

# ------------------------------
# Examples Window
# ------------------------------

def verify_input_output(examples, parameters):
    # Check for each parameter that its input and output values are integers or '' (empty string)
    example_num = 1
    for example in examples:
        for param in parameters:
            input_value = example[param][0]
            output_value = example[param][1]
            if input_value and not (is_int(input_value) or input_value == ''):
                return False, "Input value for parameter '{}', in example '{}' is not a number or an empty string.".format(param, example_num)
            if output_value and not (is_int(output_value) or output_value == ''):
                return False, "Input value for parameter '{}', in example '{}' is not a number or an empty string.".format(param, example_num)     
        example_num += 1
        
    return True, None

def save_examples(example_frames, parameters):
    examples = []
    for frame in example_frames:
        example = {}
        for param in parameters:
            input_value = frame["input_vars"][param].get()
            output_value = frame["output_vars"][param].get()
            example[param] = (input_value, output_value)
        examples.append(example)
    print(examples)  # For testing, print the saved examples

    # Verify the input/output values
    is_verified, error = verify_input_output(examples, parameters)
    print("is_verified:", ("False, Error: " + error) if not is_verified else "True")

    if is_verified:
        pbe.examples = examples
        pbe.inputs_examples_synth_format, pbe.outputs_examples_synth_format = convert_examples_to_synthersizer_format(examples)
        print("pbe.inputs_examples_synth_format:", pbe.inputs_examples_synth_format)
        print("pbe.outputs_examples_synth_format:", pbe.outputs_examples_synth_format)
        set_disabled_window_text_flash(pbe.message_text, "Examples saved successfully.", False)
    else:
        set_disabled_window_text_flash(pbe.message_text, "Error: " + error, True)

def add_example(tab: PBE_Tab, example_frames, parameters, existing_example=None):
    # Create a frame to hold input/output fields for a new example
    example_frame = tk.Frame(tab.examples_window)
    example_frame.pack(pady=5)

    input_entry_vars = {}
    output_entry_vars = {}

    for param in parameters:
        tk.Label(example_frame, text=param).pack(side=tk.LEFT, padx=5)

        input_var = tk.Entry(example_frame, width=5)
        input_var.pack(side=tk.LEFT, padx=5)
        output_var = tk.Entry(example_frame, width=5)
        output_var.pack(side=tk.LEFT, padx=5)

        input_entry_vars[param] = input_var
        output_entry_vars[param] = output_var

        # Populate fields if existing example is provided
        if existing_example:
            input_value, output_value = existing_example.get(param, ('', ''))
            input_var.insert(0, input_value)
            output_var.insert(0, output_value)

    # Add delete button for each example
    delete_button = tk.Button(example_frame, text="Delete", command=lambda: delete_example(example_frames, example_frame))
    delete_button.pack(side=tk.LEFT, padx=5)

    # Store the variables for later use
    example_frames.append({
        "frame": example_frame,
        "input_vars": input_entry_vars,
        "output_vars": output_entry_vars
    })

def delete_example(example_frames, example_frame):
    # Remove the example frame and its associated variables
    example_frames.remove(next(frame for frame in example_frames if frame["frame"] == example_frame))
    example_frame.destroy()

def open_examples_window(tab: PBE_Tab, parameters, current_examples=None):
    # Check if the window is already open
    if tab.examples_window is not None and tab.examples_window.winfo_exists():
        tab.examples_window.lift()  # Bring the existing window to the front
        return

    tab.examples_window = tk.Toplevel(tab.root)
    tab.examples_window.title("Set Examples")

    example_frames = []

    # Button to add a new example row
    add_button = tk.Button(tab.examples_window, text="Add Example", command=lambda: add_example(tab, example_frames, parameters))
    add_button.pack(pady=10)

    # Button to save examples
    save_button = tk.Button(tab.examples_window, text="Save Examples", command=lambda: save_examples(example_frames, parameters))
    save_button.pack(pady=10)

    # Load existing examples if they are provided
    if current_examples:
        for example in current_examples:
            add_example(tab, example_frames, parameters, existing_example=example)
    else:
        # Add an initial empty example
        add_example(tab, example_frames, parameters)

def set_examples_routine(tab: PBE_Tab):

    # Get the program input
    program = tab.program_input.get("1.0", tk.END).strip()
    
    # First try to parse the program
    ast = parse(program)
    if ast is None:
        set_disabled_window_text_flash(tab.message_text, "Error: Invalid program. Please enter a valid program.", True)
        return
    
    parameters = getPvars(ast)

    # get the parameters
    if parameters != tab.parameters:
        print("deifferent parameters - delete current examples")
        tab.parameters = getPvars(ast)
        tab.examples = []

    open_examples_window(tab, tab.parameters, tab.examples)