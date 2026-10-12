import { createHmac } from "node:crypto";
import { BlockList, isIP } from "node:net";

export function gatewayContext(req, pathname, secret, trustedCidrs = "") {
  const allowed = new BlockList();
  for (const raw of trustedCidrs.split(",").filter((value) => value.trim())) {
    const [address, width] = raw.trim().split("/");
    const version = isIP(address);
    if (!version) throw new Error("Invalid trusted proxy CIDR");
    allowed.addSubnet(
      address,
      width === undefined ? (version === 4 ? 32 : 128) : Number(width),
      version === 4 ? "ipv4" : "ipv6",
    );
  }
  let peer = req.socket.remoteAddress || "";
  if (peer.startsWith("::ffff:") && isIP(peer.slice(7)) === 4)
    peer = peer.slice(7);
  for (const raw of String(req.headers["x-forwarded-for"] || "")
    .split(",")
    .reverse()) {
    const type = isIP(peer);
    if (!type || !allowed.check(peer, type === 4 ? "ipv4" : "ipv6")) break;
    const candidate = raw.trim();
    if (!isIP(candidate)) break;
    peer = candidate;
  }
  if (!secret || secret.length < 32 || !isIP(peer)) return {};
  const stamp = String(Math.floor(Date.now() / 1000));
  const message = `${peer}\n${stamp}\n${req.method}\n${pathname}`;
  return {
    "x-website-client-ip": peer,
    "x-website-context-time": stamp,
    "x-website-context-signature": createHmac("sha256", secret)
      .update(message)
      .digest("hex"),
  };
}
