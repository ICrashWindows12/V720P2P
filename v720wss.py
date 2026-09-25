#!/usr/bin/env python3

import asyncio
import base64
import json
import struct
import subprocess
import sys
import time
from urllib.parse import urlencode
import websockets


# ============================================================
# V720 CAMERA SETTINGS
# ============================================================

DEVICE_ID = ""

# This is the CAMERA/P2P token (tarPwd), NOT the V720 account JWT.
CAMERA_TOKEN = ""

SERVER_IP = ""
SERVER_PORT = ""
WSS_BASE = "wss://h5v720app.naxclowyun.com/p2p/live2"


# ============================================================
# BUILD THE SAME URL USED BY THE V720 WEB APP
# ============================================================

params = {
    "deviceId": DEVICE_ID,
    "token": CAMERA_TOKEN,
    "serverIp": SERVER_IP,
    "serverPort": SERVER_PORT,
}

WSS_URL = WSS_BASE + "?" + urlencode(params)


# ============================================================
# V720 PACKET TYPES
#
# From the V720 JavaScript:
#
# 0   = JSON/status
# 1   = JPEG video
# 4   = compressed audio
# 6   = PCM16 audio
# 301 = JSON command response
# ============================================================

TYPE_STATUS = 0
TYPE_JPEG = 1
TYPE_AUDIO = 4
TYPE_PCM = 6
TYPE_COMMAND = 301


# ============================================================
# V720 PACKET CREATION
#
# Browser:
#
# new ArrayBuffer(4 + payload.length)
# DataView.setUint32(0, type, true)
# payload starts at byte 4
# ============================================================

def make_packet(packet_type, payload):

    if isinstance(payload, str):
        payload = payload.encode("utf-8")

    return struct.pack("<I", packet_type) + payload


# ============================================================
# FFPLAY
# ============================================================

def start_ffplay():

    command = [
        "ffplay",
        "-loglevel", "warning",

        # Reduce buffering.
        "-fflags", "nobuffer",
        "-flags", "low_delay",

        # JPEG sequence.
        "-f", "mjpeg",

        # Read from stdin.
        "-i", "pipe:0",
    ]

    print()
    print("Starting ffplay...")
    print(" ".join(command))
    print()

    return subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    print("==============================================")
    print(" V720 WSS -> FFplay")
    print("==============================================")
    print()

    print("Device ID :", DEVICE_ID)
    print("Server    :", SERVER_IP)
    print("Port      :", SERVER_PORT)
    print("WSS URL   :", WSS_BASE)
    print()

    # ========================================================
    # RECONNECT LOOP
    # ========================================================

    while True:

        print("Connecting...")
        print()

        ffplay = None
        first_frame_saved = False
        frame_count = 0
        last_keepalive = time.monotonic()
        last_rx = time.monotonic()
        reconnecting = False

        try:

            # ------------------------------------------------
            # Connect to the exact URL the browser constructs.
            # ------------------------------------------------

            async with websockets.connect(
                WSS_URL,
                origin="https://h5v720app.naxclowyun.com",
                user_agent_header=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/153.0.0.0 Safari/537.36"
                ),
                max_size=None,

                # Keep the websocket alive at the protocol level.
                ping_interval=20,
                ping_timeout=20,

            ) as ws:

                print("CONNECTED")
                print()

                # ------------------------------------------------
                # This is EXACTLY what the V720 JavaScript does:
                #
                # p(0, JSON.stringify({code:30}))
                # ------------------------------------------------

                start_command = json.dumps(
                    {"code": 30},
                    separators=(",", ":"),
                )

                await ws.send(
                    make_packet(TYPE_STATUS, start_command)
                )

                print("TX type=0")
                print("TX payload:", start_command)
                print()

                print("Waiting for V720 packets...")
                print()

                # =================================================
                # WATCHDOG
                #
                # If absolutely nothing is received for 5 seconds,
                # reconnect the entire connection.
                # =================================================

                async def signal_watchdog():

                    nonlocal last_rx
                    nonlocal reconnecting

                    while True:

                        await asyncio.sleep(1)

                        if time.monotonic() - last_rx >= 5:

                            if not reconnecting:

                                reconnecting = True

                                print()
                                print("Signal lost, reconnecting...")
                                print()

                                try:
                                    await ws.close()
                                except Exception:
                                    pass

                            return

                watchdog_task = asyncio.create_task(
                    signal_watchdog()
                )

                try:

                    # ------------------------------------------------
                    # Receive packets.
                    # ------------------------------------------------

                    async for message in ws:

                        # Every received message resets the
                        # 5-second signal-loss timer.
                        last_rx = time.monotonic()

                        # ==================================================
                        # TEXT MESSAGE
                        # ==================================================

                        if isinstance(message, str):

                            print(
                                "RX TEXT:",
                                repr(message)
                            )

                            continue


                        # ==================================================
                        # BINARY MESSAGE
                        # ==================================================

                        if not isinstance(message, bytes):

                            print(
                                "RX UNKNOWN:",
                                type(message)
                            )

                            continue


                        if len(message) < 4:

                            print(
                                "RX SHORT PACKET:",
                                len(message),
                                "bytes"
                            )

                            continue


                        # --------------------------------------------------
                        # Read little-endian uint32 packet type.
                        # --------------------------------------------------

                        packet_type = struct.unpack_from(
                            "<I",
                            message,
                            0,
                        )[0]

                        payload = message[4:]


                        # ==================================================
                        # STATUS / JSON
                        # ==================================================

                        if packet_type == TYPE_STATUS:

                            try:

                                text = payload.decode(
                                    "utf-8",
                                    errors="replace",
                                )

                                print(
                                    "RX STATUS:",
                                    text
                                )

                            except Exception as e:

                                print(
                                    "RX STATUS decode error:",
                                    repr(e)
                                )

                            continue


                        # ==================================================
                        # JPEG VIDEO
                        # ==================================================

                        if packet_type == TYPE_JPEG:

                            frame_count += 1

                            print(
                                f"RX JPEG #{frame_count}: "
                                f"{len(payload):,} bytes"
                            )

                            # ------------------------------------------------
                            # Verify that this actually looks like JPEG.
                            #
                            # JPEG normally starts FF D8 and ends FF D9.
                            # ------------------------------------------------

                            if len(payload) >= 2:

                                start = payload[:2].hex(" ")
                                end = payload[-2:].hex(" ")

                                print(
                                    "    JPEG header:",
                                    start,
                                    "tail:",
                                    end
                                )


                            # ------------------------------------------------
                            # Save the first frame.
                            # ------------------------------------------------

                            if not first_frame_saved:

                                with open(
                                    "first_frame.jpg",
                                    "wb",
                                ) as f:

                                    f.write(payload)

                                first_frame_saved = True

                                print(
                                    "    Saved first frame as "
                                    "first_frame.jpg"
                                )


                            # ------------------------------------------------
                            # Start ffplay after the first real frame arrives.
                            # ------------------------------------------------

                            if ffplay is None:

                                ffplay = start_ffplay()


                            # ------------------------------------------------
                            # Feed JPEG directly into ffplay.
                            # ------------------------------------------------

                            try:

                                ffplay.stdin.write(payload)
                                ffplay.stdin.flush()

                            except (
                                BrokenPipeError,
                                OSError,
                            ):

                                print()
                                print(
                                    "ffplay closed its input."
                                )

                                break

                            continue


                        # ==================================================
                        # AUDIO
                        # ==================================================

                        if packet_type == TYPE_AUDIO:

                            print(
                                "RX AUDIO:",
                                len(payload),
                                "bytes"
                            )

                            # We deliberately ignore audio for now.

                            continue


                        # ==================================================
                        # PCM AUDIO
                        # ==================================================

                        if packet_type == TYPE_PCM:

                            print(
                                "RX PCM:",
                                len(payload),
                                "bytes"
                            )

                            # We deliberately ignore audio for now.

                            continue


                        # ==================================================
                        # COMMAND RESPONSE
                        # ==================================================

                        if packet_type == TYPE_COMMAND:

                            try:

                                text = payload.decode(
                                    "utf-8",
                                    errors="replace",
                                )

                                print(
                                    "RX COMMAND:",
                                    text
                                )

                            except Exception as e:

                                print(
                                    "RX COMMAND decode error:",
                                    repr(e)
                                )

                            continue


                        # ==================================================
                        # UNKNOWN PACKET
                        # ==================================================

                        print(
                            "RX UNKNOWN PACKET:",
                            "type=",
                            packet_type,
                            "length=",
                            len(payload),
                        )

                        print(
                            "    first bytes:",
                            payload[:32].hex(" ")
                        )


                        # ==================================================
                        # KEEPALIVE
                        #
                        # Browser source:
                        #
                        # const e = JSON.stringify({
                        #     code: 4,
                        #     unixTimer: Date.now()
                        # });
                        #
                        # p(301, e)
                        #
                        # ==================================================

                        now = time.monotonic()

                        if now - last_keepalive >= 8:

                            keepalive = json.dumps(
                                {
                                    "code": 4,
                                    "unixTimer": int(
                                        time.time() * 1000
                                    ),
                                },
                                separators=(",", ":"),
                            )

                            await ws.send(
                                make_packet(
                                    TYPE_COMMAND,
                                    keepalive,
                                )
                            )

                            print(
                                "TX KEEPALIVE:",
                                keepalive
                            )

                            last_keepalive = now

                finally:

                    watchdog_task.cancel()

                    try:
                        await watchdog_task
                    except asyncio.CancelledError:
                        pass


        except Exception as e:

            if not reconnecting:

                print()
                print("==============================================")
                print("CONNECTION ERROR")
                print("==============================================")

                print(
                    type(e).__name__,
                    ":",
                    str(e),
                )

                print()


        finally:

            if ffplay is not None:

                try:
                    ffplay.stdin.close()
                except Exception:
                    pass

                try:

                    ffplay.terminate()
                    ffplay.wait(timeout=2)

                except Exception:

                    try:
                        ffplay.kill()
                    except Exception:
                        pass

        # ========================================================
        # If the connection ended for ANY reason, start it again.
        # ========================================================

        print()
        print("Restarting connection...")
        print()

        await asyncio.sleep(1)


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        asyncio.run(main())

    except KeyboardInterrupt:

        print()
        print("Interrupted.")
