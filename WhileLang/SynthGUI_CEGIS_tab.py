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

        self.name = "CEGIS"
        self.root = None
        self.message_text = None
        self.verify_program_button = None
        self.output_text = None
        self.loop_unrolling_entry = None
        self.program_input = None

    # Global variable to keep track of the conditions window
    conditions_window = None

cegis = CEGIS_Tab()

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

# Function to handle the button press
def process_assertion_program_input():

    global process

    cegis.message_text.config(state='normal')  # Make output editable
    cegis.message_text.delete('1.0', tk.END)  # Clear previous output

    try:
        loop_unrolling_limit = int(cegis.loop_unrolling_entry.get())  # Try to convert to integer
    except Exception:
        cegis.message_text.insert("1.0", "Error: Loop unrolling limit must be an integer.")  # Display error message
        cegis.message_text.config(state='disabled')  # Make it non-editable again
        return 

    program_text = cegis.program_input.get("1.0", tk.END).strip()  # Get text from input area

    # Check if the loop unrolling limit is less than 0
    if loop_unrolling_limit < 0:
        cegis.message_text.insert("1.0", "Error: Loop unrolling limit must be greater than or equal to 0.")  # Display error message
        cegis.message_text.config(state='disabled')  # Make it non-editable again
        return

    # Create a wait window which will be destroyed after the synthesis is done. Also pass it a callback function to cancel the synthesis
    wait_window = create_wait_window(cegis.root,"Please wait while synthesizing...", cancel_process)

    # Prevent pressing the main window while the wait window is open
    wait_window.grab_set()

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target = run_synthesis, args=(program_text, queue, loop_unrolling_limit, cegis.P_str, cegis.Q_str, cegis.linv_str))
    process.start()

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
                    cegis.message_text.config(state='normal')  # Make output editable
                    cegis.message_text.delete('1.0', tk.END)  # Clear previous output
                    cegis.message_text.insert("1.0", error)  # Display the synthesized program
                    cegis.message_text.config(state='disabled')  # Make the output non-editable again
                    cegis.verify_program_button.config(state='disabled')  # Enable the button
                    cegis.output_text.config(state='normal')  # Make output editable
                    cegis.output_text.delete('1.0', tk.END)  # Clear previous output
                    cegis.output_text.config(state='disabled')  # Make the output non-editable again
                if(final_output != ""):
                    cegis.output_text.config(state='normal')  # Make output editable
                    cegis.output_text.delete('1.0', tk.END)  # Clear previous output
                    cegis.output_text.insert("1.0", final_output)  # Display the synthesized program
                    cegis.output_text.config(state='disabled')  # Make the output non-editable again
                    cegis.verify_program_button.config(state='normal')  # Enable the button


    check_process()

def verify_output_program(tab):
    global process

    tab.message_text.config(state='normal')  # Make output editable
    tab.message_text.delete('1.0', tk.END)  # Clear previous output

    program_text = tab.output_text.get("1.0", tk.END).strip()  # Get text from output area

    # Create a wait window which will be destroyed after the synthesis is done. Also pass it a callback function to cancel the synthesis
    wait_window = create_wait_window(tab.root, "Please wait while synthesizing...", cancel_process)

    # Prevent pressing the main window while the wait window is open
    wait_window.grab_set()

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target = run_verifier, args=(program_text, queue, tab.P_str, tab.Q_str, tab.linv_str))
    process.start()

    # Function to check the process status, waiting for it to finish and then display the result
    def check_process():

        if process.is_alive():
            # Schedule the next check after 100 ms
            tab.root.after(100, check_process)
        else:
            print("check_process: process has finished.")
            # Code here will execute only after the process has finished

            # Close the wait window and display the result
            wait_window.destroy()

            if not queue.empty():

                # Get the result from the queue
                verifier_result = queue.get()
                final_output = ""
                if isinstance(verifier_result, Exception):
                    final_output = f"An unexpected error occurred: {verifier_result}"
                else:
                    print("Verifier result:", verifier_result)
                    final_output = verifier_result

                tab.message_text.config(state='normal')  # Make output editable
                tab.message_text.delete('1.0', tk.END)  # Clear previous output
                tab.message_text.insert("1.0", final_output)  # Display the synthesized program
                tab.message_text.config(state='disabled')  # Make the output non-editable again

    check_process()