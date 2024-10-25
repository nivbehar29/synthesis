import tkinter as tk
from tkinter import Toplevel
from z3 import ForAll, Implies, Not, And, Or
import os
from contextlib import redirect_stdout
from wp import verify
from syntax.while_lang import parse

# ------------------------------
# ToolTip
# ------------------------------

tool_tips_dict = {
    "Set_Conditions_Button": (
        "Click to open a window where you can set P, Q, and Loop Invariant (Linv) conditions."
    ),

    "Set_Examples_Button": (
        "Click to open a window where you can set input-output examples to synthesize the program with.\n"
        "Note:\tYou will need to enter a valid program first."
    ),

    "Synthesize_PBE_Button": (
        "Click to synthesize the program using the provided input-output examples and Conditions."
    ),

    "Verify_Output_Button": (
        "Click to verify the output program using the provided Conditions."
    ),

    "Loop_Unrolling_Entry": (
        "Enter the number of times to unroll a 'while' loop in the program.\n"
        "Note:\tA higher number may lead to a more precise verification, but may also take longer to synthesize.\n"
        "\tA lower number may lead to a faster synthesis, but may not be able to synthesize the program.\n"
        "Note:\tThis value is relevant only for the synthesis process, and will not be used to verify the program.\n"
    ),

    "Add_Example_Button": (
        "Click to create a new input-output example to the list below, which can be modified or deleted."
    ),

    "Save_Examples_Button": (
        "Click to save the input-output examples below."
    ),

    "Delete_Example_Button": (
        "Click to delete this input-output example from the list.."
    ),

    "Synthesize_CEGIS_Button": (
        "Click to synthesize the program using the provided Conditions."
    ),

    "Interactive_Mode_Checkbox": (
        "Check to enable interactive mode. In this mode, you can step through the synthesis process."
    ),

    "Interactive_Mode_States_Box": (
        "Shows the different states in the synthesis process.\n"
        "You can select a state to see its details in the description box.\n"
        "Current state is highlighted in blue, and in yellow in case you have selected a different state."
    ),

    "Interactive_Mode_State_Description_Box": (
        "Shows a description of the current state in the synthesis process.\n"
        "You can also select a step to see its details here."
    ),

    "Interactive_Mode_Excluded_Holes_Box": (
        "Shows the holes which are excluded from the synthesis process, after a verification failure."
    ),

    "Interactive_Mode_Current_Holes_Box": (
        "Shows the current holes assignments which are being used in the synthesis process."
    ),

    "Interactive_Mode_Current_Program_Box": (
        "Shows the current program in the synthesis process. it may contain holes ('??'), or filled holes."
    ),

    "Interactive_Mode_Messages_Box": (
        "Shows different messages\errors, which are generated after a step execution."
    ),

    "Interactive_Mode_Holes_Program_Box": (
        "Shows the program after replacing holes ('??') with holes variables."
    ),

    "Interactive_Mode_Next_Step_Button": (
        "Click to execute the current selected step in the synthesis process."
    ),

    "Interactive_Mode_Abort_Button": (
        "Click to abort the synthesis process."
    ),
}

# Function to create a tooltip
class CreateToolTip(object):
    def __init__(self, widget, text):
        self.widget : tk.Widget = widget
        self.text : tk.Text = text
        self.tooltip_window = None
        widget.bind("<Enter>", self.schedule_tooltip)
        widget.bind("<Leave>", self.hide_tooltip)

    def schedule_tooltip(self, event=None):
        # Schedule the tooltip to appear after 0.65 seconds (650 milliseconds)
        self.tooltip_id = self.widget.after(650, self.show_tooltip)

    def show_tooltip(self, event=None):
        x = y = 0
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Remove window decorations
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="lemon chiffon", relief="solid", borderwidth=1, justify='left')
        label.pack()

    def hide_tooltip(self, event=None):
        # Cancel the scheduled tooltip if it hasn't appeared yet
        if self.tooltip_id:
            self.widget.after_cancel(self.tooltip_id)
            self.tooltip_id = None
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

# ------------------------------
# Wait Window For Output Program Verification
# ------------------------------

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

import multiprocessing

# Function to cancel a process running in the background
def cancel_process(wait_window, process, tab):

    if process and process.is_alive():
        print("Cancelling the process...")
        process.terminate()  # Terminate the child process
        process.join()  # Wait for it to finish
        print("Process terminated.")
    
    wait_window.destroy()  # Close the wait window
    tab.verification_cancelled = True

# Function to create the "Please Wait" window
def create_wait_window(root, wait_window_text, cancel_callback, process, tab):
    # Show the "Please Wait" window
    wait_window = tk.Toplevel(root)
    wait_window.title("Please Wait")
    wait_window.geometry("300x100")
    wait_label = tk.Label(wait_window, text=wait_window_text, font=("Helvetica", 12))
    wait_label.pack(pady=20)

    cancel_button = tk.Button(wait_window, text="Cancel", command = lambda: cancel_callback(wait_window, process, tab))
    cancel_button.pack(pady=10)

    return wait_window

def verify_output_program(tab):
    tab.message_text.config(state='normal')  # Make output editable
    tab.message_text.delete('1.0', tk.END)  # Clear previous output

    program_text = tab.output_text.get("1.0", tk.END).strip()  # Get text from output area

    queue = multiprocessing.Queue()
    process = multiprocessing.Process(target = run_verifier, args=(program_text, queue, tab.P_str, tab.Q_str, tab.linv_str))
    process.start()

    # Create a wait window which will be destroyed after the synthesis is done. Also pass it a callback function to cancel the synthesis
    wait_window = create_wait_window(tab.root, "Please wait while synthesizing...", cancel_process, process, tab)

    # Prevent pressing the main window while the wait window is open
    wait_window.grab_set()

    # Function to check the process status, waiting for it to finish and then display the result
    def check_process():

        if process.is_alive():
            # Schedule the next check after 100 ms
            tab.root.after(100, check_process)
        else:
            print("check_process: process has finished.")
            # Code here will execute only after the process has finished

            if tab.verification_cancelled == True:
                tab.verification_cancelled = False
                set_disabled_window_text_flash(tab.message_text, "Error: Verification process has been canceled.", True)
                return

            # Close the wait window and display the result
            wait_window.destroy()

            if not queue.empty():

                # Get the result from the queue
                verifier_result = queue.get()
                final_output = ""
                error = False
                if isinstance(verifier_result, Exception):
                    final_output = f"An unexpected error occurred: {verifier_result}"
                    error = True
                else:
                    print("Verifier result:", verifier_result)
                    final_output = verifier_result

                set_disabled_window_text_flash(tab.message_text, final_output, error)

    check_process()

# ------------------------------
# Conditions Window
# ------------------------------

# Reset condition button logic
def reset_condition(tab, cond_type : str, input_window):
    set_disabled_window_text_flash(tab.message_text, f"{cond_type}: \"True\" has been set successfully.\n", error=False)

    input_window.delete('1.0', tk.END)  # Clear previous condition
    input_window.insert("1.0", "True")  # Set new condition

    if(cond_type == "Pre-Condition"):
        tab.P = lambda _: True
        tab.P_str = "True"
    elif(cond_type == "Post-Condition"):
        tab.Q = lambda _: True
        tab.Q_str = "True"
    elif(cond_type == "Loop-Invariant"):
        tab.linv = lambda _: True
        tab.linv_str = "True"

# Set condition button logic
def set_condition(tab, cond_text, cond_type : str):
    cond = None

    # Try to evaluate the loop invariant using eval() in a safe environment
    safe_env = {
        'And': And, 'Or': Or, 'Implies': Implies, 'Not': Not, 'ForAll': ForAll
    }

    try:
        cond = eval("lambda d: " + cond_text, safe_env)  # Evaluate in Z3 context
        set_disabled_window_text_flash(tab.message_text, f"{cond_type}: \"{cond_text}\" has been set successfully.\n", error=False)
    except Exception as e:
        set_disabled_window_text_flash(tab.message_text, f"Error: Invalid {cond_type}: {e}\n", error=True)

    if(cond != None):
        if(cond_type == "Pre-Condition"):
            tab.P = cond
            tab.P_str = cond_text
        elif(cond_type == "Post-Condition"):
            tab.Q = cond
            tab.Q_str = cond_text
        elif(cond_type == "Loop-Invariant"):
            tab.linv = cond
            tab.linv_str = cond_text

# Initializes the conditions window
def open_conditions_window(tab):
    # Check if the window is already open
    if tab.conditions_window is not None and tab.conditions_window.winfo_exists():
        tab.conditions_window.lift()  # Bring the existing window to the front
        return

    # Create a new window
    tab.conditions_window = Toplevel(tab.root)
    tab.conditions_window.title("Set Conditions - " + tab.name)
    tab.conditions_window.geometry("650x600")
    # conditions_window.grab_set()

    # Label for the window
    window_label = tk.Label(tab.conditions_window, text="Set Conditions - " + tab.name, font=("Helvetica", 14))  # Larger font size
    window_label.pack(pady=10)

    pad_y = 240

    description_text = (
        "Enter the Loop-Invariant, Pre-Condition, and Post-Condition for the program.\n"
        "The syntax is used to define a lambda function in Python, using Z3 operators.\n\n"
        "For example, you can use 'And', 'Or' functions, and 'd' as a dictionary:\n"
        "And(d['a'] == d['b'], Or(d['a'] > 5, d['a'] < -5))\n\n"
        "Please make sure you are using parameters which are present in the program you have provided.\n\n"
        "After writing a condition, press the respective 'Set' button to set the condition.\n"
        "In addition, you can reset a condition to 'True' by clicking the respective 'Reset' button."
    )

    description_label = tk.Label(tab.conditions_window, text=description_text, font=("Helvetica", 10))
    description_label.pack(pady=5)

    # --- Loop-Invariant Section ---

    # Create a label for the invariant input
    label_linv = tk.Label(tab.conditions_window, text="Loop-Invariant:")
    label_linv.place(x=5, y=30 + pad_y)  # Set the position of the label (x, y)

    # Create a text input for the loop invariant
    invariant_input = tk.Text(tab.conditions_window, height=5, width=40)
    invariant_input.place(x=120, y=10 + pad_y)  # Set the position of the text input (x, y)
    invariant_input.insert('1.0', tab.linv_str)  # Add initial text

    # Create a button to set the loop-invariant
    set_linv_button = tk.Button(tab.conditions_window, text="Set Loop Invariant", command=lambda: set_condition(tab, invariant_input.get("1.0", tk.END).strip(), "Loop-Invariant"))
    set_linv_button.place(x = 450, y=30 + pad_y)  # Set the position of the button (x, y)

    # Create a button to reset the loop-invariant
    reset_linv_button = tk.Button(tab.conditions_window, text="Reset Loop Invariant", command=lambda: reset_condition(tab, "Loop-Invariant", invariant_input))
    reset_linv_button.place(x = 450, y=60 + pad_y)  # Set the position of the button (x, y)

    # --- Pre-Condition Section ---

    # Create a label for the pre-condition input
    label_pre = tk.Label(tab.conditions_window, text="Pre-Condition:")
    label_pre.place(x=5, y=150 + pad_y)  # Set the position of the label (x, y)

    # Create a text input for the pre-condition
    precondition_input = tk.Text(tab.conditions_window, height=5, width=40)
    precondition_input.place(x=120, y=130 + pad_y)  # Set the position of the text input (x, y)
    precondition_input.insert('1.0', tab.P_str)  # Add initial text (if applicable)

    # Create a button to set the pre-condition
    set_pre_button = tk.Button(tab.conditions_window, text="Set Pre-Condition", command=lambda: set_condition(tab, precondition_input.get("1.0", tk.END).strip(), "Pre-Condition"))
    set_pre_button.place(x=450, y=150 + pad_y)  # Set the position of the button (x, y)

    # Create a button to reset the pre-condition
    reset_pre_button = tk.Button(tab.conditions_window, text="Reset Pre-Condition", command=lambda: reset_condition(tab, "Pre-Condition", precondition_input))
    reset_pre_button.place(x = 450, y=180 + pad_y)  # Set the position of the button (x, y)

    # --- Post-Condition Section ---

    # Create a label for the post-condition input
    label_post = tk.Label(tab.conditions_window, text="Post-Condition:")
    label_post.place(x=5, y=270 + pad_y)  # Set the position of the label (x, y)

    # Create a text input for the post-condition
    post_condition_input = tk.Text(tab.conditions_window, height=5, width=40)
    post_condition_input.place(x=120, y=250 + pad_y)  # Set the position of the text input (x, y)
    post_condition_input.insert('1.0', tab.Q_str)

    # Create a button to set the post-condition
    set_post_button = tk.Button(tab.conditions_window, text="Set Post-Condition", command=lambda: set_condition(tab, post_condition_input.get("1.0", tk.END).strip(), "Post-Condition"))
    set_post_button.place(x=450 + 5, y=270 + pad_y)  # Set the position of the button (x, y)

    # Create a button to reset the post-condition
    reset_post_button = tk.Button(tab.conditions_window, text="Reset Post-Condition", command=lambda: reset_condition(tab, "Post-Condition", post_condition_input))
    reset_post_button.place(x = 450, y=300 + pad_y)  # Set the position of the button (x, y)

# ------------------------------
# Common Functions
# ------------------------------

# Scrollable Text Widget Function
def create_scrollable_text(parent, height, width, x = None, y = None, wrap = "char"):
    frame = tk.Frame(parent)

    if x != None and y != None:
        frame.place(x=x, y=y)
    else:
        frame.pack(pady=10, fill=tk.BOTH, expand=True)

    # Create a Text widget
    text_widget = tk.Text(frame, height=height, width=width, font=("Helvetica", 12), wrap=wrap)
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Create a scrollbar
    scrollbar = tk.Scrollbar(frame, command=text_widget.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # Configure the Text widget to use the scrollbar
    text_widget.config(yscrollcommand=scrollbar.set)

    return text_widget

def create_scrollable_listbox(root, x, y, height, width):
    # Create a Listbox widget
    listbox = tk.Listbox(root, height=10, width=40)
    listbox.place(x=x, y=y, width=width, height=height)

    # Create a Scrollbar widget and place it next to the Listbox
    scrollbar = tk.Scrollbar(root, orient="vertical", command=listbox.yview)
    scrollbar.place(x=x+width, y=y, height=height)

    # Configure the Listbox to work with the Scrollbar
    listbox.config(yscrollcommand=scrollbar.set)

    return listbox

# Function to evaluate the conditions
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

# Function to flash a text widget
def flash_text_widget(text_widget, original_color, flash_color="yellow", flash_duration=500):
    # Change to the flash color
    text_widget.config(bg=flash_color)

    # After a delay, change it back to the original color
    text_widget.after(flash_duration, lambda: text_widget.config(bg=original_color))

def set_disabled_window_text(window: tk.Text, text: str):
    window.config(state='normal')  # Make output editable
    window.delete('1.0', tk.END)  # Clear previous output
    window.insert("1.0", text)  # Display new text
    window.config(state='disabled')  # Make it non-editable again

def set_disabled_window_text_flash(window: tk.Text, text: str, error = False):
    set_disabled_window_text(window, text)  # Display the text
    if error:
        flash_color = 'red'
    else:
        flash_color = 'lightgreen'
    flash_text_widget(window, 'lightgray', flash_color)  # Flash the text widget to indicate the change

def set_disabled_window_text_flash_2(window: tk.Text, text: str, flash_color, original_background_color):
    set_disabled_window_text(window, text)  # Display the text
    flash_text_widget(window, original_background_color, flash_color)  # Flash the text widget to indicate the change