<?php
/* Knocbrac Learning — results receiver, v3 (PHP 5.6 compatible).
   Runs through Apache's PHP handler like any other page — no CGI setup,
   no execute permissions. Email settings live in config.txt beside this
   file. All responses use HTTP 200 with the truth in the JSON body, so
   shared-host ErrorDocument handling can never blank them. */

header('Content-Type: application/json');
header('Cache-Control: no-store');
header('X-Robots-Tag: noindex, nofollow');

$KB_LOG = __DIR__ . '/receiver.log.php';
function kb_log($event) {
    global $KB_LOG;
    if (!file_exists($KB_LOG)) {
        @file_put_contents($KB_LOG, "<?php exit; ?>\n"); /* web access shows nothing */
    }
    if (@filesize($KB_LOG) > 200000) {           /* simple rotation */
        @rename($KB_LOG, $KB_LOG . '.1');
        @file_put_contents($KB_LOG, "<?php exit; ?>\n");
    }
    @file_put_contents($KB_LOG,
        date('Y-m-d H:i:s') . ' | ' . $event . "\n", FILE_APPEND);
}

function kb_get($arr, $key, $default) {
    return (is_array($arr) && isset($arr[$key])) ? $arr[$key] : $default;
}
function kb_clean($s, $fallback) {
    $s = preg_replace('/[^a-z0-9_-]/', '', strtolower(strval($s)));
    return $s !== '' ? substr($s, 0, 40) : $fallback;
}

$NOTIFY = 'timothy@knocbrac.com';
$FROM   = 'learning@knocbrac.com';
$cfg = @file(__DIR__ . '/config.txt', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
if ($cfg) {
    foreach ($cfg as $line) {
        if (strpos($line, 'NOTIFY_EMAIL=') === 0) $NOTIFY = trim(substr($line, 13));
        if (strpos($line, 'FROM_EMAIL=') === 0)   $FROM   = trim(substr($line, 11));
    }
}

$RESULTS = __DIR__ . '/../results';
if (!is_dir($RESULTS)) @mkdir($RESULTS, 0755, true);

$method = kb_get($_SERVER, 'REQUEST_METHOD', '');
if ($method !== 'POST') {
    if (isset($_GET['logtail'])) {
        /* grown-up diagnostics: last ~120 log lines */
        $lines = array();
        if (file_exists($KB_LOG)) {
            $all = file($KB_LOG, FILE_IGNORE_NEW_LINES);
            if (is_array($all)) {
                array_shift($all);                 /* drop the php guard line */
                $lines = array_slice($all, -120);
            }
        }
        echo json_encode(array('ok' => true, 'lines' => $lines));
        exit;
    }
    if (isset($_GET['progress'])) {
        /* which sessions has this course already submitted results for?
           filenames are course-session-kind-date-time.json (no hyphens
           inside the individual ids) */
        $course = kb_clean($_GET['progress'], 'course');
        $done = array();
        $files = glob($RESULTS . '/' . $course . '-*.json');
        if (is_array($files)) {
            foreach ($files as $f) {
                $rest = substr(basename($f, '.json'), strlen($course) + 1);
                $bits = explode('-', $rest);
                if (count($bits) >= 1 && $bits[0] !== '' && !in_array($bits[0], $done)) {
                    $done[] = $bits[0];
                }
            }
        }
        echo json_encode(array('ok' => true, 'course' => $course, 'done' => $done));
        exit;
    }
    echo json_encode(array('ok' => false, 'error' => 'POST only',
        'status' => 'receiver alive (php ' . PHP_VERSION . ') - this URL only accepts results submissions'));
    exit;
}

$raw = file_get_contents('php://input');
if ($raw === false || strlen($raw) > 300000) {
    echo json_encode(array('ok' => false, 'error' => 'bad size'));
    exit;
}
$data = json_decode($raw, true);
if (!is_array($data)) {
    kb_log('ERROR invalid JSON (' . strlen($raw) . ' bytes)');
    echo json_encode(array('ok' => false, 'error' => 'invalid JSON'));
    exit;
}

/* client-side error beacon: log it, save no results file */
if (isset($data['clientlog'])) {
    kb_log('CLIENT ' . substr(preg_replace('/\s+/', ' ',
        strval($data['clientlog'])), 0, 500));
    echo json_encode(array('ok' => true, 'logged' => true));
    exit;
}

$course  = kb_clean(kb_get($data, 'course', ''),  'course');
$kind    = kb_clean(kb_get($data, 'kind', ''),    'session');
$session = kb_clean(kb_get($data, 'session', ''), 's');
$fname   = $course . '-' . $session . '-' . $kind . '-' . date('Ymd-His') . '.json';

$written = @file_put_contents($RESULTS . '/' . $fname,
    json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
if ($written === false) {
    kb_log('ERROR cannot write ' . $fname . ' (results permissions?)');
    echo json_encode(array('ok' => false,
        'error' => 'cannot write to results folder (check its permissions: 755, or 775 if needed)'));
    exit;
}

/* ---- rebuild the family folder index ---- */
$rows  = '';
$files = glob($RESULTS . '/*.json');
if (!is_array($files)) $files = array();
rsort($files);
foreach ($files as $f) {
    $d = json_decode(@file_get_contents($f), true);
    if (!is_array($d)) $d = array();
    $label = kb_get($d, 'student', '?') . ' — '
           . kb_get($d, 'title', kb_get($d, 'session', '?'))
           . ' (' . kb_get($d, 'kind', 'session') . ')';
    $when  = substr(str_replace('T', ' ', strval(kb_get($d, 'when', ''))), 0, 16);
    $b     = basename($f);
    $rows .= '<li><a href="' . htmlspecialchars($b) . '" download>'
           . htmlspecialchars($label) . '</a> <span class="sub">'
           . htmlspecialchars($when) . "</span></li>\n";
}
if ($rows === '') $rows = '<li>Nothing here yet.</li>';
$page = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex, nofollow"><title>Results — family folder</title>
<link rel="stylesheet" href="../assets/base.css"></head><body><div class="wrap">
<h1>Family results folder</h1>
<p class="sub">Newest first. Tap to download a file, then upload it to Claude to build the next course block.</p>
<div class="card"><ul style="line-height:2.2">' . $rows . '</ul></div>
<p class="grownup"><a href="../index.html">&larr; Back to Knocbrac Learning</a></p>
</div></body></html>';
@file_put_contents($RESULTS . '/index.html', $page);

/* ---- notification email ---- */
$student = substr(strval(kb_get($data, 'student', '?')), 0, 40);
$title   = substr(strval(kb_get($data, 'title', $session)), 0, 80);
$correct = 0; $skipped = 0; $total = 0;
$detail = kb_get($data, 'detail', array());
if (is_array($detail)) {
    foreach ($detail as $d) {
        $parts = kb_get($d, 'parts', array());
        if (!is_array($parts)) continue;
        foreach ($parts as $p) {
            $total++;
            $mark = kb_get($p, 'mark', '');
            if ($mark === 'correct') $correct++;
            if ($mark === 'skipped') $skipped++;
        }
    }
}
$subject = 'Knocbrac Learning: ' . $student . ' finished "' . $title . '"';
$body = $student . ' has just finished "' . $title . '" (' . $kind . ").\n\n"
      . 'Quick tally: ' . $correct . ' of ' . $total . ' parts correct, ' . $skipped . " skipped.\n\n"
      . "Full results: https://www.knocbrac.com/learn/results/\n"
      . 'File: ' . $fname . "\n\n— Knocbrac Learning";
$headers = 'From: Knocbrac Learning <' . $FROM . ">\r\n"
         . 'Reply-To: ' . $FROM . "\r\n"
         . 'Content-Type: text/plain; charset=utf-8';
$emailed = @mail($NOTIFY, $subject, $body, $headers);

kb_log('SAVE ' . $fname . ' | ' . $correct . '/' . $total . ' correct | emailed='
       . ($emailed ? 'yes' : 'NO'));
echo json_encode(array('ok' => true, 'file' => $fname, 'emailed' => (bool)$emailed));
