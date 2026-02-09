---
name: top-prospects
description: Money & network candidates — who can write checks and who can connect us to check-writers
---

# /top-prospects — Money & Network Candidates

Query `data/followers.db` to find **who can write checks and who can connect us to people who write checks**. Results are grouped into 4 priority tiers ordered by fundraising capacity and network value — NOT pet/dog alignment.

## Step 1: Run the Queries

Connect to `data/followers.db` using the Bash tool with `sqlite3`. Run all four tier queries below.

### Exclusion Rules (apply to ALL tiers)

Every query MUST exclude:
- `status != 'completed'`
- `category = 'charity'` — nonprofits/charities compete for the same donor dollars
- `category = 'spam_bot'`
- `subcategory = 'school'`
- `subcategory = 'real_estate'`
- `subcategory = 'veterinary'`
- `subcategory IN ('pet_care', 'trainer')`
- `subcategory = 'groomer'`
- `subcategory = 'photographer'` where bio mentions dogs/pets (filter in post-processing)
- Personal dog/pet accounts with no business identity (filter in post-processing)
- `handle = 'sunnyskalihi'` (grocery store, manual exclusion)

Base WHERE clause for all queries:
```sql
WHERE status = 'completed'
  AND category != 'charity'
  AND category != 'spam_bot'
  AND COALESCE(subcategory, '') NOT IN ('school', 'real_estate', 'veterinary', 'pet_care', 'trainer', 'groomer')
  AND handle != 'sunnyskalihi'
```

### TIER 1 — Large Businesses & Elected Officials

**Goal:** Direct donations, corporate sponsorships, legislative advocacy, grant access.

```sql
SELECT handle, display_name, category, subcategory, follower_count,
  is_hawaii, bio, website, profile_url
FROM followers
WHERE status = 'completed'
  AND category != 'charity'
  AND category != 'spam_bot'
  AND COALESCE(subcategory, '') NOT IN ('school', 'real_estate', 'veterinary', 'pet_care', 'trainer', 'groomer')
  AND handle != 'sunnyskalihi'
  AND category IN ('corporate', 'bank_financial', 'business_local', 'business_national', 'elected_official')
ORDER BY follower_count DESC;
```

Post-processing: Remove any results that are clearly personal pet pages miscategorized as businesses. Assess each for: Can they write a check? Can they sponsor an event? Can they open doors to other donors?

### TIER 2 — Organizations with Donor-Class Members

**Goal:** Access to their member/sponsor base who can write checks.

```sql
SELECT handle, display_name, category, subcategory, follower_count,
  is_hawaii, bio, website, profile_url
FROM followers
WHERE status = 'completed'
  AND category = 'organization'
  AND COALESCE(subcategory, '') NOT IN ('school', 'real_estate', 'veterinary', 'pet_care', 'trainer', 'groomer')
  AND handle != 'sunnyskalihi'
ORDER BY follower_count DESC;
```

Post-processing: Exclude dog clubs and pet pages miscategorized as orgs. Focus on orgs whose members are business owners, professionals, or corporate sponsors.

### TIER 3 — Influencers & Media Amplifiers

**Goal:** Social media reach, PR coverage, event documentation, audience access.

```sql
SELECT handle, display_name, category, subcategory, follower_count,
  is_hawaii, bio, website, profile_url
FROM followers
WHERE status = 'completed'
  AND category != 'charity'
  AND category != 'spam_bot'
  AND COALESCE(subcategory, '') NOT IN ('school', 'real_estate', 'veterinary', 'pet_care', 'trainer', 'groomer')
  AND handle != 'sunnyskalihi'
  AND (
    category IN ('influencer', 'media_event')
    OR (category = 'personal_engaged' AND follower_count > 5000)
  )
ORDER BY follower_count DESC;
```

Post-processing: Exclude pure pet/dog photographers and pet influencer pages (check bio for dog/pet-only content with no professional identity). Only keep accounts with professional identity or media reach.

### TIER 4 — Dog-Related Businesses with Revenue >$30k/yr

**Goal:** In-store collection points, co-branded events, customer base overlap.

```sql
SELECT handle, display_name, category, subcategory, follower_count,
  is_hawaii, bio, website, profile_url
FROM followers
WHERE status = 'completed'
  AND category = 'pet_industry'
  AND COALESCE(subcategory, '') NOT IN ('veterinary', 'pet_care', 'trainer', 'groomer', 'photographer', 'school', 'real_estate')
  AND handle != 'sunnyskalihi'
ORDER BY follower_count DESC;
```

Post-processing: Only keep businesses with physical locations, established operations, and clear revenue >$30k/yr. Exclude individual trainers, groomers, walkers, vets, pet sitters, and personal pet pages.

## Step 2: Assess Each Account

For every account in each tier, determine these values by reading the bio, website, follower_count, and category context:

| Field | How to assess |
|-------|--------------|
| **$$ Potential** | Can they write a donation check? `High` = $5k+, `Med` = $1-5k, `Low` = <$1k, `None` = amplification only |
| **Network Value** | Can they connect us to other donors/orgs? `High` = direct access to wealthy network, `Med` = some connections, `Low` = limited network |
| **Best Move** | 1-line recommended outreach action |

## Step 3: Format Output

### For each tier, render a markdown table:

```
## TIER [N] — [Title] ([count] accounts)

| Rank | Handle | Who They Are | Followers | Hawaii | $$ Potential | Network Value | Best Move |
|------|--------|-------------|-----------|--------|-------------|--------------|-----------|
| 1 | [@handle](profile_url) | display_name — 1-line description | follower_count | Y/N | High/Med/Low/None | High/Med/Low | 1-line action |
```

### Known high-value accounts to watch for:

These accounts have been verified as high-value. Make sure they appear in the correct tier and are assessed honestly:

**Tier 1:** hawaiianelectric, hanakoabrewing, vibecreativehawaii, theofficialroute99hawaii, augietulba.hnl, jabbalikespho, inform_hi, teamjacohawaii, pearlhotelwaikiki, repbranco, akamaienergy, fvchawaii, hawaiidisability, hondahawaiiguy, premiumincorporated

**Tier 2:** fishcakehawaii, sonyopenhawaii, shinnyolanternfloatinghawaii, northshoresurfgirls, rotaryeclubhi, rceasthonolulu

**Tier 3:** leilahurst, yafavoritelatinaa, imjakeacedo, michaelsunlee, im.alexis.renae, thecoconutpages, mrjasontom, adriennearieff, kanter, sunny_aloha_in_paradise, finnowitz, pono_shell_creations

**Tier 4:** thepublicpet, fureverfriendshi, kamaainak9, tailshawaii

### End with: Top 5 Actions

After all tier tables, add:

```
## Top 5 Actions — Highest ROI Moves

1. **[Action]** — [Handle] — [Why this is highest ROI]
2. ...
3. ...
4. ...
5. ...
```

These should be the 5 single highest-ROI outreach moves across all tiers, considering donation capacity, network access, and ease of approach.

## Optional Filters (from user arguments)
- `--tier <N>` — show only the specified tier (1-4)
- `--hawaii` — only show `is_hawaii = 1`
- `--limit <N>` — limit accounts per tier (default: no limit)
