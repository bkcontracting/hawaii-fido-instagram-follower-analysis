# Enrichment Script - Usage Guide

## Quick Start (No Changes Needed)

The script works exactly as before with default reconnection settings:

```bash
# Basic usage (30-min reconnection, 100 profiles per reconnection)
python3 scripts/enrich.py

# Dry run (test with 1 profile)
python3 scripts/enrich.py --dry-run
```

## New Command-Line Options

### `--reconnect-minutes` (default: 30)
Reconnect browser after N minutes of operation.

```bash
# Reconnect every 15 minutes
python3 scripts/enrich.py --reconnect-minutes 15

# Reconnect every 60 minutes (longer-lived connections)
python3 scripts/enrich.py --reconnect-minutes 60

# Aggressive testing: reconnect every 2 minutes
python3 scripts/enrich.py --dry-run 20 --reconnect-minutes 2
```

### `--reconnect-count` (default: 100)
Reconnect browser after fetching N profiles.

```bash
# Reconnect every 50 profiles
python3 scripts/enrich.py --reconnect-count 50

# Reconnect every 200 profiles
python3 scripts/enrich.py --reconnect-count 200

# For testing: reconnect every 5 profiles
python3 scripts/enrich.py --dry-run 10 --reconnect-count 5
```

### `--page-timeout` (default: 30)
Set page operation timeout in seconds.

```bash
# Increase timeout to 45 seconds (for slow internet)
python3 scripts/enrich.py --page-timeout 45

# Decrease to 20 seconds (for faster networks)
python3 scripts/enrich.py --page-timeout 20
```

## Common Usage Patterns

### Pattern 1: Quick Testing
Test the new reconnection logic without long waits:

```bash
python3 scripts/enrich.py --dry-run 10 --reconnect-minutes 2 --reconnect-count 5
```

**What to look for in output:**
```
Dry run: fetching 10 profile(s)

  [1/10] @user1 — completed (1234 followers)
Reconnecting browser (reason: age (120s > 120s))...
  [2/10] @user2 — completed (5678 followers)
...
[DRY RUN] No database changes were made.
```

### Pattern 2: Long-Running Enrichment (Default)
Process all pending profiles with default reconnection:

```bash
python3 scripts/enrich.py
```

**Expected behavior:**
- Reconnects every 30 minutes OR every 100 profiles (whichever comes first)
- Can run for 2+ hours on 800+ profiles without crashing
- Memory usage stays bounded

### Pattern 3: Conservative Reconnection
For very large databases, reconnect more frequently:

```bash
python3 scripts/enrich.py --reconnect-minutes 20 --reconnect-count 50
```

**Benefits:**
- More frequent connection refresh
- Lower memory usage per connection
- Better resilience to temporary network issues

### Pattern 4: Aggressive Long Connections
For stable networks, use longer connection lifespan:

```bash
python3 scripts/enrich.py --reconnect-minutes 60 --reconnect-count 200
```

**Benefits:**
- Fewer reconnection interruptions
- Slightly faster overall (fewer connection overhead)
- Still safe up to 2+ hours of operation

## Monitoring Output

### Success Indicators
Look for these patterns in the output:

```bash
# Normal operation
  [15/200] @influencer1 — completed (50000 followers)
  [16/200] @influencer2 — completed (75000 followers)
  [17/200] @influencer3 — private

# Proactive reconnection (time-based)
Reconnecting browser (reason: age (1800s > 1800s))...

# Proactive reconnection (count-based)
Reconnecting browser (reason: operations (100 >= 100))...

# Error recovery
  CDP error on @user123, reconnecting: browser is closed
Reconnecting browser (reason: error)...
  [45/200] @user123 — completed (12345 followers)
```

### Warning Signs
- ❌ Long pause (30+ seconds) without reconnection message = hung page (may timeout)
- ❌ "CDP error" repeated without reconnection = non-recoverable error
- ❌ Memory usage growing beyond 500MB = possible cache leak

## Advanced Tuning

### For Slow/Unreliable Networks
```bash
python3 scripts/enrich.py \
  --page-timeout 60 \
  --reconnect-minutes 15 \
  --reconnect-count 50
```

### For Fast/Stable Networks
```bash
python3 scripts/enrich.py \
  --page-timeout 20 \
  --reconnect-minutes 45 \
  --reconnect-count 150
```

### For Very Large Databases (800+)
```bash
python3 scripts/enrich.py \
  --reconnect-minutes 30 \
  --reconnect-count 80 \
  --page-timeout 35
```

## Troubleshooting

### Issue: Script crashes after 40 minutes
**Solution:** You're running the old version. Update to use the new `BrowserConnectionManager` by running the latest `scripts/enrich.py`.

### Issue: "CDP error" messages appear frequently
**Cause:** Connection instability or Chrome hanging
**Solution:** Increase `--page-timeout` and decrease `--reconnect-count`:
```bash
python3 scripts/enrich.py --page-timeout 45 --reconnect-count 50
```

### Issue: Script runs slowly
**Cause:** Frequent reconnections
**Solution:** Increase reconnection thresholds:
```bash
python3 scripts/enrich.py --reconnect-minutes 45 --reconnect-count 150
```

### Issue: Memory usage is high (> 500MB)
**Cause:** Connection living too long
**Solution:** Force more frequent reconnections:
```bash
python3 scripts/enrich.py --reconnect-minutes 20 --reconnect-count 50
```

## Backward Compatibility

All new arguments have defaults that provide safe, reasonable behavior:
- `--reconnect-minutes 30` (safe 30-minute interval)
- `--reconnect-count 100` (safe after 100 profiles)
- `--page-timeout 30` (30-second timeout for pages)

**Old scripts continue to work unchanged:**
```bash
# This still works exactly as before
python3 scripts/enrich.py --db data/followers.db --delay-min 3 --delay-max 5 --dry-run 5
```

## How to Know It's Working

Run this test command:

```bash
python3 scripts/enrich.py --dry-run 5 --reconnect-minutes 1 --reconnect-count 2
```

**Expected output:**
```
Dry run: fetching 5 profile(s)

  [1/5] @user1 — completed (1234 followers)
Reconnecting browser (reason: age (60s > 60s))...
  [2/5] @user2 — completed (5678 followers)
Reconnecting browser (reason: operations (2 >= 2))...
  [3/5] @user3 — private
Reconnecting browser (reason: age (60s > 60s))...
  [4/5] @user4 — completed (9000 followers)
Reconnecting browser (reason: operations (2 >= 2))...
  [5/5] @user5 — completed (3000 followers)

[DRY RUN] No database changes were made.
```

If you see "Reconnecting browser" messages appearing at expected intervals, the fix is working correctly!
