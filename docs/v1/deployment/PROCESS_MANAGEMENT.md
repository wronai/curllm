# curllm-web - Process Management

## 🎯 Nowe komendy zarządzania procesem

Klient webowy curllm obsługuje teraz pełne zarządzanie procesem:

```bash
curllm-web start      # Uruchom w tle
curllm-web stop       # Zatrzymaj
curllm-web restart    # Zrestartuj
curllm-web status     # Sprawdź status
curllm-web --help     # Pomoc
```

## 📖 Użycie

### Start - Uruchomienie w tle

```bash
$ curllm-web start
✅ curllm-web started on http://0.0.0.0:5000
   PID: 12345
   Press Ctrl+C to stop
```

Serwer działa w tle jako proces daemona.

### Status - Sprawdzenie statusu

```bash
$ curllm-web status
✅ curllm-web is running
   PID: 12345
   URL: http://localhost:5000
   Memory: 44.9 MB
   Status: ✅ Responding on port 5000
```

Pokazuje:
- PID procesu
- URL serwera
- Zużycie pamięci
- Status portu (czy odpowiada)

### Stop - Zatrzymanie serwera

```bash
$ curllm-web stop
⏹️  Stopping curllm-web (PID: 12345)...
✅ curllm-web stopped
```

Bezpieczne zatrzymanie z:
- Graceful shutdown (SIGTERM)
- 5 sekund na zamknięcie
- Force kill jeśli potrzeba (SIGKILL)
- Automatyczne czyszczenie PID file

### Restart - Restart serwera

```bash
$ curllm-web restart
🔄 Restarting curllm-web...
⏹️  Stopping curllm-web (PID: 12345)...
✅ curllm-web stopped
✅ curllm-web started on http://0.0.0.0:5000
   PID: 12346
   Press Ctrl+C to stop
```

Atomowa operacja:
1. Zatrzymanie starego procesu
2. Czekanie 1 sekundy
3. Uruchomienie nowego procesu

## 🔧 Techniczne szczegóły

### PID File

Lokalizacja: `/tmp/curllm_web.pid`

Zawiera PID aktualnie działającego procesu.

### Wykrywanie procesu

System sprawdza:
1. Czy plik PID istnieje
2. Czy proces o tym PID działa
3. Czy to faktycznie curllm-web (sprawdza cmdline)

Automatyczne czyszczenie jeśli proces nie działa.

### Zależności

```bash
pip install psutil
```

Wymagane dla zarządzania procesami.

## 💡 Przykłady użycia

### Przykład 1: Start w tle

```bash
# Uruchom w tle
curllm-web start

# Sprawdź czy działa
curllm-web status

# Otwórz w przeglądarce
xdg-open http://localhost:5000
```

### Przykład 2: Automatyczny restart po zmianach

```bash
# Edytuj kod
vim curllm_web.py

# Zrestartuj serwer
curllm-web restart

# Sprawdź czy działa
curl http://localhost:5000/health
```

### Przykład 3: Monitoring

```bash
# Status w pętli
watch -n 5 curllm-web status

# Lub w skrypcie
while true; do
    curllm-web status
    sleep 10
done
```

### Przykład 4: Integracja z systemd

Utwórz `/etc/systemd/system/curllm-web.service`:

```ini
[Unit]
Description=curllm Web Client
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/curllm
ExecStart=/usr/local/bin/curllm-web start
ExecStop=/usr/local/bin/curllm-web stop
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Następnie:

```bash
sudo systemctl daemon-reload
sudo systemctl enable curllm-web
sudo systemctl start curllm-web
sudo systemctl status curllm-web
```

## 🚨 Rozwiązywanie problemów

### Problem: "Already running"

```bash
$ curllm-web start
❌ curllm-web is already running (PID: 12345)
   Use 'curllm-web stop' to stop it first
```

**Rozwiązanie:**

```bash
curllm-web stop
curllm-web start
# Lub prościej:
curllm-web restart
```

### Problem: Stary PID file

Jeśli proces został zabity z zewnątrz, PID file może pozostać.

**Rozwiązanie:**

```bash
# Usuń stary PID file
rm /tmp/curllm_web.pid

# Uruchom ponownie
curllm-web start
```

### Problem: Port zajęty

```bash
$ curllm-web start
# ... błąd: Address already in use
```

**Rozwiązanie:**

```bash
# Sprawdź co używa portu 5000
lsof -i :5000

# Zabij proces
kill <PID>

# Lub zmień port
export CURLLM_WEB_PORT=5001
curllm-web start
```

## 📊 Porównanie

### Przed (stara wersja):

```bash
# Terminal 1
curllm-web

# Ctrl+C aby zatrzymać
# Brak statusu
# Brak restartu
```

### Po (nowa wersja):

```bash
# Uruchom w tle
curllm-web start

# Sprawdź status
curllm-web status

# Zrestartuj
curllm-web restart

# Zatrzymaj
curllm-web stop
```

## ✅ Korzyści

1. **Wygoda** - Serwer w tle, brak potrzeby dedykowanego terminala
2. **Status** - Szybki podgląd PID, pamięci, portu
3. **Restart** - Łatwa aktualizacja po zmianach w kodzie
4. **Skrypty** - Łatwa automatyzacja i monitoring
5. **Systemd** - Integracja z systemami init

## 🎓 Best Practices

### Development

```bash
# Uruchom w trybie debug
export CURLLM_DEBUG=true
curllm-web start

# Sprawdź logi
tail -f /tmp/curllm-web-start.log
```

### Production

```bash
# Użyj systemd dla auto-restart
sudo systemctl enable curllm-web
sudo systemctl start curllm-web

# Monitoring
sudo systemctl status curllm-web
journalctl -u curllm-web -f
```

### Testing

```bash
# Szybkie iteracje
curllm-web restart && sleep 2 && curl http://localhost:5000/health
```

## 🔄 Migracja

### Z starej wersji:

```bash
# Zatrzymaj stary sposób (Ctrl+C w terminalu)
# Lub:
pkill -f curllm-web

# Uruchom nowym sposobem
curllm-web start
```

### Zachowanie kompatybilności:

```bash
# Nadal działa:
curllm-web

# To jest równoważne:
curllm-web start
```

## 📚 Zobacz też

- [WEB_CLIENT_README.md](WEB_CLIENT_README.md) - Pełna dokumentacja
- [QUICKSTART_WEB.md](QUICKSTART_WEB.md) - Szybki start
- [WEB_CLIENT_FIXES.md](WEB_CLIENT_FIXES.md) - Historia poprawek
