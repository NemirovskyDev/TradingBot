import "vitest";

// tipo do matcher registrado em test/setup.ts (vitest-axe/matchers)
declare module "vitest" {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars
  interface Assertion<T = any> {
    toHaveNoViolations(): void;
  }
}
