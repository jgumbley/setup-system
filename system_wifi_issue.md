# Wi-Fi Dropout Diagnosis (2026-02-22)

## Conclusion
The dropouts are AP-driven disconnect/steering events on SSID `Nyumbani`, not a local Wi-Fi adapter crash.

## Key evidence from this boot
- Interface and client are healthy when connected: `wlp2s0` up, `iwlwifi` loaded normally, no rfkill blocks, power save is off.
- `wpa_supplicant` repeatedly logs `WNM: Disassociation Imminent`, then `CTRL-EVENT-DISCONNECTED ... reason=12`.
- Counts since boot: 27 `WNM: Disassociation Imminent`, 27 `reason=12` disconnects, 14 auth rejects (`status_code=37`), 37 NetworkManager association failures (`association took too long` / `ssid-not-found`), 31 kernel-level low-ACK/lost/auth-timeout events.
- Example sequence (UTC):  
  13:03:06 `WNM: Disassociation Imminent` ->  
  13:03:12 disassociated `reason=12` ->  
  retries to `94:2A:6F:CE:6C:D4` fail/time out ->  
  reconnect to `94:2A:6F:CE:6C:D5` at 13:03:17.

## Why it keeps dropping
The AP is steering the client between multiple BSSIDs for the same SSID (`...:D5` on 5 GHz and `...:D4` on 2.4 GHz). During or after steering, authentication/association often fails (rejects/timeouts), creating repeated outage loops.

## AP-side correlation (UniFi events)
- Controller history shows repeated roaming between `Smegnet` and `Garden AP` throughout the day.
- Many roam decisions move to materially worse signal targets (examples from events: `-51 -> -74 dBm`, `-50 -> -83 dBm`, `-49 -> -85 dBm`), which is consistent with unstable steering policy rather than normal client roaming.
- Recent window:
  - 12:49:28 disconnect from `Smegnet` (`Last Connected To ... -65 dBm`)
  - 13:00:57 reconnect to `Smegnet` on 2.4 GHz channel 6 at `-51 dBm`
- This aligns with local logs (`WNM Disassociation Imminent`, reason `12`, repeated reauth failures).

## Isolation update: Garden AP powered off
- Even with `Garden AP` turned off, drop behavior continues.
- Post-`13:03:00` (UTC) local logs show 18 `WNM: Disassociation Imminent` events and 18 matching disconnects `reason=12` from `94:2A:6F:CE:6C:D5` (Smegnet 5 GHz BSSID).
- Current client state shows fallback/attachment on `94:2A:6F:CE:6C:D4` (2.4 GHz), confirming this is reproducible on a single AP/radio group and not only AP-to-AP roaming.

## Most likely cause
UniFi steering policy on `Smegnet` (especially 5 GHz -> other BSSID transitions) is too aggressive or mis-tuned for this client/environment, causing repeated AP-initiated disconnect cycles.

## Targeted mitigations to test
- Temporarily disable for this SSID: band steering, BSS Transition (802.11v), and Fast Roaming (802.11r).
- Use WPA2-only temporarily (disable WPA3 transition mode) while testing.
- Reduce 2.4 GHz TX power (Low/Medium) and keep 5 GHz preferred; avoid forcing clients onto distant 2.4 cells.
- Verify AP country/regulatory domain is correct for location (in US, avoid 2.4 GHz channel 12/13 plans).

## Current state
As of `2026-02-22T13:25:00+00:00`, the client is connected to `Nyumbani` (`wlp2s0`, `192.168.1.164/24`) on `94:2A:6F:CE:6C:D4` (2.4 GHz).

## Change log
- `2026-02-22T14:02:28Z`: In UniFi SSID `Nyumbani`, switched SSID settings from `Auto` to manual/custom so individual controls could be edited, then set `BSS Transition (802.11v)` to `Off` for isolation testing. Left other major roaming/security controls unchanged for this test pass.
- `2026-02-22T14:02:28Z`: `Garden AP` was powered back on to test under normal two-AP conditions.

## Active test window
- Test objective: verify whether disabling `802.11v` removes forced roam/disconnect loops while both `Smegnet` and `Garden AP` are active.
- Watch metrics: roam ping-pong frequency, roams to materially worse RSSI targets, and disconnect bursts around roam events.
