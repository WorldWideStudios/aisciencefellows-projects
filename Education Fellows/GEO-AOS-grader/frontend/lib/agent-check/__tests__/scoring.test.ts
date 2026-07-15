import { describe, it, expect } from "vitest"
import { getGrade } from "../scoring"

describe("getGrade", () => {
  it("returns Not Agent Ready for 0", () => {
    expect(getGrade(0)).toEqual({ grade: "Not Agent Ready", gradeColor: "#ef4444" })
  })
  it("returns Not Agent Ready for 25", () => {
    expect(getGrade(25).grade).toBe("Not Agent Ready")
  })
  it("returns Early Stage for 26", () => {
    expect(getGrade(26).grade).toBe("Early Stage")
  })
  it("returns Early Stage for 50", () => {
    expect(getGrade(50).grade).toBe("Early Stage")
  })
  it("returns Agent Friendly for 51", () => {
    expect(getGrade(51).grade).toBe("Agent Friendly")
  })
  it("returns Agent Friendly for 75", () => {
    expect(getGrade(75).grade).toBe("Agent Friendly")
  })
  it("returns Agent Ready for 76", () => {
    expect(getGrade(76).grade).toBe("Agent Ready")
  })
  it("returns Agent Ready for 90", () => {
    expect(getGrade(90).grade).toBe("Agent Ready")
  })
  it("returns Agent Native for 91", () => {
    expect(getGrade(91).grade).toBe("Agent Native")
  })
  it("returns Agent Native for 100", () => {
    expect(getGrade(100)).toEqual({ grade: "Agent Native", gradeColor: "#3b82f6" })
  })
})
