import { act, renderHook, waitFor } from "@testing-library/react";
import { makeIndex, makeRun } from "../test/fixtures";
import { loadIndex, loadRun } from "./load";
import { DataError } from "./validate";
import { useRun } from "./useRun";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

test("loadIndex parses and returns the index", async () => {
  const index = await loadIndex(async () => jsonResponse(makeIndex()));
  expect(index.runs).toHaveLength(2);
});

test("loadRun 404 throws DataError", async () => {
  await expect(loadRun("demo-sma_cross", async () => new Response("nope", { status: 404 }))).rejects.toThrow(DataError);
});

test("loadRun with a non-JSON body throws DataError", async () => {
  await expect(loadRun("demo-sma_cross", async () => new Response("<html>", { status: 200 }))).rejects.toThrow(
    /JSON/,
  );
});

test("loadRun rejects ids that are not file-safe without calling fetch", async () => {
  const fetchFn = vi.fn();
  await expect(loadRun("../etc", fetchFn)).rejects.toThrow(DataError);
  expect(fetchFn).not.toHaveBeenCalled();
});

test("loadRun network failure becomes a DataError", async () => {
  await expect(
    loadRun("demo-sma_cross", async () => {
      throw new TypeError("Failed to fetch");
    }),
  ).rejects.toThrow(DataError);
});

test("useRun is idle without an id", () => {
  const { result } = renderHook(() => useRun(null, vi.fn()));
  expect(result.current.status).toBe("idle");
});

test("useRun retry refetches after an error", async () => {
  const fetchFn = vi
    .fn()
    .mockResolvedValueOnce(new Response("boom", { status: 500 }))
    .mockResolvedValueOnce(jsonResponse(makeRun()));
  const { result } = renderHook(() => useRun("demo-sma_cross", fetchFn));
  await waitFor(() => expect(result.current.status).toBe("error"));
  act(() => result.current.retry());
  await waitFor(() => expect(result.current.status).toBe("ready"));
  expect(fetchFn).toHaveBeenCalledTimes(2);
  expect(result.current.run?.trades).toHaveLength(3);
});

test("useRun ignores a late response from a previous id", async () => {
  let resolveFirst: (r: Response) => void = () => {};
  const fetchFn = vi.fn((url: RequestInfo | URL) => {
    if (String(url).includes("slow")) return new Promise<Response>((r) => (resolveFirst = r));
    return Promise.resolve(jsonResponse(makeRun({ verdict: { passed: true, reasons: [] } })));
  });
  const { result, rerender } = renderHook(({ id }) => useRun(id, fetchFn), { initialProps: { id: "slow" } });
  rerender({ id: "fast" });
  await waitFor(() => expect(result.current.status).toBe("ready"));
  await act(async () => resolveFirst(jsonResponse(makeRun({ verdict: { passed: false, reasons: ["velho"] } }))));
  expect(result.current.run?.verdict.passed).toBe(true);
});
