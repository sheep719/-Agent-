export const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

/** 手写 SSE 客户端：fetch POST + ReadableStream（EventSource 不支持 POST） */
export async function streamSSE(
  url: string,
  body: FormData,
  onEvent: (event: string, data: any) => void,
): Promise<void> {
  const resp = await fetch(url, { method: "POST", body });
  if (!resp.ok || !resp.body) {
    let detail = `HTTP ${resp.status}`;
    try {
      const j = await resp.json();
      detail = j.detail || detail;
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const blocks = buf.split("\n\n");
    buf = blocks.pop() || "";
    for (const block of blocks) {
      const ev = block.match(/^event: (.+)$/m)?.[1];
      const raw = block.match(/^data: (.+)$/m)?.[1];
      if (ev && raw) {
        try {
          onEvent(ev, JSON.parse(raw));
        } catch {
          /* 忽略坏块 */
        }
      }
    }
  }
}
