from rc3563 import RC3563

rc = RC3563("/dev/ttyUSB0")
while True:
    print(rc.read())