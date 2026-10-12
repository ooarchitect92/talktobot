import test from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { gatewayContext } from "../proxy-context.mjs";
const secret = "test-only-gateway-secret-32-characters-long";
test("untrusted forwarding and caller signatures cannot replace observed peer", () => {
  const req = {method:"POST",socket:{remoteAddress:"::ffff:203.0.113.12"},headers:{"x-forwarded-for":"198.51.100.9","x-website-client-ip":"198.51.100.9","x-website-context-signature":"forged"}};
  const context = gatewayContext(req,"/api/v1/website/inquiries",secret);
  assert.equal(context["x-website-client-ip"],"203.0.113.12");
  const message = `203.0.113.12\n${context["x-website-context-time"]}\nPOST\n/api/v1/website/inquiries`;
  assert.equal(context["x-website-context-signature"],createHmac("sha256",secret).update(message).digest("hex"));
  assert.deepEqual(gatewayContext(req,"/api/v1/website/inquiries",""),{});
});
test("forwarding walks from trusted proxy toward first untrusted hop", () => {
  const req={method:"POST",socket:{remoteAddress:"10.1.0.5"},headers:{"x-forwarded-for":"198.51.100.99, 203.0.113.25, 10.1.0.8"}};
  const context=gatewayContext(req,"/api/v1/website/inquiries",secret,"10.0.0.0/8");
  assert.equal(context["x-website-client-ip"],"203.0.113.25");
});
