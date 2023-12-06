# Streamsim
- Way to execute the code: 
    - `pip install -r requirements.txt`
    - `pip install -e .`
    - `sudo apt-get update && sudo apt-get install ffmpeg libsm6 libxext6 redis -y`
    - Open a tab and `redis-server`
    - `cd bin && python main.py sfhmmy` This launches 2 robots and all env actors/sensors/effectors

## Notes
- Remove derpme dependency, everything goes through the broker
- Upgrade commlib
- Put the connectivity params inside the .yaml
- Check detects_redis in robot