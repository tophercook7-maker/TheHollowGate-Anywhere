#!/usr/bin/env python3
"""
THE HOLLOW GATE
A text adventure. Save the King's daughter. Or die trying.

Run: python3 game.py
"""

import json
import sys
from pathlib import Path

# ── Game State ──────────────────────────────────────────────────────────────
class GameState:
    def __init__(self):
        self.inventory = []        # list of item names
        self.max_inventory = 6
        self.companions = []       # list of companion names
        self.gold = 0
        self.trust = 50            # 0-100, affects endings
        self.chapter = 0
        self.flags = {}            # story flags (events, choices)
        self.character_class = None

    def has(self, item):
        return item in self.inventory

    def add_item(self, item):
        if len(self.inventory) < self.max_inventory:
            self.inventory.append(item)
            return True
        return False

    def remove_item(self, item):
        if item in self.inventory:
            self.inventory.remove(item)
            return True
        return False

# ── Story Data ──────────────────────────────────────────────────────────────
# Scenes are keyed by ID.
# Each scene has:
#   text: str           – narrative shown to player
#   choices: list       – each choice is {text, next, condition?, action?}
#   condition: optional str (python expression using state vars)
#   on_enter: optional list of actions to run when scene loads

CHARACTERS = {
    "Castellan": {
        "description": "Born in the castle. You know halls and guards.",
        "items": ["sword", "gold_50", "castle_talisman"],
        "gold": 0,
        "bonus": "castle_talisman",
    },
    "Hedgeborn": {
        "description": "Raised in the villages. You know dirt roads and secrets.",
        "items": ["knife", "poultice", "village_map"],
        "gold": 5,
        "bonus": "village_map",
    },
}

COMPANIONS = {
    "ser_vale": {
        "name": "Ser Vale",
        "description": "A knight stripped of his honor.",
        "requires": None,
    },
    "moth": {
        "name": "Moth",
        "description": "A street urchin with quick fingers.",
        "requires": "gold_20",
    },
    "hedge_witch": {
        "name": "The Hedge Witch",
        "description": "Old magic in a cabin of bones.",
        "requires": "village_map",
    },
    "rook": {
        "name": "Rook",
        "description": "A raven that speaks. Or a madman.",
        "requires": "castle_talisman",
    },
}

SCENES = {
    "intro": {
        "text": """\
THE HOLLOW GATE

The King does not look up when you enter. His crown is upside-down on the table.
The spymaster was found dead that morning — no wounds, no marks, a scream frozen on his face.

"Elara was taken last night from her chambers. No body. No ransom. The royal wizard
says he felt a door open... somewhere else."

He slides three things across the table:

  1. A signet ring — opens any door in the kingdom
  2. A pouch of gold
  3. A sealed letter from the spymaster

"One condition," he says. "Find her. Come back without her, and I won't need to execute you."

You step into the courtyard. The sun is setting.

WHAT DO YOU DO?

  A) Take the signet ring and ride for the Wastes
  B) Take the gold and find the city underworld
  C) Ask the wizard about the sealed letter
  D) Seek out the castle captain for men""",
        "choices": [
            {"text": "Take the signet ring", "next": "wastes_gate", "action": "add_item,signet_ring"},
            {"text": "Take the gold", "next": "city_gates", "action": "add_item,gold_50,gold,50"},
            {"text": "Ask the wizard", "next": "wizard_tower", "condition": "never"},
            {"text": "Seek the captain", "next": "barracks", "condition": "never"},
        ],
    },
    "wastes_gate": {
        "text": """\
THE WASTES GATE

The city wall ends. Beyond it, the Wastes — grey hills and old bones. A storm
is rolling in.

A merchant caravan is huddled by the gate, too afraid to move. A lone rider
watches you from a rock.

You have the signet ring. You could:

  A) Show the ring, demand passage and horses
  B) Sneak past when the storm hits
  C) Talk to the rider — they look like they know this land
  D) Join the caravan and wait for morning""",
        "choices": [
            {"text": "Demand passage", "next": "rider_join", "action": "trust,-10"},
            {"text": "Sneak past", "next": "wastes_lost", "condition": "hedgeborn_only"},
            {"text": "Talk to the rider", "next": "rider_join"},
            {"text": "Join caravan", "next": "caravan", "action": "add_item,supplies"},
        ],
    },
    "rider_join": {
        "text": """\
THE RIDER

The rider is young. Eyes like flint.

"I know where the tracks go," they say. "But I don't work for crowns."

They watch your hand on your weapon.

"I guide lost souls through the Wastes for a pouch of gold. Or a favor. Or..."

They smile. It doesn't reach their eyes.

"...I could use a companion who isn't likely to die before sundown."

WHAT DO YOU DO?

  A) Pay the rider (20 gold) and gain a guide
  B) Refuse and continue alone
  C) Offer something else instead of gold""",
        "choices": [
            {"text": "Pay 20 gold", "next": "wastes_ride", "condition": "gold_20", "action": "gold,-20,add_companion,rider"},
            {"text": "Refuse", "next": "wastes_alone", "action": "trust,-5"},
            {"text": "Offer something else", "next": "rider_bargain", "condition": "castle_talisman"},
        ],
    },
    "wastes_ride": {
        "text": """\
ON THE ROAD

You ride hard for two days. The rider — who calls themselves Ash — knows every
rock and raven in the Wastes.

On the second night, Ash points north.

"Someone was here," they say. "Not long ago. Not human."

You find an old doorway half-buried in the hillside. Stone. No handle. No keyhole.

Just a symbol carved above it — something that makes your eyes hurt.

Ash steps back.

"I'm not going in there."

WHAT DO YOU DO?

  A) Enter alone
  B) Find another way
  C) Convince Ash to stay with you (requires trust 60+)""",
        "choices": [
            {"text": "Enter alone", "next": "hollow_gate", "action": "trust,-15"},
            {"text": "Find another way", "next": "hill_search"},
            {"text": "Convince Ash", "next": "hollow_gate", "condition": "trust_60"},
        ],
    },
    "hollow_gate": {
        "text": """\
THE HOLLOW GATE

The stone is cold under your fingers. The symbol glows when you touch it.

The wall doesn't open — it breathes.

You step through, and the world ends.

Darkness. Not night-dark. Something older. Something that eats light.

Ahead, you hear a voice — a girl's voice, singing a lullaby your mother used
to hum.

Elara.

She's close. But something else is with her.

WHAT DO YOU DO?

  A) Follow the singing
  B) Move quietly through the dark
  C) Light a torch to see what's around you""",
        "choices": [
            {"text": "Follow singing", "next": "finale_start"},
            {"text": "Move quietly", "next": "finale_start", "action": "add_item,shadow_blade"},
            {"text": "Light torch", "next": "finale_blind", "condition": "poultice"},
        ],
    },
    "finale_start": {
        "text": """\
THE SINGER

The lullaby stops.

A girl sits in a room made of stone, hands folded in her lap. Her eyes are
empty — not blind, but seeing things you can't.

"Her name isn't Elara," says a voice from the shadows. "But she answers to it
sometimes."

A figure steps out. Tall. Wearing the dead spymaster's face like a mask.

"Take her. She's broken now. Not worth much to anyone."

WHAT DO YOU DO?

  A) Fight
  B) Talk
  C) Use what you've gathered""",
        "choices": [
            {"text": "Fight", "next": "ending_fight"},
            {"text": "Talk", "next": "ending_talk", "condition": "trust_70"},
            {"text": "Use an item", "next": "ending_clever", "condition": "signet_ring"},
        ],
    },
}

CHAPTER_SCENES = {
    1: ["intro", "wastes_gate", "rider_join", "wastes_ride"],
    2: ["hollow_gate", "finale_start"],
}

# ── Engine ──────────────────────────────────────────────────────────────────

class Engine:
    def __init__(self):
        self.state = GameState()
        self.current_scene = "intro"
        self.history = []

    def evaluate_condition(self, condition):
        if not condition:
            return True
        if condition == "never":
            return False
        if condition.endswith("_only"):
            return self.state.character_class == condition.replace("_only", "")
        if condition.startswith("trust_"):
            threshold = int(condition.split("_")[1])
            return self.state.trust >= threshold
        if condition.startswith("gold_"):
            threshold = int(condition.split("_")[1])
            return self.state.gold >= threshold
        return self.state.has(condition)

    def apply_action(self, action_str):
        if not action_str:
            return
        for cmd in action_str.split(","):
            cmd = cmd.strip()
            if cmd.startswith("add_item,"):
                item = cmd.split(",", 1)[1]
                if self.state.add_item(item):
                    print(f"  [ + {item} ]")
                else:
                    print(f"  [ Inventory full! Couldn't take {item} ]")
            elif cmd.startswith("gold,"):
                _, amt = cmd.split(",")
                self.state.gold += int(amt)
                sign = "+" if int(amt) >= 0 else ""
                print(f"  [ {sign}{amt} gold ]")
            elif cmd.startswith("trust,"):
                _, amt = cmd.split(",")
                self.state.trust = max(0, min(100, self.state.trust + int(amt)))
                print(f"  [ trust {self.state.trust} ]")
            elif cmd == "add_companion,rider":
                self.state.companions.append("rider")
                print("  [ Ash joins your party ]")

    def show_scene(self):
        scene = SCENES.get(self.current_scene)
        if not scene:
            print("ERROR: scene not found:", self.current_scene)
            return

        # Chapter header
        ch = self.state.chapter
        if ch:
            print(f"\n{'='*40}")
            print(f" CHAPTER {ch}")
            print(f"{'='*40}\n")

        print(scene["text"])
        print()

        # Show status bar
        print("─" * 40)
        print(f"  HP/Trust: {self.state.trust}  |  Gold: {self.state.gold}  |  Pack: {len(self.state.inventory)}/{self.state.max_inventory}")
        if self.state.inventory:
            print(f"  Items: {', '.join(self.state.inventory)}")
        if self.state.companions:
            print(f"  Party: {', '.join(COMPANIONS[c]['name'] for c in self.state.companions)}")
        print("─" * 40)

        # Filter choices
        available = []
        for i, choice in enumerate(scene.get("choices", []), 1):
            if self.evaluate_condition(choice.get("condition")):
                available.append((i, choice))

        if not available:
            print("\n [ No available choices? Something went wrong. ]")
            return

        print("\nChoose:")
        for num, choice in available:
            print(f"  {num}) {choice['text']}")

        # Get input
        while True:
            try:
                raw = input("\n> ").strip()
                if raw.isdigit():
                    idx = int(raw) - 1
                    if 0 <= idx < len(available):
                        num, choice = available[idx]
                        break
                print("Pick a number from the list.")
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye.")
                sys.exit(0)

        # Execute
        self.apply_action(choice.get("action"))
        self.history.append((self.current_scene, choice["text"]))
        self.current_scene = choice["next"]

    def start(self):
        print("=" * 40)
        print(" THE HOLLOW GATE")
        print("=" * 40)
        print("\nThe King's daughter is gone. The kingdom is silent.\n")
        print("Who are you?\n")

        classes = list(CHARACTERS.keys())
        for i, cls in enumerate(classes, 1):
            info = CHARACTERS[cls]
            print(f"  {i}) {cls}")
            print(f"     {info['description']}")
            print(f"     Starts with: {', '.join(info['items'])}")
            print()

        while True:
            try:
                raw = input("Choose your origin (1 or 2): ").strip()
                if raw.isdigit():
                    idx = int(raw) - 1
                    if 0 <= idx < len(classes):
                        self.state.character_class = classes[idx]
                        cls_data = CHARACTERS[classes[idx]]
                        for item in cls_data["items"]:
                            self.state.add_item(item)
                        self.state.gold += cls_data["gold"]
                        print(f"\nYou are the {classes[idx]}.")
                        print(f"Pack: {', '.join(self.state.inventory)}")
                        if self.state.gold:
                            print(f"Gold: {self.state.gold}")
                        break
                print("Pick 1 or 2.")
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye.")
                sys.exit(0)

        self.state.chapter = 1
        self.loop()

    def loop(self):
        while True:
            self.show_scene()
            if self.current_scene.startswith("ending"):
                self.show_ending()
                break
            # Advance chapter based on scenes visited
            max_ch = max(CHAPTER_SCENES.keys())
            self.state.chapter = min(max_ch, self.state.chapter + 1)

    def show_ending(self):
        print("\n" + "=" * 40)
        print(" THE END")
        print("=" * 40 + "\n")

        if self.current_scene == "ending_fight":
            print("You won by force. The kingdom will remember your name.\n")
        elif self.current_scene == "ending_talk":
            print("You won with words. The darkness didn't stand a chance.\n")
        elif self.current_scene == "ending_clever":
            print("You won with a trick. The hollow gate closes behind you.\n")
        else:
            print("The story ends here... for now.\n")

        print(f" Trust: {self.state.trust}  |  Gold: {self.state.gold}  |  Pack: {len(self.state.inventory)} items")
        print(f" Party: {len(self.state.companions)} companion(s)")

        print("\nThanks for playing.\n")


if __name__ == "__main__":
    try:
        Engine().start()
    except Exception as e:
        print(f"\n\nSomething broke: {e}")
        sys.exit(1)
