# service/

Bar and front-of-house routines (Bartender, and Janitor-lite cleanup that any
crew script can reuse). One `run_script` call, one compact dict back.

| Script | Args | Purpose |
| --- | --- | --- |
| `showcase_stock.py` | `vendor` (default "Booze-O-Mat"), `showcase` (default "drink showcase"), `count` (default 6) or `items: [names]` | Vends bottles and racks them in the drink showcase. Product refs are read AT RUNTIME from the open Vending window - never hard-code ids. Walks vendor -> showcase per bottle. |
| `clean_bar.py` | `tool` (default "rag"), `radius` (default 6), `max_tiles` (default 10) | Pick up the tool by name, walk to every dirt/vomit/blood tile in view, scrub it. Re-run after new messes; cleaned tiles vanish. |
| `serve_item.py` | `item`, `mob` (both names, required), `say` (optional line after handing) | Fetch the item (walks adjacent first: in view is NOT in reach), walk to the patron, plain click GIVES the item (help intent; combat mode must be off), verify by the hand emptying. |

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
  before and after every vend.
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
