# Capitulation Meter

A small add-on for the [BUG Mod](https://forums.civfanatics.com/forums/civ4-bug-mod.196/)
for Civilization IV: Beyond the Sword. While you are at war, it shows on the main screen how
close each AI is to capitulating to you, and which conditions are still missing.

```
Montezuma: no (1 missing)
  - War success 50, need 52 (theirs 12)
  + Their power 400, max ~593 (by world average)
  + Land 30% / pop 26% of yours (one under 50%)
```

> **Status:** passes offline tests on the game's Python 2.4 with a mocked game world.
> It has not been confirmed in a real game yet.

This shows information the game normally hides, so it is arguably cheating. It only reads
game data and changes nothing. It turns itself off in network multiplayer.

## Requirements

- Civilization IV: Beyond the Sword 3.19
- BUG Mod installed in `CustomAssets` (written against BUG 4.4)

Mods that ignore `CustomAssets` (`NoCustomAssets = 1`) do not load it. Numbers may also be
wrong in mods that ship their own DLL, because they can change the rules.

## Install

From a PowerShell window in this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

The script copies two files into `My Games\Beyond the Sword\CustomAssets`, adds one line to BUG's
`Config\init.xml`, and keeps a backup of it as `init.xml.bak`. Pass `-CustomAssets "<path>"` if
yours is elsewhere.

By hand:

1. Copy the `CustomAssets` folder here over your own.
2. In `CustomAssets\Config\init.xml`, add this below `<load mod="MoreCiv4lerts"/>`:
   ```xml
   <load mod="Capitulation Meter"/>
   ```

To uninstall, remove that line.

## Use

- The panel appears at the top left while you are at war with an AI.
- `Alt+Ctrl+V` cycles full details, one line per enemy, and hidden.
- You get a message when an enemy becomes willing to capitulate.
- Position and alert settings are in `Capitulation Meter.ini` in BUG's `UserSettings` folder.

The headline verdict is the game's own answer. The lines below it re-implement the game's
formula to explain the verdict. The "max" power is approximate, because the world average moves
as units are built and lost.

## How capitulation works

The rule is `CvTeamAI::AI_surrenderTrade` in the BTS DLL. There is no random roll. An enemy you
are at war with accepts when all of these hold:

| Condition | Rule |
|---|---|
| War success | Yours is at least theirs + 40. City capture +10, kill attacking +4, kill defending +3, capturing a unit such as a worker +1. Peace resets it. |
| Power vs world | Their power x 1.4 is at or below the average power per living team, adjusted for strong or hostile land neighbours. |
| Power vs you | Their power x 1.4 is at or below 2/3 of yours. Yours is scaled by relative war success (up to x2), and cut 25% if you are their worst enemy. |
| Size | Their land or their population is under 50% of yours. |
| Neighbours | No stronger land neighbour of theirs is at war with you but not with them. |
| Basics | You have Feudalism, neither of you is a vassal, and they are willing to talk. |

The 1.4 varies by leader: 1.9 for Genghis Khan and Sitting Bull, 1.2 for Gandhi, Mansa Musa,
Catherine and De Gaulle, for example.

The AI only offers capitulation by itself after more than 10 turns of war. You can propose it
as soon as they will talk.

## Tests

`tests\run.ps1` runs the module in the game's own `python24.dll` against a mocked game. It needs
the game installed and 32-bit PowerShell:

```powershell
& "$env:WINDIR\SysWOW64\WindowsPowerShell\v1.0\powershell.exe" -ExecutionPolicy Bypass -File .\tests\run.ps1
```

## License

GNU General Public License, version 3 or later. See [LICENSE](LICENSE). The BUG Mod, which this
extends, is also GPL version 3. No BUG or Firaxis files are included here.
