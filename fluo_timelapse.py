#!/usr/bin/env python3

import os
import sys
import time
import json
import argparse

# filter wheel
import hid
# relay switch
import serial
# camera
import gphoto2 as gp

DEBUG = True
config_dict = {
    'camera': {
        'aWHITE': {
            'exp': '1/4',
            'iso': '200',
            'f_val': '2',
        },
        'bGFP': {
            'exp': '1/25',
            'iso': '400',
            'f_val': '1',
        },
        'cCFP': {
            'exp': '1',
            'iso': '800',
            'f_val': '9',
        },
        'mCherry': {
            'exp': '2',
            'iso': '1600',
            'f_val': '1',
        },
    },
    'wheel': {
        'ven_id': 0x1278,
        'pro_id': 0x0920,
        'filters': ['aWHITE', 'bGFP', 'cCFP', 'mCherry'],
    },
    'relay': {
        'path': '/dev/tty.usbmodem1421',
    },
    'interval': 5,
    'work_dir': '.',
    'out_fmt': 'arw',
}


# class CameraException(Exception):
#     pass
#
# class WheelException(Exception):
#     pass
#
# class RelayException(Exception):
#     pass


def clean_env(camera, wheel, relay):

    if DEBUG:
        print('Closing camera connection...', file=sys.stderr)

    gp.check_result(gp.gp_camera_exit(camera))

    if DEBUG:
        print('Camera connection closed', file=sys.stderr)
        print('Closing filter wheel connection...', file=sys.stderr)

    wheel.close()

    if DEBUG:
        print('Filter wheel connection closed', file=sys.stderr)
        print('Closing relay switch connection...', file=sys.stderr)

    relay.close()

    if DEBUG:
        print('Relay switch connection closed', file=sys.stderr)

def set_camera_config(camera, exp, iso, f_val):

    if DEBUG:
        print('Getting previous camera configuration...', file=sys.stderr)
    camera_config = camera.get_config()

    error, exp_conf = gp.gp_widget_get_child_by_name(camera_config, 'shutterspeed')
    assert error == 0, "ERROR while retrieving current exposure"
    error, iso_conf = gp.gp_widget_get_child_by_name(camera_config, 'iso')
    assert error == 0, "ERROR while retrieving current ISO"
    error, f_conf = gp.gp_widget_get_child_by_name(camera_config, 'f-number')
    assert error == 0, "ERROR while retrieving current aperture"

    error = gp.check_result(gp.gp_widget_set_value(exp_conf, exp))
    assert error == 0, "ERROR while setting exposure to {}".format(exp)
    error = gp.check_result(gp.gp_widget_set_value(iso_conf, iso))
    assert error == 0, "ERROR while setting ISO to {}".format(iso)
    error = gp.check_result(gp.gp_widget_set_value(f_conf, f_val))
    assert error == 0, "ERROR while setting aperture to {}".format(f_val)

    if DEBUG:
        print('Setting new camera configuration...', file=sys.stderr)
    error = gp.check_result(gp.gp_camera_set_config(camera, camera_config))
    assert error == 0, "ERROR while setting camera configuration"
    if DEBUG:
        print('New camera configuration set', file=sys.stderr)


def timelapse(camera, wheel, relay, config_dict):

    ch_idx = 0
    capture_idx = -1
    work_dir = config_dict['work_dir']
    interval = config_dict['interval']
    out_fmt = config_dict['out_fmt']
    channels = config_dict['wheel']['filters']
    assert len(config_dict['camera']) == len(channels), "ERROR: Different number of channels for camera and filter wheel"
    ch = channels[0]

    # INIT
    exp = str(config_dict['camera'][ch]['exp'])
    iso = str(config_dict['camera'][ch]['iso'])
    f_val = float(config_dict['camera'][ch]['f_val'])
    set_camera_config(camera, exp, iso, f_val)
    relay.write("reset\n\r".encode('utf-8'))
    wheel.write([1, 0])

    try:
        while True:
            if ch_idx == 0:
                capture_idx += 1

            if DEBUG:
                print("CHANNEL {} (ch) [IT {}]".format(ch_idx, capture_idx), file=sys.stderr)

            # LIGHTS UP AND CAPTURE
            if DEBUG:
                print("Lights up...", file=sys.stderr)
            relay_cmd = "relay on {}\n\r".format(ch_idx).encode('utf-8')
            relay.write(relay_cmd)
            if DEBUG:
                print("Lights up! Relay status:", file=sys.stderr)
                relay_cmd = "relay readall\n\r".encode('utf-8')
                relay.write(relay_cmd)
                print(relay.readlines(), file=sys.stderr)
                print("Shoot...", file=sys.stderr)
            camera_fn = gp.check_result(gp.gp_camera_capture(camera, gp.GP_CAPTURE_IMAGE))
            if DEBUG:
                print("Shoot!", file=sys.stderr)
                print("Lights down...", file=sys.stderr)
            relay_cmd = "relay off {}\n\r".format(ch_idx).encode('utf-8')
            relay.write(relay_cmd)
            if DEBUG:
                print("Lights down! Relay status:", file=sys.stderr)
                relay_cmd = "relay readall\n\r".encode('utf-8')
                relay.write(relay_cmd)
                print(relay.readlines(), file=sys.stderr)

            # SAVE PICTURE
            # TODO: save all channels' pictures during sleep
            if DEBUG:
                print('Saving picture...', file=sys.stderr)
            camera_f = gp.check_result(gp.gp_camera_file_get(camera, camera_fn.folder, camera_fn.name, gp.GP_FILE_TYPE_NORMAL))
            out_fn = os.path.join(work_dir, "{}_{}.{}".format(str(capture_idx).zfill(10), ch, out_fmt))
            gp.check_result(gp.gp_file_save(camera_f, out_fn))
            if DEBUG:
                print('Picture saved', file=sys.stderr)

            if ch_idx == 0:
                time_first_shot = time.time()

            # GET READY FOR NEXT SHOT
            ch_idx = (ch_idx+1) % len(channels)
            ch = channels[ch_idx]
            # TODO: multithreaded/asynchronous config
            exp = str(config_dict['camera'][ch]['exp'])
            iso = str(config_dict['camera'][ch]['iso'])
            f_val = float(config_dict['camera'][ch]['f_val'])
            set_camera_config(camera, exp, iso, f_val)
            # TODO: check that the wheel is on the right position
            if DEBUG:
                print('Rotating filter wheel...', file=sys.stderr)
            wheel.write([ch_idx+1, 0])
            if DEBUG:
                print('Filter wheel rotated', file=sys.stderr)

            if ch_idx == len(channels)-1:
                # just to be sure...if relay off command lost, screw up only one shot
                relay.write("reset\n\r".encode('utf-8'))
                if DEBUG:
                    print("Relay switch reset! Relay status:", file=sys.stderr)
                    relay_cmd = "relay readall\n\r".encode('utf-8')
                    relay.write(relay_cmd)
                    print(relay.readlines(), file=sys.stderr)
                # TODO: sleep the diff between time of first shot and now
                # (so that same channel has ~ interval)
                time.sleep(interval)

    except KeyboardInterrupt:
        clean_env(camera, wheel, relay)


def init_camera(**kwd_args):

    context = gp.gp_context_new()
    error, camera = gp.gp_camera_new()
    error = gp.gp_camera_init(camera, context)

    if DEBUG:
        error, summary = gp.gp_camera_get_summary(camera, context)
        print('Summary', file=sys.stderr)
        print('=======', file=sys.stderr)
        print(summary.text, file=sys.stderr)

    return camera


def init_wheel(ven_id, pro_id, **kwd_args):

    wheel = hid.device()
    wheel.open(ven_id, pro_id)

    if DEBUG:
        # TODO: check filter total positions
        if not wheel:
            print("Error", file=sys.stderr)

    return wheel


def init_relay(path, **kwd_args):

    relay = serial.Serial(path, 19200, timeout=1)
    relay.write(b'reset\n\r')

    if DEBUG:
        relay.readlines()
        relay.write(b'relay readall\n\r')
        res = relay.readlines()
        # TODO: check that all relays are off
        if not res:
            print("Error", file=sys.stderr)

    return relay


def parse_args():

    desc = "Script for running fluorescent timelapses"

    parser = argparse.ArgumentParser(description=desc)

    parser.add_argument(
        'config_fn',
        metavar='conf.json',
        type=str,
        help='json file containing the channel configurations'
    )

    args = parser.parse_args()
    return args


def main(config_dict):

    if DEBUG:
        print('Initializing camera connection...', file=sys.stderr)

    camera = init_camera(**config_dict['camera'])

    if DEBUG:
        print('Camera connection initialized', file=sys.stderr)
        print('Initializing filter wheel connection...', file=sys.stderr)

    wheel = init_wheel(**config_dict['wheel'])

    if DEBUG:
        print('Filter wheel connection initialized', file=sys.stderr)
        print('Initializing relay switch connection...', file=sys.stderr)

    relay = init_relay(**config_dict['relay'])

    if DEBUG:
        print('Relay switch connection initialized', file=sys.stderr)
        print('Starting timelapse', file=sys.stderr)

    timelapse(camera, wheel, relay, config_dict)


if __name__ == '__main__':

    if len(sys.argv) > 1:
        args = parse_args()
        with open(args.config_fn, 'r') as config_f:
            config_dict = json.load(config_f)

    if DEBUG:
        print(config_dict, file=sys.stderr)

    main(config_dict)
