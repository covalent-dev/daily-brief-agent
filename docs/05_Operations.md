# Operations

## Running Manually
```bash
python3 src/brief.py
```

## Scheduling (macOS launchd)
```bash
chmod +x scripts/run_daily_brief.sh
cp scripts/com.covalent.daily-brief.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.covalent.daily-brief.plist
```

## Logs
- `output/brief.log`
- `output/launchd.log`
- `output/launchd.err.log`

## Cache
- `output/cache.json` (1 hour TTL)
