import { describe, it, expect } from "vitest";
import { chunkBySentence } from "./speech";

describe("chunkBySentence", () => {
  it("returns an empty array for empty input", () => {
    expect(chunkBySentence("")).toEqual([]);
  });

  it("returns a single chunk for a single sentence", () => {
    expect(chunkBySentence("Hello world.")).toEqual(["Hello world."]);
  });

  it("splits on period, question mark, and exclamation point", () => {
    expect(chunkBySentence("Hi! How are you? I am fine.")).toEqual([
      "Hi!",
      "How are you?",
      "I am fine.",
    ]);
  });

  it("treats consecutive terminators as part of the same sentence", () => {
    expect(chunkBySentence("What?? Really!!!")).toEqual(["What??", "Really!!!"]);
  });

  it("captures trailing fragments without a terminator", () => {
    expect(chunkBySentence("First sentence. Trailing fragment")).toEqual([
      "First sentence.",
      "Trailing fragment",
    ]);
  });

  it("returns a single chunk when there is no terminator at all", () => {
    expect(chunkBySentence("no terminator here")).toEqual(["no terminator here"]);
  });

  it("strips surrounding whitespace from each chunk", () => {
    expect(chunkBySentence("  One.   Two.   ")).toEqual(["One.", "Two."]);
  });

  it("keeps trailing quote characters with the sentence they end", () => {
    expect(chunkBySentence('He said "Hi." and left.')).toEqual([
      'He said "Hi."',
      "and left.",
    ]);
  });
});
