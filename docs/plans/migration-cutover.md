# knocbrac.com cutover runbook: 34sp old cluster to new cluster

> Prepared 15 Nov 2026 (agent, hosting workstream). Status: **NOT STARTED.**
> DNS still points at the old cluster, and every step below is still to do.
> Owner tags: **[T]** = Timothy runs it (interactive: passwords, DNS panel,
> 34sp panel, tablets). **[A]** = an agent can run it once [T] prerequisites
> are done (needs the SSH key in place; never needs a password).

## Facts this runbook is built on (all probed 15 Nov 2026)

| | OLD cluster (live) | NEW cluster (staged) |
|---|---|---|
| IPv4 / IPv6 | 80.82.113.174 / (no AAAA published) | 185.114.98.6 / 2a00:1ee0:2:207::b972:6206 |
| Web server | Apache 2.2.15 (CentOS) | Apache 2.4.58, OpenSSL 3.1.4 |
| Receiver says | `receiver alive (php 7.4.33)`, which is **not** the 5.6.36 in CLAUDE.md | `receiver alive (php 8.5.12)` |
| Transfer | vsFTPd 2.2.2 on :21 (plain FTP; FTPS 530s) | OpenSSH 9.9 on :22 (SFTP); **:21 closed** |
| TLS on :443 | expired `*.34sp.com` cert (2020) | handshake gives no certificate yet |
| Content / code | r12 / 1.1.2 | **r7 / 1.1.0**: the snapshot is stale |
| results/*.json | 44 | **34**, newest 20261011-180624 |
| Chyrp blog `/` | 200 | **HTTP 500, empty body** |

- Preview `http://knocbrac-com.temp.link/` resolves to 80.82.115.25, a 34sp
  front proxy (nginx 1.20.1) in front of the new cluster. For true probes, hit the IP
  with the real Host header: `curl --resolve www.knocbrac.com:80:185.114.98.6 http://www.knocbrac.com/...`
  It answers fast that way (~0.06 s).
- **The 34sp snapshot is from about 11 Oct**, not today. The new cluster is
  missing 10 results files: `ascent-cp1`, `ascent-w3s1..w3s3`,
  `graceco-cp1`, `graceco-w3s1..w3s3`, `gracees-diag`, `vozvrat-diag`.
  Its state store is also behind: ascent and graceco have 6 sessions
  (newest 11 Oct), against 10 on old (newest 3 Nov), and gracees and vozvrat have none.
  Progress on new shows ascent and graceco only through w2s3. **Flipping DNS
  without the re-sync in step C would visibly lose children's work.**
  The same staleness applies to everything else in httpdocs, including Chyrp's
  data. Code and content are fixed by a deploy; results and state are fixed
  only by step C.
- **DNS:** the 34sp migration page says "managed by another provider", but
  `whois`/`dig` show registrar Easyspace with nameservers **ns.34sp.com /
  ns2.34sp.com** (SOA serial 2019011801, A TTL 3600). The zone is most likely
  on the old 34sp platform's DNS, which the new panel treats as "another provider".
  [T] needs to confirm where it is edited (old 34sp control panel, or Easyspace).
  Current records: `knocbrac.com A 80.82.113.174`; `www` and `ftp` are CNAMEs to
  `knocbrac.com`; `*` resolves to 80.82.113.174; **`mail.knocbrac.com A
  46.183.13.250` is an explicit record and must not be changed**; MX = mx3/mx4.34sp.com +
  mail.knocbrac.com. No AAAA records exist today.
- Old-cluster filenames use Europe/London local time (`graceco-cp1-...-155655`
  has `when` 14:56:46Z in BST). The new cluster's `date.timezone` is unknown, so
  check it in A6.

## A. Pre-flight on the new cluster (no traffic moves yet)

- [ ] **A1 [A]** Receiver alive with the expected PHP:
  `curl -sS --resolve www.knocbrac.com:80:185.114.98.6 http://www.knocbrac.com/learn/api/submit.php`
  should return `receiver alive (php 8.5.x)`, with HTTP 200 (verified 15 Nov).
- [ ] **A2 [A]** `.htaccess` is honoured: `curl -I` on `/learn/` must show
  `X-Robots-Tag: noindex, nofollow` and `Cache-Control: no-cache, must-revalidate`
  (verified 15 Nov). `/learn/.htaccess` should give 403 (verified).
- [ ] **A3 [A]** HTTP-200 invariant (CLAUDE.md invariant 2): every receiver path
  answers 200 with JSON. Check `?progress=ascent`, `?state=ascent`, `?logtail=1`, and a
  POST of `nope` (must be 200 + `{"ok":false,"error":"invalid JSON"}`). Note that the
  new host's 404 ErrorDocument is a small 196-byte page, where old has a 9.5 KB Chyrp page.
  The receiver never relies on either, but recheck that a non-200 never appears from
  `submit.php`.
- [ ] **A4 [A]** PHP 8.5 compatibility of `submit.php`: done locally 15 Nov on
  PHP 8.5.11 (php-cgi). `php -l` is clean, the 10 php-cgi receiver tests pass, and all paths
  were exercised at `error_reporting=E_ALL` + `display_errors=1` with **no
  deprecations**. The only output is "Array to string conversion" warnings when a malformed
  request sends an array where a scalar is expected (`?progress[]=x`, `clientlog:[...]`, array
  `course`/`student`/`title`/`when`). The real client never does that, and 5.6/7.4 behave the
  same way (Notice there). It matters only if the new host has `display_errors` on, because
  the warning HTML would then precede the JSON.
- [ ] **A5 [T→A]** Ask 34sp, or check over SSH after B, whether `display_errors` is off:
  `ssh knocbraccom@185.114.98.6 'php -i | grep -E "display_errors|date.timezone|sendmail_path"'`
  (the CLI ini may differ from FPM; treat it as a hint).
- [ ] **A6 [A]** `date.timezone` should be Europe/London, so filenames stay on the same
  clock as the 44 existing ones. In winter UK = UTC, so a test submission cannot tell
  them apart. Use the A5 command.
- [ ] **A7 [T]** **Chyrp returns 500 on the new cluster.** Out of scope for this repo
  (never touch Chyrp), but it blocks a clean flip of the whole domain. Likely causes: PHP
  8.5 incompatibility, or a DB host/credentials still pointing at the old cluster. Decide
  between fixing it with 34sp first, accepting a broken blog, or asking 34sp for an older
  PHP on the new account. Note that the old cluster already runs Chyrp on 7.4 fine.
- [ ] **A8 [A]** After B: delete the leaked `/learn/README.md` on the NEW
  cluster (it exists on both: HTTP 200): `sftp> rm httpdocs/learn/README.md`.
  Leave the old one for the decommission (or delete it via FTP now: [T]).

## B. SSH key setup for the new cluster [T], one time, interactive

The new sshd is OpenSSH 9.9 (rsa-sha2-256/512, ed25519). **No ssh-rsa workaround is
needed.** Today the existing `~/.ssh/id_rsa` is offered and refused (not installed), and
the server also offers password auth. The host key (ED25519
`SHA256:siTdRVJBk6Ki1q6Vu5Wu4vaLLV1Rd8Q6KEffN47RV84`) was added to
`~/.ssh/known_hosts` by the 15 Nov probe.

- [ ] **B1** `ssh-copy-id -p 22 knocbraccom@185.114.98.6` (uses the 34sp
  password once). The existing id_rsa is fine, or make an ed25519 key first.
- [ ] **B2** If the account turns out to be sftp-only and ssh-copy-id fails, install the key by hand:
  `sftp -P 22 knocbraccom@185.114.98.6` then `mkdir .ssh`,
  `put ~/.ssh/id_rsa.pub .ssh/authorized_keys`, `chmod 700 .ssh`,
  `chmod 600 .ssh/authorized_keys`.
- [ ] **B3 [A]** Readiness test (must exit 0):
  `sftp -b /dev/null -o BatchMode=yes -o ConnectTimeout=10 -P 22 knocbraccom@185.114.98.6`
- [ ] **B4 [A]** Confirm the layout: `echo 'ls -la httpdocs/learn/results' | sftp -b - -P 22 knocbraccom@185.114.98.6`.
  Record the owner of the files and whether the folder is writable by the PHP user. The
  re-synced files must be writable by PHP, or state saves fail with `cannot write state`.

## C. Bring the new cluster current, then re-sync results/ old → new

Pick a quiet window (kids asleep). Tell the second household that the site is
"under maintenance for an hour", or just pick an hour nobody uses it. **[T]**

- [ ] **C1 [A]** Ship current code + content to the new cluster. Temporarily
  set in site.json `transport: "sftpcli"`, `host: "185.114.98.6"`, delete
  `use_tls`, and set `site_url: "http://knocbrac-com.temp.link"` (so verify probes
  the NEW box rather than old). Then `python3 tools/deploy.py knocbrac --all`.
  `--all` is mandatory because the manifest records the old host. Never use `--init`:
  that would overwrite `results/index.html`. Verify must show code 1.1.2 and content
  r12 (or whatever is current). Leave site.json in this state; F finalises it.
  `tools/tests/test_transports.py::test_knocbrac_declares_the_legacy_algorithm`
  then starts running and **will fail**, because it asserts ssh-rsa. Retire or invert it in
  the same change: the new host must NOT need it.
- [ ] **C2 [T]** Pull everything in results/ from old over FTP. Kids' data goes outside
  the repo:
  ```sh
  D=~/knocbrac-cutover/$(date +%Y%m%d-%H%M%S); mkdir -p "$D/old"; cd "$D/old"
  umask 077; printf 'machine 80.82.113.174 login knocbraccom password ' > ../.netrc
  read -rs P; printf '%s\n' "$P" >> ../.netrc; unset P
  U=ftp://80.82.113.174/httpdocs/learn/results/
  curl -sS --netrc-file ../.netrc "$U" > ../old-LIST.txt          # ls -l with mtimes
  curl -sS --netrc-file ../.netrc --list-only "$U" | grep -v '^\.\.\?$' > ../old-names.txt
  while read -r f; do curl -sS --netrc-file ../.netrc -o "$f" "$U$f"; done < ../old-names.txt
  ls | wc -l; wc -l < ../old-names.txt                              # must match
  ```
  Use the IP, not ftp.knocbrac.com: after the DNS flip that name points at the new
  box, which has no FTP. vsFTPd hides dotfiles from listings by default. None are
  expected in results/ (the repo ships only `index.html` there), so treat any `.ht*`
  that the sftp listing in B4 shows on new as something to ask about, not to copy blindly.
  Also take `httpdocs/learn/api/receiver.log.php` if you want the log history.
- [ ] **C3 [A]** Push to the new cluster. Results filenames are unique timestamps, so this
  is a pure union. `index.html` and `state-*.json` are overwrites, which is correct
  **only while the new box has received no real traffic**:
  ```sh
  cd "$D/old"; { echo 'cd httpdocs/learn/results'; for f in *; do echo "put \"$f\""; done; } > ../put.sftp
  sftp -b ../put.sftp -P 22 knocbraccom@185.114.98.6
  ```
  Match the permissions B4 recorded for the existing files. If PHP runs as a different
  user than knocbraccom, sftp-owned `state-*.json` files must stay group/world-writable
  (as the existing ones are), or the next state save fails.
- [ ] **C4 [A]** Verify, and do not proceed unless all four pass:
  1. File count: `echo 'ls -1 httpdocs/learn/results' | sftp -b - -P 22 knocbraccom@185.114.98.6 | grep -vc '^sftp>'`
     is greater than or equal to the count of `$D/old`.
  2. Newest filename matches: `ls "$D/old" | grep -E '^[a-z]+-[a-z0-9]+-(session|checkpoint)-[0-9]{8}-[0-9]{6}\.json$' | awk -F- '{print $(NF-1)$NF" "$0}' | sort | tail -1`
     against the same pipeline over the sftp listing.
  3. Byte-identity for every file:
     `for f in *; do a=$(shasum -a 256 < "$f"); b=$(curl -sS --resolve www.knocbrac.com:80:185.114.98.6 "http://www.knocbrac.com/learn/results/$f" | shasum -a 256); [ "$a" = "$b" ] || echo "MISMATCH $f"; done`
     must print nothing.
  4. Receiver view: for c in ascent graceco gracees vozvrat, `?progress=$c` and
     `?state=$c` on old (plain URL) and on new (`--resolve ...:185.114.98.6`) give identical JSON.

## D. DNS change [T]

- [ ] **D0** Ideally 24 h ahead, lower the A/CNAME TTL from 3600 to 300 where the zone is edited
  (confirm where first; see Facts).
- [ ] **D1** Immediately after C4 passes, set:

  | Host | Type | Data |
  |---|---|---|
  | @ | A | 185.114.98.6 |
  | * | A | 185.114.98.6 |
  | @ | AAAA | 2a00:1ee0:2:207::b972:6206 |
  | * | AAAA | 2a00:1ee0:2:207::b972:6206 |

  Leave `mail` (A 46.183.13.250) and the MX records exactly as they are. `www`/`ftp`
  are CNAMEs to @ and follow automatically.
- [ ] **D2 [A]** Watch propagation: `dig +short www.knocbrac.com` against
  1.1.1.1 / 8.8.8.8 / ns.34sp.com until all show 185.114.98.6.
- [ ] **D3 [A]** **Propagation-window delta sync.** Until every resolver has flipped
  (at least the old TTL, so 1 h+), tablets may still write to old. Afterwards:
  - Old log: `curl -sS --resolve www.knocbrac.com:80:80.82.113.174 'http://www.knocbrac.com/learn/api/submit.php?logtail=1'`
    and look for `SAVE` lines after the flip time. Each one is a results file to copy across
    (repeat C2–C4 for just those names).
  - State writes are not logged. Compare `?state=<course>` on old and new. Where both sides
    changed, merge per session by newer `savedAt` (same rule as `KB.bestWork()`) and put the
    merged file on new:
    ```sh
    python3 - old/state-ascent.json new/state-ascent.json > merged.json <<'PY'
    import json,sys; a,b=(json.load(open(p)) for p in sys.argv[1:3]); m=dict(a)
    for k,v in b.items():
        if k not in m or v.get("savedAt","") > m[k].get("savedAt",""): m[k]=v
    print(json.dumps(m, indent=4, ensure_ascii=False))
    PY
    ```
  - Repeat the D3 checks again 24 h later. Stop when old's log and state are quiet.

## E. TLS, once DNS points at the new cluster

- [ ] **E1 [T]** In the 34sp panel, issue Let's Encrypt for `knocbrac.com` +
  `www.knocbrac.com` (HTTP-01 validation needs DNS already flipped).
- [ ] **E2 [A]** `echo | openssl s_client -connect www.knocbrac.com:443 -servername www.knocbrac.com 2>/dev/null | openssl x509 -noout -subject -dates -text | grep DNS:`
  must list www.knocbrac.com with a future notAfter.
- [ ] **E3 [T: steering]** Before switching to https, note that **localStorage is per-origin**.
  `http://www.knocbrac.com` and `https://www.knocbrac.com` are different origins, so tablets
  start empty on https (and lose the Aa setting). Completion and typed work come back from the
  server (invariant 5), but only what has already been mirrored. Make sure each tablet has been
  used online on http since the D flip (its state mirrors to the server), then try https on ONE
  device first. Add an http→https redirect only after that works.
- [ ] **E4 [A]** `site_url` → `https://www.knocbrac.com` in site.json, `deploy --check`, then a
  normal deploy so verify runs over https. Also update the hardcoded
  `http://www.knocbrac.com/learn/results/` in `tools/recover_state.py`.
  (The receiver email already says https.)
- [ ] **E5 [A]** Parked TODO follow-ups: "TLS ... then site_url back to https and revisit
  cache headers" (TODO § Later) and the 34sp-contact item on the cert. Revisit the
  `Cache-Control: no-cache, must-revalidate` policy in `.htaccess` once https is live.

## F. Finalise the transport swap in site.json [A]

- [ ] **F1** Make the C1 settings permanent: `transport: "sftpcli"`, `host: "185.114.98.6"`,
  `port: 22`, no `use_tls`, no `ssh_options`. Remove the `_sftp_when_migrated` block and
  rewrite `_notes` to describe the new host. Set `site_url` per E4 (http until E is done).
- [ ] **F2** Readiness test (B3) exits 0, `python3 tools/run_tests.py` is green (with the
  ssh-rsa test retired/inverted per C1), and `python3 tools/deploy.py knocbrac --check` is green.
- [ ] **F3** README.md "Auth" section (lines ~87–125) still describes OpenSSH 5.3 /
  ssh-rsa / ftp.knocbrac.com. Rewrite it for the new host.

## G. Post-cutover verification

- [ ] **G1 [A]** `python3 tools/deploy.py knocbrac --check`, then a no-op deploy
  ("Nothing changed") whose verify shows receiver alive, code and content markers matching.
- [ ] **G2 [A]** Test submission lands in results/:
  `curl -sS -X POST -H 'Content-Type: application/json' -d '{"course":"cutover","session":"t1","kind":"session","student":"Test","title":"cutover test","detail":[]}' http://www.knocbrac.com/learn/api/submit.php`
  should return `ok:true`, a filename, and `emailed:true`. Then `?progress=cutover` should show
  `["t1"]`. Afterwards `rm httpdocs/learn/results/cutover-t1-*.json` over sftp. The index keeps
  a dead link until the next real submission rebuilds it.
- [ ] **G3 [T]** The notification email for G2 arrived at the NOTIFY address
  (mail() from a new IP; there is no SPF record, so check spam).
- [ ] **G4 [A]** State round trip: POST `{"kind":"state","course":"cutover","session":"t1","work":{"answers":{}}}`,
  then `?state=cutover`, then remove `state-cutover.json`. This proves PHP can write the folder.
  Also re-POSTing a real course's state proves that the re-synced (sftp-owned) files are
  overwritable. Only do that by reading the current value and posting it back unchanged, or
  skip it and rely on G5.
- [ ] **G5 [T]** On each tablet: open the course map. Ticks match the server's `?progress=`,
  and an in-progress session shows its typed answers. Type one answer, then confirm
  `?state=<course>` shows a fresh `savedAt`.
- [ ] **G6 [A]** `?logtail=1` on new shows the G2 SAVE line and no ERROR lines.

## H. Old-cluster decommission guard [T]

- [ ] **H1** Do NOT cancel the old account or its FTP access until all of the following hold:
  (a) at least one real child submission has landed on the new cluster (seen in G6 or the
  family index); (b) D3 has been run at least 24 h after the flip and old has been quiet since;
  (c) a final C2-style FTP pull of old results/ has been archived locally
  (`~/knocbrac-cutover/final-old/`) and diffed against new.
- [ ] **H2** Until then, the old box is reachable only by IP: ftp://80.82.113.174
  and `curl --resolve www.knocbrac.com:80:80.82.113.174 ...`.

## After cutover: steering items (flagged, not changed here)

- **CLAUDE.md invariant 1** ("server runs PHP 5.6.36 ... no `??`") is already untrue: old
  reports 7.4.33 and new 8.5.12. Whether to relax the 5.6 syntax ban is a steering decision
  for after cutover. Until then the same submit.php must keep running on 7.4 and 8.5. It does
  today, and it is still 5.6-clean.
- **The `php56` pre-flight check** (`tools/deploy.py` `check_php56`) bans PHP 7 tokens and runs
  `php -l` with whatever local PHP exists (8.5.11 here). Revisit it after cutover: rename it, or
  retarget it to the host's version.
- **CLAUDE.md invariant 6** (deploy over SFTP to 80.82.113.174, `receiver alive (php 5.6.36)`,
  http-only site_url) needs rewriting once F and E are done.
