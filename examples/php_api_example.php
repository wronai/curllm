#!/usr/bin/env php
<?php
// Minimal PHP example calling curllm API using values from examples/.env
// No external dependencies required.

function load_env($path) {
    if (!file_exists($path)) return;
    $lines = file($path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    foreach ($lines as $line) {
        if (strlen($line) === 0 || $line[0] === '#') continue;
        $pos = strpos($line, '=');
        if ($pos === false) continue;
        $key = trim(substr($line, 0, $pos));
        $val = trim(substr($line, $pos + 1));
        if (!array_key_exists($key, $_ENV)) {
            $_ENV[$key] = $val;
            putenv($key . '=' . $val);
        }
    }
}

$envPath = __DIR__ . '/.env';
if (file_exists($envPath)) load_env($envPath);

function env_bool($k, $def = false) {
    $v = getenv($k);
    if ($v === false) return $def;
    $s = strtolower(strval($v));
    return in_array($s, ['1','true','yes','on'], true);
}

$apiHost = getenv('CURLLM_API_HOST');
if (!$apiHost) $apiHost = 'http://localhost:8000';

$payload = [
    'url' => getenv('API_URL') ?: 'https://ceneo.pl',
    'data' => getenv('API_INSTRUCTION') ?: 'Find all products under 150zł and extract names, prices and urls',
    'visual_mode' => env_bool('API_VISUAL_MODE', false),
    'stealth_mode' => env_bool('API_STEALTH_MODE', true),
    'captcha_solver' => env_bool('API_CAPTCHA_SOLVER', true),
    'use_bql' => env_bool('API_USE_BQL', false),
    'headers' => []
];
$acceptLang = getenv('ACCEPT_LANGUAGE');
if ($acceptLang) {
    $payload['headers']['Accept-Language'] = $acceptLang;
}

$endpoint = rtrim($apiHost, '/') . '/api/execute';
$ch = curl_init($endpoint);
$body = json_encode($payload, JSON_UNESCAPED_UNICODE);

curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_CUSTOMREQUEST => 'POST',
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'Content-Length: ' . strlen($body)
    ],
    CURLOPT_POSTFIELDS => $body,
]);

$response = curl_exec($ch);
if ($response === false) {
    fwrite(STDERR, 'Request failed: ' . curl_error($ch) . PHP_EOL);
    exit(1);
}
$code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($code >= 200 && $code < 300) {
    echo $response . PHP_EOL;
} else {
    fwrite(STDERR, 'HTTP ' . $code . ': ' . $response . PHP_EOL);
    exit(1);
}
