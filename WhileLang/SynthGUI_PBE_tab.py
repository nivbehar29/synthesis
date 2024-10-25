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

        self.verify_program_button = None

        # Global variable to keep track of the conditions window
        self.conditions_window = None

        # Global variable to keep track of the conditions window
        self.examples_window = None

        # Variable to keep track if a verification process has been canceled or not
        self.verification_cancelled = False

pbe = PBE_Tab()

# ------------------------------
# Common Functions
# ------------------------------

def convert_examples_to_synthersizer_format(examples):
    synth_inputs = []
    synth_outputs = []
    for example in examples:
        synth_input = [(param, int(example[param][0])) for param in example if example[param][0] != '']
        synth_output = [(param, int(example[param][1])) for param in example if example[param][1] != '']
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

    if parameters != None:
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
    CreateToolTip(delete_button, tool_tips_dict["Delete_Example_Button"])

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

    description_text = (
        "Enter input-output examples for the program.\n"
        "Each example has its own row with input and output values for each parameter.\n"
        "For each parameter, the left input box is for the input value and the right input box is for the output value.\n"
        "Leave empty fields for unknown values.\n"
    )

    description_label = tk.Label(tab.examples_window, text=description_text, font=("Helvetica", 10))
    description_label.pack(pady=5)

    # Button to add a new example row
    add_button = tk.Button(tab.examples_window, text="Add Example", command=lambda: add_example(tab, example_frames, parameters))
    add_button.pack(pady=10)
    CreateToolTip(add_button, tool_tips_dict["Add_Example_Button"])

    # Button to save examples
    save_button = tk.Button(tab.examples_window, text="Save Examples", command=lambda: save_examples(example_frames, parameters))
    save_button.pack(pady=10)
    CreateToolTip(save_button, tool_tips_dict["Save_Examples_Button"])

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
        set_disabled_window_text_flash(tab.message_text, "Error: Invalid program. Please enter a valid program, and then set the examples.", True)
        return
    
    parameters = list(getPvars(ast))
    parameters.sort()
    print("parameters:", parameters)

    # get the parameters
    if parameters != tab.parameters:
        print("deifferent parameters - delete current examples")
        tab.parameters = parameters
        tab.examples = []

    open_examples_window(tab, tab.parameters, tab.examples)


# ------------------------------
# Synthesize PBE
# ------------------------------

def synth_program_pbe(program, P, Q, linv, inputs_examples, output_examples, debug=False, unroll_limit=10):
    returned_program = ""
    synth = Synthesizer(program)
    if not debug:
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f):
                for ex_in, ex_out in zip(inputs_examples, output_examples):
                    synth.add_io_example(ex_in, ex_out)
                returned_program = synth.synth_IO_program(program, synth.inputs, synth.outputs, P, Q, linv, unroll_limit, True)
    else:
        for ex_in, ex_out in zip(inputs_examples, output_examples):
            synth.add_io_example(ex_in, ex_out)
        returned_program = synth.synth_IO_program(program, synth.inputs, synth.outputs, P, Q,  linv, unroll_limit, True)

    return returned_program

def run_synthesis_pbe(program_text, queue, loop_unrolling_limit, inputs_examples, output_examples, P_str = None, Q_str = None, linv_str = None):

    P, Q, linv = eval_conditions(P_str, Q_str, linv_str)

    try:
        returned_program = synth_program_pbe(program_text, P, Q, linv, inputs_examples, output_examples, True, loop_unrolling_limit)
        queue.put(returned_program)
    except (Synthesizer.ProgramNotValid, Synthesizer.ProgramNotVerified, Synthesizer.ProgramHasNoHoles, Synthesizer.NoExamplesProvided,
            Synthesizer.ProgramHasInvalidVarName) as e:
        print("run_synthesis_cegis raised an exception:", e)
        queue.put(e)
    except Exception as e:
        queue.put(e)

def run_synthesis_pbe_no_process(program_text, loop_unrolling_limit, inputs_examples, output_examples, P_str = None, Q_str = None, linv_str = None):

    P, Q, linv = eval_conditions(P_str, Q_str, linv_str)

    returned_program = synth_program_pbe(program_text, P, Q, linv, inputs_examples, output_examples, True, loop_unrolling_limit)


# Function to cancel a process running in the background
def cancel_process_pbe(wait_window):
    global process_pbe

    if process_pbe and process_pbe.is_alive():
        print("Cancelling the process...")
        process_pbe.terminate()  # Terminate the child process
        process_pbe.join()  # Wait for it to finish
        print("Process terminated.")
    
    wait_window.destroy()  # Close the wait window

# Function to create the "Please Wait" window
def create_wait_window_pbe(root, wait_window_text, cancel_callback):
    # Show the "Please Wait" window
    wait_window = tk.Toplevel(root)
    wait_window.title("Please Wait")
    wait_window.geometry("300x100")
    wait_label = tk.Label(wait_window, text=wait_window_text, font=("Helvetica", 12))
    wait_label.pack(pady=20)

    cancel_button = tk.Button(wait_window, text="Cancel", command = lambda: cancel_callback(wait_window))
    cancel_button.pack(pady=10)

    return wait_window

def clear_output(tab: PBE_Tab):
    set_disabled_window_text(tab.output_text, "")
    tab.verify_program_button.config(state='disabled')  # Disable the button

# Function to handle the button press
def process_pbe_program_input():

    print("process_pbe_program_input")
    global process_pbe

    pbe.message_text.config(state='normal')  # Make output editable
    pbe.message_text.delete('1.0', tk.END)  # Clear previous output

    try:
        loop_unrolling_limit = int(pbe.loop_unrolling_entry.get())  # Try to convert to integer
    except Exception:
        set_disabled_window_text_flash(pbe.message_text, "Error: Loop unrolling limit must be an integer.", True)
        clear_output(pbe)
        return 

    program_text = pbe.program_input.get("1.0", tk.END).strip()  # Get text from input area

    # Check if the loop unrolling limit is less than 0
    if loop_unrolling_limit < 0:
        set_disabled_window_text_flash(pbe.message_text, "Error: Loop unrolling limit must be greater than or equal to 0.", True)
        clear_output(pbe)
        return

    # Check if the program is valid
    # Also check if the program has the same parameters as the examples
    try:
        ast = parse(program_text)
        if ast is None:
            set_disabled_window_text_flash(pbe.message_text, "Error: The given program can't be parsed", True)
            clear_output(pbe)
            return
    
        parameters = list(getPvars(ast))
        parameters.sort()

        if(pbe.parameters != [] and parameters != pbe.parameters):
            set_disabled_window_text_flash(pbe.message_text, "Error: The program has different parameters than the examples. Please set examples and then synthesize", True)
            clear_output(pbe)
            return
    except Exception as e:
        set_disabled_window_text_flash(pbe.message_text, f"Error: unexpected error: {e}", True)
        clear_output(pbe)
        return 

    # run_synthesis_pbe_no_process(program_text, loop_unrolling_limit, pbe.inputs_examples_synth_format, pbe.outputs_examples_synth_format, None, pbe.Q_str, pbe.linv_str)

    queue = multiprocessing.Queue()
    print(pbe.inputs_examples_synth_format)
    print(pbe.outputs_examples_synth_format)
    process_pbe = multiprocessing.Process(target = run_synthesis_pbe, args=(program_text, queue, loop_unrolling_limit, pbe.inputs_examples_synth_format, pbe.outputs_examples_synth_format, pbe.P_str, pbe.Q_str, pbe.linv_str))
    process_pbe.start()

    # Create a wait window which will be destroyed after the synthesis is done. Also pass it a callback function to cancel the synthesis
    wait_window = create_wait_window_pbe(pbe.root,"Please wait while synthesizing...", cancel_process_pbe)

    # Prevent pressing the main window while the wait window is open
    wait_window.grab_set()

    # Function to check the process status, waiting for it to finish and then display the result
    def check_process():

        if process_pbe.is_alive():
            # Schedule the next check after 100 ms
            pbe.root.after(100, check_process)
        else:
            print("check_process: process has finished.")
            # Code here will execute only after the process has finished

            # Close the wait window and display the result
            wait_window.destroy()

            if not queue.empty():

                # Get the result from the queue
                synth_result = queue.get()
                final_output = ""
                error = ""
                if isinstance(synth_result, Synthesizer.ProgramNotVerified):
                    error = "Error: The program can't be verified for the given input-output examples. If this is not the excpected outcome:\n"
                    error += "1. Try increasing the loop unrolling limit.\n"
                    error += "2. Check if the loop invariant is correct.\n"
                    error += "3. Check if the post-condition is correct.\n"
                    error += "4. Check that the examples do not contradict each other."
                elif isinstance(synth_result, Synthesizer.ProgramNotValid):
                    error = "Error: The given program can't be parsed"
                elif isinstance(synth_result, Synthesizer.ProgramHasNoHoles):
                    error = "Message: Program has no holes. You can try to verify your program."
                    final_output = program_text
                elif isinstance(synth_result, Synthesizer.ProgramHasInvalidVarName):
                    error = f"Error: Invalid variable name: {synth_result}.\nPlease use valid variable names which are not of the form 'hole_x', where x is a number."
                elif isinstance(synth_result, Synthesizer.NoExamplesProvided):
                    error = "Error: No input-output examples has been provided. Please set examples and then synthesize."
                elif isinstance(synth_result, Exception):
                    error = f"An unexpected error occurred: {synth_result}"
                else:
                    print("Synthesis result:", synth_result)
                    final_output = synth_result

                if(error != ""):
                    set_disabled_window_text_flash(pbe.message_text, error, True)
                    pbe.verify_program_button.config(state='disabled')  # Disable the button
                    clear_output(pbe)

                if(final_output != ""):
                    if(error == ""):
                        set_disabled_window_text_flash(pbe.message_text, "The program has been synthesized successfully", False)
                    set_disabled_window_text(pbe.output_text, remove_assertions_program(final_output))
                    pbe.verify_program_button.config(state='normal')  # Enable the button

    check_process()