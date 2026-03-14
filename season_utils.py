import datetime

def get_current_season():
    m = datetime.datetime.now().month
    if m in [11, 12, 1, 2]: return "Winter"
    if m in [3, 4]: return "Spring"
    if m in [5, 6]: return "Summer"
    if m in [7, 8, 9]: return "Monsoon"
    return "Autumn"

def get_season_emoji(s): return {"Winter":"❄️","Spring":"🌸","Summer":"☀️","Monsoon":"🌧️","Autumn":"🍂"}.get(s, "🌍")
def get_time_of_day_emoji(t):
    l = t.lower()
    return "🌅" if "morning" in l else "☀️" if "afternoon" in l else "🌆" if "evening" in l else "⏰"

def get_day_of_week(start_date_str=None, day_offset=0):
    try: start = datetime.datetime.strptime(start_date_str, "%Y-%m-%d") if start_date_str else datetime.datetime.now()
    except: start = datetime.datetime.now()
    return (start + datetime.timedelta(days=day_offset)).strftime('%A')

def infer_famous_for(p, c, d):
    pl, cl, dl = p.lower(), (c or "").lower(), (d or "").lower()
    if any(w in pl for w in ['fort','palace','mon','temple','mosque']): return "Historic architecture"
    if any(w in pl for w in ['lake','garden','park','beach','valley']): return "Natural beauty"
    if 'museum' in pl: return "Cultural exhibits"
    if any(w in pl for w in ['market','bazaar','mall']): return "Shopping"
    if any(w in pl for w in ['rest','cafe','food']): return "Local cuisine"
    return "Must-visit attraction"

def infer_best_time(p, c):
    pl = p.lower()
    if any(w in pl for w in ['sunset','night','market','lake']): return "evening"
    if any(w in pl for w in ['garden','park','trek']): return "morning"
    if any(w in pl for w in ['museum','palace','fort']): return "afternoon"
    return "morning"

def generate_why_now_explanation(f, s, t, p):
    res = [ {"morning":"Quiet morning","afternoon":"Ideal afternoon","evening":"Perfect evening"}.get(t.lower(), "Great time") ] if p else []
    res.append({"Winter":"Pleasant weather","Summer":"Cooler hours","Monsoon":"Lush greenery","Spring":"Outdoor weather","Autumn":"Comfortable climate"}.get(s, "Iconic attraction"))
    return ' • '.join(res)
