#!/usr/bin/env python3
"""Preprocess GymRats challenge JSON into Hugo data files."""

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

RESOURCES_DIR = os.path.join(os.path.dirname(__file__), "..", "resources")
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
INPUT_FILE = os.path.join(RESOURCES_DIR, "challenge-data.json")

SEASON_POINTS = {
    1: 10000, 2: 8500, 3: 7500, 4: 6500, 5: 5500,
    6: 5000, 7: 4500, 8: 4000, 9: 3500, 10: 3000,
}

ACTIVITY_NAMES = {
    "strength_training": "Musculação",
    "running": "Corrida",
    "walking": "Caminhada",
    "surfing": "Surfe",
    "calisthenics": "Calistenia",
    "gymnastics": "Ginástica",
    "functional_training": "Funcional",
    "swimming": "Natação",
    "hiking": "Trilha",
    "volleyball": "Vôlei",
    "cycling": "Ciclismo",
    "cardio": "Cardio",
    "snow_sports": "Esportes de Neve",
    "rec_sport": "Esporte Recreativo",
    "other": "Outros",
}

# Merge similar activities into a single category
ACTIVITY_MERGE = {
    "treadmill": "running",
    "pilates": "gymnastics",
    "yoga": "gymnastics",
    "spinning": "cycling",
    "mountain_bike": "cycling",
    "stationary_bike": "cycling",
    "circuit_training": "functional_training",
    "hiit": "cardio",
    "mixed_cardio": "cardio",
    "elliptical": "cardio",
    "rowing": "cardio",
    "water_aerobics": "swimming",
}

# Patterns checked in order (first match wins).
TITLE_RULES = [
    (r"surf|aurf|mei metr", "surfing"),
    (r"calist|calixt|calista|cabe[çc]a pra baixo", "calisthenics"),
    (r"pilat", "pilates"),
    (r"snowboard|snow sport", "snow_sports"),
    (r"spinning", "spinning"),
    (r"tabata|hi[i]t|hitt", "hiit"),
    (r"funcional|condicionamento", "functional_training"),
    (r"circuito", "circuit_training"),
    (r"nata[cç]", "swimming"),
    (r"volei|vôlei", "volleyball"),
    (r"trilha|cachoeira", "hiking"),
    (r"encontro com as amiga|escorrega|aurora.*tocantins", "mountain_bike"),
    (r"pedal|ciclism", "cycling"),
    (r"altinha|skate|skatim|futebol|futzi|futz|canoa|rafting", "rec_sport"),
    (r"corri|corrida|corridinha|corridex|correndo|pace \d|\d+\s*km"
     r"|morro a(cima|rriba)|strava|fumal|🏃", "running"),
    (r"caminh|andando|só anda|chuva mesmo", "walking"),
    (r"muscula|malh|gym|pern[aix]|glut|posterior|bra[cç]o|b[ií]ceps"
     r"|tr[ií]ceps|ombro|costas|abdom|🏋|feio", "strength_training"),
    (r"c[aá]rdio|bike|esteira|ergom", "mixed_cardio"),
    (r"trein|ed[\.\s]*f[ií]sica", "strength_training"),
]

# Per-member: remap an already-classified activity to another
MEMBER_REMAP_BY_NAME = {
    "Luan Guimarães": {"strength_training": "calisthenics"},
    "Pedro": {"surfing": "rec_sport"},
}

# Per-member: fallback activity when nothing else matches
MEMBER_FALLBACK_BY_NAME = {
    "Luan Guimarães": "surfing",
    "Beatriz Franco": "surfing",
    "Guilherme Guimarães Lacerda": "calisthenics",
    "Anyne Vilhardo": "strength_training",
    "Aryane Vilhardo Guimarães": "strength_training",
    "Isadora": "strength_training",
    "José Vitor Guimarães": "rec_sport",
    "Nedma Guimarães": "walking",
    "Nelia": "running",
}

NAME_OVERRIDES = {
    "luang": "Luan Guimarães",
}

MONTH_NAMES = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr"}


def load_data():
    with open(INPUT_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_json(filename, data):
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  {filename}")


IANA_TO_OFFSET = {
    "America/Sao_Paulo": -3,
    "America/Araguaina": -3,
    "America/New_York": -5,
    "America/Panama": -5,
    "Europe/Lisbon": 0,
}


def resolve_tz(tz_str):
    if not tz_str:
        return timezone(timedelta(hours=-3))
    if tz_str in IANA_TO_OFFSET:
        return timezone(timedelta(hours=IANA_TO_OFFSET[tz_str]))
    m = re.match(r"^([+-])(\d{2}):(\d{2})$", tz_str)
    if m:
        sign = 1 if m.group(1) == "+" else -1
        hours = int(m.group(2)) * sign
        mins = int(m.group(3)) * sign
        return timezone(timedelta(hours=hours, minutes=mins))
    return timezone(timedelta(hours=-3))


def parse_date(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def merge_sessions(checkins, gap_minutes=30):
    """Merge check-ins that start within gap_minutes of the previous end."""
    by_account = defaultdict(list)
    for ci in checkins:
        by_account[ci["account_id"]].append(ci)

    merged = []
    for aid, cis in by_account.items():
        cis.sort(key=lambda c: c["occurred_at"])
        groups = [[cis[0]]]
        for ci in cis[1:]:
            prev = groups[-1][-1]
            prev_start = parse_date(prev["occurred_at"])
            prev_dur = prev.get("duration_millis") or 0
            prev_end = prev_start + timedelta(milliseconds=prev_dur)
            curr_start = parse_date(ci["occurred_at"])
            gap = (curr_start - prev_end).total_seconds() / 60
            if 0 <= gap < gap_minutes:
                groups[-1].append(ci)
            else:
                groups.append([ci])

        for group in groups:
            if len(group) == 1:
                merged.append(group[0])
            else:
                first = dict(group[0])
                first["duration_millis"] = sum(
                    c.get("duration_millis") or 0 for c in group
                )
                all_acts = []
                all_media = []
                for c in group:
                    all_acts.extend(c.get("check_in_activities") or [])
                    all_media.extend(c.get("check_in_media") or [])
                first["check_in_activities"] = all_acts
                first["check_in_media"] = all_media
                merged.append(first)

    return merged


def compute_streak(dates_sorted):
    if not dates_sorted:
        return 0
    max_streak = 1
    cur = 1
    for i in range(1, len(dates_sorted)):
        d1 = datetime.strptime(dates_sorted[i - 1], "%Y-%m-%d")
        d2 = datetime.strptime(dates_sorted[i], "%Y-%m-%d")
        if (d2 - d1).days == 1:
            cur += 1
            max_streak = max(max_streak, cur)
        else:
            cur = 1
    return max_streak


def _classify_from_title(title):
    t = title.lower()
    for pattern, activity in TITLE_RULES:
        if re.search(pattern, t):
            return activity
    return None


def classify_activity(checkin, member_remap, member_fallback):
    title = (checkin.get("title") or "").strip()
    acts = checkin.get("check_in_activities") or []
    pa = None
    for a in acts:
        pa = a.get("platform_activity") or None

    if pa and pa != "other":
        result = member_remap.get(pa, pa)
    elif (from_title := _classify_from_title(title)):
        result = member_remap.get(from_title, from_title)
    else:
        fallback = member_fallback or "other"
        result = member_remap.get(fallback, fallback)

    return ACTIVITY_MERGE.get(result, result)


def translate_activity(key):
    return ACTIVITY_NAMES.get(key, key.replace("_", " ").title())


def process_members(raw):
    members = {}
    for m in raw["members"]:
        name = NAME_OVERRIDES.get(m["full_name"], m["full_name"])
        members[m["id"]] = {
            "id": m["id"],
            "name": name,
            "short_name": name.split()[0],
            "profile_picture_url": m.get("profile_photo") or "",
        }
    # Disambiguate duplicate short_names
    short_counts = Counter(m["short_name"] for m in members.values())
    for m in members.values():
        if short_counts[m["short_name"]] > 1:
            parts = m["name"].split()
            if len(parts) >= 2:
                m["short_name"] = f"{parts[0]} {parts[1][0]}."
    return members


def process_all(raw):
    members = process_members(raw)
    checkins = merge_sessions(raw["check_ins"])

    # Build per-account remap and fallback dicts
    name_to_id = {m["name"]: aid for aid, m in members.items()}
    account_remap = {}
    account_fallback = {}
    for name, remap in MEMBER_REMAP_BY_NAME.items():
        if name in name_to_id:
            account_remap[name_to_id[name]] = remap
    for name, fallback in MEMBER_FALLBACK_BY_NAME.items():
        if name in name_to_id:
            account_fallback[name_to_id[name]] = fallback

    # Per-member aggregations
    account_days = defaultdict(set)
    account_checkins = Counter()
    account_duration = defaultdict(int)
    account_duration_count = defaultdict(int)
    account_activities = defaultdict(Counter)
    account_monthly_days = defaultdict(lambda: defaultdict(set))
    account_photos = Counter()
    activity_metric_sums = {}
    sport_checkin_metrics = []
    account_times = defaultdict(list)
    daily_counts = Counter()
    global_duration_sum = 0
    global_duration_count = 0
    no_duration_checkins = []

    for ci in checkins:
        aid = ci["account_id"]
        occ_dt = parse_date(ci["occurred_at"])
        tz = resolve_tz(ci.get("timezone"))
        local_dt = occ_dt.astimezone(tz)
        occ_date = local_dt.strftime("%Y-%m-%d")

        account_days[aid].add(occ_date)
        account_checkins[aid] += 1
        daily_counts[occ_date] += 1

        month = local_dt.month
        account_monthly_days[aid][month].add(occ_date)

        dur = ci.get("duration_millis") or 0
        if dur > 0:
            account_duration[aid] += dur
            account_duration_count[aid] += 1
            global_duration_sum += dur
            global_duration_count += 1
        else:
            no_duration_checkins.append(aid)

        remap = account_remap.get(aid, {})
        fallback = account_fallback.get(aid)
        activity = classify_activity(ci, remap, fallback)
        account_activities[aid][activity] += 1

        # Collect per-activity metrics for sport details
        ci_dist = 0
        try:
            ci_dist = float(ci.get("distance_miles") or 0) * 1.60934
        except (ValueError, TypeError):
            pass
        ci_cal = 0
        try:
            ci_cal = float(ci.get("calories") or 0)
        except (ValueError, TypeError):
            pass
        ci_dur_h = dur / 3600000 if dur > 0 else 0

        # Track raw values and missing counts per activity type
        if activity not in activity_metric_sums:
            activity_metric_sums[activity] = {
                "dist_sum": 0, "dist_n": 0,
                "cal_sum": 0, "cal_n": 0,
                "dur_sum": 0, "dur_n": 0,
            }
        ams = activity_metric_sums[activity]
        if ci_dist > 0:
            ams["dist_sum"] += ci_dist
            ams["dist_n"] += 1
        if ci_cal > 0:
            ams["cal_sum"] += ci_cal
            ams["cal_n"] += 1
        if ci_dur_h > 0:
            ams["dur_sum"] += ci_dur_h
            ams["dur_n"] += 1

        sport_checkin_metrics.append({
            "aid": aid,
            "activity": activity,
            "dist_km": ci_dist,
            "calories": ci_cal,
            "hours": ci_dur_h,
        })

        media = ci.get("check_in_media") or []
        account_photos[aid] += len(media)

        account_times[aid].append(local_dt.hour + local_dt.minute / 60.0)

    # Backfill duration for check-ins without one using global average
    if global_duration_count > 0:
        avg_duration = global_duration_sum / global_duration_count
        for aid in no_duration_checkins:
            account_duration[aid] += avg_duration

    # Backfill sport metrics: estimate missing values using per-activity averages
    # Compute per-activity averages; only backfill a metric if at least
    # 10% of that activity's check-ins had real values for it.
    activity_totals = Counter()
    for scm in sport_checkin_metrics:
        activity_totals[scm["activity"]] += 1

    activity_avgs = {}
    for act, sums in activity_metric_sums.items():
        total = activity_totals.get(act, 1)
        activity_avgs[act] = {
            "dist_km": sums["dist_sum"] / sums["dist_n"] if sums["dist_n"] / total >= 0.1 else 0,
            "calories": sums["cal_sum"] / sums["cal_n"] if sums["cal_n"] / total >= 0.1 else 0,
            "hours": sums["dur_sum"] / sums["dur_n"] if sums["dur_n"] / total >= 0.1 else 0,
        }

    # Aggregate per (aid, activity) with backfill
    account_sport_metrics = {}
    for scm in sport_checkin_metrics:
        aid = scm["aid"]
        act = scm["activity"]
        key = (aid, act)
        if key not in account_sport_metrics:
            account_sport_metrics[key] = {
                "count": 0, "dist_km": 0, "calories": 0, "hours": 0,
            }
        m_sport = account_sport_metrics[key]
        m_sport["count"] += 1
        avgs = activity_avgs.get(act, {})
        m_sport["dist_km"] += scm["dist_km"] if scm["dist_km"] > 0 else avgs.get("dist_km", 0)
        m_sport["calories"] += scm["calories"] if scm["calories"] > 0 else avgs.get("calories", 0)
        m_sport["hours"] += scm["hours"] if scm["hours"] > 0 else avgs.get("hours", 0)

    # Ranking by unique days (with tie handling)
    day_counts = [(aid, len(days)) for aid, days in account_days.items()]
    day_counts.sort(key=lambda x: x[1], reverse=True)

    ranking = []
    pos = 1
    i = 0
    while i < len(day_counts):
        # Find all tied at this count
        tied = [day_counts[i]]
        j = i + 1
        while j < len(day_counts) and day_counts[j][1] == day_counts[i][1]:
            tied.append(day_counts[j])
            j += 1

        points = SEASON_POINTS.get(pos, 0)
        if pos > 10:
            for aid, days in tied:
                if days >= 10:
                    points = 2500
                else:
                    points = 0

        for aid, days in tied:
            m = members.get(aid, {})
            sorted_dates = sorted(account_days[aid])
            streak = compute_streak(sorted_dates)
            total_hours = round(account_duration[aid] / 3600000, 1)

            top_acts = account_activities[aid].most_common(3)
            top_activities = [
                {"name": translate_activity(a), "count": c} for a, c in top_acts
            ]

            monthly = {}
            for mn, label in MONTH_NAMES.items():
                monthly[label] = len(account_monthly_days[aid].get(mn, set()))

            act_pts = points
            if pos > 10 and days >= 10:
                act_pts = 2500
            elif pos > 10:
                act_pts = 0

            ranking.append({
                "position": pos,
                "name": m.get("name", f"id={aid}"),
                "short_name": m.get("short_name", ""),
                "account_id": aid,
                "unique_days": days,
                "checkins": account_checkins[aid],
                "points": act_pts,
                "streak": streak,
                "total_hours": total_hours,
                "monthly": monthly,
                "top_activities": top_activities,
                "activity_variety": len(account_activities[aid]),
                "photos": account_photos[aid],
            })

        pos = j + 1
        i = j

    # Fix positions for display (tied members share the same position)
    # Re-number: after a tie of N, next position is current + N
    display_pos = 1
    idx = 0
    while idx < len(ranking):
        current_days = ranking[idx]["unique_days"]
        tie_count = sum(1 for r in ranking if r["unique_days"] == current_days)
        for k in range(idx, idx + tie_count):
            ranking[k]["position"] = display_pos
        display_pos += tie_count
        idx += tie_count

    save_json("ranking.json", ranking)

    # Members list
    members_list = sorted(members.values(), key=lambda m: m["name"])
    save_json("members.json", members_list)

    # Activities global
    global_acts = Counter()
    for aid_acts in account_activities.values():
        for act, cnt in aid_acts.items():
            global_acts[act] += cnt

    activities = [
        {"name": translate_activity(a), "key": a, "count": c}
        for a, c in global_acts.most_common()
    ]
    save_json("activities.json", activities)

    # Timeline (daily total check-ins)
    start = datetime(2026, 1, 5)
    end = datetime(2026, 4, 15)
    timeline = []
    d = start
    while d <= end:
        ds = d.strftime("%Y-%m-%d")
        timeline.append({"date": ds, "count": daily_counts.get(ds, 0)})
        d += timedelta(days=1)
    save_json("timeline.json", timeline)

    # Heatmap (calendar-style: weeks as columns, weekdays as rows)
    heatmap_weeks = []
    week_start = start - timedelta(days=start.weekday())  # rewind to Monday
    last_month = None
    while week_start <= end:
        week_label = ""
        days = []
        for wd in range(7):
            day = week_start + timedelta(days=wd)
            ds = day.strftime("%Y-%m-%d")
            if day < start or day > end:
                days.append({"date": "", "count": 0, "empty": True})
            else:
                days.append({
                    "date": ds,
                    "count": daily_counts.get(ds, 0),
                    "empty": False,
                })
                if day.month != last_month:
                    week_label = MONTH_NAMES.get(day.month, "")
                    last_month = day.month
        heatmap_weeks.append({"days": days, "month_label": week_label})
        week_start += timedelta(days=7)

    save_json("heatmap.json", {
        "weeks": heatmap_weeks,
        "weekday_labels": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"],
    })

    # Race data (cumulative unique days per member, sampled weekly)
    top_members = ranking[:10]
    race = {"labels": [], "datasets": []}
    week_dates = []
    d = start
    while d <= end:
        week_dates.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=7)
    if week_dates[-1] != end.strftime("%Y-%m-%d"):
        week_dates.append(end.strftime("%Y-%m-%d"))

    race["labels"] = [datetime.strptime(wd, "%Y-%m-%d").strftime("%d/%m") for wd in week_dates]

    colors = [
        "#E6B800", "#C0C0C0", "#CD7F32", "#2563EB", "#DC2626",
        "#059669", "#7C3AED", "#EA580C", "#0891B2", "#DB2777",
    ]
    for idx, r in enumerate(top_members):
        aid = r["account_id"]
        days_set = account_days[aid]
        cumulative = []
        for wd in week_dates:
            count = sum(1 for day in days_set if day <= wd)
            cumulative.append(count)
        race["datasets"].append({
            "label": r["short_name"],
            "data": cumulative,
            "color": colors[idx % len(colors)],
        })
    save_json("race.json", race)

    # Weekdays
    weekday_names = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]
    weekday_counts = Counter()
    for ci in checkins:
        dt = parse_date(ci["occurred_at"])
        tz = resolve_tz(ci.get("timezone"))
        weekday_counts[dt.astimezone(tz).weekday()] += 1
    weekdays = [{"day": weekday_names[i], "count": weekday_counts[i]} for i in range(7)]
    save_json("weekdays.json", weekdays)

    # Monthly (per-member, for grouped bar chart)
    monthly_data = {"labels": list(MONTH_NAMES.values()), "datasets": []}
    for r in ranking[:10]:
        aid = r["account_id"]
        monthly_data["datasets"].append({
            "label": r["short_name"],
            "data": [len(account_monthly_days[aid].get(mn, set())) for mn in MONTH_NAMES],
        })
    save_json("monthly.json", monthly_data)

    # Highlights
    busiest_date = max(daily_counts, key=daily_counts.get) if daily_counts else ""
    total_hours_all = sum(account_duration.values()) / 3600000
    highlights = {
        "total_checkins": len(checkins),
        "total_days": (end - start).days + 1,
        "total_competitors": len(members),
        "total_unique_exercise_days": sum(len(d) for d in account_days.values()),
        "total_hours": round(total_hours_all, 0),
        "busiest_date": busiest_date,
        "busiest_date_count": daily_counts.get(busiest_date, 0),
        "most_popular_activity": translate_activity(global_acts.most_common(1)[0][0]),
        "most_popular_activity_count": global_acts.most_common(1)[0][1],
        "champions_tied": ranking[0]["unique_days"] == ranking[1]["unique_days"] if len(ranking) > 1 else False,
    }
    save_json("highlights.json", highlights)

    # Awards: true leaders per category. Everyone must appear at least once.
    awards = []
    awarded = set()

    def award(emoji, title, winner_name, description):
        awards.append({
            "emoji": emoji, "title": title,
            "winner": winner_name, "description": description,
        })
        for n in winner_name.split(" e "):
            awarded.add(n.strip())

    def top_activity_member(activity_key):
        """Return (short_name, count) of the member with most sessions."""
        best_name, best_cnt = None, 0
        for aid, acts in account_activities.items():
            cnt = acts.get(activity_key, 0)
            if cnt > best_cnt:
                best_cnt = cnt
                best_name = members.get(aid, {}).get("short_name", "?")
        return best_name, best_cnt

    # --- Merit awards (always go to the true leader) ---

    # Campeão(ã) do Verão
    champ_days = ranking[0]["unique_days"]
    champs = [r for r in ranking if r["unique_days"] == champ_days]
    if len(champs) > 1:
        award("🏆", "Campeões do Verão",
              " e ".join(r["short_name"] for r in champs),
              f"Empatados com {champ_days} dias de exercício!")
    else:
        award("🏆", "Campeão do Verão", champs[0]["short_name"],
              f"{champ_days} dias de exercício na estação.")

    # Máquina de Sequência
    top_streak = max(r["streak"] for r in ranking)
    streak_winners = [r for r in ranking if r["streak"] == top_streak]
    award("🔥", "Máquina de Sequência",
          " e ".join(r["short_name"] for r in streak_winners),
          f"{top_streak} dias seguidos sem parar!")

    # Maratonista (mais horas)
    best = max(ranking, key=lambda r: r["total_hours"])
    award("⏱️", "Maratonista", best["short_name"],
          f"{best['total_hours']}h de treino na estação.")

    # Fotógrafo(a) Oficial (mais fotos)
    best = max(ranking, key=lambda r: r["photos"])
    award("📸", "Fotógrafo(a) Oficial", best["short_name"],
          f"{best['photos']} fotos compartilhadas com o grupo.")

    # Eclético(a) (mais variedade)
    best = max(ranking, key=lambda r: r["activity_variety"])
    award("🎯", "Eclético(a)", best["short_name"],
          f"{best['activity_variety']} tipos de atividades diferentes.")

    # Rainha/Rei do Ferro (musculação)
    name, cnt = top_activity_member("strength_training")
    if name:
        award("🏋️", "Rainha do Ferro", name,
              f"{cnt} sessões de musculação na estação.")

    # Surfista
    name, cnt = top_activity_member("surfing")
    if name:
        award("🏄", "Alma de Surfista", name,
              f"{cnt} sessões de surfe. Sal na veia!")

    # Corredor(a)
    name, cnt = top_activity_member("running")
    if name:
        award("🏃", "Sola de Vento", name,
              f"{cnt} sessões de corrida. Não para!")

    # Tagarela (mais mensagens no chat)
    msg_counts = Counter()
    for msg in raw.get("messages", []):
        aid = msg.get("account_id")
        if msg.get("message_type") == "text" and aid in members:
            msg_counts[aid] += 1
    if msg_counts:
        top_aid, top_cnt = msg_counts.most_common(1)[0]
        award("💬", "Tagarela",
              members.get(top_aid, {}).get("short_name", "?"),
              f"{top_cnt} mensagens no chat do grupo.")

    # Madrugador(a) e Noturno(a)
    earliest_aid, earliest_time = None, 24.0
    latest_aid, latest_time = None, 0.0
    for aid, times in account_times.items():
        if len(times) >= 5:
            avg = sum(times) / len(times)
            if avg < earliest_time:
                earliest_time, earliest_aid = avg, aid
            if avg > latest_time:
                latest_time, latest_aid = avg, aid
    if earliest_aid:
        name = members.get(earliest_aid, {}).get("short_name", "?")
        h, m_val = int(earliest_time), int((earliest_time % 1) * 60)
        award("🌅", "Madrugador(a)", name,
              f"Média de check-in às {h:02d}:{m_val:02d}.")
    if latest_aid:
        name = members.get(latest_aid, {}).get("short_name", "?")
        h, m_val = int(latest_time), int((latest_time % 1) * 60)
        award("🌙", "Noturno(a)", name,
              f"Média de check-in às {h:02d}:{m_val:02d}.")

    # Multitarefa (mais atividades em um dia)
    day_checkins_per_account = defaultdict(lambda: defaultdict(int))
    for ci in checkins:
        aid = ci["account_id"]
        dt = parse_date(ci["occurred_at"])
        tz = resolve_tz(ci.get("timezone"))
        local_date = dt.astimezone(tz).strftime("%Y-%m-%d")
        day_checkins_per_account[aid][local_date] += 1
    max_in_day, max_aid = 0, None
    for aid, days in day_checkins_per_account.items():
        for _, cnt in days.items():
            if cnt > max_in_day:
                max_in_day, max_aid = cnt, aid
    if max_aid:
        award("💪", "Multitarefa",
              members.get(max_aid, {}).get("short_name", "?"),
              f"{max_in_day} atividades registradas em um único dia!")

    # Constância de Ferro (menor variância mensal, mín 30 dias)
    consistent = []
    for r in ranking:
        if r["unique_days"] >= 30:
            vals = list(r["monthly"].values())
            avg = sum(vals) / len(vals)
            var = sum((v - avg) ** 2 for v in vals) / len(vals)
            consistent.append((r, var))
    if consistent:
        consistent.sort(key=lambda x: x[1])
        award("📊", "Constância de Ferro", consistent[0][0]["short_name"],
              "Treinou de forma mais regular ao longo de toda a estação.")

    # --- Ensure everyone has at least one award ---
    # Personalized awards for everyone still missing.
    # Each title is unique even within the same tier.
    titles_top = [
        ("🥷", "Atleta Completo(a)", "Faz de tudo e faz bem."),
        ("🦾", "Incansável", "Não lidera uma categoria, lidera todas um pouco."),
        ("🫡", "Soldado da Disciplina", "Presente em campo, chuva ou sol."),
    ]
    titles_mid = [
        ("🎖️", "Guerreiro(a) Silencioso(a)", "Fala pouco, faz muito."),
        ("🐢", "Devagar e Sempre", "No ritmo dele(a), chega lá."),
    ]
    titles_low = [
        ("🌱", "Semente Plantada", "A semente foi plantada, falta regar!"),
    ]
    titles_couch = [
        ("🛋️", "Participou... do Sofá", "O sofá agradece a companhia."),
        ("📱", "Torcida de Casa", "Acompanhou de longe, mas o espírito estava lá."),
        ("👻", "Lenda Urbana", "Dizem que participou, mas ninguém viu."),
    ]

    uncovered = [r for r in ranking if r["short_name"] not in awarded]
    top_idx = mid_idx = low_idx = couch_idx = 0

    for r in uncovered:
        name = r["short_name"]
        days = r["unique_days"]

        if days >= 60:
            emoji, title, phrase = titles_top[top_idx % len(titles_top)]
            desc = f"{days} dias, {r['activity_variety']} modalidades. {phrase}"
            top_idx += 1
        elif days >= 20:
            emoji, title, phrase = titles_mid[mid_idx % len(titles_mid)]
            desc = f"{days} dias de treino. {phrase}"
            mid_idx += 1
        elif days >= 10:
            emoji, title, phrase = titles_low[low_idx % len(titles_low)]
            desc = f"{days} dias. {phrase}"
            low_idx += 1
        else:
            emoji, title, phrase = titles_couch[couch_idx % len(titles_couch)]
            desc = f"{days} dias em 101. {phrase}"
            couch_idx += 1

        award(emoji, title, name, desc)

    save_json("awards.json", awards)

    # Per-activity leaderboards
    activity_leaders = {}
    for aid, acts in account_activities.items():
        for act, cnt in acts.items():
            key = translate_activity(act)
            if key not in activity_leaders:
                activity_leaders[key] = []
            activity_leaders[key].append({
                "name": members.get(aid, {}).get("short_name", "?"),
                "count": cnt,
            })
    for key in activity_leaders:
        activity_leaders[key].sort(key=lambda x: x["count"], reverse=True)
        activity_leaders[key] = activity_leaders[key][:5]
    save_json("activity_leaders.json", activity_leaders)

    # Sport spotlight: top athletes in key sports
    spotlight_sports = [
        ("Corrida", "🏃", "Maiores Corredores"),
        ("Musculação", "🏋️", "Maiores Marombas"),
        ("Surfe", "🏄", "Maiores Surfistas"),
        ("Natação", "🏊", "Maiores Nadadores"),
        ("Ciclismo", "🚴", "Maiores Ciclistas"),
    ]
    sport_spotlights = []
    for key, emoji, title in spotlight_sports:
        if key in activity_leaders and activity_leaders[key]:
            sport_spotlights.append({
                "key": key,
                "emoji": emoji,
                "title": title,
                "athletes": activity_leaders[key][:5],
            })
    save_json("sport_spotlights.json", sport_spotlights)

    # Sport detail pages: per-sport stats with per-member breakdown
    # Map translated name back to internal key
    name_to_key = {v: k for k, v in ACTIVITY_NAMES.items()}
    # Also handle merged activities
    merge_map = getattr(__import__(__name__), "ACTIVITY_MERGE", {}) if False else {}
    # Get ACTIVITY_MERGE from module scope
    try:
        from __main__ import ACTIVITY_MERGE as _am
    except ImportError:
        _am = globals().get("ACTIVITY_MERGE", {})

    # Reverse: for each target sport, collect all source keys that map to it
    sport_source_keys = defaultdict(set)
    for src, tgt in _am.items():
        sport_source_keys[tgt].add(src)
    # Each sport also includes itself
    for key in ACTIVITY_NAMES:
        sport_source_keys[key].add(key)

    sport_detail_configs = [
        ("running", "🏃", "Corrida", ["dist_km", "hours", "calories", "count"]),
        ("strength_training", "🏋️", "Musculação", ["hours", "calories", "count"]),
        ("surfing", "🏄", "Surfe", ["hours", "count"]),
        ("swimming", "🏊", "Natação", ["dist_km", "hours", "calories", "count"]),
        ("cycling", "🚴", "Ciclismo", ["dist_km", "hours", "calories", "count"]),
    ]

    METRIC_LABELS = {
        "dist_km": ("Distância", "km"),
        "hours": ("Horas", "h"),
        "calories": ("Calorias", "kcal"),
        "count": ("Sessões", ""),
    }

    sport_details = []
    for sport_key, emoji, display_name, metric_keys in sport_detail_configs:
        # Gather all members who did this sport
        source_keys = sport_source_keys.get(sport_key, {sport_key})
        member_data = defaultdict(lambda: {
            "count": 0, "dist_km": 0.0, "calories": 0.0, "hours": 0.0,
        })
        for (aid, act), metrics in account_sport_metrics.items():
            if act in source_keys:
                md = member_data[aid]
                md["count"] += metrics["count"]
                md["dist_km"] += metrics["dist_km"]
                md["calories"] += metrics["calories"]
                md["hours"] += metrics["hours"]

        if not member_data:
            continue

        # Build athletes list sorted by count
        athletes = []
        for aid, md in member_data.items():
            m = members.get(aid, {})
            athletes.append({
                "name": m.get("short_name", "?"),
                "count": md["count"],
                "dist_km": round(md["dist_km"], 1),
                "calories": round(md["calories"]),
                "hours": round(md["hours"], 1),
            })
        athletes.sort(key=lambda x: x["count"], reverse=True)

        # Compute totals
        totals = {}
        for mk in metric_keys:
            totals[mk] = round(sum(a[mk] for a in athletes), 1)

        # Build metrics list with label, unit, total, and who leads
        metrics_out = []
        for mk in metric_keys:
            label, unit = METRIC_LABELS[mk]
            total = totals[mk]
            if total <= 0 and mk != "count":
                continue
            leader = max(athletes, key=lambda a: a[mk])
            metrics_out.append({
                "key": mk,
                "label": label,
                "unit": unit,
                "total": total,
                "leader_name": leader["name"],
                "leader_value": leader[mk],
            })

        sport_details.append({
            "key": sport_key,
            "emoji": emoji,
            "name": display_name,
            "athletes": athletes[:8],
            "metrics": metrics_out,
            "total_athletes": len(athletes),
        })

    save_json("sport_details.json", sport_details)

    # Annual ranking (all 4 seasons, only Verão has data so far)
    seasons = ["Verão", "Outono", "Inverno", "Primavera"]
    annual = []
    for r in ranking:
        annual.append({
            "position": r["position"],
            "name": r["name"],
            "short_name": r["short_name"],
            "seasons": {
                "Verão": r["points"],
                "Outono": None,
                "Inverno": None,
                "Primavera": None,
            },
            "total": r["points"],
        })
    annual.sort(key=lambda x: x["total"], reverse=True)
    # Re-assign positions with tie handling
    pos = 1
    idx = 0
    while idx < len(annual):
        total = annual[idx]["total"]
        tie_count = sum(1 for a in annual if a["total"] == total)
        for k in range(idx, idx + tie_count):
            annual[k]["position"] = pos
        pos += tie_count
        idx += tie_count
    save_json("annual_ranking.json", {"seasons": seasons, "ranking": annual})

    print("Done!")


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    raw = load_data()
    print("Processing challenge data...")
    process_all(raw)
