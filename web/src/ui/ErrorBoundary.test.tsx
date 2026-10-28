import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { ErrorBoundary } from "./ErrorBoundary";

function Bomb({ explode }: { explode: boolean }) {
  if (explode) throw new Error("falha ao desenhar");
  return <p>tudo certo</p>;
}

function Harness() {
  const [explode, setExplode] = useState(true);
  return (
    <ErrorBoundary onReset={() => setExplode(false)}>
      <Bomb explode={explode} />
    </ErrorBoundary>
  );
}

test("a render error shows an alert with a retry instead of a blank screen", async () => {
  const spy = vi.spyOn(console, "error").mockImplementation(() => {});
  render(<Harness />);
  expect(screen.getByRole("alert")).toHaveTextContent(/não foi possível desenhar/i);
  await userEvent.click(screen.getByRole("button", { name: /tentar de novo/i }));
  expect(screen.getByText("tudo certo")).toBeInTheDocument();
  spy.mockRestore();
});

test("without errors the boundary is invisible", () => {
  render(
    <ErrorBoundary>
      <p>conteúdo</p>
    </ErrorBoundary>,
  );
  expect(screen.getByText("conteúdo")).toBeInTheDocument();
});
