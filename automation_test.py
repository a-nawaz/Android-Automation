from airtest.core.api import *
from airtest.core.android import Android
from airtest.core.android.adb import ADB
from poco.drivers.android.uiautomation import AndroidUiautomationPoco
from poco.exceptions import PocoNoSuchNodeException

import logging
logging.getLogger("airtest").setLevel(logging.WARNING)


# Give the App Name here
APP_NAME = "minesweeper"  # <-- Input any app name Here


def connection():  # Initialize the device
    try:
        connect_device("Android:///")
    except IndexError:
        print("\n*** Please connect your Android device properly and make sure 'usb debugging' is 'On' in Developer options ***\n")
        print("*** Please run the script again ***\n\n")


class AndroidApp:
    def __init__(self, name):
        self.name = name
        self.gps_app_name = None
        self.install_status = None
        self.adb = ADB()
        self.droid = Android()
        self.poco = AndroidUiautomationPoco()
        self._device_state(self.droid)
        self.gps_operations(self.name, self.gps_app_name, self.install_status, self.adb, self.droid, self.poco)

    def gps_operations(self, name, gps_app_name, install_status, adb, droid, poco):
        droid.home()
        droid.stop_app("com.android.vending")
        droid.start_app("com.android.vending")  # Play Store
        poco(text="Search for apps & games").click()
        sleep(1)
        droid.text(name)

        # Setting the var 'obj_exists' to True if UI Object 'Horizontal Scroll view' exists
        obj_exists = poco(type="android.widget.HorizontalScrollView").wait(timeout=2).exists()

        # Checking if Google play store has found a perfect match for the app name provided. (obj_exists = True, means perfect Match)
        if obj_exists:
            app_size_obj = poco(type="android.widget.HorizontalScrollView").child(
                "com.android.vending:id/0_resource_name_obfuscated").child("com.android.vending:id/0_resource_name_obfuscated")[1]
            gps_app_size = app_size_obj.attr("desc")
            gps_app_name = poco("com.android.vending:id/nested_parent_recycler_view").offspring(type="android.widget.RelativeLayout").child(
                "com.android.vending:id/0_resource_name_obfuscated")[1].offspring(type="android.widget.TextView").get_text()
        else:
            # calling the _app_compare to get the best match from the results
            app_details = self._app_compare(name, poco)
            if app_details:
                app_details[0].click()
                gps_app_name = app_details[1]
            else:
                self.invalid_app_name(name)
                return
        install_status = poco(type="android.widget.Button", text="Open", enabled=True).exists()
        if install_status:
            print(f"'{gps_app_name}' App is already installed")
            droid.stop_app("com.android.vending")
            gps_app_size = "n/a"
            self.settings_app_operations(gps_app_name, gps_app_size, adb, droid, poco)
            return
        app_size_obj = poco(type="android.widget.HorizontalScrollView").child(
            "com.android.vending:id/0_resource_name_obfuscated").child("com.android.vending:id/0_resource_name_obfuscated")[1]
        gps_app_size = app_size_obj.attr("desc")
        try:
            poco(type="android.widget.Button", text="Install").click()
        except PocoNoSuchNodeException:
            poco(type="android.widget.Button", text="Update").click()
        while not install_status:
            sleep(3)
            install_status = poco(type="android.widget.Button", text="Open", enabled=True).exists()
        print(f"'{gps_app_name}' App successfully installed")
        droid.stop_app("com.android.vending")
        self.settings_app_operations(gps_app_name, gps_app_size, adb, droid, poco)

    def settings_app_operations(self, gps_app_name, gps_app_size, adb, droid, poco):
        droid.stop_app("com.android.settings")
        droid.start_app("com.android.settings")  # Opening Device Settings
        poco(text="Apps & notifications").click()
        self._settings_see_all_app(poco)  # Makeing sure 'See all Apps' is clicked

        # Make sure to get the app name as it would be in the settings App
        if " -" in gps_app_name:
            gps_app_name = gps_app_name.split(" -")[0]
        elif "-" in gps_app_name:
            gps_app_name = gps_app_name.split("-")[0]
        elif " :" in gps_app_name:
            gps_app_name = gps_app_name.split(" :")[0]
        elif ":" in gps_app_name:
            gps_app_name = gps_app_name.split(":")[0]

        app = poco("android:id/title", text=gps_app_name)
        while not app.exists():
            poco.swipe((0.5, 0.9), (0.5, 0.1), duration=0.1)  # Swipe until the matching app is found in 'all apps'
        app.click()
        poco(text="Storage & cache").click()
        settings_app_size = poco("com.android.settings:id/content_frame").offspring(
            "com.android.settings:id/recycler_view").child("android.widget.LinearLayout")[2].child("android:id/summary").get_text()
        keyevent("BACK")
        self.app_operations(gps_app_name, gps_app_size, settings_app_size, adb, droid, poco)

    def app_operations(self, gps_app_name, gps_app_size, settings_app_size, t_adb, droid, poco):
        adb = self.adb_initialize(t_adb)
        logs = adb.start_cmd("logcat")  # Starting 'adb logcat' subprocess
        poco("com.android.settings:id/button1").click()  # Opening the app
        droid.stop_app("com.android.settings")
        app_package_name = poco(type="android.widget.FrameLayout").attr("package")
        sleep(180)  # Keeping the app open for 3 minutes
        droid.stop_app(app_package_name)  # closing app
        logs.terminate()  # stopping the logcat process
        log_b = logs.stdout  # Byte logs
        device_logs = log_b.read().decode()  # decoded logs
        self.log_to_txt(device_logs)
        self.print_output(gps_app_name, gps_app_size, settings_app_size)  # Printing desired output

    ################### Helper Functions #########################

    def _device_state(self, droid):  # Getting Device State
        locked_state = droid.is_locked()
        if locked_state:
            print("\nPlease unlock the device and keep the screen 'ON'\n")
            raise Exception("Device must be Unlocked")

    def _app_compare(self, name, poco):
        try:
            # Getting all the Apps containg objects in the screen
            app_objs = poco("com.android.vending:id/nested_parent_recycler_view").child(type="android.widget.LinearLayout")
            for obj in app_objs:
                app_obj = obj.offspring(type="android.widget.FrameLayout")
                app_desc = app_obj.attr("desc")  # Getting the 'desc' property of the apps
                app_name = app_desc.split("\n")[0][5:]  # Stripping the description to find the app name
                if name.lower() == app_name.lower():
                    return (app_obj, app_name)
            return None
        except PocoNoSuchNodeException:
            return None

    def invalid_app_name(self, name):
        print(f"'\n\n{name}' App didnot match with any search results. Please run the script again with a valid App Name")
        return

    def _settings_see_all_app(self, poco):
        try:
            poco("com.android.settings:id/header_details", enabled=True, touchable=True).click()
            poco("More options").attr("type")
        except PocoNoSuchNodeException:
            self._settings_see_all_app(poco)  # Making sure 'see all apps' is clicked
        return

    def adb_initialize(self, t_adb):
        device_serialno = t_adb.devices()[0][0]  # Getting the Android device serial number
        return ADB(serialno=device_serialno)  # Returning ADB intance with Device Serial Number

    def log_to_txt(self, logs):
        with open("./logs/logs.txt", "w") as file:
            file.write(logs)  # writing the logs to a .txt file

    def print_output(self, name, g_size, s_size):
        print("\n\n-------- OUTPUT -------")
        print(f"App : {name}\nApp Size in Google Play Store : {g_size}\nApp Size in Settings : {s_size}")


if __name__ == '__main__':
    connection()
    run = AndroidApp(APP_NAME)
