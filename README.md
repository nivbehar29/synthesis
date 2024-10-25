# SynthGUI

---

## **Table of Contents**

1. [Introduction](#introduction)
2. [Features](#Features)
3. [Usage](#usage)

---

## **Introduction**

SynthGUI is a graphical user interface for synthesizing programs using PBE (Programming by Examples) and CEGIS (Counterexample-Guided Inductive Synthesis) approach. This project is built using Python.
The programs synthesized by SynthGUI follow the syntax of the WhileLang language.


## **Features**

- **Synthesis with PBE (Programming By Examples)**:
This feature allows you to synthesize programs by providing examples for inputs and outputs. The synthesizer will generate a program that matches the given examples.

- **Synthesis with CEGIS (Counterexample Guided Inductive Synthesis)**:
This feature uses the CEGIS approach to synthesize programs. It iteratively refines the program by generating counterexamples and updating the program to handle them.

- **Assertions**:
Assertions are used to specify properties that the synthesized program must satisfy. These assertions are part of the syntax of the programs provided by the user.
The synthesizer will generate a program that meets these assertions, ensuring that the synthesized program behaves as expected according to the specified properties.

- **Loops Handling in Synthesis**:
This feature handles loops in the synthesis process by unrolling loops. Loop unrolling helps in dealing with loops by expanding them into a sequence of repeated statements.

- **Interactive Mode for Step-by-Step Synthesis (CEGIS only)**:
Interactive mode allows you to step through the synthesis process interactively. This is useful for learning puposes, and understanding how the CEGIS approach works.

- **Tooltip Support for Better User Guidance**:
Tooltips provide additional information about various elements in the GUI. They appear when hovering over an element, helping users understand the functionality of different components.


## **Usage**

To run the GUI, execute the following command:
```sh
python SynthGUI.py