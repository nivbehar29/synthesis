from Synthesizer import Synthesizer
import os
from contextlib import redirect_stdout
import threading
import multiprocessing
import tkinter as tk
from tkinter import ttk, messagebox
import time

# Initialize the main window
root = tk.Tk()
root.title("While Language Synthesis")
root.geometry("800x800")  # Increased height to accommodate both input and output areas

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
program_input = create_scrollable_text(root, height=10, width=80)  # Reduced width from 90 to 80

# Label for the output section
output_label = tk.Label(root, text="Synthesis Output", font=("Helvetica", 14))
output_label.pack(pady=10)

# Create scrollable output text widget with reduced width
output_text = create_scrollable_text(root, height=10, width=80)  # Reduced width from 90 to 80

# Insert initial text
output_text.config(state='normal')  # Temporarily make the output editable
output_text.insert('1.0', "Output program")  # Add initial text
output_text.config(state='disabled')  # Make the output non-editable again

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

def synth_program(program, P, Q, linv, expected_program, debug=False, unroll_limit=10):
    returned_program = ""
    synth = Synthesizer(program)
    if not debug:
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f):
                returned_program = synth.synth_program(program, P, Q, linv, None, None, unroll_limit)
    else:
        returned_program = synth.synth_program(program, P, Q, linv, None, None, unroll_limit)

    return returned_program

def run_synthesis(program_text, queue, loop_unrolling_limit):
    try:
        returned_program = synth_program(program_text, None, None, None, None, False, loop_unrolling_limit)

        print("Synthesis successful.")
        queue.put(returned_program)
    except (Synthesizer.ProgramNotValid, Synthesizer.ProgramNotVerified) as e:
        queue.put(e)
    except Exception as e:
        queue.put(e)

# Function to handle the button press
def process_assertion_program_input():

    global process

    output_text.config(state='normal')  # Make output editable
    output_text.delete('1.0', tk.END)  # Clear previous output
  
    try:
        loop_unrolling_limit = int(loop_unrolling_entry.get())  # Try to convert to integer
    except Exception:
        output_text.insert("1.0", "Error: Loop unrolling limit must be an integer.")  # Display error message
        output_text.config(state='disabled')  # Make it non-editable again
        return 

    program_text = program_input.get("1.0", tk.END).strip()  # Get text from input area
    loop_unrolling_limit = int(loop_unrolling_entry.get())  # Get loop unrolling limit

    # Check if the loop unrolling limit is less than 0
    if loop_unrolling_limit < 0:
        output_text.insert("1.0", "Error: Loop unrolling limit must be greater than or equal to 0.")  # Display error message
        output_text.config(state='disabled')  # Make it non-editable again
        return

    # Show the "Please Wait" window
    wait_window = tk.Toplevel(root)
    wait_window.title("Please Wait")
    wait_window.geometry("300x100")
    wait_label = tk.Label(wait_window, text="Please wait while synthesizing...", font=("Helvetica", 12))
    wait_label.pack(pady=20)

    cancel_button = tk.Button(wait_window, text="Cancel", command=lambda: cancel_synthesis(wait_window))
    cancel_button.pack(pady=10)

    # Prevent pressing the main window while the wait window is open
    wait_window.grab_set()

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target = run_synthesis, args=(program_text, queue, loop_unrolling_limit))
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
                # output_text.insert("1.0", f"Error: {str(result)}")
                if isinstance(synth_result, Synthesizer.ProgramNotValid):
                    final_output = "Error: Program not valid"
                elif isinstance(synth_result, Synthesizer.ProgramNotVerified):
                    final_output = "Error: Program not verified."
                elif isinstance(synth_result, Exception):
                    final_output = f"An unexpected error occurred: {synth_result}"
                else:
                    print("synthesis result:", synth_result)
                    final_output = synth_result

                output_text.insert("1.0", final_output)  # Display the synthesized program


    check_process()

# Function to cancel the synthesis
def cancel_synthesis(wait_window):
    global process

    if process and process.is_alive():
        print("Cancelling the process...")
        process.terminate()  # Terminate the child process
        process.join()  # Wait for it to finish
        print("Process terminated.")
    
    wait_window.destroy()  # Close the wait window

# Label for Assertion tab
assertion_label = tk.Label(assertion_frame, text="Assertion-based Synthesis Mode", font=("Helvetica", 14))  # Larger font size
assertion_label.pack(pady=10)

# Add information label for the assertion mode
assertion_info = tk.Label(assertion_frame, text="Define assertions to synthesize the program", font=("Helvetica", 12))
assertion_info.pack(pady=5)

# Add a button to trigger synthesis in the assertion mode
synthesize_button = tk.Button(assertion_frame, text="Synthesize with Assertion", command=process_assertion_program_input)
synthesize_button.pack(pady=20)  # Positioned below the program input

# Add a label for the loop unrolling limit
loop_unrolling_label = tk.Label(assertion_frame, text="Loop Unrolling Limit:", font=("Helvetica", 12))
loop_unrolling_label.pack(pady=5)

# Create an entry widget for the loop unrolling limit with a default value of 10
loop_unrolling_entry = tk.Entry(assertion_frame, font=("Helvetica", 12))
loop_unrolling_entry.insert(0, "10")  # Set default value
loop_unrolling_entry.pack(pady=5)

# Function to create buttons below the output window
def create_buttons(parent):
    add_condition_button = tk.Button(assertion_frame, text="Add Condition (P, Q, Linv)", state='disabled')
    add_condition_button.pack(pady=5)

    verify_program_button = tk.Button(assertion_frame, text="Verify Program", state='disabled')
    verify_program_button.pack(pady=5)

    return add_condition_button, verify_program_button

# Create buttons below the output window
add_condition_button, verify_program_button = create_buttons(root)

# Start the main GUI loop
if __name__ == "__main__":
    root.mainloop()