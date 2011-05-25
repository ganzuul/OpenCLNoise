#!/usr/bin/python
from openclnoise import *
from openclnoise.filterstack import ByteKernel
import optparse
import sys
import os

# Function to prompt for device selection
def askLongOptions(prompt,options):
    print("{0}:".format(prompt))
    for i,o in enumerate(options):
        print("\t{0}: {1}".format(i,o.name))
    while 1:
        x = raw_input('? ')
        try:
            x = int(x)
        except ValueError:
            print("Error: choose a number between 0 and {0}.".format(len(options)))
            continue
        if x < 0 or x >= len(options):
            print("Error: choose a number between 0 and {0}.".format(len(options)))
            continue
        return options[x]

# Handle command line options
parser = optparse.OptionParser()
parser.add_option("-d", "--device", # Which device to use?
    action="store", type=int, dest="device", default=None,
    help="which compute device to use (starts at 0)")
parser.add_option("-W", "--width",
    default=800, type=int, dest="width",
    help="width of output file (default: %default)")
parser.add_option("-H", "--height",
    default=800, type=int, dest="height",
    help="height of output file (default: %default)")
parser.add_option("-D", "--depth",
    default=1, type=int, dest="depth",
    help="depth of output file (default: %default)")
parser.add_option("-c", "--code",
    action="store", dest="savecode",
    help="save the generated kernel to this file")
parser.add_option("-s", "--scale",
    default=10, type=float, dest="scale",
    help="range from -scale/2 to scale/2 (default: %default)")
parser.add_option("-l", "--load",
    default=None, type=str, dest="load_path",
    help="the path specifying location of saved filter stack file")
parser.add_option("-f","--file",
    default=None, type=str, dest="filename",
    help="write image to this filename")
parser.add_option("-b","--byte",
    default=False, action="store_true", dest="byte_mode",
    help="use byte kernel (default: float for raw, byte for images)")
parser.add_option("-r","--raw",
    default=False, action="store_true", dest="raw_mode",
    help="write raw data (see README for format)")
(options, args) = parser.parse_args()

# Select a device
filter_runtime = FilterRuntime()
devices = filter_runtime.get_devices()
if len(devices) == 0:
    raise Exception("No OpenCL devices found.")
elif options.device is not None:
    filter_runtime.device = devices[options.device]
elif len(devices) >= 1: 
    filter_runtime.device = askLongOptions("Which compute device to use",devices)
else:
    filter_runtime.device = devices[0]

# Define input parameters
width = options.width
height = options.height
depth = options.depth
scale = options.scale

# build filter stack
fs = FilterStack(filter_runtime=filter_runtime)

# choose correct kernel
if options.byte_mode:
    fs.kernel = ByteKernel()

if options.load_path:
    fs.load(options.load_path)
else:
    # Push clear and scale-trans filters
    #from clear import Clear
    #from scaletrans import ScaleTrans
    #rom perlin import Perlin
    clear = Clear()
    #scale = ScaleTrans(scale=(scale*width/height,scale,scale,1), translate=(-scale/2.0*width/height,-scale/2.0,0,0))
    #scale = ScaleTrans(scale=(width/16,height/16,depth/16,1), translate=(0.5,0.5,0.5,0))
    scale = ScaleTrans(scale=(width/64,height/64,depth/64), translate=(1.0/128,1.0/128,1.0/128))
    cs = [clear,scale]

    # TESTING FILTERS HERE
    fs.push(cs)
    
    #~ fs.push(CheckerBoard())
    #~ fs.push(cs)
    #~ fs.push(Constant(constant_color=(1,0,0,1)))
    #~ fs.push(cs)
    #~ fs.push(Constant(constant_color=(0,1,0,1)))
    #~ fs.push(HeightMap(min_height=-5,max_height=5))
     
    fs.push(ZeroComponent(component='x'))
    fs.push(Worley(seed=321))
    fs.push(AddColor(color=.5))
    fs.push(cs)
    fs.push(Constant(constant_color=1.0))
    fs.push(cs)
    fs.push(Constant(constant_color=0.0))

    fs.push(HeightMap(max_height=width/64,component='x'))
    fs.push(Worley(seed=666))
    fs.push(Blend(mode="Darken"))
    
    # fs.push(cs)
    # fs.push(Worley(distance='manhattan', seed=809))
    # fs.push(cs)
    # fs.push(Worley(distance='manhattan', seed=908))
    # fs.push(cs)
    # fs.push(Worley(distance='manhattan'))
    # fs.push(cs)
    # fs.push(Perlin())
    # fs.push(cs)
    # fs.push(Worley(seed=666))
    # fs.push(Select())
    # fs.push(cs)
    # fs.push(Perlin(seed=897))
    # fs.push(Select())
    # fs.push(cs)
    # fs.push(Worley(seed=234))
    # fs.push(Select())
    # END TESTING FILTERS

print "Filters:"
for f in fs:
    print "\t%s" % (f,)

# Save code to file
if options.savecode:
    print "Saving kernel code to %s." % (options.savecode,)
    with open(options.savecode,'w') as out:
        out.write(fs.generate_code())

# Run!
if options.filename:
    if options.raw_mode: # Raw mode
        print "Saving output to %dx%dx%d raw file '%s'" % (width,height,depth,options.filename)
        fs.run_to_file(options.filename,width,height,depth)
    else: # Image mode
        print "Saving output to %dx%d image '%s'" % (width,height,options.filename)
        fs.save_image(options.filename,width,height)
else:
    print "Running and discarding output of %dx%dx%d data" % (width,height,depth)
    fs.run_to_discard(width,height,depth)

# Time
print "Last run took: %.2fms" % (fs.last_run_time*1000.0,)
