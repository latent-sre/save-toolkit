// test-setup.ts — the Vitest setup file that vite.config.ts names as src/test/setup.ts: write it
// in at that path. It registers Testing Library's jest-dom matchers (`toBeInTheDocument`,
// `toHaveTextContent` ...) and unmounts rendered trees between tests, which Testing Library does
// on its own only when Vitest's globals are on.
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());
