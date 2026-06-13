#!/usr/bin/env python3
"""
WordGen - Custom Wordlist Generator
Generates targeted wordlists from personal information for authorized security assessments.

Author: Aarush P
License: MIT
"""

import itertools
import json
import csv
import os
import sys
import time
import argparse
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Set, Optional, Dict, Callable
from pathlib import Path


# ---------------------------------------------------------------
# ANSI Colors (no dependency needed)
# ---------------------------------------------------------------

class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"

    @staticmethod
    def disable():
        for attr in dir(Colors):
            if attr.isupper() and not attr.startswith("_"):
                setattr(Colors, attr, "")

    @staticmethod
    def supports_color():
        if os.getenv("NO_COLOR"):
            return False
        if sys.platform == "win32":
            return os.getenv("ANSICON") is not None or "WT_SESSION" in os.environ
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def c(text, color):
    return f"{color}{text}{Colors.RESET}"


# ---------------------------------------------------------------
# Banner
# ---------------------------------------------------------------

BANNER = r"""
 __        __            _ ____
 \ \      / /__  _ __ __| / ___| ___ _ __
  \ \ /\ / / _ \| '__/ _` | |  _ / _ \ '_ \
   \ V  V / (_) | | | (_| | |_| |  __/ | | |
    \_/\_/ \___/|_|  \__,_|\____|\___|_| |_|
"""

VERSION = "1.0.0"


def print_banner():
    print(c(BANNER, Colors.CYAN))
    print(c(f"  Custom Wordlist Generator v{VERSION}", Colors.BOLD))
    print(c("  Targeted wordlists from personal intel\n", Colors.DIM))


# ---------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------

@dataclass
class UserProfile:
    first_name: str = ""
    last_name: str = ""
    nickname: str = ""
    dob: str = ""
    city: str = ""
    state: str = ""
    country: str = ""
    phone: str = ""
    pet_names: List[str] = field(default_factory=list)
    partner_name: str = ""
    partner_dob: str = ""
    children_names: List[str] = field(default_factory=list)
    company: str = ""
    keywords: List[str] = field(default_factory=list)
    favorite_numbers: List[str] = field(default_factory=list)
    sports_teams: List[str] = field(default_factory=list)

    def get_base_words(self):
        words = []
        for val in [
            self.first_name, self.last_name, self.nickname,
            self.city, self.state, self.country,
            self.partner_name, self.company,
        ]:
            if val.strip():
                words.append(val.strip())
        for lst in [self.pet_names, self.children_names, self.keywords, self.sports_teams]:
            words.extend([w.strip() for w in lst if w.strip()])
        return words

    def get_dates(self):
        return [d for d in [self.dob, self.partner_dob] if d.strip()]

    def get_numbers(self):
        nums = []
        phone_digits = "".join(ch for ch in self.phone if ch.isdigit())
        if phone_digits:
            nums.append(phone_digits)
            if len(phone_digits) >= 4:
                nums.append(phone_digits[-4:])
            if len(phone_digits) >= 3:
                nums.append(phone_digits[-3:])
        nums.extend([n.strip() for n in self.favorite_numbers if n.strip()])
        return nums


# ---------------------------------------------------------------
# Mutation Rules
# ---------------------------------------------------------------

LEET_MAP = {
    "a": ["@", "4"],
    "e": ["3"],
    "i": ["1", "!"],
    "o": ["0"],
    "s": ["$", "5"],
    "t": ["7"],
    "l": ["1"],
    "g": ["9"],
    "b": ["8"],
}

COMMON_SUFFIXES = [
    "0", "1", "2", "3",
    "12", "123", "1234", "12345", "123456",
    "!", "!!", "!!!", "@", "#", "$",
    "01", "02", "69", "99", "00",
    "007", "666", "777", "888",
    "abc", "qwerty",
]

COMMON_PREFIXES = [
    "the", "my", "i", "mr", "ms",
    "x", "xx", "xxx",
    "@", "@1", "@2", "#", "#1",
    "1", "12", "123",
    "!", "!1",
]

SEPARATORS = ["", "_", "-", ".", "@", "#"]

KEYBOARD_WALKS = [
    "qwerty", "qwert", "asdf", "asdfgh", "zxcv", "zxcvbn",
    "1234", "12345", "123456", "1q2w3e", "1qaz2wsx",
    "qazwsx", "!@#$%", "1q2w3e4r",
]


class MutationEngine:
    PRESETS = {
        "standard": {
            "leet_speak": True,
            "capitalization": True,
            "common_suffixes": True,
            "common_prefixes": False,
            "date_formats": True,
            "reverse": False,
            "substring": False,
            "keyboard_walks": False,
            "multi_word_join": False,
            "year_suffix": True,
            "number_padding": True,
            "double_word": False,
        },
        "aggressive": {
            "leet_speak": True,
            "capitalization": True,
            "common_suffixes": True,
            "common_prefixes": True,
            "date_formats": True,
            "reverse": True,
            "substring": True,
            "keyboard_walks": True,
            "multi_word_join": True,
            "year_suffix": True,
            "number_padding": True,
            "double_word": True,
        },
        "minimal": {
            "leet_speak": False,
            "capitalization": True,
            "common_suffixes": True,
            "common_prefixes": False,
            "date_formats": True,
            "reverse": False,
            "substring": False,
            "keyboard_walks": False,
            "multi_word_join": False,
            "year_suffix": True,
            "number_padding": False,
            "double_word": False,
        },
    }

    def __init__(self, preset="standard", custom_rules=None):
        if preset not in self.PRESETS:
            raise ValueError(f"Unknown preset: {preset}. Choose from: {list(self.PRESETS.keys())}")
        self.rules = dict(self.PRESETS[preset])
        if custom_rules:
            self.rules.update(custom_rules)
        self.stats = {}

    def _track(self, category, words):
        self.stats[category] = self.stats.get(category, 0) + len(words)
        return words

    def mutate_word(self, word):
        results = {word}
        word_lower = word.lower()

        if self.rules["capitalization"]:
            caps = {
                word_lower,
                word.upper(),
                word.capitalize(),
                word_lower[0].upper() + word_lower[1:] if len(word_lower) > 1 else word_lower.upper(),
                word.swapcase(),
            }
            if len(word_lower) > 2:
                caps.add(word_lower[0] + word_lower[1:].capitalize())
            results.update(self._track("capitalization", caps))

        if self.rules["leet_speak"]:
            leet_results = set()
            self._leet_recursive(word_lower, 0, [], leet_results, max_depth=2)
            results.update(self._track("leet_speak", leet_results))

        if self.rules["reverse"]:
            rev = {word_lower[::-1], word.capitalize()[::-1]}
            results.update(self._track("reverse", rev))

        if self.rules["substring"] and len(word_lower) > 3:
            subs = set()
            for i in range(len(word_lower)):
                for j in range(i + 3, min(i + 8, len(word_lower) + 1)):
                    subs.add(word_lower[i:j])
            results.update(self._track("substring", subs))

        if self.rules["double_word"]:
            doubles = {word_lower * 2, word.capitalize() * 2}
            results.update(self._track("double_word", doubles))

        return results

    def _leet_recursive(self, word, pos, current, results, max_depth):
        if pos == len(word):
            results.add("".join(current))
            return
        if max_depth <= 0:
            results.add("".join(current) + word[pos:])
            return
        ch = word[pos]
        current.append(ch)
        self._leet_recursive(word, pos + 1, current, results, max_depth)
        current.pop()
        if ch in LEET_MAP:
            for sub in LEET_MAP[ch]:
                current.append(sub)
                self._leet_recursive(word, pos + 1, current, results, max_depth - 1)
                current.pop()

    def generate_date_variants(self, date_str):
        results = set()
        if not date_str or "/" not in date_str:
            return results
        parts = date_str.strip().split("/")
        if len(parts) != 3:
            return results
        dd, mm, yyyy = parts
        yy = yyyy[-2:] if len(yyyy) == 4 else yyyy
        variants = [
            dd + mm + yyyy, dd + mm + yy,
            mm + dd + yyyy, mm + dd + yy,
            yyyy + mm + dd, yy + mm + dd,
            dd + mm, mm + dd,
            dd + "-" + mm, mm + "-" + dd,
            yyyy, yy, dd, mm,
        ]
        results.update(variants)
        return self._track("date_formats", results)

    def generate_year_suffixes(self, date_str):
        if not self.rules["year_suffix"] or not date_str or "/" not in date_str:
            return []
        parts = date_str.strip().split("/")
        if len(parts) != 3:
            return []
        yyyy = parts[2]
        yy = yyyy[-2:] if len(yyyy) == 4 else yyyy
        return [yyyy, yy]

    def get_suffixes(self, dates, numbers):
        suffixes = [""]
        if self.rules["common_suffixes"]:
            suffixes.extend(COMMON_SUFFIXES)
        if self.rules["year_suffix"]:
            for d in dates:
                suffixes.extend(self.generate_year_suffixes(d))
        if self.rules["number_padding"]:
            suffixes.extend(numbers)
        return list(dict.fromkeys(suffixes))

    def get_prefixes(self):
        prefixes = [""]
        if self.rules["common_prefixes"]:
            prefixes.extend(COMMON_PREFIXES)
        return prefixes


# ---------------------------------------------------------------
# Combination Generator
# ---------------------------------------------------------------

class CombinationGenerator:
    def __init__(self, profile, engine, min_length=4, max_length=32):
        self.profile = profile
        self.engine = engine
        self.min_length = min_length
        self.max_length = max_length
        self.wordlist = set()

    def _add(self, words):
        for w in words:
            if self.min_length <= len(w) <= self.max_length:
                self.wordlist.add(w)

    def generate(self):
        base_words = self.profile.get_base_words()
        dates = self.profile.get_dates()
        numbers = self.profile.get_numbers()

        suffixes = self.engine.get_suffixes(dates, numbers)
        prefixes = self.engine.get_prefixes()

        # Phase 1: Mutate each base word
        all_mutations = set()
        for word in base_words:
            all_mutations.update(self.engine.mutate_word(word))

        # Phase 2: Date variants as standalone words
        if self.engine.rules["date_formats"]:
            for d in dates:
                all_mutations.update(self.engine.generate_date_variants(d))

        # Phase 3: Keyboard walks (added directly, no suffix/prefix treatment)
        if self.engine.rules["keyboard_walks"]:
            self._add(set(KEYBOARD_WALKS))
            self.engine._track("keyboard_walks", set(KEYBOARD_WALKS))

        # Phase 4: Apply prefixes and suffixes (including combined prefix+word+suffix)
        combined = set()
        for word in all_mutations:
            for suffix in suffixes:
                combined.add(word + suffix)
                for prefix in prefixes:
                    if prefix:
                        combined.add(prefix + word + suffix)
            for prefix in prefixes:
                if prefix:
                    combined.add(prefix + word)

        self._add(combined)

        # Phase 5: Multi-word joins (pairs of base words)
        if self.engine.rules["multi_word_join"] and len(base_words) > 1:
            joined = set()
            for w1, w2 in itertools.permutations(base_words, 2):
                for sep in SEPARATORS:
                    joined.add(w1.lower() + sep + w2.lower())
                    joined.add(w1.capitalize() + sep + w2.capitalize())
                    joined.add(w1.lower() + sep + w2.lower()[::-1])
            for w in base_words:
                for n in numbers:
                    joined.add(w.lower() + n)
                    joined.add(n + w.lower())
            self._add(joined)
            self.engine._track("multi_word_join", joined)

        # Phase 6: Numbers standalone
        self._add(numbers)

        return self.wordlist


# ---------------------------------------------------------------
# Output Module
# ---------------------------------------------------------------

class OutputWriter:
    @staticmethod
    def write_txt(wordlist, filepath, sort=True):
        words = sorted(wordlist) if sort else list(wordlist)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(words) + "\n")

    @staticmethod
    def write_csv(wordlist, filepath, sort=True):
        words = sorted(wordlist) if sort else list(wordlist)
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["index", "word", "length"])
            for i, word in enumerate(words, 1):
                writer.writerow([i, word, len(word)])

    @staticmethod
    def write_json(wordlist, profile, engine, filepath, sort=True):
        words = sorted(wordlist) if sort else list(wordlist)
        data = {
            "metadata": {
                "generator": f"WordGen v{VERSION}",
                "generated_at": datetime.now().isoformat(),
                "total_words": len(words),
                "preset": next(
                    (k for k, v in engine.PRESETS.items() if v == engine.rules),
                    "custom"
                ),
                "rules": engine.rules,
                "stats": engine.stats,
                "min_length": min((len(w) for w in words), default=0),
                "max_length": max((len(w) for w in words), default=0),
                "avg_length": round(sum(len(w) for w in words) / max(len(words), 1), 1),
            },
            "profile_summary": {
                "fields_used": sum(1 for v in asdict(profile).values()
                                   if v and v != [] and v != ""),
            },
            "wordlist": words,
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def print_stats(wordlist, engine):
        total = len(wordlist)
        lengths = [len(w) for w in wordlist]
        print(f"\n{c('=' * 50, Colors.CYAN)}")
        print(c("  GENERATION STATS", Colors.BOLD))
        print(c("=" * 50, Colors.CYAN))
        print(f"  Total words:    {c(str(total), Colors.GREEN)}")
        if lengths:
            print(f"  Min length:     {c(str(min(lengths)), Colors.YELLOW)}")
            print(f"  Max length:     {c(str(max(lengths)), Colors.YELLOW)}")
            print(f"  Avg length:     {c(str(round(sum(lengths)/len(lengths), 1)), Colors.YELLOW)}")
        if engine.stats:
            print(f"\n  {c('Mutations by type:', Colors.DIM)}")
            for rule, count in sorted(engine.stats.items(), key=lambda x: -x[1]):
                bar = "#" * min(count // 5, 30)
                print(f"    {rule:<20} {c(str(count), Colors.CYAN):>8}  {c(bar, Colors.BLUE)}")
        print(c("=" * 50, Colors.CYAN))


# ---------------------------------------------------------------
# Interactive CLI
# ---------------------------------------------------------------

class InteractiveCLI:
    @staticmethod
    def ask(prompt, required=False, default=""):
        suffix = f" [{default}]" if default else ""
        marker = c("*", Colors.RED) if required else " "
        while True:
            val = input(f"  {marker} {prompt}{suffix}: ").strip()
            if not val and default:
                return default
            if not val and required:
                print(c("    This field is required.", Colors.RED))
                continue
            return val

    @staticmethod
    def ask_list(prompt):
        val = input(f"    {prompt} (comma-separated): ").strip()
        if not val:
            return []
        return [x.strip() for x in val.split(",") if x.strip()]

    @staticmethod
    def ask_choice(prompt, options, default=""):
        print(f"\n  {prompt}")
        for i, opt in enumerate(options, 1):
            marker = c("->", Colors.CYAN) if opt == default else "  "
            print(f"    {marker} [{i}] {opt}")
        while True:
            val = input(f"  Choice [{options.index(default)+1 if default else 1}]: ").strip()
            if not val and default:
                return default
            try:
                idx = int(val) - 1
                if 0 <= idx < len(options):
                    return options[idx]
            except ValueError:
                pass
            print(c("    Invalid choice.", Colors.RED))

    def collect_profile(self):
        profile = UserProfile()
        print(c("\n  +-- TARGET INFORMATION -----------------------+", Colors.BLUE))
        print(c("  | Fields marked with * are required.           |", Colors.DIM))
        print(c("  | Press Enter to skip optional fields.         |", Colors.DIM))
        print(c("  +---------------------------------------------+\n", Colors.BLUE))

        print(c("  [Personal]", Colors.MAGENTA))
        profile.first_name = self.ask("First name", required=True)
        profile.last_name = self.ask("Last name")
        profile.nickname = self.ask("Nickname / username")
        profile.dob = self.ask("Date of birth (DD/MM/YYYY)")
        profile.phone = self.ask("Phone number")

        print(c("\n  [Location]", Colors.MAGENTA))
        profile.city = self.ask("City")
        profile.state = self.ask("State / Province")
        profile.country = self.ask("Country")

        print(c("\n  [Relationships]", Colors.MAGENTA))
        profile.partner_name = self.ask("Partner's name")
        profile.partner_dob = self.ask("Partner's DOB (DD/MM/YYYY)")
        profile.children_names = self.ask_list("Children's names")
        profile.pet_names = self.ask_list("Pet names")

        print(c("\n  [Work & Interests]", Colors.MAGENTA))
        profile.company = self.ask("Company / organization")
        profile.sports_teams = self.ask_list("Favorite sports teams")
        profile.favorite_numbers = self.ask_list("Favorite / lucky numbers")
        profile.keywords = self.ask_list("Custom keywords (anything else relevant)")

        return profile

    def collect_config(self):
        print(c("\n  +-- GENERATION CONFIG ------------------------+", Colors.BLUE))
        print(c("  +---------------------------------------------+\n", Colors.BLUE))

        preset = self.ask_choice(
            "Mutation preset:",
            ["minimal", "standard", "aggressive", "custom"],
            default="standard"
        )

        custom_rules = None
        if preset == "custom":
            print(c("\n  Toggle rules (y/n):", Colors.DIM))
            custom_rules = {}
            for rule in MutationEngine.PRESETS["aggressive"]:
                val = input(f"    {rule}? [y/n]: ").strip().lower()
                custom_rules[rule] = val in ("y", "yes", "1", "true", "")
            preset = "standard"

        min_len = self.ask("Min word length", default="4")
        max_len = self.ask("Max word length", default="32")
        output_name = self.ask("Output filename (without extension)", default="wordlist")
        formats = self.ask_choice(
            "Output format:",
            ["txt", "csv", "json", "all"],
            default="all"
        )

        return {
            "preset": preset,
            "custom_rules": custom_rules,
            "min_length": int(min_len),
            "max_length": int(max_len),
            "output_name": output_name,
            "formats": formats,
        }


def run_interactive():
    if not Colors.supports_color():
        Colors.disable()

    print_banner()
    cli = InteractiveCLI()
    profile = cli.collect_profile()
    config = cli.collect_config()

    engine = MutationEngine(
        preset=config["preset"],
        custom_rules=config["custom_rules"]
    )

    print(c("\n  [*] Generating wordlist...", Colors.YELLOW))
    start = time.time()

    generator = CombinationGenerator(
        profile=profile, engine=engine,
        min_length=config["min_length"], max_length=config["max_length"],
    )
    wordlist = generator.generate()
    elapsed = time.time() - start

    print(c(f"  [+] Generated {len(wordlist)} words in {elapsed:.2f}s", Colors.GREEN))

    output_base = config["output_name"]
    formats = config["formats"]
    written_files = []

    if formats in ("txt", "all"):
        path = f"{output_base}.txt"
        OutputWriter.write_txt(wordlist, path)
        written_files.append(path)
    if formats in ("csv", "all"):
        path = f"{output_base}.csv"
        OutputWriter.write_csv(wordlist, path)
        written_files.append(path)
    if formats in ("json", "all"):
        path = f"{output_base}.json"
        OutputWriter.write_json(wordlist, profile, engine, path)
        written_files.append(path)

    OutputWriter.print_stats(wordlist, engine)

    print(c("\n  Files written:", Colors.GREEN))
    for fpath in written_files:
        size = os.path.getsize(fpath)
        size_str = f"{size/1024:.1f} KB" if size > 1024 else f"{size} B"
        print(f"    -> {c(fpath, Colors.CYAN)} ({size_str})")
    print(c(f"\n  Done. Use responsibly.\n", Colors.DIM))


def run_cli_args():
    parser = argparse.ArgumentParser(
        description="WordGen - Custom Wordlist Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python wordgen.py                          # Interactive mode
  python wordgen.py --name John Doe --dob 15/03/1990 --city NewYork
  python wordgen.py --name Jane --preset aggressive --format all
        """
    )
    parser.add_argument("--name", nargs="+", help="First and last name")
    parser.add_argument("--nickname", help="Nickname or username")
    parser.add_argument("--dob", help="Date of birth (DD/MM/YYYY)")
    parser.add_argument("--city", help="City")
    parser.add_argument("--state", help="State or province")
    parser.add_argument("--country", help="Country")
    parser.add_argument("--phone", help="Phone number")
    parser.add_argument("--partner", help="Partner's name")
    parser.add_argument("--partner-dob", help="Partner's DOB (DD/MM/YYYY)")
    parser.add_argument("--pets", nargs="+", help="Pet names")
    parser.add_argument("--children", nargs="+", help="Children's names")
    parser.add_argument("--company", help="Company name")
    parser.add_argument("--teams", nargs="+", help="Sports teams")
    parser.add_argument("--numbers", nargs="+", help="Favorite numbers")
    parser.add_argument("--keywords", nargs="+", help="Custom keywords")
    parser.add_argument("--preset", choices=["minimal", "standard", "aggressive"],
                        default="standard", help="Mutation preset (default: standard)")
    parser.add_argument("--min-length", type=int, default=4, help="Min word length (default: 4)")
    parser.add_argument("--max-length", type=int, default=32, help="Max word length (default: 32)")
    parser.add_argument("--output", "-o", default="wordlist", help="Output filename base")
    parser.add_argument("--format", "-f", choices=["txt", "csv", "json", "all"],
                        default="all", help="Output format (default: all)")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output")
    parser.add_argument("--quiet", "-q", action="store_true", help="Minimal output")

    args = parser.parse_args()

    if args.no_color:
        Colors.disable()

    if not args.name:
        return None

    if not args.quiet:
        print_banner()

    profile = UserProfile()
    if args.name:
        profile.first_name = args.name[0]
        if len(args.name) > 1:
            profile.last_name = " ".join(args.name[1:])
    profile.nickname = args.nickname or ""
    profile.dob = args.dob or ""
    profile.city = args.city or ""
    profile.state = args.state or ""
    profile.country = args.country or ""
    profile.phone = args.phone or ""
    profile.partner_name = args.partner or ""
    profile.partner_dob = args.partner_dob or ""
    profile.pet_names = args.pets or []
    profile.children_names = args.children or []
    profile.company = args.company or ""
    profile.sports_teams = args.teams or []
    profile.favorite_numbers = args.numbers or []
    profile.keywords = args.keywords or []

    engine = MutationEngine(preset=args.preset)

    if not args.quiet:
        print(c("  [*] Generating wordlist...", Colors.YELLOW))
    start = time.time()

    generator = CombinationGenerator(
        profile=profile, engine=engine,
        min_length=args.min_length, max_length=args.max_length,
    )
    wordlist = generator.generate()
    elapsed = time.time() - start

    if not args.quiet:
        print(c(f"  [+] Generated {len(wordlist)} words in {elapsed:.2f}s", Colors.GREEN))

    written_files = []
    fmt = args.format

    if fmt in ("txt", "all"):
        path = f"{args.output}.txt"
        OutputWriter.write_txt(wordlist, path)
        written_files.append(path)
    if fmt in ("csv", "all"):
        path = f"{args.output}.csv"
        OutputWriter.write_csv(wordlist, path)
        written_files.append(path)
    if fmt in ("json", "all"):
        path = f"{args.output}.json"
        OutputWriter.write_json(wordlist, profile, engine, path)
        written_files.append(path)

    if not args.quiet:
        OutputWriter.print_stats(wordlist, engine)
        print(c("\n  Files written:", Colors.GREEN))
        for fpath in written_files:
            size = os.path.getsize(fpath)
            size_str = f"{size/1024:.1f} KB" if size > 1024 else f"{size} B"
            print(f"    -> {c(fpath, Colors.CYAN)} ({size_str})")
        print()
    else:
        for fpath in written_files:
            print(fpath)

    return True


def main():
    if len(sys.argv) > 1:
        result = run_cli_args()
        if result is not None:
            return
    run_interactive()


if __name__ == "__main__":
    main()
