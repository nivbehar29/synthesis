from Synthesizer import Synthesizer
import os
from contextlib import redirect_stdout
import multiprocessing
import tkinter as tk
from wp import verify
from syntax.while_lang import parse, remove_assertions_program
from SynthGUI_common import *

class CEGIS_Tab:
    def __init__(self):
        self.P = lambda d: True
        self.Q = lambda d: True
        self.linv = lambda d: True

        self.P_str = "True"
        self.Q_str = "True"
        self.linv_str = "True"

        self.loop_unrolling_entry = None

        self.name = "CEGIS"
        self.root = None
        self.message_text : tk.Text = None
        self.output_text : tk.Text = None
        self.program_input : tk.Text = None
        self.verify_program_button = None

        # Global variable to keep track of the conditions window
        self.conditions_window = None

        # Variable to keep track if a verification process has been canceled or not
        self.verification_cancelled = False

cegis = CEGIS_Tab()

def synth_program_cegis(program, P, Q, linv, debug=False, unroll_limit=10):
    returned_program = ""
    synth = Synthesizer(program)
    if not debug:
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f):
                returned_program = synth.synth_program(program, P, Q, linv, None, None, unroll_limit)
    else:
        returned_program = synth.synth_program(program, P, Q, linv, None, None, unroll_limit)

    return returned_program

def run_synthesis_cegis(program_text, queue, loop_unrolling_limit, P_str = None, Q_str = None, linv_str = None):

    P, Q, linv = eval_conditions(P_str, Q_str, linv_str)

    try:
        returned_program = synth_program_cegis(program_text, P, Q, linv, True, loop_unrolling_limit)

        print("Synthesis successful.")
        queue.put(returned_program)
    except (Synthesizer.ProgramNotValid, Synthesizer.ProgramNotVerified, Synthesizer.ProgramHasNoHoles) as e:
        print("run_synthesis_cegis raised an exception:", e)
        queue.put(e)
    except Exception as e:
        queue.put(e)

# Function to cancel a process running in the background
def cancel_process_cegis(wait_window):
    global process

    if process and process.is_alive():
        print("Cancelling the process...")
        process.terminate()  # Terminate the child process
        process.join()  # Wait for it to finish
        print("Process terminated.")
    
    wait_window.destroy()  # Close the wait window

# Function to create the "Please Wait" window
def create_wait_window_cegis(root, wait_window_text, cancel_callback):
    # Show the "Please Wait" window
    wait_window = tk.Toplevel(root)
    wait_window.title("Please Wait")
    wait_window.geometry("300x100")
    wait_label = tk.Label(wait_window, text=wait_window_text, font=("Helvetica", 12))
    wait_label.pack(pady=20)

    cancel_button = tk.Button(wait_window, text="Cancel", command = lambda: cancel_callback(wait_window))
    cancel_button.pack(pady=10)

    return wait_window

# Function to handle the button press
def process_assertion_program_input():

    global process

    cegis.message_text.config(state='normal')  # Make output editable
    cegis.message_text.delete('1.0', tk.END)  # Clear previous output

    try:
        loop_unrolling_limit = int(cegis.loop_unrolling_entry.get())  # Try to convert to integer
    except Exception:
        set_disabled_window_text_flash(cegis.message_text, "Error: Loop unrolling limit must be an integer.", True)
        return 

    program_text = cegis.program_input.get("1.0", tk.END).strip()  # Get text from input area

    # Check if the loop unrolling limit is less than 0
    if loop_unrolling_limit < 0:
        set_disabled_window_text_flash(cegis.message_text, "Error: Loop unrolling limit must be greater than or equal to 0.", True)
        return

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target = run_synthesis_cegis, args=(program_text, queue, loop_unrolling_limit, cegis.P_str, cegis.Q_str, cegis.linv_str))
    process.start()

    # Create a wait window which will be destroyed after the synthesis is done. Also pass it a callback function to cancel the synthesis
    wait_window = create_wait_window_cegis(cegis.root,"Please wait while synthesizing...", cancel_process_cegis)

    # Prevent pressing the main window while the wait window is open
    wait_window.grab_set()

    # Function to check the process status, waiting for it to finish and then display the result
    def check_process():

        if process.is_alive():
            # Schedule the next check after 100 ms
            cegis.root.after(100, check_process)
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
                # cegis.output_text.insert("1.0", f"Error: {str(result)}")
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
                    set_disabled_window_text_flash(cegis.message_text, error, True)
                    cegis.verify_program_button.config(state='disabled')  # Disable the button
                    set_disabled_window_text(cegis.output_text, "")

                if(final_output != ""):
                    if(error == ""):
                        set_disabled_window_text_flash(cegis.message_text, "The program has been synthesized successfully", False)
                    set_disabled_window_text(cegis.output_text, final_output)
                    cegis.verify_program_button.config(state='normal')  # Enable the button

    check_process()