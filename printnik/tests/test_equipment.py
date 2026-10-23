import unittest

from printnik.equipment import Device, DeviceKind, DeviceStatus, EquipmentScheduler


def ready(device_id, kind):
    return Device(
        device_id=device_id,
        kind=kind,
        status=DeviceStatus.READY,
        roles=frozenset({"stickers"} if kind == DeviceKind.PRINTER else {"contour_cut"}),
        approved_materials=frozenset({"matte_white"}),
        approved_profiles=frozenset({"standard"}),
    )


class EquipmentSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.scheduler = EquipmentScheduler([
            ready("PRN-01", DeviceKind.PRINTER),
            ready("PRN-02", DeviceKind.PRINTER),
            ready("CUT-01", DeviceKind.CUTTER),
            ready("CUT-02", DeviceKind.CUTTER),
        ])

    def test_orders_are_balanced_but_each_order_is_kept_on_one_device(self):
        first = self.scheduler.assign_order("ORD-1", 7, "matte_white", "standard")
        repeated = self.scheduler.assign_order("ORD-1", 7, "matte_white", "standard")
        second = self.scheduler.assign_order("ORD-2", 6, "matte_white", "standard")
        self.assertIs(first, repeated)
        self.assertEqual(first.printer_id, "PRN-01")
        self.assertEqual(second.printer_id, "PRN-02")

    def test_emergency_transfer_continues_with_next_confirmed_sheet(self):
        assignment = self.scheduler.assign_order("ORD-18", 7, "matte_white", "standard")
        segment = self.scheduler.emergency_transfer(
            "ORD-18",
            kind=DeviceKind.PRINTER,
            new_device_id="PRN-02",
            last_confirmed_sheet=4,
            material="matte_white",
            reason="printer_failure",
        )
        self.assertEqual((segment.first_sheet, segment.last_sheet), (5, 7))
        self.assertEqual(assignment.printer_segments[0].last_sheet, 4)
        self.assertEqual(assignment.printer_id, "PRN-02")

    def test_uncalibrated_device_cannot_receive_transfer(self):
        self.scheduler.assign_order("ORD-3", 2, "matte_white", "standard")
        self.scheduler.devices["PRN-02"] = Device("PRN-02", DeviceKind.PRINTER)
        with self.assertRaises(RuntimeError):
            self.scheduler.emergency_transfer(
                "ORD-3",
                kind=DeviceKind.PRINTER,
                new_device_id="PRN-02",
                last_confirmed_sheet=1,
                material="matte_white",
                reason="printer_failure",
            )


if __name__ == "__main__":
    unittest.main()
