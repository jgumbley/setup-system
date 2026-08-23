#!/usr/bin/env python3
"""Pair, reconnect, and verify Rocks' Xbox Elite controller."""

import curses
import socket
import time

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from evdev import InputDevice, ecodes, list_devices
from gi.repository import GLib


HOSTNAME = "rocks"
CONTROLLER_NAME = "Xbox Elite Wireless Controller"
CONTROLLER_ADDRESS = "98:7A:14:3F:25:77"
BLUEZ = "org.bluez"
ADAPTER_IFACE = "org.bluez.Adapter1"
DEVICE_IFACE = "org.bluez.Device1"
PROPERTIES_IFACE = "org.freedesktop.DBus.Properties"
OBJECT_MANAGER_IFACE = "org.freedesktop.DBus.ObjectManager"
AGENT_MANAGER_IFACE = "org.bluez.AgentManager1"
AGENT_IFACE = "org.bluez.Agent1"
AGENT_PATH = "/setup_system/xbox_agent"


class PairingAgent(dbus.service.Object):
    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Release(self):
        return None

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, _device):
        return "0000"

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, _device):
        return dbus.UInt32(0)

    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, _device, _passkey):
        return None

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, _device):
        return None

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, _device, _uuid):
        return None

    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Cancel(self):
        return None


class XboxControllerUI:
    def __init__(self, screen):
        self.screen = screen
        self.bus = dbus.SystemBus()
        self.manager = dbus.Interface(
            self.bus.get_object(BLUEZ, "/"), OBJECT_MANAGER_IFACE
        )
        self.agent = PairingAgent(self.bus, AGENT_PATH)
        self.agent_manager = dbus.Interface(
            self.bus.get_object(BLUEZ, "/org/bluez"), AGENT_MANAGER_IFACE
        )
        self.agent_manager.RegisterAgent(AGENT_PATH, "NoInputNoOutput")
        self.agent_registered = True

        self.adapter_path = self.find_adapter()
        self.adapter = dbus.Interface(
            self.bus.get_object(BLUEZ, self.adapter_path), ADAPTER_IFACE
        )
        self.adapter_properties = dbus.Interface(
            self.bus.get_object(BLUEZ, self.adapter_path), PROPERTIES_IFACE
        )
        self.adapter_properties.Set(ADAPTER_IFACE, "Powered", dbus.Boolean(True))

        self.device_path = f"{self.adapter_path}/dev_{CONTROLLER_ADDRESS.replace(':', '_')}"
        self.device_properties = {}
        self.pending_action = None
        self.discovery_started = False
        self.retry_at = 0.0
        self.last_poll = 0.0
        self.last_error = ""
        self.pair_completed = False
        self.pair_attempted = False
        self.connect_attempted = False
        self.phase = "STARTING"
        self.instruction = "Press nothing while Bluetooth status is checked."
        self.input_device = None
        self.seen = {"up": False, "down": False, "left": False, "right": False}
        self.face_button_seen = False
        self.done = False

    def find_adapter(self):
        adapters = [
            path
            for path, interfaces in self.manager.GetManagedObjects().items()
            if ADAPTER_IFACE in interfaces
        ]
        if len(adapters) != 1:
            raise RuntimeError(f"Expected one Bluetooth adapter, found {len(adapters)}")
        return str(adapters[0])

    def refresh_device(self):
        objects = self.manager.GetManagedObjects()
        interfaces = objects.get(dbus.ObjectPath(self.device_path), {})
        properties = interfaces.get(DEVICE_IFACE)
        if properties is None:
            for path, candidate in objects.items():
                candidate_properties = candidate.get(DEVICE_IFACE, {})
                if str(candidate_properties.get("Name", "")) == CONTROLLER_NAME:
                    self.device_path = str(path)
                    properties = candidate_properties
                    break
        self.device_properties = dict(properties or {})

    def property_is_true(self, name):
        return bool(self.device_properties.get(name, False))

    def device_interface(self):
        return dbus.Interface(
            self.bus.get_object(BLUEZ, self.device_path), DEVICE_IFACE
        )

    def set_device_property(self, name, value):
        properties = dbus.Interface(
            self.bus.get_object(BLUEZ, self.device_path), PROPERTIES_IFACE
        )
        properties.Set(DEVICE_IFACE, name, dbus.Boolean(value))

    def start_discovery(self):
        if self.discovery_started:
            return
        try:
            self.adapter.StartDiscovery()
        except dbus.DBusException as error:
            if error.get_dbus_name() != "org.bluez.Error.InProgress":
                raise
        self.discovery_started = True

    def stop_discovery(self):
        if not self.discovery_started:
            return
        try:
            self.adapter.StopDiscovery()
        except dbus.DBusException as error:
            if error.get_dbus_name() != "org.bluez.Error.NotReady":
                raise
        self.discovery_started = False

    def action_succeeded(self, action):
        self.pending_action = None
        self.last_error = ""
        self.retry_at = time.monotonic() + 1.0
        if action == "pair":
            self.pair_completed = True
            self.phase = "CONNECTING"
            self.instruction = "Pairing completed. Press nothing while it connects."
        elif action == "connect":
            self.pair_completed = False

    def action_failed(self, action, error):
        self.pending_action = None
        if action == "connect":
            self.pair_completed = False
        self.last_error = f"{action}: {error.get_dbus_message()}"
        self.retry_at = time.monotonic() + 2.0

    def begin_action(self, action):
        if self.pending_action is not None:
            return
        interface = self.device_interface()
        self.pending_action = action
        if action == "pair":
            interface.Pair(
                reply_handler=lambda: self.action_succeeded("pair"),
                error_handler=lambda error: self.action_failed("pair", error),
            )
        else:
            interface.Connect(
                reply_handler=lambda: self.action_succeeded("connect"),
                error_handler=lambda error: self.action_failed("connect", error),
            )

    def open_input_device(self):
        if self.input_device is not None:
            return True
        matches = []
        for path in list_devices():
            device = InputDevice(path)
            if device.name == CONTROLLER_NAME:
                matches.append(device)
            else:
                device.close()
        if len(matches) != 1:
            for device in matches:
                device.close()
            return False
        self.input_device = matches[0]
        self.input_device.grab()
        return True

    def close_input_device(self):
        if self.input_device is None:
            return
        try:
            self.input_device.ungrab()
        except OSError:
            pass
        self.input_device.close()
        self.input_device = None

    def record_input(self):
        if self.input_device is None:
            return
        try:
            while True:
                event = self.input_device.read_one()
                if event is None:
                    break
                if event.type == ecodes.EV_ABS:
                    if event.code == ecodes.ABS_HAT0X and event.value == -1:
                        self.seen["left"] = True
                    elif event.code == ecodes.ABS_HAT0X and event.value == 1:
                        self.seen["right"] = True
                    elif event.code == ecodes.ABS_HAT0Y and event.value == -1:
                        self.seen["up"] = True
                    elif event.code == ecodes.ABS_HAT0Y and event.value == 1:
                        self.seen["down"] = True
                elif event.type == ecodes.EV_KEY and event.value == 1:
                    dpad_keys = {
                        getattr(ecodes, "BTN_DPAD_UP", -1): "up",
                        getattr(ecodes, "BTN_DPAD_DOWN", -1): "down",
                        getattr(ecodes, "BTN_DPAD_LEFT", -1): "left",
                        getattr(ecodes, "BTN_DPAD_RIGHT", -1): "right",
                    }
                    if event.code in dpad_keys:
                        self.seen[dpad_keys[event.code]] = True
                    if event.code in {
                        ecodes.BTN_SOUTH,
                        ecodes.BTN_EAST,
                        ecodes.BTN_NORTH,
                        ecodes.BTN_WEST,
                    }:
                        self.face_button_seen = True
        except OSError:
            self.close_input_device()

        if all(self.seen.values()) and self.face_button_seen:
            self.phase = "READY"
            self.instruction = "Controller input works. Press Enter to close."
            self.close_input_device()

    def update_state(self):
        now = time.monotonic()
        if now - self.last_poll >= 0.25:
            self.refresh_device()
            self.last_poll = now

        connected = self.property_is_true("Connected")
        paired = self.property_is_true("Paired")

        if connected:
            self.pair_completed = False
            self.pair_attempted = False
            self.connect_attempted = False
            self.stop_discovery()
            if not self.property_is_true("Trusted"):
                self.set_device_property("Trusted", True)
            if "WakeAllowed" in self.device_properties and not self.property_is_true(
                "WakeAllowed"
            ):
                self.set_device_property("WakeAllowed", True)
            if self.open_input_device():
                if self.phase != "READY":
                    self.phase = "TESTING"
                    self.instruction = (
                        "Press every D-pad direction and one A/B/X/Y button."
                    )
                    self.record_input()
            else:
                self.phase = "WAITING FOR INPUT"
                self.instruction = (
                    "Press nothing while Linux creates the controller input device."
                )
            return

        self.close_input_device()
        if self.pending_action == "pair":
            self.phase = "PAIRING"
            self.instruction = "Pairing now. Release the pairing button and press nothing."
            return
        if self.pending_action == "connect":
            self.phase = "CONNECTING"
            self.instruction = "Press nothing while Bluetooth connects the controller."
            return

        if self.pair_completed:
            self.phase = "CONNECTING"
            self.instruction = "Pairing completed. Press nothing while it connects."
            self.connect_attempted = True
            self.begin_action("connect")
            return

        self.start_discovery()
        controller_present = self.device_properties.get("RSSI") is not None
        if not controller_present:
            self.pair_attempted = False
            self.connect_attempted = False

        if paired:
            self.phase = "WAITING TO RECONNECT"
            self.instruction = "Press the Xbox logo once. Do not hold the pairing button."
            if controller_present and not self.connect_attempted and now >= self.retry_at:
                self.connect_attempted = True
                self.begin_action("connect")
            return

        self.phase = "WAITING TO PAIR"
        self.instruction = (
            "Hold the small button beside USB-C until the Xbox logo flashes rapidly, "
            "then release it."
        )
        if controller_present and not self.pair_attempted and now >= self.retry_at:
            self.pair_attempted = True
            self.begin_action("pair")

    def add_line(self, row, text, attributes=0):
        height, width = self.screen.getmaxyx()
        if row < height:
            self.screen.addnstr(row, 1, text, max(1, width - 2), attributes)

    @staticmethod
    def yes_no(value):
        return "YES" if value else "NO"

    def draw(self):
        self.screen.erase()
        self.add_line(1, "Xbox Elite Controller — rocks", curses.A_BOLD)
        self.add_line(3, f"State       {self.phase}", curses.A_BOLD)
        self.add_line(
            4, f"Paired      {self.yes_no(self.property_is_true('Paired'))}"
        )
        self.add_line(
            5, f"Bonded      {self.yes_no(self.property_is_true('Bonded'))}"
        )
        self.add_line(
            6, f"Trusted     {self.yes_no(self.property_is_true('Trusted'))}"
        )
        self.add_line(
            7, f"Connected   {self.yes_no(self.property_is_true('Connected'))}"
        )
        self.add_line(9, self.instruction, curses.A_BOLD)
        if self.last_error:
            self.add_line(11, f"Last Bluetooth result: {self.last_error}")

        mark = lambda name: "X" if self.seen[name] else " "
        self.add_line(13, f"                 [{mark('up')}] UP")
        self.add_line(
            14,
            f" [{mark('left')}] LEFT                    [{mark('right')}] RIGHT",
        )
        self.add_line(15, f"                [{mark('down')}] DOWN")
        self.add_line(17, f" A/B/X/Y button          [{'X' if self.face_button_seen else ' '}] ")
        self.add_line(19, "q: close")
        self.screen.refresh()

    def run(self):
        curses.curs_set(0)
        self.screen.nodelay(True)
        self.screen.timeout(50)
        while not self.done:
            context = GLib.MainContext.default()
            while context.pending():
                context.iteration(False)
            self.update_state()
            if self.phase == "TESTING":
                self.record_input()
            self.draw()
            key = self.screen.getch()
            if key in (ord("q"), 27):
                self.done = True
            elif self.phase == "READY" and key in (curses.KEY_ENTER, 10, 13):
                self.done = True

    def close(self):
        self.close_input_device()
        try:
            self.stop_discovery()
        finally:
            if self.agent_registered:
                try:
                    self.agent_manager.UnregisterAgent(AGENT_PATH)
                except dbus.DBusException:
                    pass


def run(screen):
    ui = XboxControllerUI(screen)
    try:
        ui.run()
    finally:
        ui.close()


def main():
    if socket.gethostname() != HOSTNAME:
        raise SystemExit(f"Xbox controller pairing is only supported on {HOSTNAME}.")
    DBusGMainLoop(set_as_default=True)
    try:
        curses.wrapper(run)
    except Exception as error:
        raise SystemExit(f"Xbox controller utility failed: {error}") from error


if __name__ == "__main__":
    main()
