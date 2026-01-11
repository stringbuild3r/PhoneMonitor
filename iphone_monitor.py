#!/usr/bin/env python3

import subprocess
import time
import threading
from typing import Optional

try:
    from pymobiledevice3.usbmux import list_devices
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.diagnostics import DiagnosticsService
except ImportError:
    print("Required package not found. Install with:")
    print("  pip install pymobiledevice3")
    exit(1)


def get_iphone_info() -> Optional[dict]:
    devices = list_devices()
    if not devices:
        return None

    try:
        lockdown = create_using_usbmux()

        device_info = {
            "model": lockdown.display_name,
            "product_type": lockdown.product_type,
            "ios_version": lockdown.product_version,
        }

        try:
            with DiagnosticsService(lockdown) as diag:
                battery_info = diag.get_battery()

                if "CurrentCapacity" in battery_info:
                    device_info["battery_percent"] = battery_info["CurrentCapacity"]
                elif "BatteryCurrentCapacity" in battery_info:
                    device_info["battery_percent"] = battery_info["BatteryCurrentCapacity"]

                if "Temperature" in battery_info:
                    temp_raw = battery_info["Temperature"]
                    device_info["temperature_c"] = round((temp_raw / 100) - 273.15, 1)

                device_info["is_charging"] = battery_info.get("IsCharging", False)

        except Exception as e:
            device_info["diagnostics_error"] = str(e)

        return device_info

    except Exception as e:
        return {"error": str(e)}


def show_popup(title: str, message: str):
    script = f'''
    display dialog "{message}" with title "{title}" buttons {{"OK"}} default button "OK"
    '''
    subprocess.run(["osascript", "-e", script], capture_output=True)


def format_device_info(info: dict) -> str:
    lines = []

    if "error" in info:
        return f"Error: {info['error']}"

    model = info.get("model", "Unknown")
    product_type = info.get("product_type", "")
    ios_version = info.get("ios_version", "Unknown")
    lines.append(f"Model: {model} ({product_type})")
    lines.append(f"iOS Version: {ios_version}")

    if "battery_percent" in info:
        charging = " (Charging)" if info.get("is_charging") else ""
        lines.append(f"Battery: {info['battery_percent']}%{charging}")

    if "temperature_c" in info:
        temp_c = info["temperature_c"]
        temp_f = round((temp_c * 9/5) + 32, 1)

        if temp_c < 0:
            status = " (Too Cold!)"
        elif temp_c > 35:
            status = " (Too Hot!)"
        else:
            status = " (Normal)"

        lines.append(f"Temperature: {temp_c}°C / {temp_f}°F{status}")

    if "diagnostics_error" in info:
        lines.append(f"\\nNote: Some data unavailable - {info['diagnostics_error']}")

    return "\\n".join(lines)


def monitor_iphone_connection():
    print("iPhone Monitor started. Waiting for device connection...")
    print("Press Ctrl+C to stop.\n")

    was_connected = False

    while True:
        try:
            devices = list_devices()
            is_connected = len(devices) > 0

            if is_connected and not was_connected:
                print("iPhone detected! Gathering information...")

                time.sleep(1)

                info = get_iphone_info()
                if info:
                    message = format_device_info(info)
                    print(f"\n{message}\n")
                    show_popup("iPhone Connected", message)
                else:
                    print("Could not retrieve device information.")

            elif not is_connected and was_connected:
                print("iPhone disconnected.\n")

            was_connected = is_connected
            time.sleep(2)  

        except KeyboardInterrupt:
            print("\nMonitor stopped.")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(2)


if __name__ == "__main__":
    monitor_iphone_connection()
