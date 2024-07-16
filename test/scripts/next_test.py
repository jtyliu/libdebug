#
# This file is part of libdebug Python library (https://github.com/libdebug/libdebug).
# Copyright (c) 2024 Francesco Panebianco. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project root for details.
#
import unittest

from libdebug import debugger

TEST_ENTRYPOINT = 0x4011f8

# Addresses of the dummy functions
CALL_C_ADDRESS = 0x4011fd
TEST_BREAKPOINT_ADDRESS = 0x4011f1

# Addresses of noteworthy instructions
RETURN_POINT_FROM_C = 0x401202

class NextTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_next(self):
        d = debugger("binaries/finish_test", auto_interrupt_on_command=False)
        d.run()

        # Get to test entrypoint
        entrypoint_bp = d.breakpoint(TEST_ENTRYPOINT)
        d.cont()

        self.assertEqual(d.regs.rip, TEST_ENTRYPOINT)

        # -------- Block 1 ------- #
        #        Simple Step       #
        # ------------------------ #

        # Reach call of function c

        print(f"RIP IS AT {hex(d.regs.rip)}")
        d.next()
        print('Simple step')
        print(f"RIP IS AT {hex(d.regs.rip)}")
        print(f'Should be {hex(CALL_C_ADDRESS)}')
        self.assertEqual(d.regs.rip, CALL_C_ADDRESS)

        # -------- Block 2 ------- #
        #        Skip a call       #
        # ------------------------ #

        print(f"RIP IS AT {hex(d.regs.rip)}")
        d.next()
        print('Skip a call')
        print(f"RIP IS AT {hex(d.regs.rip)}")
        print(f'Should be {hex(RETURN_POINT_FROM_C)}')
        self.assertEqual(d.regs.rip, RETURN_POINT_FROM_C)

        d.kill()

    def test_next_breakpoint(self):
        d = debugger("binaries/finish_test", auto_interrupt_on_command=False)
        d.run()

        # Get to test entrypoint
        entrypoint_bp = d.breakpoint(TEST_ENTRYPOINT)
        d.cont()

        self.assertEqual(d.regs.rip, TEST_ENTRYPOINT)

        print(f"RIP IS AT {hex(d.regs.rip)}")

        # Reach call of function c
        d.next()

        print('Simple step')
        print(f"RIP IS AT {hex(d.regs.rip)}")
        print(f'Should be {hex(CALL_C_ADDRESS)}')
        self.assertEqual(d.regs.rip, CALL_C_ADDRESS)

        # -------- Block 1 ------- #
        #    Call with breakpoint  #
        # ------------------------ #

        # Set breakpoint
        test_breakpoint = d.breakpoint(TEST_BREAKPOINT_ADDRESS)
        
        
        print(f"RIP IS AT {hex(d.regs.rip)}")
        d.next()

        print('Breakpoint hit')
        print(f"RIP IS AT {hex(d.regs.rip)}")
        print(f'Should be {hex(TEST_BREAKPOINT_ADDRESS)}')

        # Check we hit the breakpoint
        self.assertEqual(d.regs.rip, TEST_BREAKPOINT_ADDRESS)
        self.assertEqual(test_breakpoint.hit_count, 1)

        d.kill()

    def test_next_breakpoint_hw(self):
        d = debugger("binaries/finish_test", auto_interrupt_on_command=False)
        d.run()

        # Get to test entrypoint
        entrypoint_bp = d.breakpoint(TEST_ENTRYPOINT)
        d.cont()

        self.assertEqual(d.regs.rip, TEST_ENTRYPOINT)

        # Reach call of function c
        d.next()

        self.assertEqual(d.regs.rip, CALL_C_ADDRESS)

        # -------- Block 1 ------- #
        #    Call with breakpoint  #
        # ------------------------ #

        # Set breakpoint
        test_breakpoint = d.breakpoint(TEST_BREAKPOINT_ADDRESS, hardware=True)

        d.next()

        # Check we hit the breakpoint
        self.assertEqual(d.regs.rip, TEST_BREAKPOINT_ADDRESS)
        self.assertEqual(test_breakpoint.hit_count, 1)

        d.kill()