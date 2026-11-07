#!/usr/bin/env python3
"""Host-only C/C++ ABI-header smoke tests for PE-Reborn AOSP17 Qualcomm thermal-client.

Does NOT check device thermal mitigation, HAL service, vendor blobs, or firmware.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HEADER = ROOT / "thermal_client.h"

SOURCE = r"""
#include "thermal_client.h"
#include "thermal_client.h"
#include <stddef.h>
#ifdef __cplusplus
static_assert(MAX_ACTIONS == 32, "ABI constant changed");
static_assert(sizeof(((struct action_info_data*)0)->num_actions) == sizeof(uint32_t),
              "ABI count changed");
#else
_Static_assert(MAX_ACTIONS == 32, "ABI constant changed");
_Static_assert(sizeof(((struct action_info_data*)0)->num_actions) == sizeof(uint32_t),
               "ABI count changed");
#endif
int main(void) {
    struct config_instance c = {0};
    struct action_info_data a = {0};
    (void)c; (void)a;
    if (thermal_bandwidth_client_merge_input_info(0, 0) != 0) return 1;
    if (thermal_bandwidth_client_merge_input_info(0x7fff, 0x7fff) != 0x7fff7fff) return 2;
    if (thermal_bandwidth_client_merge_input_info(0x123, 0x456) != 0x04560123) return 3;
    if (thermal_bandwidth_client_merge_input_info(-1, 0) != -1) return 4;
    if (thermal_bandwidth_client_merge_input_info(0, -1) != -1) return 5;
    if (thermal_bandwidth_client_merge_input_info(0x8000, 0) != -1) return 6;
    if (thermal_bandwidth_client_merge_input_info(0, 0x8000) != -1) return 7;
    return 0;
}
"""


class ThermalClientHeaderTest(unittest.TestCase):
    def test_no_daemon_or_thermal_hal_implementation_in_this_repo(self):
        build = (ROOT / "Android.bp").read_text(encoding="utf-8")
        self.assertIn('name: "libThermal_headers"', build)
        self.assertIn('vendor_available: true', build)
        self.assertIn('export_include_dirs: ["."]', build)
        self.assertNotIn("cc_binary", build)
        self.assertNotIn("cc_library_shared", build)
        self.assertFalse(list(ROOT.glob("*.rc")))
        self.assertFalse(list(ROOT.glob("*.xml")))

    def test_public_client_abi_declarations_not_replaced_with_fake_hal(self):
        source = HEADER.read_text(encoding="utf-8")
        self.assertIn("#include <stdint.h>", source)
        self.assertNotIn("#include <cutils/properties.h>", source)
        self.assertTrue(source.index("#ifndef __THERMAL_CLIENT_H__") <
                        source.index("#include <stdint.h>"))
        for symbol in (
            "thermal_client_config_query(",
            "thermal_client_config_cleanup(",
            "thermal_client_config_set(",
            "thermal_client_register_callback(",
            "thermal_client_request(",
            "thermal_client_unregister_callback(",
            "thermal_bandwidth_client_request(",
            "thermal_bandwidth_client_cancel_request(",
            "thermal_bandwidth_client_merge_input_info(",
        ):
            with self.subTest(symbol=symbol):
                self.assertIn(symbol, source)

    def compile_and_run(self, compiler: str, suffix: str, standard: str):
        if not shutil.which(compiler):
            self.fail(f"Compiler unavailable: {compiler}")
        with tempfile.TemporaryDirectory(prefix="pe-thermal-client-") as tmp:
            folder = Path(tmp)
            source = folder / ("smoke" + suffix)
            output = folder / "smoke"
            source.write_text(SOURCE, encoding="utf-8")
            flags = ["-std=" + standard, "-Wall", "-Wextra",
                     "-Werror", "-pedantic-errors", "-I", str(ROOT)]
            build = subprocess.run([compiler, *flags, str(source), "-o", str(output)],
                                   capture_output=True, text=True, check=False)
            self.assertEqual(build.returncode, 0, build.stdout + build.stderr)
            runtime = subprocess.run([str(output)], capture_output=True,
                                     text=True, check=False)
            self.assertEqual(runtime.returncode, 0, runtime.stdout + runtime.stderr)

    def test_host_c11_header_and_packing_boundaries(self):
        self.compile_and_run("cc", ".c", "c11")

    def test_host_cpp17_header_and_packing_boundaries(self):
        self.compile_and_run("c++", ".cpp", "c++17")


if __name__ == "__main__":
    unittest.main(verbosity=2)
