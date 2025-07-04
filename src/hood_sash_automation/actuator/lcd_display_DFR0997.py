#!/usr/bin/env python3
'''
Python wrapper for the DFR0997 “Gravity” IPS display (V2.0 protocol).
Based on DFRobot_LcdDisplay.h from:
https://github.com/DFRobot/DFRobot_LcdDisplay/blob/master/src/DFRobot_LcdDisplay.h
'''

import smbus2
import time

class DFRobotLCD:
    # I2C defaults
    DEFAULT_BUS  = 1
    DEFAULT_ADDR = 0x2C

    # Packet header bytes (CMD_HEADER_HIGH, CMD_HEADER_LOW)
    HDR_HIGH = 0x55
    HDR_LOW  = 0xAA

    def __init__(self, bus=DEFAULT_BUS, address=DEFAULT_ADDR):
        self.bus = smbus2.SMBus(bus)
        self.addr = address
        time.sleep(0.1)  # allow firmware to boot

    def _cmd(self, cmd_id: int, params: bytes = b''):
        length = 1 + len(params)
        pkt = [self.HDR_HIGH, self.HDR_LOW, length, cmd_id] + list(params)
        print(f"[I2C SEND] CMD=0x{cmd_id:02X}, LEN={length}, BYTES={pkt}")
        self.bus.write_i2c_block_data(self.addr, 0x00, pkt)
        time.sleep(0.01)

    def begin(self):
        time.sleep(0.1)

    def clean_screen(self):
        self._cmd(0x1D)

    def set_background_color(self, rgb: int):
        r = (rgb >> 16) & 0xFF
        g = (rgb >> 8)  & 0xFF
        b = rgb & 0xFF
        self._cmd(0x19, bytes([r, g, b]))

    def set_backlight(self, brightness: int):
        b = max(0, min(255, brightness))
        self._cmd(0x41, bytes([b]))

    def set_background_img(self, location: int, path: str):
        data = path.encode('utf-8')  # Do NOT null-terminate
        params = bytes([location]) + data
        self._cmd(0x1A, params)


    def draw_pixel(self, x: int, y: int, rgb: int):
        r = (rgb >> 16) & 0xFF; g = (rgb >> 8) & 0xFF; b = rgb & 0xFF
        params = bytes([
            (x >> 8) & 0xFF, x & 0xFF,
            (y >> 8) & 0xFF, y & 0xFF,
            r, g, b
        ])
        self._cmd(0x02, params)

    def draw_line(self, x0, y0, x1, y1, width, rgb):
        r = (rgb >> 16) & 0xFF; g = (rgb >> 8) & 0xFF; b = rgb & 0xFF
        params = bytes([
            0x01,
            width,
            r, g, b,
            (x0>>8)&0xFF, x0&0xFF,
            (y0>>8)&0xFF, y0&0xFF,
            (x1>>8)&0xFF, x1&0xFF,
            (y1>>8)&0xFF, y1&0xFF
        ])
        self._cmd(0x03, params)

    def delete_line(self, obj_id):
        params = bytes([0x03, obj_id])
        self._cmd(0x1B, params)

    def draw_rect(self, x, y, w, h, border, border_color, fill, fill_color, rounded):
        bc = [ (border_color>>16)&0xFF, (border_color>>8)&0xFF, border_color&0xFF ]
        fc = [ (fill_color>>16)&0xFF, (fill_color>>8)&0xFF, fill_color&0xFF ]
        params = bytes([
            0x01,  # ID placeholder
            border, *bc,
            fill, *fc,
            rounded,
            (x>>8)&0xFF, x&0xFF,
            (y>>8)&0xFF, y&0xFF,
            (w>>8)&0xFF, w&0xFF,
            (h>>8)&0xFF, h&0xFF
        ])
        self._cmd(0x04, params)

    def delete_rect(self, obj_id):
        self._cmd(0x1B, bytes([0x04, obj_id]))

    def draw_circle(self, x, y, r, border, border_color, fill, fill_color):
        bc = [ (border_color>>16)&0xFF, (border_color>>8)&0xFF, border_color&0xFF ]
        fc = [ (fill_color>>16)&0xFF, (fill_color>>8)&0xFF, fill_color&0xFF ]
        params = bytes([
            0x01, border, *bc, fill, *fc,
            (r>>8)&0xFF, r&0xFF,
            (x>>8)&0xFF, x&0xFF,
            (y>>8)&0xFF, y&0xFF
        ])
        self._cmd(0x06, params)

    def delete_circle(self, obj_id):
        self._cmd(0x1B, bytes([0x06, obj_id]))

    def draw_icon(self, x, y, icon_num, size=255):
        params = bytes([
            0x00,
            (icon_num>>8)&0xFF, icon_num&0xFF,
            (size>>8)&0xFF, size&0xFF,
            (x>>8)&0xFF, x&0xFF,
            (y>>8)&0xFF, y&0xFF
        ])
        self._cmd(0x08, params)

    def draw_icon_external(self, x, y, path: str, zoom=255):
        data = path.encode('utf-8') + b'\\x00'
        params = bytes([
            0x00,
            (zoom>>8)&0xFF, zoom&0xFF,
            (x>>8)&0xFF, x&0xFF,
            (y>>8)&0xFF, y&0xFF
        ]) + data
        self._cmd(0x09, params)

    def draw_gif_external(self, x, y, path: str, zoom=255):
        data = path.encode('utf-8')  # do NOT null-terminate — the protocol omits \x00
        params = bytes([
            0x00,  # ID placeholder
            (zoom >> 8) & 0xFF, zoom & 0xFF,
            (x >> 8) & 0xFF, x & 0xFF,
            (y >> 8) & 0xFF, y & 0xFF
        ]) + data
        self._cmd(0x20, params)  # 0x21 is CMD_OF_DRAW_GIF_EXTERNAL

    def delete_gif(self, obj_id):
        self._cmd(0x1B, bytes([0x14, obj_id]))


    def draw_string(self, x, y, text, font=0, color=0xFFFFFF):
        data = text.encode('utf-8')
        params = bytes([
            0x01, font,
            (color>>16)&0xFF, (color>>8)&0xFF, color&0xFF,
            (x>>8)&0xFF, x&0xFF,
            (y>>8)&0xFF, y&0xFF
        ]) + data
        self._cmd(0x18, params)