const MAX_BODY_CHARS = 2_048;
const SENSITIVE_KEY_RE = /token|secret|password|api[_-]?key|authorization/i;
const SENSITIVE_ASSIGNMENT_RE =
  /\b(token|secret|password|api[_-]?key|authorization)\b\s*[:=]\s*\S+/gi;
const PATH_PATTERNS = [
  { re: /^\/workspace\/\S*/gm, reason: "contains /workspace path" },
  { re: /^\/Users\/\S*/gm, reason: "contains /Users path" },
  { re: /\.pnpm\/\S*/g, reason: "contains .pnpm path" },
];
const SHA_RE = /\b[0-9a-f]{40}\b/gi;
const LOG_PREFIX_RE = /^\s*@?[\w.-]+\/[\w.-]+:[\w.-]+:/;

export function redactBody(text: string): { text: string; reasons: string[] } {
  const reasons = new Set<string>();
  let redacted = text;

  if (text.length > MAX_BODY_CHARS) {
    reasons.add(`exceeds ${MAX_BODY_CHARS} character limit`);
  }

  redacted = redactSensitiveAssignments(redacted, reasons);
  redacted = redactPaths(redacted, reasons);
  redacted = redactShasOutsideBackticks(redacted, reasons);

  if (logPrefixLines(text) >= 5) {
    reasons.add("looks like a log dump");
  }

  return { text: redacted, reasons: [...reasons] };
}

/** Refuse Slack-bound text the same way comment bodies are gated. */
export function assertSafeSlackText(
  body: string,
  label = "body",
  opts: { enforceMaxChars?: boolean } = {}
): string {
  const enforceMax = opts.enforceMaxChars !== false;
  const result = redactBody(body);
  const reasons = enforceMax
    ? result.reasons
    : result.reasons.filter(r => !r.startsWith("exceeds "));
  if (reasons.length === 0) return result.text;
  throw new Error(`${label} refused: ${reasons.join("; ")}`);
}

/**
 * Scan file bytes before Slack upload. UTF-8 text is checked in full (no
 * length cutoff — the original buffer is what Slack receives). Binary
 * payloads get a second latin1 pass so ASCII secret assignments still
 * surface when UTF-8 decoding would replace invalid sequences.
 */
export function assertSafeSlackFileContent(
  content: Buffer,
  label = "file upload"
): void {
  const asUtf8 = content.toString("utf8");
  assertSafeSlackText(asUtf8, label, { enforceMaxChars: false });
  const asLatin1 = content.toString("latin1");
  if (asLatin1 !== asUtf8) {
    assertSafeSlackText(asLatin1, label, { enforceMaxChars: false });
  }
}

function redactSensitiveAssignments(
  text: string,
  reasons: Set<string>
): string {
  return text.replace(SENSITIVE_ASSIGNMENT_RE, match => {
    const [key] = match.split(/\s*[:=]\s*/, 1);
    if (SENSITIVE_KEY_RE.test(key ?? "")) {
      reasons.add("contains sensitive key");
      return `${key}=[redacted]`;
    }
    return match;
  });
}

function redactPaths(text: string, reasons: Set<string>): string {
  let out = text;
  for (const { re, reason } of PATH_PATTERNS) {
    out = out.replace(re, () => {
      reasons.add(reason);
      return "[redacted-path]";
    });
  }
  return out;
}

function redactShasOutsideBackticks(
  text: string,
  reasons: Set<string>
): string {
  return text
    .split("`")
    .map((part, index) => {
      if (index % 2 === 1) return part;
      return part.replace(SHA_RE, () => {
        reasons.add("contains bare 40-char SHA");
        return "[redacted-sha]";
      });
    })
    .join("`");
}

function logPrefixLines(text: string): number {
  return text.split(/\r?\n/).filter(line => LOG_PREFIX_RE.test(line)).length;
}
