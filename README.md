# WordGen

Targeted wordlist generator for authorized penetration testing. Takes personal intel (name, DOB, location, keywords) and produces high-quality credential-guessing wordlists with configurable mutation depth.

```
 __        __            _ ____
 \ \      / /__  _ __ __| / ___| ___ _ __
  \ \ /\ / / _ \| '__/ _` | |  _ / _ \ '_ \
   \ V  V / (_) | | | (_| | |_| |  __/ | | |
    \_/\_/ \___/|_|  \__,_|\____|\___|_| |_|
```

Pure Python. Zero dependencies. Runs anywhere Python 3.6+ does — laptops, Raspberry Pi, Pwnagotchi, any DIY rig.

---

## Usage

### Interactive
```bash
python wordgen.py
```
Walks you through every input field, then asks for preset and output preferences.

### CLI (scriptable)
```bash
python wordgen.py --name John Doe --dob 15/03/1990 --city Mumbai \
  --keywords hacker wifi --preset aggressive --format all -o target
```

### Quiet mode (pipe-friendly)
```bash
python wordgen.py --name Jane --preset standard -o out -q
# prints only the output file paths
```

---

## What it generates

Given a name like `Aarushna` and a keyword like `Airtel`, the aggressive preset produces patterns like:

```
@1Aarushna0       ← symbol + number + name + suffix
Airtel_Aarushna   ← keyword + separator + name
a@rushna123       ← leet substitution + suffix
AARUSHNA!         ← caps + symbol
anhusr44          ← reversed + leet
```

53,000+ candidates from just two inputs. With full profile data (DOB, phone, pets, partner, etc.), coverage scales accordingly.

---

## Mutation presets

| Rule | Minimal | Standard | Aggressive |
|------|:-------:|:--------:|:----------:|
| Capitalization variants | + | + | + |
| Common suffixes (123, !, @) | + | + | + |
| Date format permutations | + | + | + |
| Year as suffix | + | + | + |
| Leet speak (a->@, e->3) | | + | + |
| Number padding | | + | + |
| Symbol + number prefixes | | | + |
| Reversed strings | | | + |
| Substring extraction | | | + |
| Keyboard walks | | | + |
| Multi-word joins | | | + |
| Double word | | | + |

Choose `custom` in interactive mode to toggle individual rules.

---

## Output formats

**txt** — one word per line, compatible with Hydra, Hashcat, John the Ripper, Aircrack-ng.

**csv** — indexed with length column, useful for filtering and analysis.

**json** — full metadata: generation timestamp, preset used, mutation stats, word count breakdown.

---

## CLI reference

```
--name NAME [NAME ...]     First and last name (required for CLI mode)
--nickname NICK            Nickname or username
--dob DD/MM/YYYY           Date of birth
--city CITY                City
--state STATE              State / province
--country COUNTRY          Country
--phone PHONE              Phone number
--partner NAME             Partner's name
--partner-dob DD/MM/YYYY   Partner's DOB
--pets NAME [NAME ...]     Pet names
--children NAME [...]      Children's names
--company NAME             Company / organization
--teams NAME [NAME ...]    Sports teams
--numbers NUM [NUM ...]    Favorite / lucky numbers
--keywords WORD [...]      Custom keywords
--preset PRESET            minimal | standard | aggressive
--min-length N             Min word length (default: 4)
--max-length N             Max word length (default: 32)
-o, --output FILE          Output filename base (default: wordlist)
-f, --format FMT           txt | csv | json | all (default: all)
-q, --quiet                Suppress banner and stats
--no-color                 Disable ANSI colors
```

---

## Disclaimer

For authorized security testing only. Unauthorized use against systems you do not own or have explicit permission to test is illegal.

---

**Proprietary software. All rights reserved.**
