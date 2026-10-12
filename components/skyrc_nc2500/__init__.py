"""SkyRC NC2500 charger over classic Bluetooth (SPP) - original ESP32 only (not S2/S3/C3/C6)."""
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import binary_sensor, esp32, sensor, text_sensor
from esphome.components.esp32.const import VARIANT_ESP32
from esphome.const import (
    CONF_ID,
    CONF_MAC_ADDRESS,
    CONF_VOLTAGE,
    CONF_CURRENT,
    CONF_TEMPERATURE,
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_CONNECTIVITY,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_DURATION,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLTAGE,
    ENTITY_CATEGORY_DIAGNOSTIC,
    STATE_CLASS_MEASUREMENT,
    STATE_CLASS_TOTAL_INCREASING,
    UNIT_AMPERE,
    UNIT_CELSIUS,
    UNIT_MINUTE,
    UNIT_VOLT,
)

CODEOWNERS = ["@scottbambrick"]
DEPENDENCIES = ["esp32"]
AUTO_LOAD = ["sensor", "text_sensor", "binary_sensor"]

skyrc_ns = cg.esphome_ns.namespace("skyrc_nc2500")
SkyrcNC2500 = skyrc_ns.class_("SkyrcNC2500", cg.Component)

CONF_NAME_MATCH = "name_match"
CONF_CHANNEL = "channel"
CONF_PIN = "pin"
CONF_SECURITY = "security"
CONF_SLOTS = "slots"
CONF_CAPACITY = "capacity"
CONF_RUN_TIME = "run_time"
CONF_RESISTANCE = "resistance"
CONF_CYCLES = "cycles"
CONF_MODE = "mode"
CONF_STATE = "state"
CONF_SUMMARY = "summary"
CONF_PRESENT = "present"
CONF_CONNECTED = "connected"
CONF_POLL_INTERVAL = "poll_interval"
CONF_LOG_FRAMES = "log_frames"
CONF_SKIP_AUTH_CHECK = "skip_auth_check"

SECURITY = {"none": 0, "authenticate": 1}

SLOT_SCHEMA = cv.Schema(
    {
        cv.Optional(CONF_VOLTAGE): sensor.sensor_schema(
            unit_of_measurement=UNIT_VOLT, accuracy_decimals=3,
            device_class=DEVICE_CLASS_VOLTAGE, state_class=STATE_CLASS_MEASUREMENT),
        cv.Optional(CONF_CURRENT): sensor.sensor_schema(
            unit_of_measurement=UNIT_AMPERE, accuracy_decimals=3,
            device_class=DEVICE_CLASS_CURRENT, state_class=STATE_CLASS_MEASUREMENT),
        cv.Optional(CONF_CAPACITY): sensor.sensor_schema(
            unit_of_measurement="mAh", accuracy_decimals=0,
            icon="mdi:battery-charging", state_class=STATE_CLASS_MEASUREMENT),
        cv.Optional(CONF_TEMPERATURE): sensor.sensor_schema(
            unit_of_measurement=UNIT_CELSIUS, accuracy_decimals=0,
            device_class=DEVICE_CLASS_TEMPERATURE, state_class=STATE_CLASS_MEASUREMENT),
        cv.Optional(CONF_RUN_TIME): sensor.sensor_schema(
            unit_of_measurement=UNIT_MINUTE, accuracy_decimals=0,
            device_class=DEVICE_CLASS_DURATION, state_class=STATE_CLASS_MEASUREMENT),
        cv.Optional(CONF_RESISTANCE): sensor.sensor_schema(
            unit_of_measurement="mΩ", accuracy_decimals=0,
            icon="mdi:omega", state_class=STATE_CLASS_MEASUREMENT),
        cv.Optional(CONF_CYCLES): sensor.sensor_schema(
            accuracy_decimals=0, icon="mdi:counter", state_class=STATE_CLASS_TOTAL_INCREASING),
        cv.Optional(CONF_MODE): text_sensor.text_sensor_schema(icon="mdi:cog"),
        cv.Optional(CONF_STATE): text_sensor.text_sensor_schema(icon="mdi:battery-sync"),
        cv.Optional(CONF_SUMMARY): text_sensor.text_sensor_schema(icon="mdi:battery-charging-outline"),
        cv.Optional(CONF_PRESENT): binary_sensor.binary_sensor_schema(
            device_class=DEVICE_CLASS_BATTERY, icon="mdi:battery"),
    }
)

_BASE_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(SkyrcNC2500),
        cv.Optional(CONF_MAC_ADDRESS): cv.mac_address,
        cv.Optional(CONF_NAME_MATCH, default="skyrc"): cv.string,
        cv.Optional(CONF_CHANNEL): cv.int_range(min=1, max=30),
        cv.Optional(CONF_PIN, default="1234"): cv.All(cv.string_strict, cv.Length(min=1, max=16)),
        cv.Optional(CONF_SECURITY, default="authenticate"): cv.enum(SECURITY, lower=True),
        cv.Optional(CONF_POLL_INTERVAL, default="15s"): cv.positive_time_period_milliseconds,
        cv.Optional(CONF_LOG_FRAMES, default=False): cv.boolean,
        cv.Optional(CONF_SKIP_AUTH_CHECK, default=False): cv.boolean,
        cv.Optional(CONF_CONNECTED): binary_sensor.binary_sensor_schema(
            device_class=DEVICE_CLASS_CONNECTIVITY, entity_category=ENTITY_CATEGORY_DIAGNOSTIC),
        cv.Optional(CONF_SLOTS): cv.All(cv.ensure_list(SLOT_SCHEMA), cv.Length(max=4)),
    }
).extend(cv.COMPONENT_SCHEMA)

CONFIG_SCHEMA = cv.All(
    _BASE_SCHEMA,
    # Classic Bluetooth exists only on the original ESP32
    esp32.only_on_variant(supported=[VARIANT_ESP32], msg_prefix="skyrc_nc2500 (classic Bluetooth)"),
)


async def to_code(config):
    # Classic Bluetooth only: no BLE, and no esp32_ble / bluetooth_proxy on this node.
    esp32.request_bluetooth()
    esp32.request_software_coexistence()  # share the radio with Wi-Fi
    esp32.add_idf_sdkconfig_option("CONFIG_BT_ENABLED", True)
    esp32.add_idf_sdkconfig_option("CONFIG_BT_BLUEDROID_ENABLED", True)
    esp32.add_idf_sdkconfig_option("CONFIG_BT_CLASSIC_ENABLED", True)
    esp32.add_idf_sdkconfig_option("CONFIG_BT_SPP_ENABLED", True)
    esp32.add_idf_sdkconfig_option("CONFIG_BT_A2DP_ENABLE", False)
    esp32.add_idf_sdkconfig_option("CONFIG_BT_BLE_ENABLED", False)
    esp32.add_idf_sdkconfig_option("CONFIG_BTDM_CTRL_MODE_BR_EDR_ONLY", True)
    esp32.add_idf_sdkconfig_option("CONFIG_BTDM_CTRL_MODE_BLE_ONLY", False)
    esp32.add_idf_sdkconfig_option("CONFIG_BTDM_CTRL_MODE_BTDM", False)

    # The Bluetooth stack logs routine link housekeeping (sniff/unsniff every few seconds); silence it.
    for name in ("HCI", "BTM", "L2CAP", "RFCOMM", "SDP", "GAP", "BNEP", "PAN", "A2D", "AVDT", "AVCT", "APPL", "BTC", "OSI", "SMP"):
        esp32.add_idf_sdkconfig_option(f"CONFIG_BT_LOG_{name}_TRACE_LEVEL_NONE", True)

    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)

    if CONF_MAC_ADDRESS in config:
        cg.add(var.set_mac(config[CONF_MAC_ADDRESS].as_hex))
    cg.add(var.set_name_match(config[CONF_NAME_MATCH]))
    if CONF_CHANNEL in config:
        cg.add(var.set_channel(config[CONF_CHANNEL]))
    cg.add(var.set_pin(config[CONF_PIN]))
    cg.add(var.set_security(config[CONF_SECURITY]))
    cg.add(var.set_poll_interval(config[CONF_POLL_INTERVAL]))
    cg.add(var.set_log_frames(config[CONF_LOG_FRAMES]))
    cg.add(var.set_skip_auth_check(config[CONF_SKIP_AUTH_CHECK]))

    if CONF_CONNECTED in config:
        b = await binary_sensor.new_binary_sensor(config[CONF_CONNECTED])
        cg.add(var.set_connected_sensor(b))

    sensors = {
        CONF_VOLTAGE: "set_voltage_sensor", CONF_CURRENT: "set_current_sensor",
        CONF_CAPACITY: "set_capacity_sensor", CONF_TEMPERATURE: "set_temperature_sensor",
        CONF_RUN_TIME: "set_run_time_sensor", CONF_RESISTANCE: "set_resistance_sensor",
        CONF_CYCLES: "set_cycles_sensor",
    }
    for idx, slot in enumerate(config.get(CONF_SLOTS, [])):
        for key, setter in sensors.items():
            if key in slot:
                s = await sensor.new_sensor(slot[key])
                cg.add(getattr(var, setter)(idx, s))
        for key, setter in ((CONF_MODE, "set_mode_sensor"), (CONF_STATE, "set_state_sensor"), (CONF_SUMMARY, "set_summary_sensor")):
            if key in slot:
                t = await text_sensor.new_text_sensor(slot[key])
                cg.add(getattr(var, setter)(idx, t))
        if CONF_PRESENT in slot:
            b = await binary_sensor.new_binary_sensor(slot[CONF_PRESENT])
            cg.add(var.set_present_sensor(idx, b))
