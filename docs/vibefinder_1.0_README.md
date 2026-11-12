# 🎵 Music Recommender Simulation

## Project Summary

VibeFinder 1.0 is a small, CLI-first, content-based music recommender. It loads a 20-song catalog, scores every song against a user's taste profile (genre, mood, target energy), and prints the top 5 with a plain-language reason for each score.

---

## How The System Works

**Real-world systems.** Platforms like Spotify and YouTube mix two ideas. *Collaborative filtering* uses other people's behavior (likes, skips, playlists, replays): "people like you loved this." *Content-based filtering* uses song attributes (genre, tempo, energy, mood) to find songs similar to what you already like. Collaborative filtering needs lots of users; content-based works with just a catalog. My version is purely content-based, so it prioritizes **how well a song's attributes match one user's stated taste**.

**Features.**
- `Song`: id, title, artist, genre, mood, energy, tempo_bpm, valence, danceability, acousticness. Scoring uses genre, mood and energy; the OOP `Recommender` also uses acousticness.
- `UserProfile`: favorite_genre, favorite_mood, target_energy, likes_acoustic. The functional API uses a dict: `{"genre", "mood", "energy"}`.

**Algorithm recipe (score for one song):**
- +2.0 for a genre match
- +1.0 for a mood match
- up to +1.0 for energy closeness: `1 - |song.energy - target|` (rewards closeness, not high or low values)
- Max score is 4.0.

**Scoring rule vs. ranking rule.** The scoring rule judges one song alone. The ranking rule applies it to every song and sorts, so the best songs are the ones with the highest scores. You need both: a score alone is just a number, and a sort alone has nothing to sort by.

**Data flow:** user prefs -> loop over every row in `songs.csv` -> `score_song` -> sort by score -> top K with reasons.

**Expected biases.** Genre is worth twice a mood match, so the system may over-prioritize genre and hide great songs from another genre that match the vibe. Exact-string matching means "pop" and "indie pop" are treated as unrelated.

---

## Getting Started

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m src.main
pytest
```

---

## Sample Recommendation Output

```
Loaded songs: 20

=== Default Pop/Happy: {'genre': 'pop', 'mood': 'happy', 'energy': 0.8} ===
1. Sunrise City by Neon Echo [pop/happy] - 3.98
   Because: genre match (+2.0); mood match (+1.0); energy 0.82 vs target 0.80 (+0.98)
2. Gym Hero by Max Pulse [pop/intense] - 2.87
   Because: genre match (+2.0); energy 0.93 vs target 0.80 (+0.87)
3. Rooftop Lights by Indigo Parade [indie pop/happy] - 1.96
   Because: mood match (+1.0); energy 0.76 vs target 0.80 (+0.96)
4. Concrete Crown by Kid Atlas [hip hop/confident] - 0.98
   Because: energy 0.78 vs target 0.80 (+0.98)
5. Night Drive Loop by Neon Echo [synthwave/moody] - 0.95
   Because: energy 0.75 vs target 0.80 (+0.95)

=== High-Energy Pop: {'genre': 'pop', 'mood': 'euphoric', 'energy': 0.9} ===
1. Gym Hero by Max Pulse [pop/intense] - 2.97
   Because: genre match (+2.0); energy 0.93 vs target 0.90 (+0.97)
2. Sunrise City by Neon Echo [pop/happy] - 2.92
   Because: genre match (+2.0); energy 0.82 vs target 0.90 (+0.92)
3. Solar Flare by Pulse Theory [edm/euphoric] - 2.00
   Because: mood match (+1.0); energy 0.90 vs target 0.90 (+1.00)
4. Midnight Ritual by Vanta [edm/euphoric] - 1.96
   Because: mood match (+1.0); energy 0.94 vs target 0.90 (+0.96)
5. Storm Runner by Voltline [rock/intense] - 0.99
   Because: energy 0.91 vs target 0.90 (+0.99)

=== Chill Lofi: {'genre': 'lofi', 'mood': 'chill', 'energy': 0.35} ===
1. Library Rain by Paper Lanterns [lofi/chill] - 4.00
   Because: genre match (+2.0); mood match (+1.0); energy 0.35 vs target 0.35 (+1.00)
2. Midnight Coding by LoRoom [lofi/chill] - 3.93
   Because: genre match (+2.0); mood match (+1.0); energy 0.42 vs target 0.35 (+0.93)
3. Focus Flow by LoRoom [lofi/focused] - 2.95
   Because: genre match (+2.0); energy 0.40 vs target 0.35 (+0.95)
4. Spacewalk Thoughts by Orbit Bloom [ambient/chill] - 1.93
   Because: mood match (+1.0); energy 0.28 vs target 0.35 (+0.93)
5. Coffee Shop Stories by Slow Stereo [jazz/relaxed] - 0.98
   Because: energy 0.37 vs target 0.35 (+0.98)

=== Deep Intense Rock: {'genre': 'rock', 'mood': 'intense', 'energy': 0.92} ===
1. Storm Runner by Voltline [rock/intense] - 3.99
   Because: genre match (+2.0); mood match (+1.0); energy 0.91 vs target 0.92 (+0.99)
2. Gym Hero by Max Pulse [pop/intense] - 1.99
   Because: mood match (+1.0); energy 0.93 vs target 0.92 (+0.99)
3. Midnight Ritual by Vanta [edm/euphoric] - 0.98
   Because: energy 0.94 vs target 0.92 (+0.98)
4. Solar Flare by Pulse Theory [edm/euphoric] - 0.98
   Because: energy 0.90 vs target 0.92 (+0.98)
5. Iron Cathedral by Black Meridian [metal/aggressive] - 0.95
   Because: energy 0.97 vs target 0.92 (+0.95)

=== Conflict: sad but energy 0.9: {'genre': 'blues', 'mood': 'sad', 'energy': 0.9} ===
1. Blue Smoke by Ray Calloway [blues/sad] - 3.50
   Because: genre match (+2.0); mood match (+1.0); energy 0.40 vs target 0.90 (+0.50)
2. Solar Flare by Pulse Theory [edm/euphoric] - 1.00
   Because: energy 0.90 vs target 0.90 (+1.00)
3. Storm Runner by Voltline [rock/intense] - 0.99
   Because: energy 0.91 vs target 0.90 (+0.99)
4. Gym Hero by Max Pulse [pop/intense] - 0.97
   Because: energy 0.93 vs target 0.90 (+0.97)
5. Midnight Ritual by Vanta [edm/euphoric] - 0.96
   Because: energy 0.94 vs target 0.90 (+0.96)

=== Unknown genre (k-pop): {'genre': 'k-pop', 'mood': 'happy', 'energy': 0.7} ===
1. Rooftop Lights by Indigo Parade [indie pop/happy] - 1.94
   Because: mood match (+1.0); energy 0.76 vs target 0.70 (+0.94)
2. Sunrise City by Neon Echo [pop/happy] - 1.88
   Because: mood match (+1.0); energy 0.82 vs target 0.70 (+0.88)
3. Night Drive Loop by Neon Echo [synthwave/moody] - 0.95
   Because: energy 0.75 vs target 0.70 (+0.95)
4. Concrete Crown by Kid Atlas [hip hop/confident] - 0.92
   Because: energy 0.78 vs target 0.70 (+0.92)
5. Island Breeze by Coral Sun [reggae/relaxed] - 0.88
   Because: energy 0.58 vs target 0.70 (+0.88)
```

---

## Experiments You Tried

**Weight shift (energy x2, genre x0.5)**, run with `weights={"genre": 1.0, "mood": 1.0, "energy": 2.0}`. The max score stays 1.0 + 1.0 + 2.0 = 4.0, so the math is still valid.

```
##### EXPERIMENT: energy x2, genre x0.5 #####

=== Default Pop/Happy: {'genre': 'pop', 'mood': 'happy', 'energy': 0.8} ===
1. Sunrise City by Neon Echo [pop/happy] - 3.96
   Because: genre match (+1.0); mood match (+1.0); energy 0.82 vs target 0.80 (+1.96)
2. Rooftop Lights by Indigo Parade [indie pop/happy] - 2.92
   Because: mood match (+1.0); energy 0.76 vs target 0.80 (+1.92)
3. Gym Hero by Max Pulse [pop/intense] - 2.74
   Because: genre match (+1.0); energy 0.93 vs target 0.80 (+1.74)
4. Concrete Crown by Kid Atlas [hip hop/confident] - 1.96
   Because: energy 0.78 vs target 0.80 (+1.96)
5. Night Drive Loop by Neon Echo [synthwave/moody] - 1.90
   Because: energy 0.75 vs target 0.80 (+1.90)

=== Conflict: sad but energy 0.9: {'genre': 'blues', 'mood': 'sad', 'energy': 0.9} ===
1. Blue Smoke by Ray Calloway [blues/sad] - 3.00
   Because: genre match (+1.0); mood match (+1.0); energy 0.40 vs target 0.90 (+1.00)
2. Solar Flare by Pulse Theory [edm/euphoric] - 2.00
   Because: energy 0.90 vs target 0.90 (+2.00)
3. Storm Runner by Voltline [rock/intense] - 1.98
   Because: energy 0.91 vs target 0.90 (+1.98)
4. Gym Hero by Max Pulse [pop/intense] - 1.94
   Because: energy 0.93 vs target 0.90 (+1.94)
5. Midnight Ritual by Vanta [edm/euphoric] - 1.92
   Because: energy 0.94 vs target 0.90 (+1.92)
```

Result: for Pop/Happy, "Gym Hero" (pop, intense) fell from #2 to #3 and "Rooftop Lights" (indie pop, happy) rose to #2. That feels more accurate for a "happy" listener. For the sad-but-energetic profile, energy-matched songs scored much closer to the blues song. The change made results different, and mostly better, but 20 songs is too few to be sure.

---

## Limitations and Risks

- Tiny catalog (20 songs); most genres have exactly one song, so genre match decides a lot.
- Exact-string matching: "indie pop" gets no credit for a "pop" fan.
- Ignores lyrics, language, artist, tempo, valence, and listening history.
- Contradictory tastes (sad + 0.9 energy) are handled by adding points; the blues song wins at #1 even though its energy is far off.
- An unknown genre (k-pop) silently loses the 2.0 genre points, so results become mood/energy only.

---

## Reflection

See the [Model Card](model_card.md) for the full reflection.

A recommender is just "score each item, then sort," and small weight choices decide who sees what. Three added numbers already *feel* like a recommendation, especially with reasons attached. Bias shows up when data is thin or one feature is weighted too heavily, which creates a narrow filter bubble for some users.
