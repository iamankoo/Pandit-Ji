import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import HomePage from "../app/page";

describe("HomePage", () => {
  it("renders the foundation placeholder", () => {
    render(<HomePage />);
    expect(screen.getByRole("heading", { name: "Pandit Ji" })).toBeDefined();
  });
});
