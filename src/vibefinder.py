"""VibeFinder 2.0: a RAG + agentic pipeline on top of the VibeFinder 1.0 scorer.

Run:  python -m src.vibefinder "something to study to on a rainy night"
Flow: guardrails -> retrieve context -> build preferences FROM the retrieved docs -> score songs
      -> self-check (confidence) -> optional retry with related genres -> grounded explanation.
"""
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.guardrails import check_query, clamp
from src.recommender import load_songs, recommend_songs
from src.retriever import Retriever, load_knowledge_base

LOG = logging.getLogger("vibefinder")
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

MIN_CONFIDENCE = 0.35   # below this the system refuses and asks the human to rephrase
LOW_CONFIDENCE = 0.55   # below this the answer is flagged "low confidence"
RETRY_CONFIDENCE = 0.80  # below this the agent tries a retry with related genres
MAX_SCORE = 4.0

LOUD_WORDS = {"loud", "intense", "pumped", "energetic", "hype", "fast", "powerful", "high-energy"}
QUIET_WORDS = {"quiet", "soft", "gentle", "slow", "calm", "mellow", "softly", "low-key"}


@dataclass
class Result:
    status: str                      # "ok", "low_confidence" or "refused"
    message: str = ""
    prefs: Dict = field(default_factory=dict)
    recommendations: List[Dict] = field(default_factory=list)
    confidence: float = 0.0
    sources: List[str] = field(default_factory=list)
    trace: List[str] = field(default_factory=list)


class VibeFinder:
    def __init__(self, songs_path: Optional[str] = None, kb_path: Optional[str] = None,
                 relations_path: Optional[str] = None):
        self.songs = load_songs(songs_path or os.path.join(DATA_DIR, "songs.csv"))
        self.retriever = Retriever(load_knowledge_base(kb_path or os.path.join(DATA_DIR, "knowledge_base.json")))
        with open(relations_path or os.path.join(DATA_DIR, "genre_relations.json"), encoding="utf-8") as f:
            rel = json.load(f)
        self.related, self.aliases = rel["related"], rel["aliases"]
        self.genres = {s["genre"] for s in self.songs}
        self.moods = {s["mood"] for s in self.songs}

    # ---- step helpers -------------------------------------------------
    def _explicit(self, query: str, vocab, aliases: Optional[Dict] = None) -> Optional[str]:
        """Find a genre/mood the user literally named (longest match first)."""
        text = query.lower()
        candidates = {w: w for w in vocab}
        candidates.update(aliases or {})
        for word in sorted(candidates, key=len, reverse=True):
            if re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text):
                return candidates[word]
        return None

    def build_prefs(self, query: str, hits) -> Dict:
        """Turn retrieved docs (+ explicit words in the query) into a preference dict."""
        top_doc, top_score = hits[0]
        near = [(d, s) for d, s in hits if s >= 0.6 * top_score]
        total = sum(s for _, s in near)
        energy = sum(d["prefs"]["energy"] * s for d, s in near) / total
        words = set(re.findall(r"[a-z\-]+", query.lower()))
        if words & LOUD_WORDS:
            energy += 0.1
        if words & QUIET_WORDS:
            energy -= 0.1
        return {
            "genre": self._explicit(query, self.genres, self.aliases) or top_doc["prefs"]["genre"],
            "mood": self._explicit(query, self.moods) or top_doc["prefs"]["mood"],
            "energy": round(clamp(energy), 2),
        }

    @staticmethod
    def confidence(retrieval_score: float, top_song_score: float, explicit: bool) -> float:
        retrieval = clamp(retrieval_score * 2.5 + (0.3 if explicit else 0.0))
        return round(0.4 * retrieval + 0.6 * (top_song_score / MAX_SCORE), 2)

    # ---- main entry point ---------------------------------------------
    def recommend(self, query, k: int = 5) -> Result:
        trace: List[str] = []
        g = check_query(query)
        if not g.ok:
            LOG.warning("guardrail rejected query=%r reason=%s", query, g.reason)
            return Result("refused", g.reason, trace=[f"guardrail: REJECT ({g.reason})"])
        trace.append("guardrail: OK")
        LOG.info("query=%r", g.query)

        hits = self.retriever.search(g.query, k=3)
        if not hits:
            msg = "I could not match that to any mood, activity or genre I know. Try e.g. 'study', 'workout' or 'jazz'."
            LOG.warning("no retrieval hits for %r", g.query)
            return Result("refused", msg, trace=trace + ["retrieve: 0 documents"])
        trace.append("retrieve: " + ", ".join(f"{d['id']}({s:.2f})" for d, s in hits))

        prefs = self.build_prefs(g.query, hits)
        explicit_genre = self._explicit(g.query, self.genres, self.aliases)
        explicit = bool(explicit_genre or self._explicit(g.query, self.moods))
        trace.append(f"plan: prefs={prefs}")
        ranked = recommend_songs(prefs, self.songs, k)
        conf = self.confidence(hits[0][1], ranked[0][1], explicit)
        trace.append(f"check: top score {ranked[0][1]:.2f}/{MAX_SCORE:.0f}, confidence {conf:.2f}")

        # Agentic self-correction: if confidence is weak and the genre came from a retrieved guide
        # (not from the user's own words), try related genres and keep whichever attempt is better.
        # A genre the user named explicitly is never swapped.
        if conf < RETRY_CONFIDENCE and not explicit_genre:
            for alt in self.related.get(prefs["genre"], []):
                alt_prefs = {**prefs, "genre": alt}
                alt_ranked = recommend_songs(alt_prefs, self.songs, k)
                alt_conf = self.confidence(hits[0][1], alt_ranked[0][1], explicit)
                trace.append(f"retry: genre '{prefs['genre']}' -> '{alt}', confidence {alt_conf:.2f}")
                if alt_conf > conf:
                    prefs, ranked, conf = alt_prefs, alt_ranked, alt_conf
                    trace.append(f"retry: accepted '{alt}'")
                    break

        if conf < MIN_CONFIDENCE:
            LOG.warning("refused low confidence %.2f for %r", conf, g.query)
            return Result("refused", "I'm not confident I understood. Could you add a mood, activity or genre?",
                          prefs, [], conf, [d["id"] for d, _ in hits], trace)

        status = "ok" if conf >= LOW_CONFIDENCE else "low_confidence"
        recs = [{"title": s["title"], "artist": s["artist"], "genre": s["genre"], "mood": s["mood"],
                 "score": round(sc, 2), "why": why} for s, sc, why in ranked]
        top_doc = hits[0][0]
        message = (f"Based on the guide '{top_doc['title']}': {top_doc['text']} "
                   f"I searched for {prefs['genre']} / {prefs['mood']} music around energy {prefs['energy']}.")
        if status == "low_confidence":
            message += " (Low confidence: treat these as rough suggestions.)"
        LOG.info("status=%s confidence=%.2f prefs=%s top=%s", status, conf, prefs, recs[0]["title"])
        return Result(status, message, prefs, recs, conf, [d["id"] for d, _ in hits], trace)


def format_result(query: str, r: Result, show_trace: bool = False) -> str:
    lines = [f'Request: "{query}"', f"Status: {r.status} | confidence: {r.confidence:.2f}"]
    if r.prefs:
        lines.append(f"Preferences: {r.prefs}")
    if r.sources:
        lines.append(f"Retrieved sources: {', '.join(r.sources)}")
    lines.append(f"Answer: {r.message}")
    for i, rec in enumerate(r.recommendations, 1):
        lines.append(f"  {i}. {rec['title']} by {rec['artist']} [{rec['genre']}/{rec['mood']}] - {rec['score']:.2f}")
        lines.append(f"     Because: {rec['why']}")
    if show_trace:
        lines.append("Trace:")
        lines += [f"  - {t}" for t in r.trace]
    return "\n".join(lines)


def setup_logging() -> None:
    log_dir = os.path.join(os.path.dirname(DATA_DIR), "logs")
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(filename=os.path.join(log_dir, "vibefinder.log"), level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")


def main(argv: List[str]) -> None:
    setup_logging()
    args = [a for a in argv if a != "--trace"]
    vf = VibeFinder()
    queries = [" ".join(args)] if args else [input("What are you in the mood for? ")]
    for q in queries:
        print(format_result(q, vf.recommend(q), show_trace="--trace" in argv))


if __name__ == "__main__":
    main(sys.argv[1:])
