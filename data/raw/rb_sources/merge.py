import json, re, unicodedata

ALIAS = {'kenny gainwell': 'kenneth gainwell', 'aaron jones': 'aaron jones',
         'jeremiah love': 'jeremiyah love'}
TEAMFIX = {'JAC': 'JAX', 'ARZ': 'ARI', 'WSH': 'WAS', 'LVR': 'LV'}

def norm(n):
    n = unicodedata.normalize('NFKD', n).encode('ascii', 'ignore').decode()
    n = n.lower().replace('.', '').replace("'", '').replace('-', ' ')
    n = re.sub(r'\b(jr|sr|ii|iii|iv)\b', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return ALIAS.get(n, n)

def loadsrc(path):
    d = {}
    for r in json.load(open(path)):
        r['team'] = TEAMFIX.get(r['team'], r['team'])
        d[norm(r['name'])] = r
    return d

fft = loadsrc('fft.json')
espn = loadsrc('espn_rb.json')

# FantasyPros consensus (top 10 visible only, scraped Aug 26 2026)
fp = {
    'jahmyr gibbs': (13.8, 4.1), 'bijan robinson': (8.8, 3.5), 'christian mccaffrey': (8.7, 4.6),
    'jonathan taylor': (12.9, 1.5), 'derrick henry': (13.4, 0.7), 'devon achane': (6.0, 4.0),
    'james cook': (10.3, 1.9), 'chase brown': (7.8, 4.0), 'saquon barkley': (8.2, 2.1),
    'kenneth walker': (8.7, 1.2), 'josh jacobs': (11.7, 1.2),
}

# Sportsbook season-long rushing-TD O/U lines (real books)
vegas_rush = {
    'derrick henry': (12.5, 'DK via FoxSports/FantasyPoints'),
    'jonathan taylor': (11.5, 'DK via FoxSports/FantasyPoints'),
    'james cook': (10.5, 'SportsbookReview / Sharp'),
    'kyren williams': (9.5, 'SportsbookReview / Sharp'),
    'javonte williams': (9.5, 'FantasyTeamAdvice'),
    'david montgomery': (7.5, 'Sharp Football / FTA'),
    'chase brown': (5.5, 'Sharp Football'),
    'devon achane': (5.5, 'FantasyTeamAdvice'),
    'jordan mason': (4.5, 'Yahoo Sports'),
}
vegas_rec = {
    'jahmyr gibbs': (4.5, 'StatementGames/Yahoo'),
    'bijan robinson': (3.5, 'StatementGames/Yahoo'),
    'christian mccaffrey': (4.5, 'StatementGames/Yahoo'),
}
# DraftKings odds to LEAD NFL in rushing TDs
lead_odds = {
    'jahmyr gibbs': '+500', 'derrick henry': '+550', 'jonathan taylor': '+600',
    'james cook': '+850', 'josh jacobs': '+900', 'kyren williams': '+1400',
    'saquon barkley': '+1600', 'javonte williams': '+1600', 'christian mccaffrey': '+1600',
}

# Kalshi implied rush TD (illiquid, wide markets -- directional only)
kal = {}
sec = None
for line in open('kalshi_implied.txt'):
    if line.startswith('===='):
        sec = line.split()[1]; continue
    m = re.match(r'(.+?)\s+implied\s+([\d.]+)', line)
    if m and sec == 'RUSH':
        kal[norm(m.group(1))] = float(m.group(2))

QB = {'josh allen', 'jaxson dart', 'daniel jones', 'lamar jackson', 'kyler murray',
      'drake maye', 'fernando mendoza', 'jalen hurts'}

# Goal-line role: Yes / No / Committee / Unknown  + note
GL = {
    'derrick henry': ('Yes', 'Bell-cow GL back; Justice Hill is pass-down only'),
    'jonathan taylor': ('Yes', 'Owns IND short yardage; led NFL 18 rush TD 2025'),
    'jahmyr gibbs': ('Committee', 'Elite but DET added Pacheco as complement; Montgomery gone to HOU'),
    'josh jacobs': ('Yes', 'Clear GB short-yardage/GL hammer'),
    'javonte williams': ('Yes', 'DAL lead + GL; 9.5 Vegas rush TD line'),
    'kyren williams': ('Committee', 'Alternates full drives with Corum; Davante Adams is real GL target'),
    'blake corum': ('Committee', 'Takes entire 2nd drive then alternates; GL depends on whose drive'),
    'james cook': ('Committee', 'Josh Allen vultures heavily (Allen 8.2 implied rush TD himself)'),
    'saquon barkley': ('Committee', 'Tush push gives Hurts 8-12 free TDs; Hurts 8.5 rush TD line'),
    'christian mccaffrey': ('Yes', 'Full workload back incl. GL'),
    'bijan robinson': ('Committee', 'Only 48% of ATL inside-5 carries in 2025; Brian Robinson Jr. signed'),
    'brian robinson': ('Committee', 'Signed by ATL specifically as the between-tackles/GL complement'),
    'david montgomery': ('Yes', 'Bruiser, excels at GL; confirmed committee w/ Marks but Monty owns short yardage'),
    'woody marks': ('No', 'Passing-down/change-of-pace share of HOU committee'),
    'kenneth walker': ('Unknown', 'New to KC; GL split w/ Demercado/Hunt-type role unresolved'),
    'omarion hampton': ('Yes', 'Clear LAC lead back and GL option'),
    'quinshon judkins': ('Yes', 'CLE bell-cow; Sampson is the receiving back'),
    'ashton jeanty': ('Yes', 'LV workhorse incl. GL'),
    'jeremiyah love': ('Committee', 'Rookie; team depth chart opened Allgeier RB1, LaFleur has said he splits carries'),
    'tyler allgeier': ('Committee', 'Listed RB1 on ARI first depth chart; power back profile = GL risk to Love'),
    'james conner': ('Unknown', 'Listed RB3 in ARI camp; veteran GL role possible'),
    'breece hall': ('Committee', 'Braelon Allen is the NYJ short-yardage bruiser; Hall groin injury'),
    'braelon allen': ('Committee', 'Short-yardage/GL bruiser behind Hall'),
    'cam skattebo': ('Yes', 'Power profile, NYG lead back'),
    'najee harris': ('Unknown', 'On NYG roster as RB4 per Ourlads; GL vulture risk if active'),
    'bucky irving': ('No', 'Had ZERO carries inside the 5 in 2025'),
    'sean tucker': ('Yes', 'Handled overwhelming majority of TB inside-5 carries; 8 TD in 2025'),
    'kenneth gainwell': ('No', 'TB receiving-down back'),
    'bhayshul tuten': ('Committee', 'Lead back but Coen favors Rodriguez at GL'),
    'chris rodriguez': ('Yes', 'Hand-picked by Coen as JAX GL/short-yardage back'),
    'dandre swift': ('Committee', 'Roughly 55/45 with Monangai'),
    'kyle monangai': ('Committee', 'Roughly 45% share; power complement'),
    'travis etienne': ('Unknown', 'New to NO; GL role vs Kamara/Neal unresolved'),
    'alvin kamara': ('Unknown', 'Aging; role reduced behind Etienne'),
    'tony pollard': ('Committee', 'Spears and rookie Singleton cut into TEN work'),
    'jaylen warren': ('Committee', 'PIT ~50/50; Dowdle is the bruiser'),
    'rico dowdle': ('Committee', 'Profiles as GL favorite in PIT split'),
    'treveyon henderson': ('No', 'Explosive complement; Stevenson keeps GL'),
    'rhamondre stevenson': ('Yes', 'NE GL role is his to keep after SB run'),
    'jk dobbins': ('Yes', 'DEN lead back 15-18 carries incl. GL'),
    'rj harvey': ('No', 'Passing-down back'),
    'jonah coleman': ('No', 'Rookie RB3; GL insurance only'),
    'jadarian price': ('Committee', 'Rookie; leads until Charbonnet returns, unsettled 3-way room'),
    'zach charbonnet': ('Unknown', 'ACL surgery Feb 20; on PUP, return timeline uncertain'),
    'george holani': ('Committee', 'Part of unsettled SEA 3-way committee'),
    'chuba hubbard': ('Committee', 'Opens as starter but CAR GL role unsettled'),
    'jonathon brooks': ('Committee', 'Viewed as future lead; coming off ACL issues'),
    'jacory croskey merritt': ('Yes', 'WAS lead-back and GL work is his to claim'),
    'rachaad white': ('No', 'WAS primary receiving back'),
    'kaytron allen': ('Committee', 'Rookie bruiser, could steal GL work in WAS'),
    'jordan mason': ('Yes', 'MIN early-down and GL hammer'),
    'aaron jones': ('No', 'Satellite/receiving role in MIN'),
    'devon achane': ('No', 'Small back; MIA GL work goes elsewhere'),
    'ollie gordon': ('Committee', 'MIA power back, GL candidate'),
    'chase brown': ('Yes', 'CIN lead back; Perine is the passing-down back'),
    'isiah pacheco': ('Committee', 'Signed by DET as complement to Gibbs; power profile'),
    'tank bigsby': ('No', 'PHI backup behind Barkley'),
    'dylan sampson': ('No', 'CLE receiving back'),
    'justice hill': ('No', 'BAL pass-down back'),
    'samaje perine': ('No', 'CIN passing-down back'),
    'tyjae spears': ('No', 'TEN complement'),
    'tyrone tracy': ('No', 'NYG backup'),
    'mike washington': ('Unknown', 'LV rookie backup'),
    'keaton mitchell': ('No', 'LAC speed back'),
    'kimani vidal': ('Unknown', 'LAC depth'),
    'marshawn lloyd': ('Unknown', 'GB backup'),
    'ray davis': ('Committee', 'BUF power back, some short yardage'),
    'ty johnson': ('No', 'BUF receiving back'),
    'jaydon blue': ('No', 'DAL speed back'),
    'emari demercado': ('Unknown', 'KC depth'),
    'emmett johnson': ('Unknown', 'KC rookie'),
    'nicholas singleton': ('Unknown', 'TEN rookie'),
    'demond claiborne': ('Unknown', 'MIN rookie'),
    'seth mcgowan': ('Unknown', 'IND rookie'),
    'kaelon black': ('Unknown', 'SF rookie'),
    'dj giddens': ('Unknown', 'IND backup'),
    'jaylen wright': ('No', 'MIA speed back'),
    'isaiah davis': ('Unknown', 'NYJ depth'),
    'jordan james': ('Unknown', 'SF backup'),
    'will shipley': ('No', 'PHI depth'),
    'lequint allen': ('No', 'JAX receiving back'),
    'trey benson': ('Unknown', 'ARI depth, buried'),
    'roschon johnson': ('Unknown', 'CHI depth; former GL vulture'),
    'kaleb johnson': ('Unknown', 'PIT depth'),
    'tahj brooks': ('Unknown', 'CIN depth'),
    'kendre miller': ('Unknown', 'NO depth'),
    'trevor etienne': ('Unknown', 'CAR depth'),
    'aj dillon': ('Unknown', 'CAR power back signed in FA; GL sleeper'),
    'emanuel wilson': ('Committee', 'SEA power complement in 3-way room'),
    'raheim sanders': ('Unknown', 'CLE depth'),
    'jam miller': ('Unknown', 'NE rookie'),
    'jeremy mcnichols': ('No', 'WAS depth'),
    'devin neal': ('Unknown', 'NO depth'),
    'jarquez hunter': ('Unknown', 'LAR depth'),
    'isaac guerendo': ('Unknown', 'SF depth'),
    'brashard smith': ('Unknown', 'KC depth'),
    'devin singletary': ('Unknown', 'NYG depth'),
    'eli heidenreich': ('Unknown', 'PIT rookie'),
    'chris brooks': ('Unknown', 'GB depth'),
    'rasheen ali': ('Unknown', 'BAL depth'),
}

ROOKIES = {'jeremiyah love', 'jadarian price', 'kaelon black', 'mike washington',
           'jonah coleman', 'emmett johnson', 'nicholas singleton', 'kaytron allen',
           'demond claiborne', 'seth mcgowan', 'eli heidenreich', 'jam miller'}

rows = {}
for k in set(fft) | set(espn):
    if k in QB:
        continue
    f, e = fft.get(k), espn.get(k)
    name = (e or f)['name']
    team = (e or f)['team']
    if f and e and f['team'] != e['team']:
        team = e['team'] + '/' + f['team'] + '?'
    fr = float(f['rtd']) if f else None
    fe = float(f['retd']) if f else None
    er = e['rtd'] if e else None
    ee = e['retd'] if e else None
    fpr, fpe = fp.get(k, (None, None))

    rl = [x for x in (fr, er, fpr) if x is not None]
    el = [x for x in (fe, ee, fpe) if x is not None]
    rows[k] = dict(key=k, name=name, team=team, fft_r=fr, fft_e=fe, espn_r=er, espn_e=ee,
                   fp_r=fpr, fp_e=fpe,
                   rush=round(sum(rl) / len(rl), 1) if rl else None,
                   rec=round(sum(el) / len(el), 1) if el else None,
                   nsrc=len(rl), spread=(max(rl) - min(rl)) if len(rl) > 1 else 0,
                   vr=vegas_rush.get(k), ve=vegas_rec.get(k), lead=lead_odds.get(k),
                   kal=kal.get(k), gl=GL.get(k, ('Unknown', '')),
                   rookie=k in ROOKIES)

for r in rows.values():
    r['total'] = round((r['rush'] or 0) + (r['rec'] or 0), 1)
    r['pts'] = round(r['total'] * 6, 1)
    has_vegas = r['vr'] or r['ve'] or r['lead']
    if r['nsrc'] >= 2 and r['spread'] <= 2.0:
        c = 'HIGH'
    elif r['nsrc'] >= 2 and r['spread'] <= 3.5:
        c = 'MEDIUM'
    elif r['nsrc'] >= 2:
        c = 'MEDIUM'
    else:
        c = 'MEDIUM' if r['nsrc'] == 1 else 'LOW'
    if has_vegas and r['nsrc'] >= 2 and r['spread'] <= 2.5:
        c = 'HIGH'
    r['conf'] = c

out = sorted(rows.values(), key=lambda r: -r['total'])
json.dump(out, open('merged.json', 'w'), indent=1)
print(len(out))
