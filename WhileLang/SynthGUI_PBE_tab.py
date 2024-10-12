from Synthesizer import Synthesizer
import os
from contextlib import redirect_stdout
import multiprocessing
import tkinter as tk
from wp import verify
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

        self.name = "PBE"
        self.root = None
        self.message_text = None
        self.output_text = None
        self.loop_unrolling_entry = None
        self.program_input = None

    # Global variable to keep track of the conditions window
    conditions_window = None

pbe = PBE_Tab()