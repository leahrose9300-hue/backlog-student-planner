"""Small SQLite persistence layer. One local workspace per SQLite database."""
import sqlite3
from pathlib import Path
from datetime import date, timedelta
from engine import StudyTask, validate_task

DEFAULT_DB = Path(__file__).parent / 'backlog.sqlite3'

def connect(path=DEFAULT_DB):
    # Streamlit caches this connection across reruns, which may use different threads.
    # This is suitable for Backlog's single-user local demo; multi-user deployment
    # should use per-request connections with transaction-safe concurrency.
    db = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS tasks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL, subject TEXT NOT NULL,
      minutes INTEGER NOT NULL CHECK(minutes>0),
      done_minutes INTEGER NOT NULL DEFAULT 0 CHECK(done_minutes>=0),
      deadline TEXT NOT NULL, priority INTEGER NOT NULL DEFAULT 2
    );
    CREATE TABLE IF NOT EXISTS settings (
      key TEXT PRIMARY KEY, value TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS unavailable (
      day TEXT PRIMARY KEY
    );
    ''')
    db.commit()
    return db

def get_tasks(db):
    return [StudyTask(r['id'],r['title'],r['subject'],r['minutes'],r['done_minutes'],
                      date.fromisoformat(r['deadline']),r['priority'])
            for r in db.execute('SELECT * FROM tasks ORDER BY deadline,priority DESC,id')]

def add_task(db,title,subject,minutes,deadline,priority=2):
    validate_task(title,subject,minutes,deadline,priority)
    db.execute('INSERT INTO tasks(title,subject,minutes,deadline,priority) VALUES(?,?,?,?,?)',
               (title.strip(),subject.strip(),minutes,deadline.isoformat(),priority))
    db.commit()

def edit_task(db,task_id,title,subject,minutes,deadline,priority):
    validate_task(title,subject,minutes,deadline,priority)
    db.execute('UPDATE tasks SET title=?,subject=?,minutes=?,deadline=?,priority=?,done_minutes=MIN(done_minutes,?) WHERE id=?',
               (title.strip(),subject.strip(),minutes,deadline.isoformat(),priority,minutes,task_id))
    db.commit()

def delete_task(db,task_id):
    db.execute('DELETE FROM tasks WHERE id=?',(task_id,));db.commit()

def update_progress(db,task_id,done_minutes):
    row=db.execute('SELECT minutes FROM tasks WHERE id=?',(task_id,)).fetchone()
    if row is None: raise ValueError('Task not found')
    if not 0 <= done_minutes <= row['minutes']: raise ValueError('Invalid progress')
    db.execute('UPDATE tasks SET done_minutes=? WHERE id=?',(done_minutes,task_id));db.commit()

def get_setting(db,key,default):
    row=db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
    return row['value'] if row else default

def set_setting(db,key,value):
    db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(value)))
    db.commit()

def get_unavailable(db):
    return {date.fromisoformat(r['day']) for r in db.execute('SELECT day FROM unavailable')}

def toggle_unavailable(db,day):
    d=day.isoformat()
    if db.execute('SELECT 1 FROM unavailable WHERE day=?',(d,)).fetchone():
        db.execute('DELETE FROM unavailable WHERE day=?',(d,))
    else: db.execute('INSERT INTO unavailable(day) VALUES(?)',(d,))
    db.commit()

def reset_demo(db,today=None):
    today=today or date.today()
    db.execute('DELETE FROM tasks');db.execute('DELETE FROM unavailable');db.execute('DELETE FROM settings')
    demo=[('Physics · Waves lecture 12','Physics',100,3,3),
          ('Biology · Cellular respiration','Biology',150,5,3),
          ('Maths · Past paper 01','Mathematics',120,2,3),
          ('Chemistry · Organic revision','Chemistry',90,7,2),
          ('English · Essay outline','English',55,4,2),
          ('Physics · Problem set','Physics',140,9,2),
          ('Biology · Flashcards','Biology',75,10,1)]
    for name,subject,minutes,offset,priority in demo:
        db.execute('INSERT INTO tasks(title,subject,minutes,deadline,priority) VALUES(?,?,?,?,?)',
                   (name,subject,minutes,(today+timedelta(days=offset)).isoformat(),priority))
    db.execute('INSERT INTO settings VALUES(?,?)',('daily_hours','2.0'))
    db.commit()
