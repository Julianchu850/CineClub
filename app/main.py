from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from .database import init_db
from fastapi import Form
from .database import SessionLocal
from .models import Movie, Rating, FamilyMember
from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.responses import RedirectResponse
from .tmdb import search_movie
from .tmdb import get_movie_details
from .tmdb import get_person_imdb_url
from datetime import datetime
from collections import defaultdict, OrderedDict
from fastapi import Query

def stars(avg):
    if avg is None:
        return ""
    full = int(avg)
    half = 1 if (avg - full) >= 0.5 else 0
    empty = 5 - full - half
    return "★" * full + ("½" if half else "") + "☆" * empty


init_db()

app = FastAPI()

templates = Jinja2Templates(directory="app/templates")

FAMILY_MEMBERS = [
    "Julian",
    "Cata",
    "Leo",
    "Marco",
    "Sofi",
    "Chata",
    "Lety",
    "Guero",
    "Roci",
    "Pepe",
    "Mau",
    "Coqui",
    "Lalo",
    "Rafa",
    "Luly",
]



@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str = "", sort: str = "rating"):
    db = SessionLocal()

    # Movie of the Week
    weekly_movie = db.query(Movie).filter(Movie.status == "weekly").first()

    weekly_details = None
    director = None
    if weekly_movie and weekly_movie.tmdb_id:
        weekly_details = get_movie_details(weekly_movie.tmdb_id)
        # if you already compute director elsewhere, keep your existing method
        # director = get_director(weekly_movie.tmdb_id)

    # Only show history from "seen"
    seen_movies = db.query(Movie).filter(Movie.status == "seen").all()

    movie_data = []
    top_movie = None
    top_average = -1

    for movie in seen_movies:
        # Search filter
        if q and q.lower() not in (movie.title or "").lower():
            continue

        ratings = db.query(Rating).filter(Rating.movie_id == movie.id).all()
        avg = round(sum(r.score for r in ratings) / len(ratings), 2) if ratings else None

        if avg is not None and avg > top_average:
            top_average = avg
            top_movie = movie

        details = get_movie_details(movie.tmdb_id) if movie.tmdb_id else None

        movie_data.append({
            "movie": movie,
            "average": avg,     # numeric for home cards
            "details": details
        })

    # Sorting
    if sort == "date":
        movie_data.sort(key=lambda x: x["movie"].date_watched or "", reverse=True)
    else:
        movie_data.sort(key=lambda x: (x["average"] is None, -(x["average"] or 0)))

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "weekly_movie": weekly_movie,
            "weekly_details": weekly_details,
            "director": director,
            "movie_data": movie_data,
            "top_movie": top_movie,
            "top_average": top_average,
            "sort": sort,
            "q": q,
        }
    )






@app.post("/add_movie")
def add_movie(title: str = Form(...), date_watched: str = Form(...)):
    db = SessionLocal()

    movie = Movie(title=title, date_watched=date_watched)
    db.add(movie)
    db.commit()

    return RedirectResponse(url="/", status_code=303)

@app.get("/movie/{movie_id}", response_class=HTMLResponse)
def movie_detail(movie_id: int, request: Request):
    db = SessionLocal()

    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    movie_details = None

    if movie and movie.tmdb_id:
        movie_details = get_movie_details(movie.tmdb_id)

    director = None
    director_id = None
    top_cast = []

    if movie_details and "credits" in movie_details:
        crew = movie_details["credits"].get("crew", [])
        for c in crew:
            if c.get("job") == "Director":
                director = c.get("name")
                director_id = c.get("id")
                break

    # first 5 cast members
    top_cast = []

    if movie_details and movie_details.get("credits"):
        cast = movie_details["credits"].get("cast", [])

        seen_ids = set()
        for a in cast:
            pid = a.get("id")
            if not pid:
                continue
            if pid in seen_ids:
                continue
            seen_ids.add(pid)
            top_cast.append(a)
            if len(top_cast) == 5:
                break



    ratings = db.query(Rating).filter(Rating.movie_id == movie_id).all()

    avg_rating = None
    highest_rating = None
    lowest_rating = None

    if ratings:
        avg_rating = round(
            sum(r.score for r in ratings) / len(ratings),
            2
        )

        highest_rating = max(ratings, key=lambda r: r.score)
        lowest_rating = min(ratings, key=lambda r: r.score)

    return templates.TemplateResponse(
        "movie.html",
        {
            "request": request,
            "movie": movie,
            "ratings": ratings,
            "avg_rating": avg_rating,
            "highest_rating": highest_rating,
            "lowest_rating": lowest_rating,
            "members": FAMILY_MEMBERS,
            "movie_details": movie_details,
            "director": director,
            "director_id": director_id,
            "top_cast": top_cast,

        }
    )


from fastapi.responses import RedirectResponse

@app.post("/rate_movie/{movie_id}")
def rate_movie(
    movie_id: int,
    member_name: str = Form(...),
    score: float = Form(...)
):
    db = SessionLocal()

    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        return RedirectResponse(url="/", status_code=303)

    # lock if not weekly
    if movie.status != "weekly":
        return RedirectResponse(url=f"/movie/{movie_id}", status_code=303)

    # prevent duplicate rating by same member
    existing = db.query(Rating).filter(
        Rating.movie_id == movie_id,
        Rating.member_name == member_name
    ).first()

    if existing:
        existing.score = score  # update instead of blocking
    else:
        db.add(Rating(movie_id=movie_id, member_name=member_name, score=score))

    db.commit()
    return RedirectResponse(url=f"/movie/{movie_id}", status_code=303)




@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, q: str = "", status: str = "all", sort: str = "date_desc"):
    db = SessionLocal()

    members = db.query(FamilyMember).order_by(FamilyMember.name).all()

    query = db.query(Movie)

    if q:
        query = query.filter(Movie.title.ilike(f"%{q}%"))

    if status != "all":
        query = query.filter(Movie.status == status)

    if sort == "date_asc":
        query = query.order_by(Movie.date_watched.asc())
    elif sort == "title":
        query = query.order_by(Movie.title.asc())
    else:
        query = query.order_by(Movie.date_watched.desc())

    movies = query.all()

    return templates.TemplateResponse(
        "admin.html",
        {"request": request, "members": members, "movies": movies, "q": q, "status": status, "sort": sort}
    )





@app.get("/admin/search", response_class=HTMLResponse)
def admin_search(request: Request, query: str):
    results = search_movie(query)

    return templates.TemplateResponse(
        "admin_results.html",
        {
            "request": request,
            "results": results
        }
    )

@app.post("/admin/add_movie_tmdb")
def add_movie_tmdb(
    tmdb_id: int = Form(...),
    title: str = Form(...),
    date_watched: str = Form(...),
    status: str = Form(...)
):
    db = SessionLocal()

    # prevent duplicates
    existing = db.query(Movie).filter(Movie.tmdb_id == tmdb_id).first()
    if existing:
        return RedirectResponse(url="/admin?error=MovieAlreadyExists", status_code=303)

    # if setting weekly, demote any existing weekly
    if status == "weekly":
        current_weekly = db.query(Movie).filter(Movie.status == "weekly").first()
        if current_weekly:
            current_weekly.status = "seen"
            db.commit()

    new_movie = Movie(
        tmdb_id=tmdb_id,
        title=title,
        date_watched=date_watched,
        status=status
    )
    db.add(new_movie)
    db.commit()

    return RedirectResponse(url="/", status_code=303)

@app.post("/admin/delete_movie/{movie_id}")
def delete_movie(movie_id: int):
    db = SessionLocal()

    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        return RedirectResponse(url="/admin", status_code=303)

    # delete ratings first (or add cascade)
    db.query(Rating).filter(Rating.movie_id == movie_id).delete()
    db.delete(movie)
    db.commit()

    return RedirectResponse(url="/admin", status_code=303)




@app.get("/movie/{movie_id}/rate", response_class=HTMLResponse)
def rate_page(movie_id: int, request: Request):
    db = SessionLocal()

    movie = db.query(Movie).filter(Movie.id == movie_id).first()

    return templates.TemplateResponse(
        "rate_movie.html",
        {
            "request": request,
            "movie": movie,
            "members": db.query(FamilyMember).order_by(FamilyMember.name).all()
        }
    )

@app.post("/admin/add_member")
def add_member(member_name: str = Form(...)):
    db = SessionLocal()
    exists = db.query(FamilyMember).filter(FamilyMember.name == member_name).first()
    if not exists:
        db.add(FamilyMember(name=member_name))
        db.commit()
    return RedirectResponse("/admin", status_code=303)

@app.get("/admin/confirm_movie", response_class=HTMLResponse)
def admin_confirm_movie(
    request: Request,
    tmdb_id: int,
    title: str,
    year: str = "",
    poster_path: str = ""
):
    return templates.TemplateResponse(
        "admin_confirm.html",
        {
            "request": request,
            "tmdb_id": tmdb_id,
            "title": title,
            "year": year,
            "poster_path": poster_path
        }
    )

@app.post("/admin/update_movie/{movie_id}")
def update_movie(
    movie_id: int,
    date_watched: str = Form(...),
    status: str = Form(...)
):
    db = SessionLocal()

    movie = db.query(Movie).filter(Movie.id == movie_id).first()
    if not movie:
        return RedirectResponse(url="/admin", status_code=303)

    # If setting this movie as weekly, demote any other weekly movie
    if status == "weekly":
        other_weekly = db.query(Movie).filter(Movie.status == "weekly", Movie.id != movie_id).first()
        if other_weekly:
            other_weekly.status = "seen"

    movie.date_watched = date_watched
    movie.status = status
    db.commit()

    return RedirectResponse(url="/admin", status_code=303)



@app.get("/diary", response_class=HTMLResponse)
def diary(request: Request, start: str = "", end: str = ""):
    db = SessionLocal()

    query = db.query(Movie)

    # filter by date range (Movie.date_watched is YYYY-MM-DD)
    if start:
        query = query.filter(Movie.date_watched >= start)
    if end:
        query = query.filter(Movie.date_watched <= end)

    movies = query.all()

    movie_data = []
    for movie in movies:
        ratings = db.query(Rating).filter(Rating.movie_id == movie.id).all()
        avg = round(sum(r.score for r in ratings) / len(ratings), 2) if ratings else None

        details = None
        if movie.tmdb_id:
            details = get_movie_details(movie.tmdb_id)

        movie_data.append({
            "movie": movie,
            "average": avg,
            "stars": stars(avg),  # your working helper
            "details": details
        })

    # sort by date desc for diary
    movie_data.sort(key=lambda x: x["movie"].date_watched or "", reverse=True)

    # group by month/year
    groups = defaultdict(list)
    for item in movie_data:
        ds = item["movie"].date_watched
        key = datetime.strptime(ds, "%Y-%m-%d").strftime("%Y-%m") if ds else "Unknown"
        groups[key].append(item)

    ordered_keys = sorted([k for k in groups.keys() if k != "Unknown"], reverse=True)
    if "Unknown" in groups:
        ordered_keys.append("Unknown")

    diary_groups = [(k, groups[k]) for k in ordered_keys]

    return templates.TemplateResponse(
        "diary.html",
        {
            "request": request,
            "diary_groups": diary_groups,
            "start": start,
            "end": end
        }
    )

@app.get("/person/imdb/{person_id}")
def person_imdb_redirect(person_id: int):
    url = get_person_imdb_url(person_id)
    return RedirectResponse(url=url or "https://www.imdb.com/", status_code=302)
