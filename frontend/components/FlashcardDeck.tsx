"use client";

import { useState } from "react";

type Card = { front: string; back: string };

const btn = "rounded-sm border border-line px-4 py-2 text-sm font-medium text-ink-700 hover:bg-ink-50 disabled:opacity-40";

export function FlashcardDeck({ cards }: { cards: Card[] }) {
  const [i, setI] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [known, setKnown] = useState<Set<number>>(new Set());

  if (!cards.length) {
    return <p className="py-8 text-center text-muted">No flashcards for this sub-topic yet.</p>;
  }
  const card = cards[i];
  const go = (d: number) => {
    setI((v) => Math.min(cards.length - 1, Math.max(0, v + d)));
    setFlipped(false);
  };
  const mark = (ok: boolean) => {
    setKnown((prev) => {
      const next = new Set(prev);
      if (ok) next.add(i); else next.delete(i);
      return next;
    });
    if (i < cards.length - 1) go(1);
  };

  return (
    <div>
      <div className="mb-2.5 flex justify-between text-sm text-muted">
        <span>Card {i + 1} of {cards.length}</span>
        <span>{known.size} marked “got it”</span>
      </div>
      <button
        type="button"
        onClick={() => setFlipped(!flipped)}
        aria-label={flipped ? "Show prompt" : "Reveal answer"}
        className={`flash ${flipped ? "flipped" : ""}`}
      >
        <span className="inner">
          <span className="face front"><span className="tag">Prompt</span>{card.front}</span>
          <span className="face back"><span className="tag">Answer</span>{card.back}</span>
        </span>
      </button>
      <p className="mt-2 text-center text-xs text-faint">Click the card to flip it.</p>
      <div className="mt-4 flex items-center justify-between">
        <button type="button" className={btn} disabled={i === 0} onClick={() => go(-1)}>Previous</button>
        <div className="flex gap-2">
          <button type="button" className={btn} onClick={() => mark(false)}>Review again</button>
          <button type="button" onClick={() => mark(true)} className="rounded-sm bg-ink-900 px-4 py-2 text-sm font-medium text-white hover:bg-ink-700">Got it</button>
        </div>
        <button type="button" className={btn} disabled={i === cards.length - 1} onClick={() => go(1)}>Next</button>
      </div>
    </div>
  );
}
