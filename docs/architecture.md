# Architecture

Answer each of these, in your own words, once the system has taken real shape.

- What are the moving pieces, and how do they talk to each other?
 > It's one Django app, no separate frontend or API layer. The config holds the settings and routing. Accounts holds the custom User model with email login and the editor or writer role, plus the account creation flow. Sections holds the Section model and a services file that decides which sections a user can see. Articles is the biggest piece, it has the Article model, the append only ArticleEvent timeline, and a services file where every lifecycle transition, search query and dashboard number actually lives. Views stay thin, they call a services function and render or redirect, never touching article.status directly. Templates are server rendered with Bootstrap and a bit of plain JS. Postgres runs in production, SQLite locally.
Apps mostly stay in their own lane. The one cross app dependency is articles/services.py importing from sections/services.py to check if a writer is assigned to a section before letting them create an article there.

- Where does each piece run?
 >Everything runs as one process on render, a single web service running gunicorn, with Django rendering the html and WhiteNoise serving static files. The database is a separate Supabase Postgres . No queue, no cache, no background worker, everything happens inside one request and response, including the overdue alert check which just recalculates on every page load.

- What is the request path for one representative user action, end to end?
 >Take an editor approving an article that's in review. The browser posts a plain form to /articles/pk/approve/. That routes to ApproveView, which requires login and looks the article up through visible_articles so an article a user can't see just 404s instead of leaking that it exists. The view then calls services.approve, which is where the real rule sits, not an editor, not currently in review, or the actor being the article's own author all raise an error. If it passes, status flips to approved and an ArticleEvent gets logged, all inside one atomic transaction. The view catches any error as a flash message, redirects back to the article detail page either way, and the page re-renders with the new status and timeline entry. Every other lifecycle action follows this same shape, thin view, one services call doing the real check and the real change, log an event, redirect.
 
- What did you decide *not* to build, and why?
 >No public self signup, account creation is editor only, see decisions.md for the reasoning. No background job runner, overdue alerts are just a plain query at request time rather than a scheduled task, since the brief only needs the alert to show up. No separate frontend framework, since the UI is mostly forms and lists, not something that needed to feel like a single page app. No full text search, just an icontains filter for now, see schema.md for what that costs at scale. No caching layer either, every page hits the database directly, which wasn't worth solving given the amount of demo data and free tier hosting.
