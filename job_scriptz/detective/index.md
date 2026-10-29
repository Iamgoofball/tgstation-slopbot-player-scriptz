# job_scriptz/detective/

The detective: forensic scanner on everything suspicious, records checks,
the office's private nook. Station: MetaStation. The office sits at
x=119-126 y=157-163 (south of the Security Office, north of the Law
Office); the private nook is behind the interior door. Clicks land only
within 1 tile - walk adjacent first (the scripts do).

## Office layout (map coords; find machines by NAME - ids re-roll)

- Public room: office chair (123,162), work tables (122,162)/(122,163) +
  (124,163), security records console (124,162), medical records console
  (124,161), security camera monitor + office shutters control (124,163),
  interior door to the nook at (120,159) (bump-opens; stand ON its tile).
- Private nook (dark): a filing cabinet row + the detective's cabinet.
- The security camera CONSOLE (Security Office, (120,169)) opens a
  CameraConsole tgui when clicked adjacent: actions `start_tracking`,
  `switch_camera {camera}` (~260 camera refs in static_data.cameras).
  Detect the window by scanning ALL tgui-window blocks for the interface
  name - matching only the first block misdiagnosed it as dead once.

## The dark nook (the biggest trap)

- **Search FORGETS dark / out-of-sight things within minutes** - the nook
  vanishes from the known index while you stand in the lit office.
  `sk.tile(x, y, all=True)` still reports REMEMBERED contents, and CLICKS
  STILL LAND on dark tiles (open/take/scan all work; a tgui window warns
  "too dark to read!" but opens anyway).
- So: anchor walks on the searchable records console, reach the nook door
  by MetaStation geometry (4W 3N of the console; args door_x/door_y
  override), then find the cabinets by TILE READ of the tiles just south
  of the door. Staging verified: public room -> interior door -> nook.

## The detective's cabinet

- Opens like a locker: 1st click UNLOCK, 2nd OPEN; RMB = lock. State
  reads from the tile line overlays ([cabinet_door], [locked],
  [unlocked]; open shows as cabinet_open).
- Contents (leave cabinet stock in place): security holobarrier
  projector, detective's holster, binoculars, crew pinpointer, inspector's
  fedora, spyglass kit, security radio headset, flak vest, seclite,
  pepperspray, evidence bag box.
- My carry kit: forensic scanner + evidence bags -> backpack (DRAG - a
  click with the scanner held SCANS the backpack instead). Everything
  else stays cabinet stock; close the cabinet after use.

## Spawn kit (all on the mob)

black gloves, trenchcoat, fedora, hard-worn suit, loose tie, chalk,
Zippo, bowman headset, mindshield, PDA/ID; INSIDE the backpack: a second
forensic scanner, a police baton, evidence bag box + bags.

## Forensic scanner (tgui "ForensicScanner")

- Scan = click the target with the scanner in the ACTIVE hand ("You scan
  X. The scanner is now analysing the results..."), result lands in the
  log ~10-15 s later. Works on objects AND mobs.
- In-hand click opens the window: actions `clear`, `delete {index}`,
  `print`; data.logs[] = entries {scanTarget, scanTime,
  dataEntries[{category, data{}}]}; categories Prints (md5-ish hashes),
  Fibers ("Material from a brown trenchcoat."), Blood.
- Read data.logs via path: it returns `items: N` + a pretty-printed JSON
  array - slice first '[' .. last ']' and json.loads it whole.
- A pristine target yields an entry with EMPTY dataEntries - "nothing
  found (clean target)" is a VALID verdict; traces appear once the target
  has been handled or bled.
- Storage is DRAG-only (scanner -> backpack id): clicking the worn
  backpack with the scanner held scans it. Retrieval: empty-hand click
  the backpack (opens the panel), click the scanner's SCREEN icon inside,
  close the panel via its "close" button.
- The X hotkey swaps hands - a scanner in the NON-active hand needs only
  a swap, not retrieval. NEVER open a records console with a held
  scanner: item-in-hand = attackby (it scan-sweeps the console).

## Records consoles (verified live as the detective)

- security records console (124,162): `security-officer/
  sec_records_control.py` with args {mode, console: <id>} - list verified
  (login/logout round-trip too).
- medical records console (124,161): a WALL COMPUTER, not a laptop, but
  `coroner/medical_records.py` with args {action: "read", laptop: <id>}
  drives it identically (same manifest; a manifest rebuild can
  transiently change the list mid-round - the script retries and reports
  honestly).
- A held item in the active hand turns the console click into an
  attackby - empty the hand or X-swap first.

## Live notes (round-labeled observations, not durable truths)

- The manifest held 17 records / 4 unique names this round (my previous
  bodies share the name "Lennox Fields" - one record per body; actions
  target the first ref per name).
- Both records consoles sit side by side (124,162)/(124,161); the camera
  monitor faces south from its table at (124,163).

## Scripts

| Script | Args | What it does |
| --- | --- | --- |
| `detective_office_check.py` | `no_walk`?, `door_x`?/`door_y`?, `say`? | One-envelope office survey: staged walk (records console -> interior door -> nook), detective's cabinet found by TILE READ (search forgets the dark nook), unlock/open/contents/close (tidy), records + medical records consoles + camera monitor + shutters control located, kit check. |
| `forensic_scan.py` | `target` (obj or mob id) or `target_name`, `x`?/`y`?, `wait_s`?=13, `print`?, `clear`? | Forensic scanner driver: scanner ensured in the active hand (both hands + X-swap + backpack panel flow), walk to target, scan click verified by chat, log window parsed (pretty JSON array; prints/fibers/blood), match + findings verdict; optional print / clear. |

Reuse (verified from this office):
`security-officer/sec_records_control.py` (records console),
`coroner/medical_records.py` (medical records console).
