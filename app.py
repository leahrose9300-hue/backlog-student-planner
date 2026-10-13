from datetime import date, timedelta
from collections import defaultdict
import streamlit as st
import pandas as pd
from engine import plan, next_step, deadline_summary
from storage import (connect, get_tasks, add_task, edit_task, delete_task,
                     update_progress, get_setting, set_setting, get_unavailable,
                     toggle_unavailable, reset_demo)

st.set_page_config(page_title='Backlog — Find your way back',page_icon='🌙',layout='wide',initial_sidebar_state='expanded')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@400;600;700;800&display=swap');
html,body,[class*="css"],div[data-testid="stApp"]{font-family:'DM Sans',sans-serif}
.stApp{background:#F8F7F5;color:#17213B}
h1,h2,h3{font-family:'Manrope',sans-serif!important;letter-spacing:-.035em}
h1{font-size:2.45rem!important}
[data-testid="stSidebar"]{background:#19243F}
[data-testid="stSidebar"] *{color:#F0EEFA!important}
[data-testid="stSidebar"] button{color:#17213B!important}
div[data-testid="stMetric"]{background:white;border:1px solid #EAE8F0;border-radius:18px;padding:18px;box-shadow:0 5px 19px #17213B09}
div[data-testid="stMetricValue"]{color:#19243F;font-weight:800}
.stButton>button[kind="primary"]{background:#7563CF;color:white;border:0;border-radius:12px}
.stButton>button{border-radius:12px}
div[data-testid="stVerticalBlockBorderWrapper"]>div{border-radius:18px!important}
.hero{background:linear-gradient(120deg,#19243F 0%,#37365F 64%,#5E5798 100%);padding:29px 35px;border-radius:22px;color:#fff;margin-bottom:22px}
.hero h1{color:white!important;margin:0;font-size:2.3rem!important}
.hero p{color:#D8D4EF;margin:.5rem 0 0;font-size:1.07rem}
.eyebrow{color:#A9A1E0;font-weight:800;font-size:.76rem;letter-spacing:.12em}
.mini{color:#7B8191;font-size:.89rem}
.pill{background:#F0EBFF;padding:5px 11px;border-radius:40px;color:#5342A5;font-weight:700}
</style>''',unsafe_allow_html=True)

# Each visitor gets a private, temporary demo database.
# No student data is shared with other visitors or persisted on the server.
if 'demo_db' not in st.session_state:
    st.session_state['demo_db'] = connect(':memory:')
db = st.session_state['demo_db']
if get_setting(db,'initialized','')!='yes':
    reset_demo(db)
    set_setting(db,'initialized','yes')

with st.sidebar:
    st.markdown('## ◉ Backlog')
    st.caption('YOU CAN FIND YOUR WAY BACK')
    page=st.radio('Workspace',['Overview','My tasks','Recovery plan','Comeback engine','Settings'],label_visibility='collapsed')
    st.divider()
    st.markdown('**Your study rhythm**')
    hours=float(get_setting(db,'daily_hours','2.0'))
    chosen=st.slider('Study hours per day',0.0,12.0,min(hours,12.0),0.5)
    if chosen!=hours:
        set_setting(db,'daily_hours',chosen);st.rerun()
    st.caption('Plans update automatically when your availability changes.')
    st.divider()
    if st.button('↺ Reset sample workspace',use_container_width=True):
        reset_demo(db);set_setting(db,'initialized','yes');st.rerun()
    st.caption('Public demo · Your tasks stay in this browser session and reset when it ends')

now=date.today()
tasks=get_tasks(db)
unavailable=get_unavailable(db)
hours=float(get_setting(db,'daily_hours','2.0'))
weekday_hours={}
# Optional overrides are stored only for days with customized availability.
for i in range(7):
    val=get_setting(db,f'weekday_{i}','')
    if val!='':weekday_hours[i]=float(val)
result=plan(tasks,hours,today=now,days=90,unavailable=unavailable,weekday_hours=weekday_hours)
active=[t for t in tasks if t.remaining]
remaining=sum(t.remaining for t in active)
finished=sum(t.remaining==0 for t in tasks)
total=sum(t.minutes for t in tasks)
completed_minutes=sum(t.minutes-t.remaining for t in tasks)


def update_session(session):
    t=next((x for x in tasks if x.id==session['task_id']),None)
    if t:
        update_progress(db,t.id,min(t.minutes,t.done_minutes+session['minutes']))
        st.toast(f"Logged {session['minutes']} minutes on {t.title}")
        st.rerun()

def session_rows(sessions):
    return pd.DataFrame([{'Day':s['date'].strftime('%a, %d %b'),
                          'Task':s['title'],'Subject':s['subject'],
                          'Duration':f"{s['minutes']} min",'Due':s['deadline'].strftime('%d %b')}
                         for s in sessions])

def task_form(prefix,task=None):
    title=st.text_input('Task or lecture name',value=task.title if task else '',key=prefix+'title')
    subject=st.text_input('Subject',value=task.subject if task else '',key=prefix+'subject')
    duration=st.number_input('Estimated total minutes',min_value=1,max_value=100000,value=task.minutes if task else 50,step=5,key=prefix+'duration')
    deadline=st.date_input('Deadline',value=task.deadline if task else now+timedelta(days=7),key=prefix+'deadline')
    priority_label=st.selectbox('Priority',['Low','Medium','High'],index=(task.priority-1 if task else 1),key=prefix+'priority')
    if st.form_submit_button('Save changes' if task else 'Add to backlog',type='primary'):
        try:
            if task:edit_task(db,task.id,title,subject,int(duration),deadline,['Low','Medium','High'].index(priority_label)+1)
            else:add_task(db,title,subject,int(duration),deadline,['Low','Medium','High'].index(priority_label)+1)
            st.rerun()
        except ValueError as e:st.error(str(e))

if page=='Overview':
    st.markdown("""<div class='hero'><div class='eyebrow'>YOUR PERSONAL RECOVERY SPACE</div><h1>One step at a time.</h1><p>You're not behind forever. You just need a way back.</p></div>""",unsafe_allow_html=True)
    a,b,c,d=st.columns(4)
    a.metric('Work remaining',f'{remaining/60:.1f} hrs')
    b.metric('Tasks completed',f'{finished} / {len(tasks)}')
    c.metric('Next 7 days',sum(1 for t in active if t.deadline <= now+timedelta(days=7)))
    d.metric('Plan status','Fits your time' if result['feasible'] else 'Needs adjusting')
    if not result['feasible']:
        st.warning(f"Your current plan can't fit {result['unscheduled_minutes']/60:.1f} hours before their deadlines. That's a capacity issue, not a personal failure. Open Recovery plan for details.")
    left,right=st.columns([1.15,1],gap='large')
    with left:
        st.subheader('Your next step')
        step=next_step(tasks,result)
        with st.container(border=True):
            if step:
                st.markdown(f"**{step['title']}**")
                st.write(f"Study for **{step['minutes']} minutes** · {step['subject']}")
                st.caption(f"Scheduled {step['date'].strftime('%A, %d %b')} · Due {step['deadline'].strftime('%d %b')}")
                if st.button('▶ Start this session',type='primary'):
                    st.session_state['focus_task']=step['task_id'];st.session_state['focus_minutes']=step['minutes']
                if st.session_state.get('focus_task')==step['task_id']:
                    st.info('Focus mode is ready. Work at your pace, then record the session when finished. (No background timer.)')
                    if st.button(f"✓ Log {step['minutes']} minutes completed"):
                        update_session(step)
            elif not active:
                st.success('All caught up. Enjoy the breathing room!')
            else: st.info('No sessions fit your current availability and deadlines. Adjust hours or deadlines in the planner.')
        st.subheader("Today's plan")
        if result['today']:
            for i,s in enumerate(result['today']):
                with st.container(border=True):
                    x,y=st.columns([5,1])
                    x.markdown(f"**{s['title']}** · {s['minutes']} min")
                    x.caption(s['subject'])
                    if y.button('Done',key=f'today_{i}',help='Log this study session'):update_session(s)
            st.caption('Take a 5–10 minute break between longer focus sessions. Breaks are not included in study-hour limits.')
        else:st.info('No study sessions scheduled for today.')
    with right:
        st.subheader('Your comeback in numbers')
        with st.container(border=True):
            percent=(completed_minutes/total*100) if total else 100
            st.markdown(f'### {percent:.0f}% of your workload finished')
            st.progress(percent/100)
            st.caption(f'{completed_minutes/60:.1f} of {total/60:.1f} hours completed')
        st.subheader('Progress by subject')
        subjects=sorted(set(t.subject for t in tasks))
        if subjects:
            for subject in subjects:
                subject_tasks=[t for t in tasks if t.subject==subject]
                total_subject=sum(t.minutes for t in subject_tasks)
                done_subject=sum(t.minutes-t.remaining for t in subject_tasks)
                st.write(f'**{subject}** · {done_subject/60:.1f} / {total_subject/60:.1f} hrs')
                st.progress(done_subject/total_subject)
        else:st.caption('Add a task to see subject progress.')

elif page=='My tasks':
    st.title('Your backlog')
    st.caption('Everything unfinished, in one manageable place.')
    with st.expander('＋ Add a task',expanded=not bool(tasks)):
        with st.form('add_task'):task_form('new_')
    search=st.text_input('Search tasks',placeholder='Search by task or subject...')
    status=st.selectbox('Show',['All','Unfinished','Completed','Overdue'])
    filtered=[t for t in tasks if search.lower() in (t.title+' '+t.subject).lower() and
              (status=='All' or status=='Unfinished' and t.remaining>0 or
               status=='Completed' and t.remaining==0 or status=='Overdue' and t.remaining>0 and t.deadline<now)]
    if not filtered:st.info('No tasks match this view. Add one above or change your filter.')
    for t in filtered:
        with st.container(border=True):
            a,b=st.columns([5,2])
            a.markdown(f"**{t.title}**")
            a.caption(f'{t.subject} · {t.remaining} min remaining · Priority: {"Low Medium High".split()[t.priority-1]}')
            b.caption(('Overdue · ' if t.deadline<now and t.remaining else 'Due ') +t.deadline.strftime('%d %b %Y'))
            b.progress((t.minutes-t.remaining)/t.minutes)
            with st.expander('Edit / progress / delete'):
                with st.form(f'edit_{t.id}'):task_form(f't{t.id}_',t)
                value=st.number_input('Minutes completed',min_value=0,max_value=t.minutes,value=t.done_minutes,step=5,key=f'progress_{t.id}')
                c1,c2=st.columns(2)
                if c1.button('Save progress',key=f'save_{t.id}'):
                    update_progress(db,t.id,value);st.rerun()
                if c2.button('Mark complete' if t.remaining else 'Mark incomplete',key=f'complete_{t.id}'):
                    update_progress(db,t.id,t.minutes if t.remaining else 0);st.rerun()
                if st.checkbox('Enable deletion',key=f'confirm_{t.id}'):
                    if st.button('Delete permanently',key=f'delete_{t.id}'):
                        delete_task(db,t.id);st.rerun()

elif page=='Recovery plan':
    st.title('Your recovery plan')
    st.caption('A realistic schedule built from actual time available—not optimism.')
    if result['feasible']:
        st.success('All remaining tasks can fit by their deadlines within the 90-day planning horizon.')
    else:
        st.error(f"{result['unscheduled_minutes']/60:.1f} hours cannot fit before their deadlines with your current schedule.")
        for s in result['shortfalls']:
            st.write(f"• **{s['title']}**: {s['minutes']} min not scheduled by {s['deadline'].strftime('%d %b %Y')}" + (' (already overdue)' if s['overdue'] else ''))
        st.info('Options: increase available study hours, move flexible deadlines, or prioritize urgent work. Overdue tasks need a new target date to appear in future sessions.')
    st.subheader('Deadline pressure')
    summaries=deadline_summary(tasks,hours,now,unavailable,weekday_hours)
    if summaries:
        st.dataframe(pd.DataFrame([{'Deadline':x['deadline'],'Cumulative work':f"{x['required_minutes']/60:.1f} hr",
             'Capacity until then':f"{x['capacity_minutes']/60:.1f} hr",'Minimum daily average':f"{x['daily_required_hours']:.1f} hr",
             'Capacity gap':f"{x['shortfall_minutes']/60:.1f} hr"} for x in summaries]),hide_index=True,use_container_width=True)
    st.subheader('Scheduled study sessions')
    if result['sessions']:
        grouped=defaultdict(list)
        for s in result['sessions']:grouped[s['date']].append(s)
        for d,items in grouped.items():
            with st.expander(f"{d.strftime('%A, %d %B')} · {sum(s['minutes'] for s in items)} min",expanded=d==now):
                for i,s in enumerate(items):
                    a,b=st.columns([5,1]);a.write(f"{s['title']} · **{s['minutes']} min**")
                    if b.button('Done',key=f'schedule_{d}_{i}'):
                        update_session(s)
    else:st.info('No sessions available. Add tasks or update availability.')

elif page=='Comeback engine':
    st.title('The Comeback Engine')
    st.caption('Missed a few days? Plans can change. Your progress still counts.')
    st.markdown('### Mark days when you could not study')
    chosen=st.date_input('Choose a missed or unavailable day',value=now,max_value=now+timedelta(days=365))
    if st.button('Toggle this day unavailable'):
        toggle_unavailable(db,chosen);st.rerun()
    if unavailable:
        st.write('Currently unavailable: '+', '.join(sorted(x.strftime('%d %b %Y') for x in unavailable)))
    if st.button('↻ Reschedule my backlog',type='primary'):
        st.session_state['replanned']=True
    if st.session_state.get('replanned'):
        st.success('Your plan has been recalculated with all unfinished work and unavailable days.')
    st.metric('Still to fit before deadlines',f"{result['unscheduled_minutes']/60:.1f} hours")
    if not result['feasible']:
        st.warning('The revised schedule is not fully achievable with your current study limits. Below are the exact tasks at risk.')
        st.subheader('Tasks at risk')
        for missing in result['shortfalls']:
            due = missing['deadline'].strftime('%d %b %Y')
            st.error(f"**{missing['title']}** · {missing['minutes']} minutes cannot fit by {due}" + (' · Deadline already passed' if missing['overdue'] else ''))
        st.subheader('Explore realistic recovery options')
        st.caption('These are previews only. Your saved study hours and deadlines will not change unless you edit them.')
        extra = st.slider('Try adding study time per available day (hours)', 0.0, 6.0, 1.0, 0.5, key='recovery_extra')
        alternative = plan(tasks, min(24.0, hours + extra), today=now, days=90,
                           unavailable=unavailable, weekday_hours={k:min(24.0,v + extra) for k,v in weekday_hours.items()})
        st.write(f"**With {extra:g} additional {'hour' if extra == 1 else 'hours'} per day:** {alternative['unscheduled_minutes']/60:.1f} hours still cannot fit.")
        if alternative['feasible']:
            st.success('This amount of additional study time would fit the work within the planning horizon, assuming the same unavailable days.')
        else:
            st.info('If more hours are not realistic, adjust a flexible deadline in My tasks or focus first on the highest-priority tasks. Backlog will recalculate the plan.')
        st.caption('Past-due work must receive a new deadline. No additional study hours can recover a deadline that has already passed.')
    else:
        st.success('Your remaining tasks fit within the currently available study time and deadlines.')
    st.markdown('### Revised upcoming sessions')
    if result['sessions']:st.dataframe(session_rows(result['sessions'][:35]),hide_index=True,use_container_width=True)
    else:st.info('No future sessions available under these constraints.')

else:
    st.title('Make Backlog yours')
    st.caption('Your time budget matters more than a perfect-looking calendar.')
    st.subheader('Weekly availability')
    st.write('Set a different study-hour limit for each weekday. Leave unchecked to use your default daily hours.')
    names=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    with st.form('weekdays'):
        updates={}
        for i,name in enumerate(names):
            a,b=st.columns([2,2])
            existing=get_setting(db,f'weekday_{i}','')
            use=a.checkbox(f'Custom {name}',value=existing!='',key=f'use_{i}')
            value=b.number_input(f'{name} hours',min_value=0.0,max_value=24.0,
                                  value=float(existing) if existing else hours,step=0.5,key=f'hours_{i}')
            updates[i]=str(value) if use else ''
        if st.form_submit_button('Save weekly availability',type='primary'):
            for i,value in updates.items():set_setting(db,f'weekday_{i}',value)
            st.rerun()
    st.divider()
    st.subheader('About this prototype')
    st.write('Backlog is an offline-first single-workspace demo. Core planning is deterministic and stores data in a local SQLite file. It does not use AI, payments, logins, notifications or a calendar sync.')
