import { describe, expect, it } from "vitest";
import { normalize, parse, resolve } from "fast-uri";

const base = "https://schemas.example.test/templates/resource.json";

describe("URI resolver used by the form validator", () => {
  // GHSA-jqff-g426-hqxp: encoded schemes must not introduce an authority or CR/LF.
  it.each(["%2f%2fexample.test:/path", "%u002f%u002fexample.test:/path", "http%0d%0a:/path"])(
    "rejects malformed scheme %s",
    (uri) => {
      expect(parse(uri).error).toBeDefined();
      expect(normalize(uri)).toBe(uri);
      expect(() => resolve(base, uri)).toThrow();
    },
  );

  // GHSA-f65p-4m7j-42xc: malformed IPv6 hosts must not collapse to valid addresses.
  it.each(["http://[::not-valid]/private", "http://[fc00::not-hex]/private", "http://[fe80::not-hex]/private"])(
    "rejects malformed host %s",
    (uri) => {
      expect(parse(uri).error).toBeDefined();
      expect(normalize(uri)).toBe(uri);
      expect(() => resolve(base, uri)).toThrow();
    },
  );

  it("does not decode a nested encoded hostname into a different destination", () => {
    // GHSA-fph4-wmhf-6fwf. These are string operations; no request is made.
    const uri = "http://%256c%256f%2563%2561%256c%2568%256f%2573%2574/";
    expect(normalize(uri)).toBe(uri);
    expect(resolve(base, uri)).toBe(uri);
  });

  it("canonicalises a scheme-relative internationalised hostname", () => {
    // GHSA-5jgf-p345-68v8.
    const uri = resolve(base, "//bücher.example/path");
    expect(uri).toBe("https://xn--bcher-kva.example/path");
    expect(normalize(uri)).toBe(uri);
  });

  it("preserves valid schema references and IPv6 addresses", () => {
    expect(resolve(base, "../common.json#/properties/name")).toBe(
      "https://schemas.example.test/common.json#/properties/name",
    );
    expect(resolve(base, "#/properties/name")).toBe(`${base}#/properties/name`);
    expect(normalize("https://[2001:db8::1]/schema")).toBe("https://[2001:db8::1]/schema");
  });
});
