from Synthesizer import Synthesizer
import os
from contextlib import redirect_stdout
import multiprocessing
import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from z3 import ForAll, Implies, Not, And, Or
from wp import verify
from syntax.while_lang import parse, remove_assertions_program

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

# Label for PBE tab
pbe_label = tk.Label(pbe_frame, text="Program by Example Mode", font=("Helvetica", 14))  # Larger font size
pbe_label.pack(pady=10)

# You can add specific widgets or buttons related to PBE here
pbe_info = tk.Label(pbe_frame, text="Enter input-output examples to synthesize the program", font=("Helvetica", 12))
pbe_info.pack(pady=5)

# Placeholder for future PBE specific functionalities

# ------------------------------
# Assertion-based Tab Layout
# ------------------------------

class CEGIS_Tab:
    def __init__(self):
        self.P = lambda d: True
        self.Q = lambda d: True
        self.linv = lambda d: True

        self.P_str = "True"
        self.Q_str = "True"
        self.linv_str = "True"

    # Global variable to keep track of the conditions window
    conditions_window = None

cegis = CEGIS_Tab()



# Create a button to confirm a condition
def reset_condition(cond_type : str, input_window):
    message_text.config(state='normal')  # Make output editable
    message_text.delete('1.0', tk.END)  # Clear previous output
    message_text.insert("1.0", f"{cond_type}: \"True\" has been set successfully.\n")
    message_text.config(state='disabled')  # Make the output non-editable again

    input_window.delete('1.0', tk.END)  # Clear previous condition
    input_window.insert("1.0", "True")  # Set new condition

    if(cond_type == "Pre-Condition"):
        cegis.P = lambda _: True
        cegis.P_str = "True"
    elif(cond_type == "Post-Condition"):
        cegis.Q = lambda _: True
        cegis.Q_str = "True"
    elif(cond_type == "Loop-Invariant"):
        cegis.linv = lambda _: True
        cegis.linv_str = "True"

# Create a button to confirm a condition
def set_condition(cond_text, cond_type : str):
    cond = None
    # cond_text = input.get("1.0", tk.END).strip()

    # Try to evaluate the loop invariant using eval() in a safe environment
    safe_env = {
        'And': And, 'Or': Or, 'Implies': Implies, 'Not': Not, 'ForAll': ForAll
    }

    message_text.config(state='normal')  # Make output editable
    message_text.delete('1.0', tk.END)  # Clear previous output

    try:
        cond = eval("lambda d: " + cond_text, safe_env)  # Evaluate in Z3 context
        message_text.insert("1.0", f"{cond_type}: \"{cond_text}\" has been set successfully.\n")
    except Exception as e:
        message_text.insert("1.0", f"Error: Invalid {cond_type}: {e}\n")
        
    message_text.config(state='disabled')  # Make the output non-editable again

    if(cond != None):
        if(cond_type == "Pre-Condition"):
            cegis.P = cond
            cegis.P_str = cond_text
        elif(cond_type == "Post-Condition"):
            cegis.Q = cond
            cegis.Q_str = cond_text
        elif(cond_type == "Loop-Invariant"):
            cegis.linv = cond
            cegis.linv_str = cond_text

def open_conditions_window():
    # Check if the window is already open
    if cegis.conditions_window is not None and cegis.conditions_window.winfo_exists():
        cegis.conditions_window.lift()  # Bring the existing window to the front
        return

    # Create a new window
    cegis.conditions_window = Toplevel(root)
    cegis.conditions_window.title("Add Loop Invariant")
    cegis.conditions_window.geometry("600x400")
    # conditions_window.grab_set()


    # --- Loop-Invariant Section ---

    # Create a label for the invariant input
    label_linv = tk.Label(cegis.conditions_window, text="Loop-Invariant:")
    label_linv.place(x=5, y=30)  # Set the position of the label (x, y)

    # Create a text input for the loop invariant
    invariant_input = tk.Text(cegis.conditions_window, height=5, width=40)
    invariant_input.place(x=120, y=10)  # Set the position of the text input (x, y)
    invariant_input.insert('1.0', cegis.linv_str)  # Add initial text

    # Create a button to set the loop-invariant
    set_linv_button = tk.Button(cegis.conditions_window, text="Set Loop Invariant", command=lambda: set_condition(invariant_input.get("1.0", tk.END).strip(), "Loop-Invariant"))
    set_linv_button.place(x = 450, y=30)  # Set the position of the button (x, y)

    # Create a button to reset the loop-invariant
    reset_linv_button = tk.Button(cegis.conditions_window, text="Reset Loop Invariant", command=lambda: reset_condition("Loop-Invariant", invariant_input))
    reset_linv_button.place(x = 450, y=60)  # Set the position of the button (x, y)

    # --- Pre-Condition Section ---

    # Create a label for the pre-condition input
    label_pre = tk.Label(cegis.conditions_window, text="Pre-Condition:")
    label_pre.place(x=5, y=150)  # Set the position of the label (x, y)

    # Create a text input for the pre-condition
    precondition_input = tk.Text(cegis.conditions_window, height=5, width=40)
    precondition_input.place(x=120, y=130)  # Set the position of the text input (x, y)
    precondition_input.insert('1.0', cegis.P_str)  # Add initial text (if applicable)

    # Create a button to set the pre-condition
    set_pre_button = tk.Button(cegis.conditions_window, text="Set Pre-Condition", command=lambda: set_condition(precondition_input.get("1.0", tk.END).strip(), "Pre-Condition"))
    set_pre_button.place(x=450, y=150)  # Set the position of the button (x, y)

    # Create a button to reset the pre-condition
    reset_pre_button = tk.Button(cegis.conditions_window, text="Reset Pre-Condition", command=lambda: reset_condition("Pre-Condition", precondition_input))
    reset_pre_button.place(x = 450, y=180)  # Set the position of the button (x, y)

    # --- Post-Condition Section ---

    # Create a label for the post-condition input
    label_post = tk.Label(cegis.conditions_window, text="Post-Condition:")
    label_post.place(x=5, y=270)  # Set the position of the label (x, y)

    # Create a text input for the post-condition
    post_condition_input = tk.Text(cegis.conditions_window, height=5, width=40)
    post_condition_input.place(x=120, y=250)  # Set the position of the text input (x, y)
    post_condition_input.insert('1.0', cegis.Q_str)

    # Create a button to set the post-condition
    set_post_button = tk.Button(cegis.conditions_window, text="Set Post-Condition", command=lambda: set_condition(post_condition_input.get("1.0", tk.END).strip(), "Post-Condition"))
    set_post_button.place(x=450 + 5, y=270)  # Set the position of the button (x, y)

    # Create a button to reset the post-condition
    reset_post_button = tk.Button(cegis.conditions_window, text="Reset Post-Condition", command=lambda: reset_condition("Post-Condition", post_condition_input))
    reset_post_button.place(x = 450, y=300)  # Set the position of the button (x, y)


def eval_conditions(P_str, Q_str, linv_str):
    P = lambda _: True
    Q = lambda _: True
    linv = lambda _: True

    safe_env = {
        'And': And, 'Or': Or, 'Implies': Implies, 'Not': Not, 'ForAll': ForAll
    }

    if P_str != None:
        P = eval("lambda d:" + P_str, safe_env)
    
    if Q_str != None:
        Q = eval("lambda d:" + Q_str, safe_env)

    if linv_str != None:
        linv = eval("lambda d:" + linv_str, safe_env)

    return P, Q, linv

def synth_program(program, P, Q, linv, debug=False, unroll_limit=10):
    returned_program = ""
    synth = Synthesizer(program)
    if not debug:
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f):
                returned_program = synth.synth_program(program, P, Q, linv, None, None, unroll_limit)
    else:
        returned_program = synth.synth_program(program, P, Q, linv, None, None, unroll_limit)

    return returned_program

def run_synthesis(program_text, queue, loop_unrolling_limit, P_str = None, Q_str = None, linv_str = None):

    P, Q, linv = eval_conditions(P_str, Q_str, linv_str)

    try:
        returned_program = synth_program(program_text, P, Q, linv, True, loop_unrolling_limit)

        print("Synthesis successful.")
        queue.put(returned_program)
    except (Synthesizer.ProgramNotValid, Synthesizer.ProgramNotVerified) as e:
        queue.put(e)
    except Exception as e:
        queue.put(e)

def verify_program(program_text, P, Q, linv, debug=False):
    if not debug:
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f):
                ast = parse(program_text)
                is_verified, solver = verify(P, ast, Q, linv)
    else:
        ast = parse(program_text)
        is_verified, solver = verify(P, ast, Q, linv)

    counter_ex = ""
    if is_verified != True:
        counter_ex = solver.model()

    return is_verified, counter_ex

def run_verifier(program_text, queue, P_str = None, Q_str = None, linv_str = None):
    try:
        P, Q, linv = eval_conditions(P_str, Q_str, linv_str)
        is_verified, counter_ex = verify_program(program_text, P, Q, linv, True)

        if is_verified:
            queue.put(">> The program is verified.")
        else:
            queue.put(">> The program is NOT verified.\nCounterexample: " + str(counter_ex))

    except Exception as e:
        queue.put(e)

# Function to cancel a process running in the background
def cancel_process(wait_window):
    global process

    if process and process.is_alive():
        print("Cancelling the process...")
        process.terminate()  # Terminate the child process
        process.join()  # Wait for it to finish
        print("Process terminated.")
    
    wait_window.destroy()  # Close the wait window

def create_wait_window(wait_window_text, callback):
    # Show the "Please Wait" window
    wait_window = tk.Toplevel(root)
    wait_window.title("Please Wait")
    wait_window.geometry("300x100")
    wait_label = tk.Label(wait_window, text=wait_window_text, font=("Helvetica", 12))
    wait_label.pack(pady=20)

    cancel_button = tk.Button(wait_window, text="Cancel", command = lambda: callback(wait_window))
    cancel_button.pack(pady=10)

    return wait_window

# Function to handle the button press
def process_assertion_program_input():

    global process

    message_text.config(state='normal')  # Make output editable
    message_text.delete('1.0', tk.END)  # Clear previous output
  
    try:
        loop_unrolling_limit = int(loop_unrolling_entry.get())  # Try to convert to integer
    except Exception:
        message_text.insert("1.0", "Error: Loop unrolling limit must be an integer.")  # Display error message
        message_text.config(state='disabled')  # Make it non-editable again
        return 

    program_text = program_input.get("1.0", tk.END).strip()  # Get text from input area

    # Check if the loop unrolling limit is less than 0
    if loop_unrolling_limit < 0:
        message_text.insert("1.0", "Error: Loop unrolling limit must be greater than or equal to 0.")  # Display error message
        message_text.config(state='disabled')  # Make it non-editable again
        return

    # Create a wait window which will be destroyed after the synthesis is done. Also pass it a callback function to cancel the synthesis
    wait_window = create_wait_window("Please wait while synthesizing...", cancel_process)

    # Prevent pressing the main window while the wait window is open
    wait_window.grab_set()

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target = run_synthesis, args=(program_text, queue, loop_unrolling_limit, cegis.P_str, cegis.Q_str, cegis.linv_str))
    process.start()

    # Function to check the process status, waiting for it to finish and then display the result
    def check_process():

        if process.is_alive():
            # Schedule the next check after 100 ms
            root.after(100, check_process)
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
                # output_text.insert("1.0", f"Error: {str(result)}")
                if isinstance(synth_result, Synthesizer.ProgramNotValid):
                    error = "Error: The given program can't be parsed"
                elif isinstance(synth_result, Synthesizer.ProgramHasNoHoles):
                    error = "Message: Program has no holes. You can try to verify your program."
                    print("synthesis result:", program_text)
                    final_output = remove_assertions_program(program_text)
                elif isinstance(synth_result, Synthesizer.ProgramNotVerified):
                    error = "Error: The program can't be verified for all possible inputs. If this is not the excpected outcome:\n "
                    error += "1. Try increasing the loop unrolling limit.\n"
                    error += "2. Check if the loop invariant is correct.\n"
                    error += "3. Check if the pre-condition and post-condition are correct."
                elif isinstance(synth_result, Exception):
                    error = f"An unexpected error occurred: {synth_result}"
                else:
                    print("synthesis result:", synth_result)
                    final_output = remove_assertions_program(synth_result)

                if(error != ""):
                    message_text.config(state='normal')  # Make output editable
                    message_text.delete('1.0', tk.END)  # Clear previous output
                    message_text.insert("1.0", error)  # Display the synthesized program
                    message_text.config(state='disabled')  # Make the output non-editable again
                    verify_program_button.config(state='disabled')  # Enable the button
                    output_text.config(state='normal')  # Make output editable
                    output_text.delete('1.0', tk.END)  # Clear previous output
                    output_text.config(state='disabled')  # Make the output non-editable again
                if(final_output != ""):
                    output_text.config(state='normal')  # Make output editable
                    output_text.delete('1.0', tk.END)  # Clear previous output
                    output_text.insert("1.0", final_output)  # Display the synthesized program
                    output_text.config(state='disabled')  # Make the output non-editable again
                    verify_program_button.config(state='normal')  # Enable the button


    check_process()

def verify_output_program():
    global process

    message_text.config(state='normal')  # Make output editable
    message_text.delete('1.0', tk.END)  # Clear previous output

    program_text = output_text.get("1.0", tk.END).strip()  # Get text from output area

    # Create a wait window which will be destroyed after the synthesis is done. Also pass it a callback function to cancel the synthesis
    wait_window = create_wait_window("Please wait while synthesizing...", cancel_process)

    # Prevent pressing the main window while the wait window is open
    wait_window.grab_set()

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target = run_verifier, args=(program_text, queue, cegis.P_str, cegis.Q_str, cegis.linv_str))
    process.start()

    # Function to check the process status, waiting for it to finish and then display the result
    def check_process():

        if process.is_alive():
            # Schedule the next check after 100 ms
            root.after(100, check_process)
        else:
            print("check_process: process has finished.")
            # Code here will execute only after the process has finished

            # Close the wait window and display the result
            wait_window.destroy()

            if not queue.empty():

                # Get the result from the queue
                verifier_result = queue.get()
                final_output = ""
                # output_text.insert("1.0", f"Error: {str(result)}")
                if isinstance(verifier_result, Exception):
                    final_output = f"An unexpected error occurred: {verifier_result}"
                else:
                    print("Verifier result:", verifier_result)
                    final_output = verifier_result

                message_text.config(state='normal')  # Make output editable
                message_text.delete('1.0', tk.END)  # Clear previous output
                message_text.insert("1.0", final_output)  # Display the synthesized program
                message_text.config(state='disabled')  # Make the output non-editable again

    check_process()
    

# Label for Assertion tab
assertion_label = tk.Label(assertion_frame, text="Assertion-based Synthesis Mode", font=("Helvetica", 14))  # Larger font size
assertion_label.pack(pady=10)

# Add information label for the assertion mode
assertion_info = tk.Label(assertion_frame, text="Define assertions to synthesize the program", font=("Helvetica", 12))
assertion_info.pack(pady=5)

# Add a label for the loop unrolling limit
loop_unrolling_label = tk.Label(assertion_frame, text="Loop Unrolling Limit (for synthesis only):", font=("Helvetica", 12))
loop_unrolling_label.pack(pady=5)

# Create an entry widget for the loop unrolling limit with a default value of 10
loop_unrolling_entry = tk.Entry(assertion_frame, font=("Helvetica", 12))
loop_unrolling_entry.insert(0, "10")  # Set default value
loop_unrolling_entry.pack(pady=5)

# Function to create buttons below the output window
def create_buttons(parent):
    add_condition_button = tk.Button(assertion_frame, text="Set Conditions (P, Q, Linv)", command=open_conditions_window)
    add_condition_button.pack(pady=5)

    # Add a button to trigger synthesis in the assertion mode
    synthesize_button = tk.Button(assertion_frame, text="Synthesize with Assertion", command=process_assertion_program_input)
    synthesize_button.pack(pady=20)  # Positioned below the program input

    verify_program_button = tk.Button(assertion_frame, text="Verify output Program", state='disabled', command=verify_output_program)
    # verify_program_button = tk.Button(assertion_frame, text="Verify output Program", state='disabled')
    verify_program_button.pack(pady=5)

    return add_condition_button, verify_program_button

# Create buttons below the output window
add_condition_button, verify_program_button = create_buttons(root)

# Start the main GUI loop
if __name__ == "__main__":

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
