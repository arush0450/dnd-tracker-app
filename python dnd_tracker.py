import time
from typing import List, Dict, Optional
import random
import re # Import the regular expression module for dice rolling

# --- Core Data Structures ---

class StatusEffect:
    """Represents a single status effect or a persistent note/item."""
    def __init__(self, name: str, duration: int, description: str = "A temporary condition."):
        """
        Initializes a status effect.

        Args:
            name (str): The common name of the effect (e.g., 'Poisoned', 'Concentration', 'Potion of Healing').
            duration (int): The duration in rounds. Use -1 for Permanent, 0 for Notes/Items (non-timed).
            description (str): A brief explanation of the effect's consequences or item details.
        """
        self.name: str = name
        self.duration: int = duration
        self.description: str = description
        self.rounds_remaining: int = duration if duration > 0 else duration

    def tick_down(self) -> bool:
        """
        Decrements the rounds remaining.

        Returns:
            bool: True if the effect has ended (rounds_remaining hits 0) and it was not a note.
        """
        # Only tick down if duration is positive
        if self.rounds_remaining > 0:
            self.rounds_remaining -= 1
        return self.rounds_remaining == 0 and self.duration > 0

    def __str__(self) -> str:
        """String representation for display."""
        if self.duration == 0:
            duration_str = "Notes/Items"
        elif self.duration == -1:
            duration_str = "Permanent"
        else:
            duration_str = f"{self.rounds_remaining} rounds remaining"
        
        # ANSI escape codes for coloring output in the terminal
        return f"    - \033[96m{self.name}\033[0m (\033[93m{duration_str}\033[0m). Details: {self.description}"

class Creature:
    """Represents a creature or character that can hold status effects and track HP."""
    def __init__(self, name: str, max_hp: int):
        """Initializes a creature with HP and an empty list of active effects."""
        self.name: str = name
        self.max_hp: int = max_hp
        self.current_hp: int = max_hp
        self.active_effects: List[StatusEffect] = []
        
    def change_hp(self, amount: int, is_heal: bool) -> int:
        """Applies damage or healing."""
        change = int(amount)
        
        if is_heal:
            # Healing cannot exceed Max HP
            new_hp = self.current_hp + change
            healed_amount = new_hp - self.current_hp # Actual amount healed
            self.current_hp = min(self.max_hp, new_hp)
            return healed_amount
        else:
            self.current_hp -= change
            return -change

    def apply_effect(self, effect: StatusEffect):
        """Adds a new effect to the creature. Checks for duplicates and updates them."""
        # Find index of existing effect with the same name (case-insensitive)
        existing_effect_index = next((i for i, e in enumerate(self.active_effects) if e.name.lower() == effect.name.lower()), -1)

        if existing_effect_index != -1:
            # Overwrite or refresh existing effect details
            old_effect = self.active_effects[existing_effect_index]
            old_effect.description = effect.description
            
            if effect.duration != 0: # Only update time if it's a timed effect
                old_effect.duration = effect.duration
                old_effect.rounds_remaining = effect.rounds_remaining
                print(f"  [INFO] {self.name} already has \033[96m{effect.name}\033[0m. Duration reset to {effect.duration}.")
            else:
                 print(f"  [INFO] {self.name}'s notes for \033[96m{effect.name}\033[0m updated.")
        else:
            self.active_effects.append(effect)
            if effect.duration == 0:
                msg = "(Notes/Items) added"
            elif effect.duration == -1:
                msg = "applied permanently"
            else:
                msg = f"applied for {effect.duration} rounds"
            print(f"  [SUCCESS] \033[96m{effect.name}\033[0m {msg} to {self.name}.")

    def remove_effect(self, name: str) -> bool:
        """Removes an effect by name."""
        initial_length = len(self.active_effects)
        # Filter the list, keeping only effects whose names do not match the input name
        self.active_effects = [e for e in self.active_effects if e.name.lower() != name.lower()]
        
        if len(self.active_effects) < initial_length:
            print(f"  [SUCCESS] Removed '\033[96m{name}\033[0m' from {self.name}.")
            return True
        else:
            print(f"  [ERROR] '\033[96m{name}\033[0m' not found on {self.name}.")
            return False
    
    def tick_down_effects(self) -> List[str]:
        """Ticks down all active effects and removes those that end."""
        ended_effects = []
        effects_to_keep = []

        for effect in self.active_effects:
            # Keep permanent (-1) and notes (0)
            if effect.duration <= 0 and effect.duration != 0: 
                effects_to_keep.append(effect)
                continue
            
            if effect.tick_down():
                ended_effects.append(effect.name)
            else:
                effects_to_keep.append(effect)
        
        self.active_effects = effects_to_keep
        return ended_effects


class EffectTracker:
    """Manages the status effects, HP, and round count for multiple creatures in combat."""
    def __init__(self):
        """Initializes the tracker with no creatures and round 0."""
        self.creatures: Dict[str, Creature] = {}
        self.round_count: int = 0

    def add_creature(self, name: str, max_hp: int):
        """Adds a creature to the tracker with initial HP."""
        name = name.strip()
        if name and name not in self.creatures:
            self.creatures[name] = Creature(name, max_hp)
            print(f"\n[SETUP] Creature '\033[92m{name}\033[0m' added with {max_hp} Max HP.")
        elif name:
            print(f"[SETUP] Creature '\033[92m{name}\033[0m' is already in the tracker.")
            
    def remove_creature(self, name: str):
        """Removes a creature completely from the tracker."""
        name = name.strip()
        if name in self.creatures:
            del self.creatures[name]
            print(f"\n[CLEANUP] Creature '\033[91m{name}\033[0m' removed from the encounter.")
        else:
            print(f"[ERROR] Creature '\033[91m{name}\033[0m' not found.")

    def apply_effect(self, creature_name: str, effect: StatusEffect):
        """Applies an effect to a specific creature."""
        creature = self.creatures.get(creature_name)
        if creature:
            creature.apply_effect(effect)
        else:
            print(f"[ERROR] Creature '{creature_name}' not found.")
            
    def modify_hp(self, creature_name: str, amount: int, is_heal: bool):
        """Modifies the HP of a specific creature."""
        creature = self.creatures.get(creature_name)
        if creature:
            change = creature.change_hp(amount, is_heal)
            action = "Healed" if is_heal else "Damaged"
            
            if is_heal:
                color = "\033[92m" # Green for heal
            else:
                color = "\033[91m" # Red for damage

            print(f"\n[HP] {creature.name} {action} for {color}{abs(change)}\033[0m. Current HP: {creature.current_hp} / {creature.max_hp}")
        else:
            print(f"[ERROR] Creature '{creature_name}' not found.")

    def remove_effect(self, creature_name: str, effect_name: str):
        """Removes an effect from a specific creature."""
        creature = self.creatures.get(creature_name)
        if creature:
            creature.remove_effect(effect_name)
        else:
            print(f"[ERROR] Creature '{creature_name}' not found.")


    def advance_round(self):
        """Advances the round count and ticks down all active effects."""
        self.round_count += 1
        print("\n" + "="*60)
        print(f"| ADVANCING TO ROUND \033[94m{self.round_count}\033[0m (Effects checked and timed effects tick down)")
        print("="*60)

        for creature in self.creatures.values():
            ended_effects = creature.tick_down_effects()
            if ended_effects:
                # Use bright yellow for emphasis
                print(f"[ROUND END] {creature.name}: \033[93m{', '.join(ended_effects)}\033[0m effects have worn off.")
        
        self.display_all_status()

    def display_all_status(self):
        """Prints the current round count, HP, and all active effects."""
        print(f"\n--- Current Status (Round \033[94m{self.round_count}\033[0m) ---")
        
        if not self.creatures:
            print("No creatures are currently being tracked.")
            return

        for creature in self.creatures.values():
            status = "Alive"
            hp_color = "\033[92m" # Green
            if creature.current_hp <= 0:
                status = "DEFEATED"
                hp_color = "\033[91m" # Red
            elif creature.current_hp < creature.max_hp / 2:
                status = "Bloodied"
                hp_color = "\033[93m" # Yellow

            print(f"\n* \033[1m{creature.name}\033[0m (\033[95m{status}\033[0m):")
            print(f"  HP: {hp_color}{creature.current_hp}/{creature.max_hp} HP\033[0m")
            
            if creature.active_effects:
                print("  Active Status/Items:")
                for effect in creature.active_effects:
                    print(effect)
            else:
                print("  Active Status/Items: (Clear)")
        
        print("-" * 37)

# --- Dice Roller Logic ---

def roll_dice(formula: str):
    """
    Parses a dice rolling formula (e.g., 2d6+3) and returns the result.
    Prints the rolls and details to the console.
    """
    formula = formula.strip().lower()
    # Pattern: [X]d[Y][+Z or -Z] -> (num_dice)d(die_size)(modifier)
    match = re.match(r'(\d*)d(\d+)([\+\-]\d+)?', formula)

    if not match:
        print(f"\n[DICE ERROR] Invalid format: {formula}. Use format like '1d20', '3d6+5', or '2d8-1'.")
        return

    num_dice_str, die_size_str, modifier_str = match.groups()
    
    num_dice = int(num_dice_str) if num_dice_str else 1
    die_size = int(die_size_str)
    modifier = int(modifier_str) if modifier_str else 0

    if die_size < 2 or num_dice < 1:
        print("[DICE ERROR] Invalid dice or count.")
        return

    total = 0
    rolls = []

    for _ in range(num_dice):
        roll = random.randint(1, die_size)
        total += roll
        rolls.append(roll)

    final_total = total + modifier
    
    # Display the result with colors
    roll_strings = " + ".join(map(str, rolls))
    mod_text = f" {modifier_str}" if modifier_str else ""
    
    print(f"\n--- Dice Roll: \033[94m{formula.upper()}\033[0m ---")
    print(f"Rolls: ({roll_strings}){mod_text} = \033[92m{final_total}\033[0m")
    print("-------------------------")

# --- Interactive CLI ---

def cli_interface():
    """Provides a command-line interface for the D&D Status Tracker."""
    tracker = EffectTracker()
    
    print("\n\n" + "="*50)
    print("  \033[1mD&D Combat & Status Tracker CLI\033[0m")
    print("="*50)
    print("Welcome! Use the commands below to manage combat status.")
    
    while True:
        print("\n--- Available Commands ---")
        # Added HP and RC commands
        print(" AC: Add Creature  | RC: Remove Creature | HP: Modify HP (Dmg/Heal)")
        print(" AE: Apply Effect  | RE: Remove Effect   | AR: Advance Round")
        print(" S: Status Check   | DR: Dice Roll       | Q: Quit")
        
        command = input("Enter command (AC/RC/HP/AE/RE/AR/S/DR/Q): ").strip().upper()

        if command == 'Q':
            print("\nExiting Tracker. Happy adventuring!")
            break
        
        elif command == 'AC':
            name = input("Creature name to add: ").strip()
            if not name:
                print("[ERROR] Name cannot be empty.")
                continue
            try:
                max_hp = int(input(f"Max HP for {name}: ").strip())
                if max_hp <= 0: raise ValueError
                tracker.add_creature(name, max_hp)
            except ValueError:
                print("[ERROR] Max HP must be a positive whole number.")
            
        elif command == 'RC':
            if not tracker.creatures:
                print("[ERROR] No creatures tracked yet.")
                continue
            
            print("\nAvailable Creatures: " + ", ".join(tracker.creatures.keys()))
            c_name = input("Creature name to REMOVE completely: ").strip()
            tracker.remove_creature(c_name)

        elif command == 'HP':
            if not tracker.creatures:
                print("[ERROR] No creatures tracked yet. Use 'AC' first.")
                continue

            print("\nAvailable Creatures: " + ", ".join(tracker.creatures.keys()))
            c_name = input("Target creature name: ").strip()
            
            if c_name not in tracker.creatures:
                print(f"[ERROR] Creature '{c_name}' not found.")
                continue
            
            try:
                amount = int(input("Amount of Damage/Healing: ").strip())
                if amount <= 0: raise ValueError
                action = input("Action (D for Damage, H for Heal): ").strip().upper()
                
                if action == 'D':
                    tracker.modify_hp(c_name, amount, is_heal=False)
                elif action == 'H':
                    tracker.modify_hp(c_name, amount, is_heal=True)
                else:
                    print("[ERROR] Invalid action. Please use 'D' or 'H'.")
            except ValueError:
                print("[ERROR] Amount must be a positive whole number.")

        elif command == 'AE':
            if not tracker.creatures:
                print("[ERROR] No creatures tracked yet. Use 'AC' first.")
                continue

            print("\nAvailable Creatures: " + ", ".join(tracker.creatures.keys()))
            c_name = input("Target creature name: ").strip()
            
            if c_name not in tracker.creatures:
                print(f"[ERROR] Creature '{c_name}' not found.")
                continue
                
            e_name = input("Effect/Item name: ").strip()
            if not e_name:
                print("[ERROR] Effect/Item name cannot be empty.")
                continue
            
            try:
                e_duration_input = input("Duration in rounds (-1 for Permanent, 0 for Notes/Items, or a positive number): ").strip()
                e_duration = int(e_duration_input)
            except ValueError:
                print("[ERROR] Duration must be a whole number (-1, 0, or positive).")
                continue
                
            e_desc = input("Description/Details (e.g., condition specifics, item quantity): ").strip() or "N/A"

            new_effect = StatusEffect(e_name, e_duration, e_desc)
            tracker.apply_effect(c_name, new_effect)

        elif command == 'RE':
            if not tracker.creatures:
                print("[ERROR] No creatures tracked yet.")
                continue
            
            print("\nAvailable Creatures: " + ", ".join(tracker.creatures.keys()))
            c_name = input("Target creature name to remove effect/item from: ").strip()
            
            if c_name not in tracker.creatures:
                print(f"[ERROR] Creature '{c_name}' not found.")
                continue
            
            # Show current effects for context
            print(f"\nActive status/items on {c_name}: {[e.name for e in tracker.creatures[c_name].active_effects]}")
            e_name = input("Status/Item name to remove: ").strip()
            
            tracker.remove_effect(c_name, e_name)

        elif command == 'AR':
            tracker.advance_round()

        elif command == 'S':
            tracker.display_all_status()
            
        elif command == 'DR':
            formula = input("Enter dice formula (e.g., 2d6+5): ").strip()
            if formula:
                roll_dice(formula)
            else:
                print("[ERROR] Dice formula cannot be empty.")

        else:
            print(f"[ERROR] Unknown command: {command}. Please use one of the listed commands.")


def main():
    """Starts the interactive CLI for the D&D Status Tracker."""
    # Ensure random module is seeded for fair dice rolls
    random.seed(time.time()) 
    cli_interface()

if __name__ == "__main__":
    main()
