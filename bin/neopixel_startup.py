
from stream_simulator.connectivity import CommlibFactory
from pidevices import LedController
import time

led_strip = None

def init_neopixel(message, meta):
    global led_strip
    if led_strip is None:
        print("Intializing Neopixel")
        settings = message["settings"]
        led_strip = LedController(led_count=settings["led_count"],
                                    led_pin=settings["led_pin"],
                                    led_freq_hz=settings["led_freq_hz"],
                                    led_brightness=settings["led_brightness"],
                                    led_channel=settings["led_channel"])
    
    return {}

def neopixel_write(message, meta):
    global led_strip
    if led_strip is not None:
        print(f"writting color: {message['color']}")
        led_strip.write([message ["color"]], wipe=True)


if __name__ == "__main__":
    startup_server = CommlibFactory.getRPCService(
        broker = "redis",
        callback = init_neopixel,
        rpc_name = "neopixel.init"
    )

    startup_server.run()

    write_sub = CommlibFactory.getSubscriber(
        broker = "redis",
        topic = "neopixel.set",
        callback = neopixel_write
    )
    
    write_sub.run()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        startup_server.stop()
        write_sub.stop()
        