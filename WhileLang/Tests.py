from pbe_tests import *
from cegis_tests import *
import sys

def main(args):
    # Check if any arguments are provided
    if not args:
        print("No arguments were passed. Please provide some arguments.")
        return

    # Assume the first argument is the case
    case = args[0]

    if case == "pbe":
        pbe_tests()
    elif case == "cegis":
        cegis_tests()
    else:
        print("Invalid case selected.")

if __name__ == "__main__":
    arguments = sys.argv[1:]
    main(arguments)