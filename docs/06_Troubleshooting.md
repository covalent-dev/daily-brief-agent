# Troubleshooting

## Ollama not running
- Start: `ollama serve`
- Verify model: `ollama list`

## Model not found
- Install: `ollama pull <model>`

## No articles
- Check RSS URLs
- Increase `filter_hours`
- Inspect `output/brief.log`

## Launchd not running
- Ensure plist is in `~/Library/LaunchAgents/`
- Reload: `launchctl unload ...` then `launchctl load ...`
