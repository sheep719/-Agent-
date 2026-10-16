export interface Experience {
  company: string;
  role: string;
  bullets: string[];
}

export interface ResumeStructured {
  education: string[];
  experience: Experience[];
  skills: string[];
  projects: string[];
}

export type ReqCategory = "hard_skill" | "project" | "education" | "bonus";
export type ReqStatus = "hit" | "partial" | "miss";

export interface JDRequirement {
  category: ReqCategory;
  requirement: string;
  status: ReqStatus;
  evidence: string;
  score: number;
}

export interface MatchResult {
  requirements: JDRequirement[];
  dimension_scores: Record<string, number>;
  total_score: number;
}

export interface RewriteSuggestion {
  original: string;
  rewritten: string;
  reason: string;
  for_requirement: string;
  was_status: ReqStatus;
}

export type AgentName = "parser" | "matcher" | "rewriter";

export interface ProgressState {
  parser: "idle" | "running" | "done";
  matcher: "idle" | "running" | "done";
  rewriter: "idle" | "running" | "done";
}

export interface TraceEntry {
  node: string;
  ms: number;
  stub?: boolean;
  skipped_precomputed?: boolean;
}
