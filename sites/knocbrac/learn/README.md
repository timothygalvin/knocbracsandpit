# Knocbrac Learning — deployment guide (r3)

Static site + one small results receiver. No database, no framework,
Chyrp untouched. **New in r3: the receiver is PHP** (`api/submit.php`) —
it runs like any other page on the host, with no CGI setup and no execute
permissions. The Python version is kept only as a fallback.

## 1. Upload
Copy the whole `learn/` folder into `httpdocs/`, so it lives at
`www.knocbrac.com/learn/`. Move `learn/robots.txt` to the site root
(`httpdocs/robots.txt`) — merge with an existing robots.txt if you have one.

Permissions: directories 755, files 644. (Nothing needs to be executable
any more.)

## 2. Email + results folder
- Edit `learn/api/config.txt` (plain text, safe in any editor):
  `NOTIFY_EMAIL=` you, `FROM_EMAIL=` ideally a real mailbox on the domain.
- Test the receiver: open `www.knocbrac.com/learn/api/submit.php` in a
  browser — you should see `{"ok":false,"error":"POST only"}`. That means
  it's alive.
- Finish a session on the site: a file appears in `/learn/results/`, the
  index page there rebuilds, and an email arrives. If the save works but
  `"emailed":false`, set FROM_EMAIL to a real mailbox on knocbrac.com.
- If saves fail with a permissions error, set `learn/results/` to 775.

## 3. Password (when you have the path from 34sp)
Uncomment the auth block in `learn/.htaccess`, create `.htpasswd`
(see `.htpasswd.example`; the example password is `lemonade` — change it),
and set `AuthUserFile` to its absolute server path.

## 4. Python fallback (only if PHP ever goes away)
`api/submit.py` still works as a CGI: chmod it 755 and rename
`api/htaccess-cgi.optional` to `.htaccess` — note that on some hosts that
`.htaccess` itself causes a 500; that's why it ships disabled. The app
automatically tries submit.php first, then submit.py, then /cgi-bin/.

## 5. Adding a course (the whole point)
1. Make `learn/<courseid>/` with a `course.json` (copy an existing one)
   and a `content/` folder of session JSON files.
2. Add one entry to `learn/courses.json`.
That's it — hub, course map, player, progress, results and email all pick
it up automatically. Grace's Spanish course will be one new folder.

## 6. Local test (recommended before uploading)
Put `dev_server.py` NEXT TO the `learn/` folder and run:

    python3 dev_server.py

then open `http://localhost:8000/learn/`. It serves the site and runs the
results receiver (via the Python fallback), so the full loop works
locally: finish a session and watch the file appear in `learn/results/`.
Emails won't send from a home machine. (Opening index.html directly as a
file won't work — the pages fetch JSON, which browsers block from `file://`.)

## Notes
- Progress lives in each tablet's browser storage (per device, automatic).
  Clearing browser data resets progress on that device only; results
  already sent to the family folder are safe on the server.
- Release: r3 (framework, PHP receiver, both Week 1 Session 1s).
