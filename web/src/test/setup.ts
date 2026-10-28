import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach, expect } from "vitest";
import * as axeMatchers from "vitest-axe/matchers";
import { installMatchMedia, setReducedMotion } from "./matchMedia";

expect.extend(axeMatchers);
installMatchMedia();
beforeEach(() => setReducedMotion(true));
afterEach(cleanup);

// jsdom nao implementa scrollIntoView
Element.prototype.scrollIntoView = function () {};
