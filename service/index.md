# service/

Bar and front-of-house routines (Bartender, and Janitor-lite cleanup that any
crew script can reuse). One `run_script` call, one compact dict back.

| Script | Args | Purpose |
| --- | --- | --- |
| `showcase_stock.py` | `vendor` (default "Booze-O-Mat"), `showcase` (default "drink showcase"), `count` (default 6) or `items: [names]` | Vends bottles and racks them in the drink showcase. Product refs are read AT RUNTIME from the open Vending window - never hard-code ids. Walks vendor -> showcase per bottle. |
| `clean_bar.py` | `tool` (default "rag"), `radius` (default 6), `max_tiles` (default 10) | Pick up the tool by name, walk to every dirt/vomit/blood tile in view, scrub it. Re-run after new messes; cleaned tiles vanish. |
| `serve_item.py` | `item` (required); `mob` + default mode, OR `table: true` (+ `table_name`, default "table"); `say` optional | Fetch the item (exact name preferred; walks adjacent first: in view is NOT in reach). Default serve: walk to the patron and press **G** (the OFFER hotkey) - NEVER a click, a click with an item in hand USES the item on the mob. Table mode sets the item on a table next to them. Verified by the hand emptying. Patrons can refuse: read the chat, never repeat. |
| `dispenser_mix.py` | `machine` ("booze dispenser"/"soda dispenser"), `container` (e.g. "shaker"), `doses: [{reagent, amount}]`, `say` optional | Mix via a ChemDispenser: container in the ACTIVE hand -> walk ADJACENT -> click machine -> tgui `insert` -> per dose `amount {target}` (5..50) + `dispense {reagent}` -> `eject` -> close. Recipes auto-convert (vodka+OJ 1:2 = Screwdriver). `mix_drink.py` (pour-by-clicks) is DEPRECATED for machine mixing - the dispensers are the verified path. |

Gotchas
- Interaction range is ~1 tile: always `bot.goto` next to the vendor/machine
  BEFORE clicking (a far click silently does nothing - the window never opens).
- Stale tgui windows lie: close leftover windows before opening a machine's
  UI, and match the window by its `interface:` line + title, not by id.
- The drink showcase stocks via a plain click WITH the bottle in hand
  (chat "You put..."); an occupied hand means the vend step failed - the
  script records it in `skipped` with the reason.
- Spill echo: cleaning only counts when chat says clean/wipe/mop; tiles that
  error are reported in `misses` (usually unreachable, e.g. behind shutters).
- **Silent cleans (verified 2SPOOKY)**: rag/mop cleaning produces NO chat echo.
  The script therefore clicks the TURF (`click {x, y, turf: true}`) with the
  tool in the active hand and verifies success by the spill object VANISHING
  from view, not by chat. Dirt has `mouse_opacity 0` (clicks pass through to
  the turf anyway); clicking the spill object itself does nothing.
- Vend drops the bottle INTO an empty active hand (does not fall to the
  floor); with both hands full it drops at the vendor's feet - that is how a
  buggy run left bottles scattered, and why the stocker checks the hand
  before and after every vend. serve_item treats "already in either hand"
  as holding (vend -> serve without a re-fetch).
- serve_item fetch priority: EXACT name at any distance beats a substring
  match next to you - a near "broken space beer" once beat a far "space
  beer" and a drunk patron got a second broken bottle. The script now also
  refuses a substring fetch whose name adds "broken" (stock exhausted ->
  vend fresh instead).
- Table mode's success check is weak: it confirms the hand emptied + SOME
  item of that name is in view - a pre-existing one can false-positive.
  After a table serve, verify by searching for the item NEAR THE TABLE TILE
  you clicked, or by a chat "You place ..." line.
- While you work, patrons talk/scream/act. Every script's postcheck surfaces
  `heard` - READ IT, don't just read the `result`. A scream you ignore is a
  customer you failed (see README 2 #15: inline probes once ate the evidence).
- **Patrons can refuse a serve.** The give click can succeed mechanically and
  still be WRONG: John Alcoholic shouted "DON'T FUCKIN' FEED IT TO ME" after
  a beer was offered. A refused serve is an escalation hazard - read the
  chat tail after the click, never repeat the offer, stow the item (plain
  click on the backpack with it in hand) and move on.
- Radio keys: Common `;`, Service `:v` - sent as a PREFIX in `sk.say` text
  (";The bar is now open!"). No echo comes back; the message just goes.
- **Offers can land LATE.** serve_item said "did not transfer" for John
  Alcoholic; the acceptance ("John takes Screwdriver from Lennox Fields",
  plus a "Thank you") arrived BETWEEN runs, ~20s later. Never re-offer on
  the "did not transfer" verdict alone - re-read the chat tail first; the
  script now refuses when the log shows the item already taken.
- **Vanished items are usually in someone's hands.** Items are picked up
  by other crew/patrons. Check order: (1) `sk.search` reports "carried by
  <mob>" for held items; (2) EXAMINE the nearby mob - their examine lists
  what they wear AND hold in each hand; (3) an inventory rustle sound in
  the sound log = someone pocketed it (bag). dispenser_mix now raises a
  "carried by X" error instead of "not found" when the container vanished.
- **Vendor UI truncates its product list.** The Booze-O-Mat window showed
  40 products but the raw window JSON had 57: 30 drinking glasses + 12
  shotglasses were invisible. Read `static_data.product_records` via
  `sk.tgui_window(id, find="drinkingglass")` (or any substring) and vend by
  the record's `ref`. The smartfridge next to the Kitchen counter was EMPTY
  (contents: []) - glasses come from the Booze-O-Mat, not the showcase.
- **Emptying a container: combat mode + right-click splash.** To dump a
  shaker's contents: (1) toggle combat mode ON - the HUD button's icon state
  is `combat` when ON and `combat_off` when OFF (read it via sk.screen());
  a click that "does not engage" usually means it was already OFF and the
  first click DID work but the state read was stale; (2) container in the
  ACTIVE hand; (3) RIGHT-click a floor tile (left-click does nothing; a
  left-click pour only transfers the 10u setting into another container).
  All contents splash out. Then toggle combat OFF immediately.
- **The kitchen/bar sink FILLS containers with Water** - it does not empty
  them. Splashing is the only way to dump; right-clicking the sink tile
  with a container just gets wet floor (and "The shaker is empty!" if it
  already was).
- **Pickup rule that bit twice**: with an item in the ACTIVE hand, clicking
  a floor item USES the active item on it (shaker-on-rag = "shaker is
  empty!" warning). Press X to bring an EMPTY hand active before picking
  anything up.
- **Dispensers are only reachable from inside the Bar.** From the Kitchen
  side they read "out of sight" even with the counter shutters open. Walk
  through the Bar door (135,127) to tile 132,125 and both dispensers are
  in view/adjacent. dispenser_mix live-verified on BOTH: 15 Vodka (booze)
  + 30 Orange Juice (soda) -> 45u Screwdriver via the auto-convert recipe.
- **Pouring between held containers**: click the TARGET container (e.g. the
  glass in your other hand) with the SOURCE in the active hand. Transfer is
  10u per click at the default setting; the examine line says the transfer
  amount ("left-click or right-click in-hand to increase or decrease").
  A drinking glass holds 50u.
