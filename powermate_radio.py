from usb1 import *
import libusb1
from threading import Thread
import struct
import serial
import re

running = True

s = serial.Serial('/dev/ttyUSB0', 38400)
s.write('AI1;')
s.flushInput()

buff = ''

def process_events(context):
    while running:
        context.handleEvents()


# Travc's answer from http://stackoverflow.com/a/9147327/1290530
def twos_comp(val, bits):
    """compute the 2's compliment of int value val"""
    if( (val&(1<<(bits-1))) != 0 ):
        val = val - (1<<bits)
    return val

def handle_data_new(transfer):
    output = struct.unpack('BbBBBB', transfer.getBuffer())
    print output[1]
    s.write('FB;')
    match = None
    data = ''
    while not match:
        data += s.read(s.inWaiting())
        print "Data: ", data
        match = re.search(r'FB(0+)(.*);', data)
    zeros = match.group(1)
    new_freq = match.group(2)
    print "New freq: ", new_freq
    const = 10 * output[1]
    s.write('FB' + zeros + str(int(new_freq) + const) + ';');
    return True

def handle_data(transfer):
    global buff
    output = struct.unpack('BbBBBB', transfer.getBuffer())
    print output[1]
    s.write('FB;')
    freq = s.read(s.inWaiting())
    print "Frequency: ", freq
    print "Buffer: ", buff
    buff += freq
    split = buff.split(';')
    if split[0] != '':
        print "In split!"
        freq = split[0]
        print "New freq: ", freq
        buff = buff.replace(freq + ';', '', 1)
        if len(split) > 1:
            for data in split[1:]:
                buff += data
        match = re.match(r'FB(0+)(.+);', freq)
        if match:
            zeros = match.group(1)
            new_freq = re.sub(r'FB(0+)(.*)', r'\2', freq)
            const = 10 * output[1]
            s.write('FB' + zeros + str(int(new_freq) + const) + ';');
    return True

def main():
    try:
        print "Creating context"
        context = USBContext()
        print "Getting handle"
        dev = context.openByVendorIDAndProductID(0x077d, 0x0410)
        if dev.kernelDriverActive(0):
            dev.detachKernelDriver(0)
        print "Creaing helper"
        helper = USBTransferHelper()
        print "Setting callback"
        helper.setDefaultCallback(handle_data_new)
        print "Getting transfer"
        transfer = dev.getTransfer()
        transfer.setInterrupt(129, 6)
        transfer.setCallback(helper)

        thread = Thread(target=process_events, args=(context,)).start()

        transfer.submit()
        while True:
            pass
    except:
        print "Excepted!"
        global running
        running = False
        try:
            print "Cancelling!"
            transfer.cancel()
        except Exception as e:
            print "Whoops!"
            print e
            pass
        print "Closing"
        dev.close()
        if thread and thread.is_alive():
            print "Joining!"
            thread.join()
        print "Done!"

if __name__ == "__main__":
    main()
