# TestCraft Goo — Permanent URL Setup (DuckDNS)

This gives TestCraft Goo a **fixed address** like `http://testcraftgoo.duckdns.org:8501` that never changes, even if your public IP changes.

Two steps need to happen on **your side** (account + router). Once done, tell Claude your DuckDNS subdomain + token, and the rest (auto-updater, testing) gets wired up automatically.

---

## Step 1 — Create a free DuckDNS subdomain

1. Go to **https://www.duckdns.org**
2. Sign in using Google, GitHub, Reddit, or Twitter (no password to create — just OAuth login)
3. In the **"domains"** box on the dashboard, type a name, e.g. `testcraftgoo`, then click **"add domain"**
   - This creates: `testcraftgoo.duckdns.org`
4. At the **top of the page**, copy your **token** (a long string like `a1b2c3d4-....`) — you'll need this.

**Give Claude:** the subdomain you chose + the token.

---

## Step 2 — Port forward on your router

This lets the internet reach your PC's TestCraft Goo server (port 8501).

1. Open a browser and go to your router's admin page: **http://192.168.15.1**
2. Log in (credentials are usually on a sticker on the router itself, or ask your IT/network admin if this is an office router)
3. Find the section called **"Port Forwarding"**, **"Virtual Server"**, or **"NAT"** (name varies by router brand)
4. Add a new rule:

   | Field | Value |
   |---|---|
   | External/Public Port | `8501` |
   | Internal/Local IP | `192.168.15.52` |
   | Internal Port | `8501` |
   | Protocol | `TCP` |

5. **Save** and apply.

> ⚠️ If this is an **office router**, you may need your IT team's help/approval — this is a network security setting, and it's worth confirming with them since it opens an inbound path from the internet to this machine.

---

## Step 3 — What Claude sets up (once you share subdomain + token)

- A small updater script + Windows Scheduled Task that pings DuckDNS every 5 minutes with your current public IP (so the address never breaks even if your ISP changes your IP)
- A verification test to confirm `http://<your-subdomain>.duckdns.org:8501` is reachable from outside your network

---

## Notes

- This is **plain HTTP**, not HTTPS — your login page will work, but traffic between browser and server isn't encrypted. Fine for internal/team use; ask Claude about adding free HTTPS (Let's Encrypt) later if this needs to be public-facing long-term.
- Keep the Streamlit app running on this PC for the link to stay live — same as before.
