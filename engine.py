"""Core engine for The Hollow Gate — loads scenes from story/*.json and runs state machine."""

import json, sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

STORY_DIR = Path(__file__).parent / "story"


@dataclass
class GameState:
    inventory: List[str] = field(default_factory=list)
    max_inventory: int = 8
    companions: List[str] = field(default_factory=list)
    gold: int = 0
    trust: int = 50
    fear: int = 0          # new
    chapter: int = 1
    flags: Dict[str, Any] = field(default_factory=dict)
    character_class: Optional[str] = None
    history: List[tuple] = field(default_factory=list)

    def has(self, item: str) -> bool:
        return item in self.inventory

    def add_item(self, item: str) -> bool:
        if len(self.inventory) < self.max_inventory:
            self.inventory.append(item)
            return True
        return False

    def remove_item(self, item: str) -> bool:
        if item in self.inventory:
            self.inventory.remove(item)
            return True
        return False

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class Engine:
    def __init__(self):
        self.state = GameState()
        self.current_scene_id: str = "intro"
        self.scenes: Dict[str, Any] = {}
        self._load_all()

    # ── Loading ──────────────────────────────────────────────────────────
    def _load_all(self):
        for path in sorted(STORY_DIR.glob("chapter_*.json")):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.scenes.update({s["id"]: s for s in data.get("scenes", [])})

    def scene(self, sid: str):
        return self.scenes.get(sid)

    # ── Conditions ───────────────────────────────────────────────────────
    def ok(self, cond: Optional[str]) -> bool:
        if not cond:
            return True
        if cond == "never":
            return False
        if cond.endswith("_only"):
            return self.state.character_class == cond.replace("_only", "")
        if "_" in cond:
            key, _, val = cond.partition("_")
            if key == "trust":
                return self.state.trust >= int(val)
            if key == "gold":
                return self.state.gold >= int(val)
            if key == "fear":
                return self.state.fear >= int(val)
            if key == "flag":
                return self.state.flags.get(val) is True
        return self.state.has(cond)

    # ── Actions ──────────────────────────────────────────────────────────
    def do(self, action: Optional[str]):
        if not action:
            return
        for cmd in action.split(","):
            cmd = cmd.strip()
            if cmd.startswith("add_item,"):
                item = cmd.split(",", 1)[1]
                if self.state.add_item(item):
                    print(f"  [ acquired: {item} ]")
                else:
                    print(f"  [ pack full — can’t take {item} ]")
            elif cmd.startswith("rem_item,"):
                item = cmd.split(",", 1)[1]
                if self.state.remove_item(item):
                    print(f"  [ used: {item} ]")
            elif cmd.startswith("gold,"):
                n = int(cmd.split(",")[1])
                self.state.gold += n
                print(f"  [ gold {'+' if n >= 0 else ''}{n} ]")
            elif cmd.startswith("trust,"):
                n = int(cmd.split(",")[1])
                self.state.trust = max(0, min(100, self.state.trust + n))
                print(f"  [ trust now {self.state.trust} ]")
            elif cmd.startswith("fear,"):
                n = int(cmd.split(",")[1])
                self.state.fear = max(0, min(100, self.state.fear + n))
                print(f"  [ fear now {self.state.fear} ]")
            elif cmd.startswith("add_companion,"):
                who = cmd.split(",", 1)[1]
                if who not in self.state.companions:
                    self.state.companions.append(who)
                    print(f"  [ {who} joins ]")
            elif cmd.startswith("rem_companion,"):
                who = cmd.split(",", 1)[1]
                if who in self.state.companions:
                    self.state.companions.remove(who)
                    print(f"  [ {who} leaves ]")
            elif cmd.startswith("set_flag,"):
                k = cmd.split(",", 1)[1]
                self.state.flags[k] = True
                print(f"  [ note: {k} ]")

    # ── Display ──────────────────────────────────────────────────────────
    def status(self) -> str:
        lines = [
            f"Trust: {self.state.trust}  |  Fear: {self.state.fear}  |  Gold: {self.state.gold}  |  Pack: {len(self.state.inventory)}/{self.state.max_inventory}",
        ]
        if self.state.inventory:
            lines.append("Items: " + ", ".join(self.state.inventory))
        if self.state.companions:
            lines.append("Party: " + ", ".join(self.state.companions))
        return "\n".join(lines)

    # ── Game loop ────────────────────────────────────────────────────────
    def start(self):
        char_select()

        cls_name = None
        while True:
            pick = input("> ").strip()
            if pick == "1":
                cls_name = "Castellan"
                break
            if pick == "2":
                cls_name = "Hedgeborn"
                break
            print("Enter 1 or 2.")

        apply_class(self.state, cls_name)
        self.state.chapter = 1
        self.current_scene_id = "intro"
        self.run()

    def run(self):
        while True:
            scene = self.scene(self.current_scene_id)
            if not scene:
                print(f"Missing scene: {self.current_scene_id}")
                break

            header = f"Chapter {self.state.chapter}"
            width = max(len(header), 40)
            print("\n" + "=" * width)
            print(header.center(width))
            print("=" * width + "\n")

            print(scene["text"])
            print()

            print("─" * width)
            print(self.status())
            print("─" * width)

            avail = []
            for i, ch in enumerate(scene.get("choices", []), 1):
                if self.ok(ch.get("condition")):
                    avail.append((i, ch))

            if not avail:
                print("\nNo path forward.")
                break

            print("\nChoose:")
            for i, ch in avail:
                print(f"  {i}) {ch['text']}")

            choice = None
            while True:
                try:
                    raw = input("\n> ").strip()
                    if raw.isdigit():
                        idx = int(raw) - 1
                        if 0 <= idx < len(avail):
                            _, choice = avail[idx]
                            break
                    print("Pick a number from the list.")
                except (EOFError, KeyboardInterrupt):
                    print("\n\nFarewell.")
                    return

            self.do(choice.get("action"))
            self.state.history.append((self.current_scene_id, choice["text"]))
            self.current_scene_id = choice["next"]

            if self.current_scene_id.startswith("ending"):
                show_ending(self.current_scene_id)
                break

            # bump chapter gently based on how deep we are
            depth = len(self.state.history)
            if depth >= 6:
                self.state.chapter = min(self.state.chapter + 1, 6)


def char_select():
    print("=" * 40)
    print("THE HOLLOW GATE".center(40))
    print("=" * 40)
    print("\nThe King’s daughter is gone. The kingdom is silent.\n")
    print("Who are you?\n")
    print("  1) Castellan")
    print("     Born in the castle. You know halls and guards.")
    print("     Starts with: sword, castle_talisman, 20 gold\n")
    print("  2) Hedgeborn")
    print("     Raised in the villages. You know dirt roads and secrets.")
    print("     Starts with: knife, poultice, village_map, 5 gold\n")


def apply_class(state: GameState, cls: str):
    state.character_class = cls
    if cls == "Castellan":
        state.gold = 20
        state.add_item("sword")
        state.add_item("castle_talisman")
    else:
        state.gold = 5
        state.add_item("knife")
        state.add_item("poultice")
        state.add_item("village_map")


def show_ending(end_id: str):
    print("\n" + "=" * 40)
    print("THE END".center(40))
    print("=" * 40 + "\n")

    if end_id == "ending_fight":
        print("You won by steel and fury. The kingdom will sing your name for a generation.")
    elif end_id == "ending_talk":
        print("You won with words and patience. Darkness retreated where it could not be reasoned with.")
    elif end_id == "ending_clever":
        print("You won with a trick the old stories never predicted. The hollow gate closes behind you.")
    elif end_id == "ending_sacrifice":
        print("You chose the hardest road. Some will remember. Most will never know.")
    else:
        print("A new ending awaits another journey.")

    print(f"\nFinal state — Trust: {50},  Fear: 10,  Gold: 50,  Pack: 3 items  (example)")
