#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import logging
import pathlib
import yaml

from stream_simulator.connectivity import CommlibFactory

logging.basicConfig(format='%(levelname)s : %(name)s : %(message)s', level=logging.DEBUG)

class SimulatorStartup:
    """
    A class to handle the startup configuration for the simulator.
    Attributes:
    -----------
    configuration : dict
        The parsed configuration dictionary.
    logger : logging.Logger
        Logger instance for logging messages.
    Methods:
    --------
    __init__(conf_file=None, configuration=None):
        Initializes the SimulatorStartup with a configuration file or a configuration dictionary.
    parse_configuration(conf_file, configuration):
        Parses the configuration from a file or a dictionary.
    load_yaml(yaml_file):
        Loads and parses a YAML file.
    recursive_conf_parse(conf, curr_dir):
        Recursively parses the configuration dictionary, handling "source" keys to include other YAML files.
    """
    def __init__(self,
                 conf_file = None,
                 uid = None,
                 curr_dir = None,
                 ):

        self.logger = logging.getLogger("Simulator Startup")

        self.curr_dir = curr_dir
        self.configuration = self.parse_configuration(conf_file)

        # Create the CommlibFactory
        self.commlib_factory = CommlibFactory(node_name = "SimulatorStartup")
        self.commlib_factory.run()

        # Generate a random 10-character UID

        self.devices_rpc_client = self.commlib_factory.getRPCClient(
            rpc_name = f'streamsim.{uid}.set_configuration',
        )

    def parse_configuration(self, conf_file):
        """
        Parses the configuration from a file or a provided dictionary.
        This method loads and parses a YAML configuration file if `conf_file` is provided.
        If `configuration` is provided instead, it uses that dictionary directly.
        Args:
            conf_file (str): The name of the configuration file (without extension) to load from the configurations directory.
            configuration (dict): A dictionary containing the configuration data.
        Returns:
            dict: The parsed configuration dictionary.
        Raises:
            Exception: If there is an error loading or parsing the YAML file.
        """
        tmp_conf = {}
        current_dir = self.curr_dir if self.curr_dir is not None else str(pathlib.Path(__file__).parent.resolve())
        current_dir += "/../configurations/"
        if conf_file is not None:
            # Must load and parse file here
            filename = current_dir + conf_file + ".yaml"
            try:
                tmp_conf = self.load_yaml(filename)
                tmp_conf = self.recursive_conf_parse(tmp_conf, current_dir)
            except yaml.YAMLError as e:
                self.logger.critical(str(e))
            except FileNotFoundError as e:
                self.logger.critical(str(e))

        return tmp_conf

    def load_yaml(self, yaml_file):
        """
        Load and parse a YAML configuration file.

        Args:
            yaml_file (str): The path to the YAML file to be loaded.

        Returns:
            dict: The parsed YAML file as a dictionary.

        Raises:
            FileNotFoundError: If the YAML file does not exist.
            yaml.YAMLError: If there is an error while parsing the YAML file.
        """
        try:
            with open(yaml_file, 'r', encoding='utf-8') as stream:
                conf = yaml.safe_load(stream)
        except yaml.YAMLError:
            self.logger.critical("Yaml file %s does not exist", yaml_file)
        return conf

    def recursive_conf_parse(self, conf, curr_dir):
        """
        Recursively parses a configuration dictionary or list, loading additional
        YAML files if a "source" key is encountered.
        Args:
            conf (dict or list): The configuration data to parse. This can be a 
                                 dictionary or a list.
            curr_dir (str): The current directory path to use when loading additional
                            YAML files specified by "source" keys.
        Returns:
            dict or list: The fully parsed configuration data, with all "source" 
                          references resolved and loaded.
        """
        if isinstance(conf, dict):
            tmp_conf = {}
            for source in conf:
                # Check if "source"
                if source == "source":
                    # self.logger.warning("We hit a source: %s", conf[source])
                    r = self.load_yaml(curr_dir + conf[source] + ".yaml")
                    r = self.recursive_conf_parse(r, curr_dir)
                    tmp_conf = {**tmp_conf, **r}
                else:
                    r = self.recursive_conf_parse(conf[source], curr_dir)
                    tmp_conf[source] = r

            return tmp_conf

        elif isinstance(conf, list):
            tmp_conf = []
            for s in conf:
                tmp_conf.append(self.recursive_conf_parse(s, curr_dir))
            return tmp_conf
        else:
            return conf

    def notify_simulator_start(self):
        """
        Notify the simulator to start with the given configuration.
        """
        response = self.devices_rpc_client.call(self.configuration)
        self.logger.info(response)

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

    startup_obj = SimulatorStartup(conf_file = c, uid = uid)
    startup_obj.notify_simulator_start()

if __name__ == "__main__":
    print("Dispatching configuration to the simulator...")
    main()
