# Automatically generated
# with the command '/home/arthur-22/spacewire/gateware/sources/FPGA-design/script_support/components/SYZYGY/SPACEWIRE/.venv/bin/ipxact2py --srcFile ipxact/spacewire.xml --destDir python'
#
# Do not manually edit!
#

from enum import IntEnum

from .acces_layer import *


class control_type(Register):
    """
    SpaceWire link control register.
    """

    def __init__(
        self,
        parent_ip: IP,
        address_offset: int,
    ):
        super().__init__(
            parent_ip,
            address_offset,
        )
        # [0]
        # Start the SpaceWire link state machine.
        self._link_start = IntegerField(
            self,
            bit_width=1,
            bit_offset=0,
            access="read-write",
            minimum=None,
            maximum=None,
        )
        # [1]
        # Enable automatic SpaceWire link startup.
        self._autostart = IntegerField(
            self,
            bit_width=1,
            bit_offset=1,
            access="read-write",
            minimum=None,
            maximum=None,
        )
        # [2]
        # Disable the SpaceWire link.
        self._link_disable = IntegerField(
            self,
            bit_width=1,
            bit_offset=2,
            access="read-write",
            minimum=None,
            maximum=None,
        )
        # [31:3]
        # unused
        self._unused0 = IntegerField(
            self,
            bit_width=29,
            bit_offset=3,
            access="read-write",
            minimum=None,
            maximum=None,
        )

    @property
    def link_start(self):
        return self._link_start.get()

    @link_start.setter
    def link_start(self, value: int):
        self._link_start.set(value)

    @property
    def autostart(self):
        return self._autostart.get()

    @autostart.setter
    def autostart(self, value: int):
        self._autostart.set(value)

    @property
    def link_disable(self):
        return self._link_disable.get()

    @link_disable.setter
    def link_disable(self, value: int):
        self._link_disable.set(value)

    @property
    def unused0(self):
        return self._unused0.get()

    @unused0.setter
    def unused0(self, value: int):
        self._unused0.set(value)


class status_type(Register):
    """
    Current SpaceWire link and FIFO status.
    """

    def __init__(
        self,
        parent_ip: IP,
        address_offset: int,
    ):
        super().__init__(
            parent_ip,
            address_offset,
        )
        # [0]
        # SpaceWire link startup has started.
        self._started = IntegerField(
            self,
            bit_width=1,
            bit_offset=0,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [1]
        # SpaceWire link is currently establishing a connection.
        self._connecting = IntegerField(
            self,
            bit_width=1,
            bit_offset=1,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [2]
        # SpaceWire link is in the Run state.
        self._running = IntegerField(
            self,
            bit_width=1,
            bit_offset=2,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [3]
        # SpaceWire transmitter can accept another character.
        self._tx_ready = IntegerField(
            self,
            bit_width=1,
            bit_offset=3,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [4]
        # SpaceWire transmit FIFO is at least half full.
        self._tx_half_full = IntegerField(
            self,
            bit_width=1,
            bit_offset=4,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [5]
        # A received SpaceWire character is available.
        self._rx_valid = IntegerField(
            self,
            bit_width=1,
            bit_offset=5,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [6]
        # SpaceWire receive FIFO is at least half full.
        self._rx_half_full = IntegerField(
            self,
            bit_width=1,
            bit_offset=6,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [31:7]
        # unused
        self._unused0 = IntegerField(
            self,
            bit_width=25,
            bit_offset=7,
            access="read-only",
            minimum=None,
            maximum=None,
        )

    @property
    def started(self):
        return self._started.get()

    @started.setter
    def started(self, value: int):
        self._started.set(value)

    @property
    def connecting(self):
        return self._connecting.get()

    @connecting.setter
    def connecting(self, value: int):
        self._connecting.set(value)

    @property
    def running(self):
        return self._running.get()

    @running.setter
    def running(self, value: int):
        self._running.set(value)

    @property
    def tx_ready(self):
        return self._tx_ready.get()

    @tx_ready.setter
    def tx_ready(self, value: int):
        self._tx_ready.set(value)

    @property
    def tx_half_full(self):
        return self._tx_half_full.get()

    @tx_half_full.setter
    def tx_half_full(self, value: int):
        self._tx_half_full.set(value)

    @property
    def rx_valid(self):
        return self._rx_valid.get()

    @rx_valid.setter
    def rx_valid(self, value: int):
        self._rx_valid.set(value)

    @property
    def rx_half_full(self):
        return self._rx_half_full.get()

    @rx_half_full.setter
    def rx_half_full(self, value: int):
        self._rx_half_full.set(value)

    @property
    def unused0(self):
        return self._unused0.get()

    @unused0.setter
    def unused0(self, value: int):
        self._unused0.set(value)


class tx_data_type(Register):
    """
    SpaceWire transmit character register. A write requests transmission when TX_READY is high.
    """

    def __init__(
        self,
        parent_ip: IP,
        address_offset: int,
    ):
        super().__init__(
            parent_ip,
            address_offset,
        )
        # [7:0]
        # SpaceWire transmit character data.
        self._data = IntegerField(
            self,
            bit_width=8,
            bit_offset=0,
            access="read-write",
            minimum=None,
            maximum=None,
        )
        # [8]
        # SpaceWire transmit data or control flag.
        self._flag = IntegerField(
            self,
            bit_width=1,
            bit_offset=8,
            access="read-write",
            minimum=None,
            maximum=None,
        )
        # [31:9]
        # unused
        self._unused0 = IntegerField(
            self,
            bit_width=23,
            bit_offset=9,
            access="read-write",
            minimum=None,
            maximum=None,
        )

    @property
    def data(self):
        return self._data.get()

    @data.setter
    def data(self, value: int):
        self._data.set(value)

    @property
    def flag(self):
        return self._flag.get()

    @flag.setter
    def flag(self, value: int):
        self._flag.set(value)

    @property
    def unused0(self):
        return self._unused0.get()

    @unused0.setter
    def unused0(self, value: int):
        self._unused0.set(value)


class rx_data_type(Register):
    """
    SpaceWire receive character register. Reading valid data consumes the current received character.
    """

    def __init__(
        self,
        parent_ip: IP,
        address_offset: int,
    ):
        super().__init__(
            parent_ip,
            address_offset,
        )
        # [7:0]
        # Received SpaceWire character data.
        self._data = IntegerField(
            self,
            bit_width=8,
            bit_offset=0,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [8]
        # Received SpaceWire data or control flag.
        self._flag = IntegerField(
            self,
            bit_width=1,
            bit_offset=8,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [9]
        # Indicates that a received SpaceWire character is available.
        self._valid = IntegerField(
            self,
            bit_width=1,
            bit_offset=9,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [31:10]
        # unused
        self._unused0 = IntegerField(
            self,
            bit_width=22,
            bit_offset=10,
            access="read-only",
            minimum=None,
            maximum=None,
        )

    @property
    def data(self):
        return self._data.get()

    @data.setter
    def data(self, value: int):
        self._data.set(value)

    @property
    def flag(self):
        return self._flag.get()

    @flag.setter
    def flag(self, value: int):
        self._flag.set(value)

    @property
    def valid(self):
        return self._valid.get()

    @valid.setter
    def valid(self, value: int):
        self._valid.set(value)

    @property
    def unused0(self):
        return self._unused0.get()

    @unused0.setter
    def unused0(self, value: int):
        self._unused0.set(value)


class tx_divider_type(Register):
    """
    SpaceWire transmitter clock divider.
    """

    def __init__(
        self,
        parent_ip: IP,
        address_offset: int,
    ):
        super().__init__(
            parent_ip,
            address_offset,
        )
        # [7:0]
        # SpaceWire transmit clock divider value.
        self._divider = IntegerField(
            self,
            bit_width=8,
            bit_offset=0,
            access="read-write",
            minimum=None,
            maximum=None,
        )
        # [31:8]
        # unused
        self._unused0 = IntegerField(
            self,
            bit_width=24,
            bit_offset=8,
            access="read-write",
            minimum=None,
            maximum=None,
        )

    @property
    def divider(self):
        return self._divider.get()

    @divider.setter
    def divider(self, value: int):
        self._divider.set(value)

    @property
    def unused0(self):
        return self._unused0.get()

    @unused0.setter
    def unused0(self, value: int):
        self._unused0.set(value)


class errors_type(Register):
    """
    Sticky SpaceWire error status. The APB wrapper implements write-one-to-clear behavior manually.
    """

    def __init__(
        self,
        parent_ip: IP,
        address_offset: int,
    ):
        super().__init__(
            parent_ip,
            address_offset,
        )
        # [0]
        # SpaceWire disconnect error.
        self._disconnect_error = IntegerField(
            self,
            bit_width=1,
            bit_offset=0,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [1]
        # SpaceWire parity error.
        self._parity = IntegerField(
            self,
            bit_width=1,
            bit_offset=1,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [2]
        # SpaceWire escape error.
        self._escape = IntegerField(
            self,
            bit_width=1,
            bit_offset=2,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [3]
        # SpaceWire credit error.
        self._credit = IntegerField(
            self,
            bit_width=1,
            bit_offset=3,
            access="read-only",
            minimum=None,
            maximum=None,
        )
        # [31:4]
        # unused
        self._unused0 = IntegerField(
            self,
            bit_width=28,
            bit_offset=4,
            access="read-only",
            minimum=None,
            maximum=None,
        )

    @property
    def disconnect_error(self):
        return self._disconnect_error.get()

    @disconnect_error.setter
    def disconnect_error(self, value: int):
        self._disconnect_error.set(value)

    @property
    def parity(self):
        return self._parity.get()

    @parity.setter
    def parity(self, value: int):
        self._parity.set(value)

    @property
    def escape(self):
        return self._escape.get()

    @escape.setter
    def escape(self, value: int):
        self._escape.set(value)

    @property
    def credit(self):
        return self._credit.get()

    @credit.setter
    def credit(self, value: int):
        self._credit.set(value)

    @property
    def unused0(self):
        return self._unused0.get()

    @unused0.setter
    def unused0(self, value: int):
        self._unused0.set(value)


class id_type(Register):
    """
    Read-only peripheral identification register. Hardware returns 0x53505731 which is ASCII SPW1.
    """

    def __init__(
        self,
        parent_ip: IP,
        address_offset: int,
    ):
        super().__init__(
            parent_ip,
            address_offset,
        )
        # [31:0]
        self._id = IntegerField(
            self,
            bit_width=32,
            bit_offset=0,
            access="read-only",
            minimum=None,
            maximum=None,
        )

    @property
    def id(self):
        return self._id.get()

    @id.setter
    def id(self, value: int):
        self._id.set(value)


class led_type(Register):
    """
    Debug LED control register. Bit zero controls GPIO bit 5.
    """

    def __init__(
        self,
        parent_ip: IP,
        address_offset: int,
    ):
        super().__init__(
            parent_ip,
            address_offset,
        )
        # [0]
        # Controls GPIO bit 5 used by the debug LED.
        self._enable = IntegerField(
            self,
            bit_width=1,
            bit_offset=0,
            access="read-write",
            minimum=None,
            maximum=None,
        )
        # [31:1]
        # unused
        self._unused0 = IntegerField(
            self,
            bit_width=31,
            bit_offset=1,
            access="read-write",
            minimum=None,
            maximum=None,
        )

    @property
    def enable(self):
        return self._enable.get()

    @enable.setter
    def enable(self, value: int):
        self._enable.set(value)

    @property
    def unused0(self):
        return self._unused0.get()

    @unused0.setter
    def unused0(self, value: int):
        self._unused0.set(value)


class spacewire_type(IP):
    def __init__(self, parent: IP, base_address=0, access_layer=accesLayer):
        super().__init__(parent, base_address, access_layer)

        self.control = control_type(self, address_offset=0x00)
        self.status = status_type(self, address_offset=0x04)
        self.tx_data = tx_data_type(self, address_offset=0x08)
        self.rx_data = rx_data_type(self, address_offset=0x0c)
        self.tx_divider = tx_divider_type(self, address_offset=0x10)
        self.errors = errors_type(self, address_offset=0x14)
        self.id = id_type(self, address_offset=0x18)
        self.led = led_type(self, address_offset=0x1c)
