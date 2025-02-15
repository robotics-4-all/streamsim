# Streamsim integration testing

The configuration used for the Streamsim integration testing is `testing.yaml`, located under the directory `streamsim/stream_simulator/configurations`. There, the following assumptions have been made:

- The world has dimensions of `100 x 100` meters, depicted by a map of `1000 x 1000` pixels, with a resolution of `0.1 m/px`
- The robot is initially placed at `(50.0, 50.0, 0)`, but in the tests we teleport it to our convenience
- A wall has been placed in `{x1: 900, y1: 10, x2: 900, y2: 990}`, i.e. in meters `{x1: 90.0, y1: 1.0, x2: 90.0, y2: 99.0}`. This is a large vertical wall to be used to test the distance sensors.
- A water source is placed at `(40.0, 70.0)`. This affects the humidity sensors.
- The robot is equipped with:
    - A pan-tilt mechanism, placed in the middle of the robot, named `pt1`
    - A sonar named `sonar_front_on_pt1`, placed on top of `pt1`, with orientation equal to 0 degrees, posting distance measurements with 5 Hz
- An area alarm is placed in `(10.0, 10.0)` with a radius of 5.0 meters
- A linear alarm is placed in `(10.0, 4.5) to (10.0, 5.5)`
- A humidity sensor is placed in `(20.0, 10.0)` and a humidifier in `(20.0, 12.0)`
- A pH sensor placed at `(60.0, 10.0)`
- A temperature sensor is placed at `(20.0, 20.0)` and a thermostat at `(20.0, 22.0)` with a range of 2 meters. Also a fire exists at `(24.0, 20.0)` with a radius of 15 meters.
- A relay is placed at `(10.0, 10.0)` with available states 0 and 1
- An environmental gas sensor is placed at `(20.0, 15.0)` (near the fire), therefore a large value is expected
- An ambient light sensor placed at `(70.0, 70.0)` and a bulb placed at `(75.0, 75.0)`