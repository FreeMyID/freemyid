// Free My ID team mail: Cloudflare Email Worker bound as the freemyid.org catch-all.
// 1) Forwards every message to the owner (FORWARD_TO, a verified Email Routing destination; set as a
//    plain-text binding, never in this file). 2) Stores a size-capped raw copy in D1 for agents, who read it
//    only through tools/mail/gateway.py as UNTRUSTED data. Forwarding happens first, so a storage error never
//    loses mail.
const MAX_RAW = 256 * 1024;

export default {
  async email(message, env, ctx) {
    await message.forward(env.FORWARD_TO);
    try {
      const buf = await new Response(message.raw).arrayBuffer();
      const truncated = buf.byteLength > MAX_RAW ? 1 : 0;
      const raw = new TextDecoder("utf-8", { fatal: false }).decode(buf.slice(0, MAX_RAW));
      const h = (k) => (message.headers.get(k) || "").slice(0, 2000);
      await env.DB.prepare(
        "INSERT INTO inbound (received_at, mail_from, rcpt_to, subject, message_id, in_reply_to, auth_results, size, truncated, raw) VALUES (?,?,?,?,?,?,?,?,?,?)"
      ).bind(new Date().toISOString(), message.from, message.to, h("subject"), h("message-id"),
             h("in-reply-to"), h("authentication-results") || h("arc-authentication-results"),
             message.rawSize, truncated, raw).run();
    } catch (e) {
      console.log("store failed", String(e).slice(0, 200));
    }
  },
};
