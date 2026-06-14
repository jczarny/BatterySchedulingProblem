import unittest
from models.battery import Battery
from models.terminal import Terminal


class TestScheduleGenerationProcedure(unittest.TestCase):

    def test_case_1(self):
        terminal = Terminal(max_power_capacity=100.0)

        b1 = Battery(energy_missing=20.0, initial_power_consumption=10.0)
        b2 = Battery(energy_missing=80.0, initial_power_consumption=100.0)
        b3 = Battery(energy_missing=45.0, initial_power_consumption=67.5)

        terminal.load_batteries([b1, b2, b3])
        makespan = terminal.process()

        # Battery 1 (Start: 0.0h, End: 4.0h)
        self.assertAlmostEqual(b1.start_time, 0.00, places=2)
        self.assertAlmostEqual(b1.completion_time, 4.00, places=2)

        # Battery 2 (Start: 4.0h, End: 5.6h)
        self.assertAlmostEqual(b2.start_time, 4.00, places=2)
        self.assertAlmostEqual(b2.completion_time, 5.60, places=2)

        # Battery 3 (Start: 5.08h, End: 6.41h)
        self.assertAlmostEqual(b3.start_time, 5.08, places=2)
        self.assertAlmostEqual(b3.completion_time, 6.41, places=2)

        # Makespan
        self.assertAlmostEqual(makespan, 6.41, places=2)

    def test_case_2(self):
        terminal = Terminal(max_power_capacity=100.0)

        b1 = Battery(energy_missing=150.0, initial_power_consumption=50.0)
        b2 = Battery(energy_missing=100.0, initial_power_consumption=50.0)
        b3 = Battery(energy_missing=50.0, initial_power_consumption=50.0)
        b4 = Battery(energy_missing=25.0, initial_power_consumption=50.0)

        terminal.load_batteries([b1, b2, b3, b4])
        makespan = terminal.process()

        # Battery 1 (Start: 0.0h, End: 6.0h)
        self.assertAlmostEqual(b1.start_time, 0.00, places=2)
        self.assertAlmostEqual(b1.completion_time, 6.00, places=2)

        # Battery 2 (Start: 0.0h, End: 4.0h)
        self.assertAlmostEqual(b2.start_time, 0.00, places=2)
        self.assertAlmostEqual(b2.completion_time, 4.00, places=2)

        # Battery 3 (Start: 2.4h, End: 4.4h)
        self.assertAlmostEqual(b3.start_time, 2.40, places=2)
        self.assertAlmostEqual(b3.completion_time, 4.40, places=2)

        # Battery 4 (Start: 3.49h, End: 4.49h)
        self.assertAlmostEqual(b4.start_time, 3.49, places=2)
        self.assertAlmostEqual(b4.completion_time, 4.49, places=2)

        # Makespan
        self.assertAlmostEqual(makespan, 6.00, places=2)

    def test_case_3(self):
        terminal = Terminal(max_power_capacity=100.0)

        b1 = Battery(energy_missing=200.0, initial_power_consumption=80.0)
        b2 = Battery(energy_missing=5.0, initial_power_consumption=25.0)
        b3 = Battery(energy_missing=5.0, initial_power_consumption=25.0)
        b4 = Battery(energy_missing=5.0, initial_power_consumption=25.0)

        terminal.load_batteries([b1, b2, b3, b4])
        makespan = terminal.process()

        # Battery 1 (Start: 0.00h, End: 5.00h)
        self.assertAlmostEqual(b1.start_time, 0.00, places=2)
        self.assertAlmostEqual(b1.completion_time, 5.00, places=2)

        # Battery 2 (Start: 0.31h, End: 0.71h)
        self.assertAlmostEqual(b2.start_time, 0.31, places=2)
        self.assertAlmostEqual(b2.completion_time, 0.71, places=2)

        # Battery 3 (Start: 0.63h, End: 1.03h)
        self.assertAlmostEqual(b3.start_time, 0.63, places=2)
        self.assertAlmostEqual(b3.completion_time, 1.03, places=2)

        # Battery 4 (Start: 0.88h, End: 1.28h)
        self.assertAlmostEqual(b4.start_time, 0.88, places=2)
        self.assertAlmostEqual(b4.completion_time, 1.28, places=2)

        # Makespan
        self.assertAlmostEqual(makespan, 5.00, places=2)

    def test_case_4(self):
        terminal = Terminal(max_power_capacity=100.0)

        b1 = Battery(energy_missing=60.0, initial_power_consumption=60.0)
        b2 = Battery(energy_missing=60.0, initial_power_consumption=60.0)
        b3 = Battery(energy_missing=60.0, initial_power_consumption=60.0)

        terminal.load_batteries([b1, b2, b3])
        makespan = terminal.process()

        # Battery 1 (Start: 0.00h, End: 2.00h)
        self.assertAlmostEqual(b1.start_time, 0.00, places=2)
        self.assertAlmostEqual(b1.completion_time, 2.00, places=2)

        # Battery 2 (Start: 0.67h, End: 2.67h)
        self.assertAlmostEqual(b2.start_time, 0.67, places=2)
        self.assertAlmostEqual(b2.completion_time, 2.67, places=2)

        # Battery 3 (Start: 1.67h, End: 3.67h)
        self.assertAlmostEqual(b3.start_time, 1.67, places=2)
        self.assertAlmostEqual(b3.completion_time, 3.67, places=2)

        # Makespan
        self.assertAlmostEqual(makespan, 3.67, places=2)

    def test_case_5(self):
        terminal = Terminal(max_power_capacity=100.0)

        b1 = Battery(energy_missing=10.0, initial_power_consumption=90.0)
        b2 = Battery(energy_missing=10.0, initial_power_consumption=90.0)
        b3 = Battery(energy_missing=10.0, initial_power_consumption=90.0)

        terminal.load_batteries([b1, b2, b3])
        makespan = terminal.process()

        # Battery 1 (Start: 0.00h, End: 0.22h)
        self.assertAlmostEqual(b1.start_time, 0.00, places=2)
        self.assertAlmostEqual(b1.completion_time, 0.22, places=2)

        # Battery 2 (Start: 0.20h, End: 0.42h)
        self.assertAlmostEqual(b2.start_time, 0.20, places=2)
        self.assertAlmostEqual(b2.completion_time, 0.42, places=2)

        # Battery 3 (Start: 0.40h, End: 0.62h)
        self.assertAlmostEqual(b3.start_time, 0.40, places=2)
        self.assertAlmostEqual(b3.completion_time, 0.62, places=2)

        # Makespan
        self.assertAlmostEqual(makespan, 0.62, places=2)

    def test_case_6(self):
        terminal = Terminal(max_power_capacity=100.0)

        b1 = Battery(energy_missing=100.0, initial_power_consumption=10.0)
        b2 = Battery(energy_missing=100.0, initial_power_consumption=10.0)
        b3 = Battery(energy_missing=100.0, initial_power_consumption=10.0)
        b4 = Battery(energy_missing=100.0, initial_power_consumption=10.0)
        b5 = Battery(energy_missing=100.0, initial_power_consumption=10.0)
        b6 = Battery(energy_missing=100.0, initial_power_consumption=10.0)
        b7 = Battery(energy_missing=100.0, initial_power_consumption=10.0)
        b8 = Battery(energy_missing=100.0, initial_power_consumption=10.0)
        b9 = Battery(energy_missing=100.0, initial_power_consumption=10.0)
        b10 = Battery(energy_missing=100.0, initial_power_consumption=10.0)
        b11 = Battery(energy_missing=100.0, initial_power_consumption=10.0)

        terminal.load_batteries([b1, b2, b3, b4, b5, b6, b7, b8, b9, b10, b11])
        makespan = terminal.process()

        # Battery 1-10
        self.assertAlmostEqual(b1.start_time, 0.00, places=2)
        self.assertAlmostEqual(b1.completion_time, 20.00, places=2)
        self.assertAlmostEqual(b10.start_time, 0.00, places=2)
        self.assertAlmostEqual(b10.completion_time, 20.00, places=2)

        # Battery 11
        self.assertAlmostEqual(b11.start_time, 2.00, places=2)
        self.assertAlmostEqual(b11.completion_time, 22.00, places=2)

        # Makespan
        self.assertAlmostEqual(makespan, 22.00, places=2)

    def test_case_7(self):
        terminal = Terminal(max_power_capacity=100.0)

        b1 = Battery(energy_missing=50.0, initial_power_consumption=50.0)
        b2 = Battery(energy_missing=30.0, initial_power_consumption=30.0)
        b3 = Battery(energy_missing=20.0, initial_power_consumption=20.0)
        b4 = Battery(energy_missing=50.0, initial_power_consumption=50.0)

        terminal.load_batteries([b1, b2, b3, b4])
        makespan = terminal.process()

        # Battery 1 (Start: 0.00h, End: 2.00h)
        self.assertAlmostEqual(b1.start_time, 0.00, places=2)
        self.assertAlmostEqual(b1.completion_time, 2.00, places=2)

        # Battery 2 (Start: 0.00h, End: 2.00h)
        self.assertAlmostEqual(b2.start_time, 0.00, places=2)
        self.assertAlmostEqual(b2.completion_time, 2.00, places=2)

        # Battery 3 (Start: 0.00h, End: 2.00h)
        self.assertAlmostEqual(b3.start_time, 0.00, places=2)
        self.assertAlmostEqual(b3.completion_time, 2.00, places=2)

        # Battery 4 (Start: 1.00h, End: 3.00h)
        self.assertAlmostEqual(b4.start_time, 1.00, places=2)
        self.assertAlmostEqual(b4.completion_time, 3.00, places=2)

        # Makespan
        self.assertAlmostEqual(makespan, 3.00, places=2)

    def test_case_8(self):
        terminal = Terminal(max_power_capacity=100.0)

        b1 = Battery(energy_missing=100.0, initial_power_consumption=100.0)
        b2 = Battery(energy_missing=50.0, initial_power_consumption=100.0)
        b3 = Battery(energy_missing=150.0, initial_power_consumption=100.0)

        terminal.load_batteries([b1, b2, b3])
        makespan = terminal.process()

        # Battery 1 (Start: 0.00h, End: 2.00h)
        self.assertAlmostEqual(b1.start_time, 0.00, places=2)
        self.assertAlmostEqual(b1.completion_time, 2.00, places=2)

        # Battery 2 (Start: 2.00h, End: 3.00h)
        self.assertAlmostEqual(b2.start_time, 2.00, places=2)
        self.assertAlmostEqual(b2.completion_time, 3.00, places=2)

        # Battery 3 (Start: 3.00h, End: 6.00h)
        self.assertAlmostEqual(b3.start_time, 3.00, places=2)
        self.assertAlmostEqual(b3.completion_time, 6.00, places=2)

        # Makespan
        self.assertAlmostEqual(makespan, 6.00, places=2)

    def test_case_9(self):
        terminal = Terminal(max_power_capacity=100.0)

        b1 = Battery(energy_missing=10.0, initial_power_consumption=20.0)
        b2 = Battery(energy_missing=20.0, initial_power_consumption=40.0)
        b3 = Battery(energy_missing=30.0, initial_power_consumption=60.0)
        b4 = Battery(energy_missing=40.0, initial_power_consumption=80.0)

        terminal.load_batteries([b1, b2, b3, b4])
        makespan = terminal.process()

        # Battery 1 (Start: 0.00h, End: 1.00h)
        self.assertAlmostEqual(b1.start_time, 0.00, places=2)
        self.assertAlmostEqual(b1.completion_time, 1.00, places=2)

        # Battery 2 (Start: 0.00h, End: 1.00h)
        self.assertAlmostEqual(b2.start_time, 0.00, places=2)
        self.assertAlmostEqual(b2.completion_time, 1.00, places=2)

        # Battery 3 (Start: 0.33h, End: 1.33h)
        self.assertAlmostEqual(b3.start_time, 0.33, places=2)
        self.assertAlmostEqual(b3.completion_time, 1.33, places=2)

        # Battery 4 (Start: 1.00h, End: 2.00h)
        self.assertAlmostEqual(b4.start_time, 1.00, places=2)
        self.assertAlmostEqual(b4.completion_time, 2.00, places=2)

        # Makespan
        self.assertAlmostEqual(makespan, 2.00, places=2)

    def test_case_10(self):
        terminal = Terminal(max_power_capacity=100.0)

        b1 = Battery(energy_missing=40.0, initial_power_consumption=80.0)
        b2 = Battery(energy_missing=30.0, initial_power_consumption=60.0)
        b3 = Battery(energy_missing=20.0, initial_power_consumption=40.0)
        b4 = Battery(energy_missing=10.0, initial_power_consumption=20.0)

        terminal.load_batteries([b1, b2, b3, b4])
        makespan = terminal.process()

        # Battery 1 (Start: 0.00h, End: 1.00h)
        self.assertAlmostEqual(b1.start_time, 0.00, places=2)
        self.assertAlmostEqual(b1.completion_time, 1.00, places=2)

        # Battery 2 (Start: 0.50h, End: 1.50h)
        self.assertAlmostEqual(b2.start_time, 0.50, places=2)
        self.assertAlmostEqual(b2.completion_time, 1.50, places=2)

        # Battery 3 (Start: 0.79h, End: 1.79h)
        self.assertAlmostEqual(b3.start_time, 0.79, places=2)
        self.assertAlmostEqual(b3.completion_time, 1.79, places=2)

        # Battery 4 (Start: 0.90h, End: 1.90h)
        self.assertAlmostEqual(b4.start_time, 0.90, places=2)
        self.assertAlmostEqual(b4.completion_time, 1.90, places=2)

        # Makespan
        self.assertAlmostEqual(makespan, 1.90, places=2)
