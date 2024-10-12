import tkinter as tk
from tkinter import Toplevel
from z3 import ForAll, Implies, Not, And, Or

# ------------------------------
# Wait Window
# ------------------------------

# Function to cancel a process running in the background
def cancel_process(wait_window):
    global process

    if process and process.is_alive():
        print("Cancelling the process...")
        process.terminate()  # Terminate the child process
        process.join()  # Wait for it to finish
        print("Process terminated.")
    
    wait_window.destroy()  # Close the wait window

# Function to create the "Please Wait" window
def create_wait_window(root, wait_window_text, cancel_callback):
    # Show the "Please Wait" window
    wait_window = tk.Toplevel(root)
    wait_window.title("Please Wait")
    wait_window.geometry("300x100")
    wait_label = tk.Label(wait_window, text=wait_window_text, font=("Helvetica", 12))
    wait_label.pack(pady=20)

    cancel_button = tk.Button(wait_window, text="Cancel", command = lambda: cancel_callback(wait_window))
    cancel_button.pack(pady=10)

    return wait_window

# ------------------------------
# Conditions Window
# ------------------------------

# Reset condition button logic
def reset_condition(tab, cond_type : str, input_window):
    tab.message_text.config(state='normal')  # Make output editable
    tab.message_text.delete('1.0', tk.END)  # Clear previous output
    tab.message_text.insert("1.0", f"{cond_type}: \"True\" has been set successfully.\n")
    tab.message_text.config(state='disabled')  # Make the output non-editable again

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
    # cond_text = input.get("1.0", tk.END).strip()

    # Try to evaluate the loop invariant using eval() in a safe environment
    safe_env = {
        'And': And, 'Or': Or, 'Implies': Implies, 'Not': Not, 'ForAll': ForAll
    }

    tab.message_text.config(state='normal')  # Make output editable
    tab.message_text.delete('1.0', tk.END)  # Clear previous output

    try:
        cond = eval("lambda d: " + cond_text, safe_env)  # Evaluate in Z3 context
        tab.message_text.insert("1.0", f"{cond_type}: \"{cond_text}\" has been set successfully.\n")
    except Exception as e:
        tab.message_text.insert("1.0", f"Error: Invalid {cond_type}: {e}\n")
        
    tab.message_text.config(state='disabled')  # Make the output non-editable again

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
    tab.conditions_window.geometry("600x400")
    # conditions_window.grab_set()

    # Label for the window
    window_label = tk.Label(tab.conditions_window, text="Set Conditions - " + tab.name, font=("Helvetica", 14))  # Larger font size
    window_label.pack(pady=10)

    pad_y = 40

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