from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import hashlib
import hmac
import os

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from datetime import datetime, date
from functools import wraps

app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get(
    'SECRET_KEY',
    'development-only-secret-key'
)

app.config['DEBUG'] = (
    os.environ.get('FLASK_DEBUG', '0') == '1'
)

DB = os.environ.get(
    'DATABASE_PATH',
    os.path.join(app.instance_path, 'eco.db')
)

os.makedirs(os.path.dirname(os.path.abspath(DB)), exist_ok=True)

# ── helpers ────────────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def hash_pw(pw):
    return generate_password_hash(pw)


def verify_password(stored_password, entered_password):
    # Check passwords created using Werkzeug
    if stored_password.startswith(('scrypt:', 'pbkdf2:')):
        return check_password_hash(stored_password, entered_password), False

    # Support existing SHA-256 passwords temporarily
    legacy_hash = hashlib.sha256(
        entered_password.encode()
    ).hexdigest()

    if hmac.compare_digest(stored_password, legacy_hash):
        return True, True

    return False, False

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_user(uid):
    db = get_db()
    u = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    db.close()
    return u

def level_for_points(pts):
    thresholds = [0,100,300,600,1000,1500,2200,3000,4000,5000]
    for i,t in enumerate(thresholds):
        if pts < t: return max(1,i)
    return len(thresholds)

def xp_progress(pts):
    thresholds = [0,100,300,600,1000,1500,2200,3000,4000,5000]
    lvl = level_for_points(pts)
    lo = thresholds[min(lvl-1, len(thresholds)-1)]
    hi = thresholds[min(lvl, len(thresholds)-1)]
    if hi == lo: return 100
    return int((pts - lo) / (hi - lo) * 100)

def check_badges(uid, db):
    u = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    completed = db.execute('SELECT COUNT(*) as c FROM completions WHERE user_id=?', (uid,)).fetchone()['c']
    badges = []
    if completed >= 1:  badges.append('first_step')
    if completed >= 5:  badges.append('eco_starter')
    if completed >= 10: badges.append('green_warrior')
    if completed >= 20: badges.append('eco_champion')
    if u['points'] >= 500:  badges.append('point_hunter')
    if u['points'] >= 1000: badges.append('eco_legend')
    existing = [r['badge_key'] for r in db.execute('SELECT badge_key FROM badges WHERE user_id=?',(uid,)).fetchall()]
    for b in badges:
        if b not in existing:
            db.execute('INSERT INTO badges(user_id,badge_key,earned_at) VALUES(?,?,?)', (uid,b,datetime.now().isoformat()))
    db.commit()

# ── init db ────────────────────────────────────────────────────────────────────
def init_db():
    os.makedirs('instance', exist_ok=True)
    db = get_db()
    db.executescript('''
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        points INTEGER DEFAULT 0,
        gold_coins INTEGER DEFAULT 0,
        streak INTEGER DEFAULT 0,
        last_activity TEXT,
        avatar TEXT DEFAULT 'leaf',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS challenges(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        points INTEGER NOT NULL,
        category TEXT NOT NULL,
        difficulty TEXT DEFAULT 'easy',
        icon TEXT DEFAULT '🌱',
        daily INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS completions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        challenge_id INTEGER,
        completed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(challenge_id) REFERENCES challenges(id)
    );
    CREATE TABLE IF NOT EXISTS badges(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        badge_key TEXT,
        earned_at TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS game_progress(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        game_id TEXT NOT NULL,
        max_level INTEGER DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(id),
        UNIQUE(user_id, game_id)
    );
    CREATE TABLE IF NOT EXISTS farm_state(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        plant_type TEXT DEFAULT 'Sprout',
        growth_stage INTEGER DEFAULT 0,
        water_level INTEGER DEFAULT 100,
        last_watered TEXT,
        health TEXT DEFAULT 'happy',
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    ''')

    try:
        db.execute('ALTER TABLE users ADD COLUMN gold_coins INTEGER DEFAULT 0;')
    except sqlite3.OperationalError:
        pass


    # Seed challenges
    if db.execute('SELECT COUNT(*) FROM challenges').fetchone()[0] == 0:
        challenges = [
            ("Plant a Sapling","Plant a tree or sapling in your neighbourhood",50,"Nature","easy","🌳",0),
            ("Go Plastic-Free","Avoid single-use plastics for one full day",30,"Waste","easy","♻️",1),
            ("Walk or Cycle","Use zero-emission transport for your commute today",25,"Transport","easy","🚴",1),
            ("Compost Kitchen Waste","Set up or use a compost bin for food scraps",40,"Waste","medium","🍂",0),
            ("Solar Energy Quiz","Complete the solar energy knowledge quiz",20,"Education","easy","☀️",1),
            ("Beach/Park Cleanup","Collect at least 1kg of litter from a public space",80,"Community","medium","🏖️",0),
            ("Meatless Monday","Eat a fully plant-based diet for one day",35,"Food","easy","🥗",1),
            ("Save Water Challenge","Reduce water usage by 50% for a day",30,"Water","easy","💧",1),
            ("Upcycle an Item","Turn waste material into something useful",60,"Creativity","medium","🔧",0),
            ("Carbon Footprint Audit","Calculate and log your weekly carbon footprint",45,"Education","medium","📊",0),
            ("Rainwater Harvesting","Set up a simple rainwater collection system",100,"Water","hard","🌧️",0),
            ("Teach a Friend","Educate someone about an environmental topic",40,"Community","medium","📚",0),
            ("Zero-Waste Lunch","Pack and eat a completely zero-waste lunch",25,"Food","easy","🥙",1),
            ("Wild Bird Feeder","Build or set up a bird feeder in your area",55,"Nature","medium","🐦",0),
            ("LED Swap","Replace at least 3 bulbs with LED alternatives",35,"Energy","easy","💡",0),
        ]
        db.executemany('INSERT INTO challenges(title,description,points,category,difficulty,icon,daily) VALUES(?,?,?,?,?,?,?)', challenges)

    # Seed demo users
    if db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
        demo = [
            ("Arjun Sharma","arjun@demo.com",hash_pw("demo123"),850,7),
            ("Priya Patel","priya@demo.com",hash_pw("demo123"),720,5),
            ("Rahul Verma","rahul@demo.com",hash_pw("demo123"),610,4),
            ("Sneha Rao","sneha@demo.com",hash_pw("demo123"),540,3),
            ("Kiran Kumar","kiran@demo.com",hash_pw("demo123"),490,2),
        ]
        for name,email,pw,pts,streak in demo:
            db.execute('INSERT INTO users(name,email,password,points,streak,last_activity) VALUES(?,?,?,?,?,?)',
                       (name,email,pw,pts,streak,date.today().isoformat()))
        db.commit()
        # add some completions for demo users
        for uid in range(1,6):
            for cid in range(1, uid*3+1):
                db.execute('INSERT INTO completions(user_id,challenge_id) VALUES(?,?)',(uid,((cid-1)%15)+1))
            check_badges(uid, db)

    db.commit()
    db.close()

# ── routes ─────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session: return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        pw = request.form['password']
db = get_db()

u = db.execute(
    'SELECT * FROM users WHERE email=?',
    (email,)
).fetchone()

if u:
    valid, needs_upgrade = verify_password(
        u['password'], pw
    )

    if valid and needs_upgrade:
        db.execute(
            'UPDATE users SET password=? WHERE id=?',
            (hash_pw(pw), u['id'])
        )
        db.commit()

db.close()

if u and valid:
            session['user_id'] = u['id']
            session['user_name'] = u['name']
            return redirect(url_for('dashboard'))
        error = "Invalid email or password."
    return render_template('login.html', error=error)

@app.route('/signup', methods=['GET','POST'])
def signup():
    error = None
    if request.method == 'POST':
        name  = request.form['name']
        email = request.form['email']
        pw    = hash_pw(request.form['password'])
        db = get_db()
        try:
            db.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',(name,email,pw))
            db.commit()
            u = db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
            db.close()
            session['user_id'] = u['id']
            session['user_name'] = u['name']
            return redirect(url_for('dashboard'))
        except sqlite3.IntegrityError:
            error = "Email already registered."
            db.close()
    return render_template('signup.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    uid = session['user_id']
    db  = get_db()
    u   = db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    daily = db.execute('''SELECT c.* FROM challenges c
        WHERE c.daily=1 AND c.id NOT IN
        (SELECT challenge_id FROM completions WHERE user_id=? AND DATE(completed_at)=DATE('now'))
        LIMIT 3''',(uid,)).fetchall()
    total_c = db.execute('SELECT COUNT(*) FROM completions WHERE user_id=?',(uid,)).fetchone()[0]
    badges  = db.execute('SELECT badge_key FROM badges WHERE user_id=?',(uid,)).fetchall()
    rank_row= db.execute('SELECT COUNT(*)+1 AS rank FROM users WHERE points>?',(u['points'],)).fetchone()
    db.close()
    lvl = level_for_points(u['points'])
    xp  = xp_progress(u['points'])
    return render_template('dashboard.html', user=u, daily=daily, total_completed=total_c,
                           badges=badges, level=lvl, xp=xp, rank=rank_row['rank'])

@app.route('/challenges')
@login_required
def challenges():
    uid = session['user_id']
    db  = get_db()
    u   = db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    all_c = db.execute('SELECT * FROM challenges ORDER BY category, difficulty').fetchall()
    done  = {r['challenge_id'] for r in db.execute('SELECT DISTINCT challenge_id FROM completions WHERE user_id=?',(uid,)).fetchall()}
    db.close()
    lvl = level_for_points(u['points'])
    xp  = xp_progress(u['points'])
    return render_template('challenges.html', challenges=all_c, done=done, user=u, level=lvl, xp=xp)

@app.route('/api/complete/<int:cid>', methods=['POST'])
@login_required
def complete_challenge(cid):
    uid = session['user_id']
    db  = get_db()
    already = db.execute('SELECT id FROM completions WHERE user_id=? AND challenge_id=?',(uid,cid)).fetchone()
    if already:
        db.close()
        return jsonify({'status':'already','message':'Already completed!'})
    c = db.execute('SELECT * FROM challenges WHERE id=?',(cid,)).fetchone()
    if not c:
        db.close()
        return jsonify({'status':'error','message':'Not found'})
    db.execute('INSERT INTO completions(user_id,challenge_id) VALUES(?,?)',(uid,cid))
    db.execute('UPDATE users SET points=points+?, last_activity=? WHERE id=?',(c['points'],date.today().isoformat(),uid))
    db.commit()
    check_badges(uid, db)
    u = db.execute('SELECT points FROM users WHERE id=?',(uid,)).fetchone()
    db.close()
    lvl = level_for_points(u['points'])
    xp  = xp_progress(u['points'])
    return jsonify({'status':'ok','points':u['points'],'level':lvl,'xp':xp,'earned':c['points'],'message':f'+{c["points"]} pts!'})

@app.route('/leaderboard')
@login_required
def leaderboard():
    uid = session['user_id']
    db  = get_db()
    users = db.execute('SELECT id,name,points,streak FROM users ORDER BY points DESC LIMIT 20').fetchall()
    me    = db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    my_rank = db.execute('SELECT COUNT(*)+1 AS r FROM users WHERE points>?',(me['points'],)).fetchone()['r']
    db.close()
    leaderboard_data = []
    for i,u in enumerate(users):
        leaderboard_data.append({'rank':i+1,'id':u['id'],'name':u['name'],'points':u['points'],
                                  'streak':u['streak'],'level':level_for_points(u['points']),'is_me': u['id']==uid})
    return render_template('leaderboard.html', users=leaderboard_data, me=me, my_rank=my_rank,
                           level=level_for_points(me['points']), xp=xp_progress(me['points']))

@app.route('/profile')
@login_required
def profile():
    uid = session['user_id']
    db  = get_db()
    u   = db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    badges_earned = [r['badge_key'] for r in db.execute('SELECT badge_key FROM badges WHERE user_id=?',(uid,)).fetchall()]
    recent = db.execute('''SELECT c.title,c.points,c.icon,co.completed_at FROM completions co
        JOIN challenges c ON c.id=co.challenge_id WHERE co.user_id=? ORDER BY co.completed_at DESC LIMIT 5''',(uid,)).fetchall()
    total_c = db.execute('SELECT COUNT(*) FROM completions WHERE user_id=?',(uid,)).fetchone()[0]
    rank = db.execute('SELECT COUNT(*)+1 AS r FROM users WHERE points>?',(u['points'],)).fetchone()['r']
    db.close()
    lvl = level_for_points(u['points'])
    xp  = xp_progress(u['points'])
    all_badges = [
        {'key':'first_step','name':'First Step','desc':'Complete your first challenge','icon':'👣'},
        {'key':'eco_starter','name':'Eco Starter','desc':'Complete 5 challenges','icon':'🌱'},
        {'key':'green_warrior','name':'Green Warrior','desc':'Complete 10 challenges','icon':'⚔️'},
        {'key':'eco_champion','name':'Eco Champion','desc':'Complete 20 challenges','icon':'🏆'},
        {'key':'point_hunter','name':'Point Hunter','desc':'Earn 500 points','icon':'🎯'},
        {'key':'eco_legend','name':'Eco Legend','desc':'Earn 1000 points','icon':'🌍'},
    ]
    return render_template('profile.html', user=u, badges_earned=badges_earned, all_badges=all_badges,
                           recent=recent, total_completed=total_c, rank=rank, level=lvl, xp=xp)

@app.route('/rewards')
@login_required
def rewards():
    uid = session['user_id']
    db  = get_db()
    u   = db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
    badges_earned = [r['badge_key'] for r in db.execute('SELECT badge_key,earned_at FROM badges WHERE user_id=?',(uid,)).fetchall()]
    db.close()
    lvl = level_for_points(u['points'])
    xp  = xp_progress(u['points'])
    rewards_list = [
        {'key':'seed_saver','name':'Seed Saver','desc':'Awarded for joining the platform','icon':'🌰','pts':0,'unlocked':True},
        {'key':'sprout','name':'Sprout','desc':'Reach Level 2','icon':'🌿','pts':100,'unlocked':u['points']>=100},
        {'key':'sapling','name':'Sapling','desc':'Reach Level 3','icon':'🌲','pts':300,'unlocked':u['points']>=300},
        {'key':'eco_starter','name':'Eco Starter','desc':'Complete 5 challenges','icon':'🌱','pts':0,'unlocked':'eco_starter' in badges_earned},
        {'key':'green_warrior','name':'Green Warrior','desc':'Complete 10 challenges','icon':'⚔️','pts':0,'unlocked':'green_warrior' in badges_earned},
        {'key':'first_step','name':'First Step','desc':'Complete first challenge','icon':'👣','pts':0,'unlocked':'first_step' in badges_earned},
        {'key':'point_hunter','name':'Point Hunter','desc':'Earn 500 points','icon':'🎯','pts':500,'unlocked':u['points']>=500},
        {'key':'eco_champion','name':'Eco Champion','desc':'Complete 20 challenges','icon':'🏆','pts':0,'unlocked':'eco_champion' in badges_earned},
        {'key':'eco_legend','name':'Eco Legend','desc':'Earn 1000 points','icon':'🌍','pts':1000,'unlocked':u['points']>=1000},
        {'key':'tree_hugger','name':'Tree Hugger','desc':'Reach Level 5','icon':'🤗','pts':1000,'unlocked':u['points']>=1000},
        {'key':'carbon_cutter','name':'Carbon Cutter','desc':'Reach Level 7','icon':'✂️','pts':2200,'unlocked':u['points']>=2200},
        {'key':'planet_protector','name':'Planet Protector','desc':'Reach Level 10','icon':'🛡️','pts':5000,'unlocked':u['points']>=5000},
    ]
    return render_template('rewards.html', user=u, rewards=rewards_list, level=lvl, xp=xp)

@app.route('/games')
@login_required
def games():
    uid = session['user_id']
    db = get_db()
    u = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    progress = db.execute('SELECT game_id, max_level FROM game_progress WHERE user_id=?', (uid,)).fetchall()
    db.close()
    
    prog_dict = {row['game_id']: row['max_level'] for row in progress}
    lvl = level_for_points(u['points'])
    xp  = xp_progress(u['points'])
    return render_template('games.html', user=u, progress=prog_dict, level=lvl, xp=xp)

@app.route('/api/games/progress', methods=['POST'])
@login_required
def update_game_progress():
    uid = session['user_id']
    data = request.json
    game_id = data.get('game_id')
    level = data.get('level', 1)
    db = get_db()
    
    db.execute('UPDATE users SET points=points+20, last_activity=? WHERE id=?', (date.today().isoformat(), uid))
    
    curr = db.execute('SELECT max_level FROM game_progress WHERE user_id=? AND game_id=?', (uid, game_id)).fetchone()
    if not curr:
        db.execute('INSERT INTO game_progress(user_id, game_id, max_level) VALUES(?,?,?)', (uid, game_id, max(2, level + 1)))
    else:
        if level >= curr['max_level']:
            db.execute('UPDATE game_progress SET max_level=? WHERE user_id=? AND game_id=?', (level + 1, uid, game_id))
    
    db.commit()
    check_badges(uid, db)
    u = db.execute('SELECT points FROM users WHERE id=?', (uid,)).fetchone()
    db.close()
    lvl = level_for_points(u['points'])
    xp = xp_progress(u['points'])
    return jsonify({'status': 'ok', 'points': u['points'], 'level': lvl, 'xp': xp, 'message': '+20 XP!'})

@app.route('/game/memory-match')
@login_required
def game_memory_match():
    uid = session['user_id']
    db = get_db()
    prog = db.execute('SELECT max_level FROM game_progress WHERE user_id=? AND game_id=?', (uid, 'memory_match')).fetchone()
    db.close()
    current_level = prog['max_level'] if prog else 1
    return render_template('games/memory_match.html', level=current_level)

@app.route('/game/waste-sort')
@login_required
def game_waste_sort():
    uid = session['user_id']
    db = get_db()
    prog = db.execute('SELECT max_level FROM game_progress WHERE user_id=? AND game_id=?', (uid, 'waste_sort')).fetchone()
    db.close()
    current_level = prog['max_level'] if prog else 1
    return render_template('games/waste_sort.html', level=current_level)

@app.route('/game/farm')
@login_required
def game_farm():
    uid = session['user_id']
    db = get_db()
    u = db.execute('SELECT points, gold_coins FROM users WHERE id=?', (uid,)).fetchone()
    if level_for_points(u['points']) < 5:
        db.close()
        return redirect(url_for('games'))
        
    state = db.execute('SELECT * FROM farm_state WHERE user_id=?', (uid,)).fetchone()
    if not state:
        db.execute("INSERT INTO farm_state(user_id) VALUES(?)", (uid,))
        db.commit()
        state = db.execute('SELECT * FROM farm_state WHERE user_id=?', (uid,)).fetchone()
    db.close()
    
    return render_template('games/farm.html', state=state, gold_coins=u['gold_coins'])

@app.route('/api/farm/action', methods=['POST'])
@login_required
def farm_action():
    uid = session['user_id']
    action = request.json.get('action') # 'water', 'fertilize'
    db = get_db()
    u = db.execute('SELECT gold_coins FROM users WHERE id=?', (uid,)).fetchone()
    state = db.execute('SELECT * FROM farm_state WHERE user_id=?', (uid,)).fetchone()
    
    msg = ""
    gold = u['gold_coins']
    if action == 'water':
        db.execute("UPDATE farm_state SET water_level=100, last_watered=?, health='happy' WHERE user_id=?", (datetime.now().isoformat(), uid))
        db.execute("UPDATE users SET gold_coins=gold_coins+5 WHERE id=?", (uid,))
        gold += 5
        msg = "Watered plant! +5 Gold Coins"
    elif action == 'grow':
        if state['water_level'] >= 50 and state['growth_stage'] < 3:
            db.execute("UPDATE farm_state SET growth_stage=growth_stage+1, water_level=water_level-20 WHERE user_id=?", (uid,))
            msg = "Your plant grew!"
    elif action == 'fertilize':
        if gold >= 10:
            db.execute("UPDATE users SET gold_coins=gold_coins-10 WHERE id=?", (uid,))
            db.execute("UPDATE farm_state SET growth_stage=MIN(3, growth_stage+1), health='happy' WHERE user_id=?", (uid,))
            gold -= 10
            msg = "Fertilized plant! (-10 Gold Coins)"
        else:
            return jsonify({'status': 'error', 'message': 'Not enough gold!'})
            
    db.commit()
    new_state = db.execute('SELECT * FROM farm_state WHERE user_id=?', (uid,)).fetchone()
    db.close()
    return jsonify({'status': 'ok', 'message': msg, 'gold': gold, 'state': dict(new_state)})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
