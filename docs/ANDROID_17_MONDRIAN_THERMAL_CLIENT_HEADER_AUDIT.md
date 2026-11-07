# AOSP Android 17 — Qualcomm thermal-client header audit for mondrian

**Scope:** Independent PixelExperience-Reborn Android 17 for POCO F5 Pro / Redmi K60 (`mondrian`, Snapdragon 8+ Gen 1 / SM8475). AOSP upstream is the base, and other ROM trees are **read-only comparative references**.

## Source provenance and finding

- The PE-Reborn archived `seventeen` and `fourteen` branches point to exact commit `db21bec66ea8d930d517bee60786c04ba0d4a2e8` (2022-08-31), Git tree `ad01d8ca8f734013176141ee47d8885f2ce35652`. It contains precisely **four files**: `.gitupstream`, `Android.bp`, `NOTICE` and `thermal_client.h`.
- `Android.bp` exports a **header-only** `cc_library_headers` named `libThermal_headers`, with `vendor_available: true`. There is **no binary**, `thermal-engine` process, `init.rc`, Thermal HAL implementation, configuration, sensor data or service here.
- `thermal_client.h` declares the old vendor-specific thermal control/configuration functions and bandwidth request API. Those are **declarations**, not an implementation. They are not interchangeable with `android.hardware.thermal.IThermal/default` or the Android framework thermal service. No vendor library has been linked or tested.
- Reference-only comparison: LineageOS `android_vendor_qcom_opensource_thermal-engine` `lineage-24.0` (commit `0815f34094ebc952c8e1dd3619e384c7f9d1195b`) has the exact same inspected header blob `b8f0ca21098c90a9efce2b577416d76aa462a67a` and `Android.bp` blob `bedc7142727f15c9d9c361f889eca0f1005ee6a9` as this historical PE checkout. **No LineageOS source copied.**

## Actual source patch

The old header included `<cutils/properties.h>` *before* its include guard although it does not call any Android property API. Its public structs require `uint32_t` but did not explicitly include `<stdint.h>`.

The isolated PE branch makes the public C ABI header **self-contained**: include guard first, `#include <stdint.h>` inside, and no unnecessary `cutils` include. Functions, enum numeric values, structures and inline thermal bandwidth packing remain unchanged. This is a host/source portability correction, **not** a new HAL implementation and not a claim that a 2022 Qualcomm binary is Android 17-compatible.

`tests/check_thermal_client_aosp17.py` uses the actual C11/C++17 compilers with `-Wall -Wextra -Werror -pedantic-errors`, includes the header twice, verifies the public declarations/Soong header module, and tests exact valid and invalid 15-bit bandwidth packing boundaries. This validates header-level compatibility only. Dedicated GitHub Actions runs it.

## Correct Android 17 thermal architecture

- Android 14+ migrated the Thermal HAL interface to **stable AIDL**. Android framework thermal mitigation requires accurate temperature/cooling/status events and must not be disabled, especially for battery, skin, USB, CPU and GPU thermal protection.
- The modern AOSP `hardware/interfaces/thermal/aidl` contract and framework ThermalManager remain authoritative. Preserve real kernel/hardware thermal limits. A header-only Qualcomm client ABI cannot replace an actual AIDL Thermal HAL, kernel thermal cooling/critical shutdown, vendor drivers or any required hardware thermal service.
- The LF52406 `sm8450-common/common.mk` hardware reference selects `android.hardware.thermal-service.qti`. **This is a hardware reference, not a PE-Reborn import;** the actual Qualcomm service implementation and Xiaomi vendor ABI need independent verification. No attempt is made to copy its ROM implementation.
- Do **not** blindly remove Xiaomi/vendor thermal components or disable thermal throttling. If a redundant vendor userspace daemon is considered for removal, first verify that an alternative thermal HAL and kernel controls actually report cooling, throttling, battery/skin shutdown thresholds and satisfy vendor binary dependencies.
- Confirm who consumes `libThermal_headers`/each `thermal_client_*` symbol among the exact Xiaomi SM8475 vendor blobs and services. Validate C/NDK ABI, Soong/namespace, vendor link dependencies, SELinux, current VINTF/FCM, CTS/VTS, temperature curves, thermal stress, charge/USB and long-duration gaming before adding any PE product package.

## Integration decision / remaining blockers

**Do not import this archived source into the active PE-Reborn AOSP17 manifest.** If a verified device-side client needs the header, choose an independently vetted source and matching implementation in a separate, pinned, explicit candidate. The 2022 header carries **no daemon** and must not be mistaken for the entire thermal stack.

**Status:** header code changed, host C/C++ regression tests added. No full AOSP17 Soong build, ABI linking, Thermal AIDL service validation, Xiaomi sensor correctness or physical mondrian test was performed. No changes to kernel thermal controls, thermal service, thermal profiles, device trees or product packages.

References: https://source.android.com/docs/core/power/thermal-mitigation ; https://android.googlesource.com/platform/hardware/interfaces/+/main/thermal/aidl/default/Android.bp
