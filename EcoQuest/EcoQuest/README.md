# 🌍 EcoQuest – SIH25009 Gamified Environmental Education Platform

## Project Structure
```
sih25009/
├── app.py                  # Flask backend (routes, DB, API)
├── requirements.txt
├── instance/
│   └── eco.db              # SQLite database (auto-created)
├── templates/
│   ├── base.html           # Shared layout + navbar
│   ├── login.html
│   ├── signup.html
│   ├── dashboard.html      # Stats, daily challenges, XP
│   ├── challenges.html     # Full challenge grid with filters
│   ├── leaderboard.html    # Rankings + podium
│   ├── profile.html        # User stats + badges + activity
│   └── rewards.html        # Achievement unlock gallery
└── static/
    ├── css/main.css        # Full design system
    └── js/main.js          # Animations + interactions
```

## Features
- ✅ Authentication (login/signup with session handling)
- ✅ Dashboard (points, level, XP bar, daily challenges, rank)
- ✅ Challenges module (15 eco-tasks, category filter, dynamic points)
- ✅ Leaderboard (podium, ranked list, streak tracking)
- ✅ Profile page (badges, recent activity, all stats)
- ✅ Rewards section (12 achievements with unlock visuals)
- ✅ Gamification: points, level progression, badge unlocking, XP tracking
- ✅ REST API: `/api/complete/<id>` for real-time updates
- ✅ Responsive for mobile + desktop

## How to Run

### 1. Install dependencies
```bash
pip install flask
```

### 2. Run the app
```bash
cd sih25009
python app.py
```

### 3. Open browser
```
http://localhost:5000
```

### Demo Credentials
| Email           | Password |
|-----------------|----------|
| arjun@demo.com  | demo123  |
| priya@demo.com  | demo123  |

Or click **Sign Up** to create a new account.

## Database Schema

```sql
users(id, name, email, password, points, streak, last_activity, avatar, created_at)
challenges(id, title, description, points, category, difficulty, icon, daily)
completions(id, user_id, challenge_id, completed_at)
badges(id, user_id, badge_key, earned_at)
```

## Gamification Logic

| Level | Points Required |
|-------|----------------|
| 1     | 0              |
| 2     | 100            |
| 3     | 300            |
| 4     | 600            |
| 5     | 1000           |
| 6     | 1500           |
| 7     | 2200           |
| 8     | 3000           |
| 9     | 4000           |
| 10    | 5000           |

### Badges
- 👣 First Step — Complete 1 challenge
- 🌱 Eco Starter — Complete 5 challenges
- ⚔️ Green Warrior — Complete 10 challenges
- 🏆 Eco Champion — Complete 20 challenges
- 🎯 Point Hunter — Earn 500 points
- 🌍 Eco Legend — Earn 1000 points
