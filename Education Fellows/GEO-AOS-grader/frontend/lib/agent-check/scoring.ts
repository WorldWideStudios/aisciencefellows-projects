interface GradeInfo {
  grade: string
  gradeColor: string
}

export function getGrade(score: number): GradeInfo {
  if (score >= 91) return { grade: "Agent Native",    gradeColor: "#3b82f6" }
  if (score >= 76) return { grade: "Agent Ready",     gradeColor: "#22c55e" }
  if (score >= 51) return { grade: "Agent Friendly",  gradeColor: "#eab308" }
  if (score >= 26) return { grade: "Early Stage",     gradeColor: "#f97316" }
  return           { grade: "Not Agent Ready",        gradeColor: "#ef4444" }
}
