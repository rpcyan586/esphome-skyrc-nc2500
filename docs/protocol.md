# SkyRC NC2500 — protocol notes (from APK com.revogi.smartcharge 0.9.9, decompiled 10 Oct 2026)

Derived by analysing the vendor Android app com.revogi.smartcharge 0.9.9 (the old "SkyRC Smart Charger" app; the current "SkyRC" app v2.92 does not support the NC2500), then confirmed against real hardware.

## Transport
- Classic Bluetooth, RFCOMM/SPP UUID 00001101-0000-1000-8000-00805F9B34FB (not BLE).
- Charger contains an "iBT-02" bridge module; app wraps it with com.vsd.android.support.ibridge (session layer with handshake — NOT yet decoded).

## Link framing (class ibridge.p, decoded)
- frame = 0x55, LEN(1 byte if <=252, else 0x00,hi,lo), PAYLOAD, CHK
- CHK = two's complement of (sum(LEN bytes) + sum(PAYLOAD)) & 0xFF

## Session layer (ibridge.c / i, NOT decoded)
- Handshake/identification before app data flows (eventProtocolInitialized).
- App data is sent as RFA write: cmd 0x12 (normal) / 0x13, payload = [0x82][len][data].
- Replies arrive via eventDRDY type 1 as [0x0F][len]...

## Application layer (StartPage)
- Query all:    0F 03 55 00 55 FF FF   (cmd 0x55, chk = cmd+arg)
- Query version: 0F 03 57 00 57 FF FF   (cmd 0x57)
- Reply starting 0x0F: device id as ASCII hex "4e4332353030" = "NC2500", firmware major.minor, serial.
- Status record: 17 bytes per slot (dealBatteryInfo), big-endian 16-bit:
  +0 mode, +1 exists, +2..3 mAh, +4..5 worktime, +6..7 voltage, +8..9 current,
  +10 nowDoing(state), +11 temp, +12 cycle count, +13..14 single-cell V, +15..16 reserved
- TODO: confirm units, slot count, state/mode enums, session handshake.

## Session/handshake findings (second pass)
- Session messages inside link frames are [0x1B][cmd][data...]  (ibridge.c.b). App data = [0x1B][0x12][0x82][len][payload]; 0x13 = alt write mode.
- Init sends [1B 11 01 09], then info requests [1B 01 lo hi] for ids 0x0100,0x0100,0x0101,0x0102,0x0103,0x0106,0x0107 (table c.b), then challenge.
- Challenge: app sends [1B 60 <16 random bytes>], module replies cmd 0xE0 (the app verifies the module). NOT needed - the charger answers without it.
- Unknown: whether the module insists on this handshake before serving RFA data (app gates writes on flag m=initialized). Untested.
- This container has NO Bluetooth (AF_BLUETOOTH socket -> EAFNOSUPPORT). Testing needs ESP32 (classic BT, original ESP32 chip) or a separate Linux box.

## Application layer details (third pass) + ESPHome build
- Reply to status query (cmd 0x55): 75 bytes = 0F, len(71), cmd, ?, 4 x 17-byte slot records (from byte 4), chk(=sum of bytes 2..71), FF FF. => 4 bays.
- Inbound RFA data inside session frames: [1B 91 (00|80) type len data...]; data starts 0x0F.
- Units: voltage mV, current mA, capacity mAh, run time SECONDS, temperature = raw - 40 degC, "single cell" = internal resistance mOhm.
- Mode names (rec[0]): 0 Charge, 1 Refresh, 2 Break-In, 3 Discharge, 4 Cycle, 5 Done, 6 Wait, 7 Error.
- State names (rec[10]): 0 Not working, 1 Charging, 2 Rest, 3 Discharging, 4 Rest, 5 Done, 6 Done.
- Bluetooth device name filter in the vendor app: lowercase name contains "skyrc" (also "skyrcnc2500").
- Info request ids sent at start: 0100 0100 0101 0102 0103 0106 0107 2000 2100 as [1B 01 lo hi]; then [1B 11 01 09]; then challenge [1B 60 <16 rand>].

## ESPHome implementation (written 10 Oct 2026, NOT yet run against hardware)
- Needs an ORIGINAL ESP32. First flash is by USB (esphome run / web flasher), later OTA.
- First run: mac_address unset -> inquiry lists every Bluetooth device in the log; copy the charger's address into the config.
- Switch "Bluetooth Link" releases the charger so the phone app can connect (it accepts one connection at a time).
- Unknowns to check on first run: PIN (1234 vs 0000), whether handshake order is accepted, units vs the app's screen.

## WORKING (confirmed live on hardware, 10 Oct 2026) - corrected stack
My first firmware skipped two layers and the charger stayed silent. The full stack, bottom to top:
1. Link:    55 | len | payload | chk                       chk = ~(len+sum)+1
2. Module:  00 | cmd | seq(2) | data  - numbered, ACKED, resent every 500 ms until acked. seq starts 0.
            3F [03 E8 01] = open channel 1000   -> reply 00 41 seq 00 3F
            43 [03 E8 | adapter frame] = data to charger -> reply 00 41 seq 00 43
            Charger data arrives as 00 42 seq(2) 03 E8 <adapter frame>; we must ack with 00 02 seq(2) 00 42.
3. Adapter: 95 19 | total(=len+4) | message | chk, chk = ~(len_lo+len_hi+88+sum(message))+1  (+90 instead of 88 if len+4>=256; 16-bit length form when long)
4. Session: 1B | cmd | data     (info requests 01, mode 11, challenge 60, RFA write 12, replies 81/91/E0)
5. Charger: status query 0F 03 55 00 55 FF FF inside RFA write 1B 12 82 07 ...; reply = 1B 91 80 02 4B 0F 47 55 ... (75 bytes)
Identity replies seen: "NC2500", "AA/AAA CHARGER", "SkyRC Technology Co.,Ltd".
Bluetooth: charger name "skyrcNNNN", address AA:BB:CC:DD:EE:FF, serial channel 2, pairing OK with PIN 1234 (no prompt).
The charger's Bluetooth only answers searches while it is switched on by holding ENTER (blue LED).
Units confirmed: 56 mAh after 1019 s at 0.200 A (= 0.2*1019/3600). Voltage mV, current mA, temp = raw-40.

## Writing slot settings (verified for Charge mode, 10 Oct 2026)
Command (inside an RFA write 1B 12 82 11 ...):  0F 0D 05 <slot 0-3> <mode> <v1 hi lo> <v2 hi lo> <v3 hi lo> <cycles> 00 00 <chk> FF FF
chk = sum of bytes 2..13. Modes: 0 Charge, 1 Refresh, 2 Break-In, 3 Discharge, 4 Cycle. Slot byte 4 = all slots (not used).
v1 = charge mA (Charge/Refresh/Cycle), v2 = discharge mA (Refresh/Discharge/Cycle), v3 = rated capacity mAh (Break-In), cycles for Cycle.
Limits: charge 200-2500 step 100 mA; discharge 100-1000 step 100 mA; capacity 500-3500 step 100 mAh; cycles 1-12.
Verified live: slot 1 Charge 0.2 A -> 0.3 A -> 0.2 A; the charger followed within one poll; other slots untouched. Refresh/Break-In/Discharge/Cycle packets are decoded from the app but NOT tested on a real battery.
The app has no stop command (stop on the charger). System settings (delta-V, temp cut-off, cutoff voltage, trickle) use cmd 0A (set) / 0B (get): decoded but not exposed.
Firmware update commands exist in the app: deliberately never used.

## Observed program sequencing (Refresh, 11 Oct 2026)
state byte 1 Charging (5 h) -> 2 Rest (1 h) -> 3 Discharging -> 2 Rest (1 h) -> 1 Charging (5 h) -> 5 Done.
The 16-bit work-time field restarts at 0 at each phase change (it is seconds; the component reports minutes).
