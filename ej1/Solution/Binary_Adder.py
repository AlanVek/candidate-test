from nmigen import *
from nmigen_cocotb import run
import cocotb
from cocotb.triggers import RisingEdge
from cocotb.clock import Clock
from random import randint

cocotb_object = cocotb.handle.ModifiableObject

class Stream(Record):
    """ Input/Output data stream """

    def __init__(self, width, **kwargs):

        # Initializes parameters:
        #   - data: Actual stored value of {width} bits.
        #   - valid: One bit. Determines whether it's output is valid
        #   - ready: One bit. Determines whether it's input is ready
        Record.__init__(self, [('data', width), ('valid', 1), ('ready', 1)], **kwargs)

    def accepted(self):
        return self.valid & self.ready

    class Driver:
        """ Driver for stream handling """

        def __init__(self, clk, dut, prefix):
            self.clk = clk
            self.data  : cocotb_object = getattr(dut, prefix + 'data')
            self.valid : cocotb_object = getattr(dut, prefix + 'valid')
            self.ready : cocotb_object = getattr(dut, prefix + 'ready')

        async def send(self, data):
            """ Sends stream of data """

            self.valid <= 1

            # Loops through every input value and stores it in self.data until
            # a RisingEdge (posedge) in which self.ready is True
            for d in data:
                self.data <= d
                await RisingEdge(self.clk)

                while not self.ready.value:
                    await RisingEdge(self.clk)

            self.valid <= 0

        async def recv(self, count):
            """ Receives stream of data with {count} values """

            self.ready <= 1
            data = []

            # Loops {count} times. In each loop, it waits for a RisingEdge (posedge) in which
            # self.valid is True. Then, it saves the value of self.data in data, to finally return it.
            for _ in range(count):
                await RisingEdge(self.clk)

                while not self.valid.value:
                    await RisingEdge(self.clk)

                data.append(self.data.value.signed_integer)

            self.ready <= 0
            return data

class Binary_Adder(Elaboratable):
    """ 2-input-1-output N-bit binary adder with N-bit output """

    def __init__(self, width):

        # Creates input streams (a, b) and output stream (r)
        self.a = Stream(width, name='a')
        self.b = Stream(width, name='b')
        self.r = Stream(width, name='r')

    def elaborate(self, platform):
        m = Module()
        sync = m.d.sync
        comb = m.d.comb

        # If r is accepted, it means there was an initialization issue, so we set r.valid to 0,
        # which means its output is not yet valid, but it's ready to receive input.
        with m.If(self.r.accepted()):
            sync += self.r.valid.eq(0)

        with m.If(self.a.accepted() & self.b.accepted()):

            res = (self.a.data + self.b.data).as_signed()

            # If both a and b are initially accepted, we set a + b to r.data.
            # Since it's a valid output, we also set r.valid to 1.
            sync += [
                self.r.valid.eq(1),
                self.r.data.eq(res)
            ]

        # a and b will be ready to send output if:
        #   - r is not currently sending valid output or
        #   - r is ready for input and has already sent valid output
        comb += self.a.ready.eq((~self.r.valid) | (self.r.accepted()))
        comb += self.b.ready.eq((~self.r.valid) | (self.r.accepted()))
        return m

async def init_test(dut):
    cocotb.fork(Clock(dut.clk, 500, 'ps').start())

    dut.rst <= 1
    await RisingEdge(dut.clk)
    await RisingEdge(dut.clk)
    dut.rst <= 0


@cocotb.test()
async def burst(dut):
    await init_test(dut)

    # Stream drivers for manual data input and recovery of output
    stream_input_a = Stream.Driver(dut.clk, dut, 'a__')
    stream_input_b = Stream.Driver(dut.clk, dut, 'b__')
    stream_output = Stream.Driver(dut.clk, dut, 'r__')

    # Number of tests
    N = 100

    # Number of bits per register
    width = len(dut.a__data)

    # Minimum and maximum limits for {width}-bit signed data.
    minlim, maxlim = -2**(width - 1), 2**(width - 1) - 1

    # Generates N random signed numbers with {width} bits for each input register.
    data_a = [randint(minlim, maxlim) for _ in range(N)]
    data_b = [randint(minlim, maxlim) for _ in range(N)]

    # Expected values from output
    expected = [

        # If sum > maxlim, it restarts forward from the negatives
        minlim + (a + b - maxlim - 1) if (a + b) > maxlim

        # If sum < minlim, it restarts backwards from the positives
        else maxlim - (minlim - a - b - 1) if (a + b) < minlim

        else (a + b) for a, b in zip(data_a, data_b)
    ]

    cocotb.fork(stream_input_a.send(data_a))
    cocotb.fork(stream_input_b.send(data_b))

    res = await stream_output.recv(N)
    assert res == expected

if __name__ == '__main__':
    core = Binary_Adder(8)

    run(
        core, 'Binary_Adder',
        ports=
        [
            *list(core.a.fields.values()),
            *list(core.b.fields.values()),
            *list(core.r.fields.values())
        ],
        vcd_file='binary_adder.vcd',
    )