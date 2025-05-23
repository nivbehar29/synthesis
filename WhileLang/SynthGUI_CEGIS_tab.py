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

        # Interactive variables
        self.synth : Synthesizer = None
        self.interactive_window : Toplevel = None # interactive window
        self.interactive_var : tk.IntVar = None # enable \ disable interactive mode (checkbox state)
        self.generator = None # generator function to make a step
        self.last_step = None # last step that was performed
        self.state_list_box: tk.Listbox = None
        self.states = [] # List of states
        self.states_dict = {} # Dictionary of states, where the key is the state name and the value is the description of the state
        self.state_description_box: tk.Text = None # Text box to show the description of the selected state
        self.excluded_holes_list_box: tk.Listbox = None # Listbox to show the excluded holes combinations
        self.current_holes_box: tk.Listbox = None # Listbox to show the current holes values

        self.next_button: tk.Button = None # Button to go to the next step
        self.abort_button: tk.Button = None # Button to abort the interactive process

        self.current_program_text_box: tk.Text = None # Text box to show the current program
        self.holes_program_text_box: tk.Text = None # Text box to show the holes program

        self.interactive_message_text: tk.Text = None # Text box to show the messages

cegis = CEGIS_Tab()

def synth_program_cegis(program, P, Q, linv, debug=False, unroll_limit=10):
    returned_program = ""
    synth = Synthesizer(program)
    if not debug:
        with open(os.devnull, 'w') as f:
            with redirect_stdout(f):
                returned_program = synth.synth_program(program, P, Q, linv, unroll_limit)
    else:
        returned_program = synth.synth_program(program, P, Q, linv, unroll_limit)

    return returned_program

def run_synthesis_cegis(program_text, queue, loop_unrolling_limit, P_str = None, Q_str = None, linv_str = None):

    P, Q, linv = eval_conditions(P_str, Q_str, linv_str)

    try:
        returned_program = synth_program_cegis(program_text, P, Q, linv, True, loop_unrolling_limit)

        print("Synthesis successful.")
        queue.put(returned_program)
    except (Synthesizer.ProgramNotValid, Synthesizer.ProgramNotVerified, Synthesizer.ProgramHasNoHoles,
            Synthesizer.ProgramHasInvalidVarName) as e:
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

cegis.states = [  
            "State_0",
            "State_1",
            "State_2",
            "State_3_1",
            "State_3_2",
            "State_3_3",
            "State_4_1",
            "State_4_2",
            "State_5",
        ]

cegis.states_dict = {
    "State_0": ("initialization", "Initialize the program"),
    "State_1": ("Replace holes with variables", "Replace all occurrences of '??' with unique hole variables"),
    "State_2": ("Fill holes with zeroes", "Fill the program holes with zeros"),
    "State_3_1": ("Try to verify the program", "Try to verify the program"),
    "State_3_2": ("Verification succeeded", "Verification succeeded, return the final program"),
    "State_3_3": ("Verification failed", "Verification failed, show counter example and exclude current holes combination"),
    "State_4_1": ("Try to find new holes", "Try to find new holes"),
    "State_4_2": ("Couldn't find new holes", "Couldn't find new holes - finish"),
    "State_5": ("New holes found", "New holes found, Show the new holes and fill the program with the new holes")
}

def finish_interactive_process(tab: CEGIS_Tab):
    # Kill generator
    tab.generator.close()

    # Disable the next / Abort buttons
    tab.next_button.config(state='disabled')
    tab.abort_button.config(state='disabled')

def update_state_description(event, tab: CEGIS_Tab):
    selected_index = tab.state_list_box.curselection()

    if not selected_index:
        return
    
    description = tab.states_dict[tab.states[selected_index[0]]][1]

    # Enable the description box
    tab.state_description_box.config(state='normal')

    # Update the text box with the corresponding description
    tab.state_description_box.delete(1.0, tk.END)  # Clear previous text
    tab.state_description_box.insert(tk.END, description)

    # Disable the description box
    tab.state_description_box.config(state='disabled')

def replace_listbox_items_dict(listbox: tk.Listbox, dic : dict):
    # Delete all of the previous items
    listbox.delete(0, tk.END)
    
    # Add the new items to the listbox
    for key, value in dic.items():
        listbox.insert(tk.END, f"{key}: {value}")

def next_step(tab: CEGIS_Tab, to_disable_prints = True):

    # Post process function to flash the changed elements in the GUI after each step
    flash_post_process = None

    # Here, perform the last step that was actually done
    last_state = tab.last_step[0]

    if last_state == "State_0":
        if len(tab.last_step) >= 3:
            program = tab.last_step[2]
            flash_post_process = lambda : set_disabled_window_text_flash_2(tab.current_program_text_box, program, 'yellow', 'white')

    if last_state == "State_1":
        program_with_holes = tab.last_step[2]
        flash_post_process = lambda : set_disabled_window_text_flash_2(tab.holes_program_text_box, program_with_holes, 'yellow', 'white')
    
    elif last_state == "State_2":
        new_holes_dict = tab.last_step[3]
        replace_listbox_items_dict(tab.current_holes_box, new_holes_dict)
        # flash_text_widget(tab.current_holes_box, 'white', 'yellow')

        program_with_zeros = tab.last_step[2]
        flash_post_process = lambda : (set_disabled_window_text_flash_2(tab.current_program_text_box, program_with_zeros, 'yellow', 'white'),
                                 flash_text_widget(tab.current_holes_box, 'white', 'yellow'))


    elif last_state == "State_3_1":
        result = tab.last_step[2]
        if result == True:
            flash_post_process = lambda : set_disabled_window_text_flash_2(tab.interactive_message_text, f"Verification secceeded. The synthesized program will be presented in the 'Current program' window", 'lightgreen', 'white')
        else:
            flash_post_process = lambda : set_disabled_window_text_flash_2(tab.interactive_message_text, f"Verification failed", 'red2', 'white')


    elif last_state == "State_3_2":
        filled_program = tab.last_step[2]
        flash_post_process = lambda : set_disabled_window_text_flash_2(tab.current_program_text_box, filled_program, 'lightgreen', 'white')
        finish_interactive_process(tab)

    elif last_state == "State_3_3":
        excluded_holes_dict = tab.last_step[3]
        
        # Add the excluded holes to the listbox
        tab.excluded_holes_list_box.insert(tk.END, str(tab.excluded_holes_list_box.size() + 1) + ". " + str(excluded_holes_dict))
        # flash_text_widget(tab.excluded_holes_list_box, 'white', 'yellow')

        # Scroll to the end of the listbox
        tab.excluded_holes_list_box.see(tk.END)

        # Set the counter example in the message box
        counter_example = tab.last_step[2]
        flash_post_process = lambda : (set_disabled_window_text_flash_2(tab.interactive_message_text, f"Counter example: {counter_example}", 'yellow', 'white'),
                                 flash_text_widget(tab.excluded_holes_list_box, 'white', 'yellow'))

    elif last_state == "State_4_2":
        flash_post_process = lambda : set_disabled_window_text_flash_2(tab.interactive_message_text, f"Couldn't find new holes - program is not solvable.\nFinish process.", 'red2', 'white')
        finish_interactive_process(tab)

    elif last_state == "State_5":
        new_holes_dict = tab.last_step[3]
        replace_listbox_items_dict(tab.current_holes_box, new_holes_dict)
        # flash_text_widget(tab.current_holes_box, 'white', 'yellow')

        filled_program = tab.last_step[2]
        # Display the filled program in the output text box
        flash_post_process = lambda : (set_disabled_window_text_flash_2(tab.current_program_text_box, filled_program, 'yellow', 'white'),
                                flash_text_widget(tab.current_holes_box, 'white', 'yellow'))


    # Now, perform the next step

    error = ""

    try:
        if to_disable_prints:
            with open(os.devnull, 'w') as f:
                with redirect_stdout(f):
                    tab.last_step = next(tab.generator)
        else:
            tab.last_step = next(tab.generator)
        print(f"step: {tab.last_step}")

        # Highlight the current state
        highlight_state(tab.state_list_box, tab.states.index(tab.last_step[0]), tab.states.index(last_state))
        update_state_description(None, tab)

    except StopIteration:
        print("StopIteration has been raised")
    except (Synthesizer.ProgramNotValid, Synthesizer.ProgramHasInvalidVarName, Synthesizer.ProgramHasNoHoles) as e:
        _, error = get_final_result(e, "Don't Care :)")
        print("error:", error)
    except Exception as e:
        error = f"An unexpected error occurred: {e}"

    if(error != ""):
        flash_post_process = lambda: set_disabled_window_text_flash_2(tab.interactive_message_text, error, 'red2', 'white')
        finish_interactive_process(tab)
    
    # Flash 
    if flash_post_process:
        flash_post_process()


def abort(tab: CEGIS_Tab):
    # Kill generator
    tab.generator.close()

    # Close the interactive window
    tab.interactive_window.destroy()

def highlight_state(state_list_box: tk.Listbox, index, prev_index):
    # Clear any previous selection
    
    selected_indices = state_list_box.curselection()
    print("selected_indices:", selected_indices)
    if selected_indices:
        state_list_box.selection_clear(selected_indices, tk.END)

    print("prev_index:", prev_index)
    state_list_box.itemconfig(prev_index, {'bg': 'white', 'fg': 'black'})

    # Highlight the selected state
    state_list_box.selection_set(index)
    state_list_box.activate(index)
    state_list_box.itemconfig(index, {'bg': 'yellow', 'fg': 'black'})

def create_info_frame(tab: CEGIS_Tab, pos_x, pos_y, width, height):
    # Create a frame inside the window
    # info_frame = tk.Frame(tab.interactive_window, highlightbackground="black", highlightthickness=2) # for debugging the frame size
    info_frame = tk.Frame(tab.interactive_window)
    info_frame.place(x=pos_x, y=pos_y, width=width, height=height)
    info_frame.update_idletasks()

    # Create states window
    state_list_box_label = tk.Label(info_frame, text="States:", font=("Helvetica", 12))
    state_list_box_label.place(x = 0, y=0)
    state_list_box_label.update_idletasks()
    CreateToolTip(state_list_box_label, tool_tips_dict["Interactive_Mode_States_Box"])

    # Create a listbox for the states. the listbox width will be the length of the longest string
    concatenated_strings = [f"{key}: {value[0]}" for key, value in cegis.states_dict.items()]
    longest_string_len = len(max(concatenated_strings, key=len))
    tab.state_list_box = tk.Listbox(info_frame, height=len(tab.states), width = longest_string_len)
    tab.state_list_box.place(x = 0, y = state_list_box_label.winfo_y() + 25)

    # Insert the states into the listbox
    for state in tab.states:
        tab.state_list_box.insert(tk.END, state + " - " + tab.states_dict[state][0])

    # nessesary to update the listbox width, so we can use it in the next lines
    tab.state_list_box.update_idletasks()

    # Create selected state description
    states_description_label = tk.Label(info_frame, text="State description:", font=("Helvetica", 12))
    states_description_label.place(x = tab.state_list_box.winfo_width() + tab.state_list_box.winfo_x(), y=state_list_box_label.winfo_y())
    CreateToolTip(states_description_label, tool_tips_dict["Interactive_Mode_State_Description_Box"])

    tab.state_description_box = tk.Text(info_frame, height=len(tab.states), width=30, wrap=tk.WORD)
    tab.state_description_box.place(x = tab.state_list_box.winfo_width() + tab.state_list_box.winfo_x(), y=tab.state_list_box.winfo_y())

    # Disable the description box
    tab.state_description_box.config(state='disabled')

    # Bind the listbox to the update_state_description function, so that the description is updated when a state is selected by the user
    tab.state_list_box.bind('<<ListboxSelect>>', lambda event: update_state_description(event, tab))  # Prevent selection with mouse clicks

    # nessesary to update the describtion box width, so we can use it in the next lines
    tab.state_description_box.update_idletasks()

    # Prevent the user from manually selecting items
    # def disable_selection(event):
    #     return "break"  # Prevents the default action
    # tab.state_list_box.bind("<Button-1>", disable_selection)  # Prevent selection with mouse clicks
    # tab.state_list_box.bind("<Key>", disable_selection)  # Prevent selection with keyboard
    # tab.state_list_box.bind("<B1-Motion>", disable_selection)       # Prevent selection by dragging
    # tab.state_list_box.bind("<ButtonRelease-1>", disable_selection) # Prevent selection when releasing mouse button

    # Create a label for excluded holes box
    excluded_holes_label = tk.Label(info_frame, text="Excluded holes combinations:", font=("Helvetica", 12))
    excluded_holes_label.place(x = 20 + tab.state_description_box.winfo_width() + tab.state_description_box.winfo_x(), y=state_list_box_label.winfo_y())
    CreateToolTip(excluded_holes_label, tool_tips_dict["Interactive_Mode_Excluded_Holes_Box"])

    # Create a listbox for excluded holes
    state_list_box_x = 20 + tab.state_description_box.winfo_width() + tab.state_description_box.winfo_x()
    state_list_box_y = tab.state_description_box.winfo_y()
    state_list_box_height = tab.state_list_box.winfo_height()
    tab.excluded_holes_list_box = create_scrollable_listbox(info_frame, state_list_box_x, state_list_box_y, state_list_box_height, 300)

    # nessesary to update the excluded holes box width, so we can use it in the next lines
    tab.excluded_holes_list_box.update_idletasks()

    # Create a label for the current holes box
    current_holes_label = tk.Label(info_frame, text="Current holes values:", font=("Helvetica", 12))
    current_holes_label.place(x = 20 + tab.excluded_holes_list_box.winfo_width() + tab.excluded_holes_list_box.winfo_x(), y=state_list_box_label.winfo_y())
    CreateToolTip(current_holes_label, tool_tips_dict["Interactive_Mode_Current_Holes_Box"])

    # Create a listbox for current holes
    current_holes_box_x = 20 + tab.excluded_holes_list_box.winfo_width() + tab.excluded_holes_list_box.winfo_x()
    current_holes_box_y = tab.excluded_holes_list_box.winfo_y()
    current_holes_box_height = tab.excluded_holes_list_box.winfo_height()
    tab.current_holes_box = create_scrollable_listbox(info_frame, current_holes_box_x, current_holes_box_y, current_holes_box_height, 200)

def create_buttons_frame(tab: CEGIS_Tab, pos_x, pos_y, width, height):
    # Create a frame inside the window
    # buttons_frame = tk.Frame(tab.interactive_window, highlightbackground="black", highlightthickness=2) # for debugging the frame size
    buttons_frame = tk.Frame(tab.interactive_window)
    buttons_frame.place(x=pos_x, y=pos_y, width=width, height=height)
    buttons_frame.update_idletasks()

    # Create Next \ Abort buttons
    tab.next_button = tk.Button(buttons_frame, text="Next step", command=lambda: next_step(cegis, True))
    tab.next_button.place(x = 0, y=0)  # Set the position of the button (x, y)
    CreateToolTip(tab.next_button, tool_tips_dict["Interactive_Mode_Next_Step_Button"])

    tab.abort_button = tk.Button(buttons_frame, text="Abort", command=lambda: abort(cegis))
    tab.abort_button.place(x = 100, y=0)  # Set the position of the button (x, y)
    CreateToolTip(tab.abort_button, tool_tips_dict["Interactive_Mode_Abort_Button"])

def create_program_frame(tab: CEGIS_Tab, pos_x, pos_y, width, height):
    # Create a frame inside the window
    # program_frame = tk.Frame(tab.interactive_window, highlightbackground="black", highlightthickness=2) # for debugging the frame size
    program_frame = tk.Frame(tab.interactive_window)
    program_frame.place(x=pos_x, y=pos_y, width=width, height=height)
    program_frame.update_idletasks()

    # Create a label for the current program
    program_label = tk.Label(program_frame, text="Current program:", font=("Helvetica", 12))
    program_label.place(x = 0, y=0)
    program_label.update_idletasks()
    CreateToolTip(program_label, tool_tips_dict["Interactive_Mode_Current_Program_Box"])

    # Create a text box for the program
    tab.current_program_text_box = tk.Text(program_frame, height=10, width=90, wrap=tk.WORD)
    tab.current_program_text_box.place(x = 0, y=program_label.winfo_y() + 25)
    tab.current_program_text_box.update_idletasks()

    # Disable the text box
    tab.current_program_text_box.config(state='disabled')

    # Create a label for the holes program
    holes_program_label = tk.Label(program_frame, text="Holes program:", font=("Helvetica", 12))
    holes_program_label.place(x = 0, y=tab.current_program_text_box.winfo_y() + tab.current_program_text_box.winfo_height() + 10)
    holes_program_label.update_idletasks()
    CreateToolTip(holes_program_label, tool_tips_dict["Interactive_Mode_Holes_Program_Box"])

    # Create a text box for the holes program
    tab.holes_program_text_box = tk.Text(program_frame, height=10, width=90, wrap=tk.WORD)
    tab.holes_program_text_box.place(x = 0, y=holes_program_label.winfo_y() + 25)
    tab.holes_program_text_box.update_idletasks()

    # Disable the text box
    tab.holes_program_text_box.config(state='disabled')

def create_message_frame(tab: CEGIS_Tab, pos_x, pos_y, width, height):
    # Create a frame inside the window
    # message_frame = tk.Frame(tab.interactive_window, highlightbackground="black", highlightthickness=2) # for debugging the frame size
    message_frame = tk.Frame(tab.interactive_window)
    message_frame.place(x=pos_x, y=pos_y, width=width, height=height)
    message_frame.update_idletasks()

    # Create a label for the message
    message_label = tk.Label(message_frame, text="Messages:", font=("Helvetica", 12))
    message_label.place(x = 0, y = 0)
    message_label.update_idletasks()
    CreateToolTip(message_label, tool_tips_dict["Interactive_Mode_Messages_Box"])

    # Create a text box for the message
    tab.interactive_message_text = create_scrollable_text(message_frame, 7, 40, 0, message_label.winfo_y() + 25, tk.WORD)
    # tab.interactive_message_text.place(x = 0, y = message_label.winfo_y() + 25)
    tab.interactive_message_text.update_idletasks()

    # Disable the text box
    tab.interactive_message_text.config(state='disabled')

# Initializes the Interactive window
def create_interactive_window(tab: CEGIS_Tab, program, P, Q, linv):
    # Check if the window is already open
    if tab.interactive_window is not None and tab.interactive_window.winfo_exists():
        tab.interactive_window.lift()  # Bring the existing window to the front
        return

    # Create a new window
    tab.interactive_window = Toplevel(tab.root)
    tab.interactive_window.title("Interactive CEGIS")
    tab.interactive_window.geometry("1200x800")

    # Label for the window
    window_label = tk.Label(tab.interactive_window, text="Interactive CEGIS", font=("Helvetica", 14))
    window_label.pack(pady=10)

    # Create a frame inside the window, to show the information
    create_info_frame(tab, 20, 40, 1050, 200)

    # Create a frame inside the window, to show the buttons
    create_buttons_frame(tab, 400, 250, 145, 30)

    # Create a frame inside the window, to show the program
    create_program_frame(tab, 20, 300, 740, 400)

    # Create a frame inside the window, to show the different messages
    create_message_frame(tab, 800, 300, 400, 200)

    # initialize the selected state in the listbox
    highlight_state(tab.state_list_box, 0, 0)
    tab.last_step = (tab.states[0], tab.states_dict[tab.states[0]][1])

    tab.synth = Synthesizer(program)
    tab.generator = tab.synth.cegis_interactive(program, P, Q, linv, 10)

def get_final_result(synth_result, program_text):
    final_output = ""
    error = ""
    # cegis.output_text.insert("1.0", f"Error: {str(result)}")
    if isinstance(synth_result, Synthesizer.ProgramNotValid):
        error = "Error: The given program can't be parsed"
    elif isinstance(synth_result, Synthesizer.ProgramHasNoHoles):
        error = "Message: Program has no holes. You can try to verify your program."
        print("synthesis result:", program_text)
        final_output = program_text # remove_assertions_program(program_text)
    elif isinstance(synth_result, Synthesizer.ProgramNotVerified):
        error = "Error: The program can't be verified for all possible inputs. If this is not the excpected outcome:\n "
        error += "1. Try increasing the loop unrolling limit.\n"
        error += "2. Check if the loop invariant is correct.\n"
        error += "3. Check if the pre-condition and post-condition are correct."
    elif isinstance(synth_result, Synthesizer.ProgramHasInvalidVarName):
        error = f"Error: Invalid variable name: {synth_result}.\nPlease use valid variable names which are not of the form 'hole_x', where x is a number."    
    elif isinstance(synth_result, Exception):
        error = f"An unexpected error occurred: {synth_result}"
    else:
        print("synthesis result:", synth_result)
        final_output = synth_result # remove_assertions_program(synth_result)

    return final_output, error

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
    if loop_unrolling_limit <= 0:
        set_disabled_window_text_flash(cegis.message_text, "Error: Loop unrolling limit must be greater than 0.", True)
        return

    # If interactive mode is enabled, create the interactive window
    if(cegis.interactive_var.get() == 1):
        print("Interactive mode is enabled")
        P, Q, linv = eval_conditions(cegis.P_str, cegis.Q_str, cegis.linv_str)
        create_interactive_window(cegis, program_text, P, Q, linv)
        # Open the conditions window
    else:
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
                    final_output, error = get_final_result(synth_result, program_text)

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

def show_selection():
    if cegis.interactive_var.get() == 1:
        print("Checkbox is checked")
    else:
        print("Checkbox is unchecked")