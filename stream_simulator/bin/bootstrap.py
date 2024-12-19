"""
This script is responsible for starting the simulator with a given configuration file.
It executes the main.py script located in the specified directory using the system's Python 3 interpreter.

Functions:
    thread_main(curr_dir):

    main():
"""

import os
import sys
import time
import threading

from stream_simulator.bin import SimulatorStartup

def thread_main(curr_dir, uid):
    """
    Executes the main.py script located in the specified directory using the system's Python 3 interpreter.

    Args:
        curr_dir (str): The directory path where main.py is located.

    Returns:
        None
    """
    print(f"python3 {curr_dir}/main.py {uid}")
    os.system(f"python3 {curr_dir}/main.py {uid}")

def main():
    """
    Main function to start the simulator with a given configuration file.
    Usage:
        python3 main.py <yaml_name> [device_name]
    Arguments:
        <yaml_name>   The name of the YAML configuration file.
        [device_name] Optional. The name of the device.
    If the required arguments are not provided, the function will print usage instructions and exit.
    Raises:
        SystemExit: If the required arguments are not provided.
    """
    if len(sys.argv) < 3:
        print("You must provide a valid yaml name as argument:")
        print(">> python3 send_configuration.py everything UID")
        exit(0)

    c = sys.argv[1]
    uid = sys.argv[2]

    # Get absolute path of the current file
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    # Start the simulator in a separate thread
    t1 = threading.Thread(target=thread_main, args=(curr_dir, uid,))
    t1.start()

    # Wait for the simulator to start
    time.sleep(1)
    startup_obj = SimulatorStartup(conf_file = c, uid = uid, curr_dir = curr_dir)
    startup_obj.notify_simulator_start()

if __name__ == "__main__":
    main()
