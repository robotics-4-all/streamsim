# Streamsim
- Way to execute the code: 
    - Create a python virtual environment (optional) 
    - `pip install -r requirements.txt`
    - `pip install -e .`
    - `pip install https://github.com/robotics-4-all/commlib-py/archive/devel.zip -U`
    - `sudo apt-get update && sudo apt-get install ffmpeg libsm6 libxext6 redis -y`
    - Open a tab and `redis-server` (if you prefer redis over mqtt)
    - Open `testing.yaml` from `stream_simulator/configurations` and declare your world
    - Create a `.env` file, following the `.env_template` template
    - Open a tab and execute `python3 stream_simulator/bin/bootstrap.py testing 123`
        - `testing` is the configuration file to be loaded
        - `123` is the namespace to be used for this simulator

## Running the tests

- Execute the streamsim like this: `python3 stream_simulator/bin/bootstrap.py testing testinguid`
- Execute the tests: `pytest tests/final_tests`